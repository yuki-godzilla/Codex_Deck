"""Read-only Git status and diff access for registered workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import os
import subprocess

from .files import ReadOnlyFileService
from .workspaces import Workspace, WorkspaceStore


class GitAccessError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GitFileStatus:
    path: str
    index_status: str
    worktree_status: str
    original_path: str | None = None


@dataclass(frozen=True, slots=True)
class GitStatus:
    is_repository: bool
    branch: str | None
    ahead: int
    behind: int
    staged_count: int
    unstaged_count: int
    untracked_count: int
    remotes: list[str]
    entries: list[GitFileStatus]


@dataclass(frozen=True, slots=True)
class GitDiff:
    path: str
    mode: str
    content: str
    truncated: bool
    is_binary: bool
    offset: int
    next_offset: int | None
    total_characters: int


class ReadOnlyGitService:
    """Runs only fixed read-only Git commands with non-interactive settings."""

    def __init__(self, workspaces: WorkspaceStore, *, maximum_diff_bytes: int = 1_000_000) -> None:
        self._workspaces = workspaces
        self._maximum_diff_bytes = maximum_diff_bytes

    def status(self, workspace_id: str) -> GitStatus:
        workspace = self._workspaces.get(workspace_id)
        if not self._is_repository(workspace):
            return GitStatus(False, None, 0, 0, 0, 0, 0, [], [])
        output = self._run(workspace, "status", "--porcelain=v1", "--branch", "-z")
        branch: str | None = None
        ahead = behind = staged = unstaged = untracked = 0
        entries: list[GitFileStatus] = []
        records = output.decode("utf-8", errors="replace").split("\0")
        index = 0
        while index < len(records):
            record = records[index]
            index += 1
            if not record:
                continue
            if record.startswith("## "):
                branch, ahead, behind = _parse_branch(record[3:])
                continue
            if len(record) < 4:
                continue
            index_status, worktree_status, path = record[0], record[1], record[3:]
            # Rename/copy records include a second NUL-delimited original path.
            original_path: str | None = None
            if index_status in {"R", "C"} and index < len(records):
                original_path = records[index]
                index += 1
            if not self._is_allowed_path(path):
                continue
            if original_path is not None and not self._is_allowed_path(original_path):
                original_path = None
            if index_status == "?":
                untracked += 1
            else:
                staged += int(index_status not in {" ", "?"})
                unstaged += int(worktree_status not in {" ", "?"})
            entries.append(GitFileStatus(path=path, index_status=index_status, worktree_status=worktree_status, original_path=original_path))
        remotes = [line for line in self._run(workspace, "remote").decode("utf-8", errors="replace").splitlines() if line]
        return GitStatus(True, branch, ahead, behind, staged, unstaged, untracked, remotes, entries)

    def diff(self, workspace_id: str, *, relative_path: str, staged: bool = False, offset: int = 0, limit: int | None = None) -> GitDiff:
        workspace = self._workspaces.get(workspace_id)
        if not self._is_repository(workspace):
            raise GitAccessError("Workspace is not a Git repository")
        normalized = _validate_path(relative_path)
        if offset < 0:
            raise GitAccessError("Diff offset must not be negative")
        chunk_size = self._maximum_diff_bytes if limit is None else min(limit, self._maximum_diff_bytes)
        if chunk_size < 1:
            raise GitAccessError("Diff limit must be positive")
        arguments = ["diff", "--no-ext-diff", "--no-color", "--find-renames", "--unified=3"]
        if staged:
            arguments.append("--cached")
        arguments.extend(["--", normalized])
        raw = self._run(workspace, *arguments)
        content = raw.decode("utf-8", errors="replace")
        total_characters = len(content)
        chunk = content[offset:offset + chunk_size]
        next_offset = offset + len(chunk) if offset + len(chunk) < total_characters else None
        is_binary = b"Binary files" in raw or b"GIT binary patch" in raw
        return GitDiff(
            path=normalized,
            mode="staged" if staged else "unstaged",
            content=chunk,
            truncated=next_offset is not None,
            is_binary=is_binary,
            offset=offset,
            next_offset=next_offset,
            total_characters=total_characters,
        )

    def _is_repository(self, workspace: Workspace) -> bool:
        completed = self._run_completed(workspace, "rev-parse", "--is-inside-work-tree", check=False)
        return completed.returncode == 0 and completed.stdout.strip() == b"true"

    def _run(self, workspace: Workspace, *arguments: str) -> bytes:
        completed = self._run_completed(workspace, *arguments, check=True)
        return completed.stdout

    @staticmethod
    def _run_completed(workspace: Workspace, *arguments: str, check: bool) -> subprocess.CompletedProcess[bytes]:
        environment = {
            **os.environ,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
        completed = subprocess.run(
            ["git", "-C", str(workspace.root_path), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            env=environment,
        )
        if check and completed.returncode != 0:
            raise GitAccessError("Git read operation failed")
        return completed

    @staticmethod
    def _is_allowed_path(path: str) -> bool:
        try:
            _validate_path(path)
        except GitAccessError:
            return False
        return True


def _validate_path(path: str) -> str:
    normalized = PurePosixPath(path.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts or ReadOnlyFileService._is_denied(normalized.as_posix()):
        raise GitAccessError("Git path is not allowed for browser access")
    return normalized.as_posix()


def _parse_branch(value: str) -> tuple[str | None, int, int]:
    if value.startswith("HEAD (no branch)"):
        return None, 0, 0
    branch, separator, tracking = value.partition("...")
    ahead = behind = 0
    if separator and "[" in tracking:
        details = tracking.partition("[")[2].rstrip("]")
        for part in details.split(", "):
            if part.startswith("ahead "):
                ahead = int(part.removeprefix("ahead "))
            elif part.startswith("behind "):
                behind = int(part.removeprefix("behind "))
    return branch, ahead, behind
