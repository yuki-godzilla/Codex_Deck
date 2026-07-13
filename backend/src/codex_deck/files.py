"""Read-only workspace file access with deny and symlink boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .workspaces import Workspace, WorkspaceAccessError, WorkspaceStore


class FileAccessError(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class FileEntry:
    path: str
    name: str
    kind: str
    size_bytes: int | None


@dataclass(frozen=True, slots=True)
class TextFile:
    path: str
    content: str
    size_bytes: int
    line_count: int


class ReadOnlyFileService:
    """Never writes, follows only in-root paths, and blocks secret-like files."""

    def __init__(self, workspaces: WorkspaceStore, *, maximum_file_bytes: int = 1_000_000) -> None:
        self._workspaces = workspaces
        self._maximum_file_bytes = maximum_file_bytes

    def list_directory(self, workspace_id: str, relative_path: str = "") -> list[FileEntry]:
        workspace = self._workspaces.get(workspace_id)
        directory = self._resolve(workspace, relative_path)
        if not directory.is_dir():
            raise ValueError("Requested path is not a directory")
        entries: list[FileEntry] = []
        for child in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold())):
            relative = child.relative_to(workspace.root_path).as_posix()
            if self._is_denied(relative):
                continue
            if child.is_symlink():
                # Symlinks are listed only if their resolved target remains inside
                # the workspace; the caller cannot use this to traverse outward.
                try:
                    self._resolve(workspace, relative)
                except FileAccessError:
                    continue
                kind = "symlink"
                size = None
            elif child.is_dir():
                kind = "directory"
                size = None
            else:
                kind = "file"
                size = child.stat().st_size
            entries.append(FileEntry(path=relative, name=child.name, kind=kind, size_bytes=size))
        return entries

    def read_text(self, workspace_id: str, relative_path: str) -> TextFile:
        workspace = self._workspaces.get(workspace_id)
        path = self._resolve(workspace, relative_path)
        if path.is_dir():
            raise ValueError("Requested path is a directory")
        size = path.stat().st_size
        if size > self._maximum_file_bytes:
            raise ValueError("File exceeds the read-only preview limit")
        raw = path.read_bytes()
        if b"\x00" in raw:
            raise ValueError("Binary files cannot be previewed")
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Only UTF-8 text files can be previewed") from error
        return TextFile(
            path=relative_path.replace("\\", "/"),
            content=content,
            size_bytes=size,
            line_count=len(content.splitlines()),
        )

    def _resolve(self, workspace: Workspace, relative_path: str) -> Path:
        normalized = PurePosixPath(relative_path.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts or self._is_denied(normalized.as_posix()):
            raise FileAccessError("Path is not allowed for browser file access")
        try:
            candidate = (workspace.root_path / Path(*normalized.parts)).resolve(strict=True)
        except FileNotFoundError as error:
            raise FileAccessError("Path does not exist") from error
        if not candidate.is_relative_to(workspace.root_path):
            raise FileAccessError("Path resolves outside the workspace")
        return candidate

    @staticmethod
    def _is_denied(relative_path: str) -> bool:
        parts = [part.casefold() for part in PurePosixPath(relative_path).parts]
        if any(part in {".git", ".ssh", ".codex", ".claude"} for part in parts):
            return True
        filename = parts[-1] if parts else ""
        return (
            filename == ".env"
            or filename.startswith(".env.")
            or filename in {"id_rsa", "id_ed25519", "credentials", "credentials.json"}
            or filename.endswith((".pem", ".key", ".p12", ".pfx"))
        )
