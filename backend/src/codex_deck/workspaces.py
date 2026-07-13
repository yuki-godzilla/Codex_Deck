"""Persistent, allowlisted workspace registration.

Workspace paths are local administrative data.  Browser-facing responses expose
only the registration ID and display name, never the absolute local path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from threading import Lock
from uuid import uuid4


class WorkspaceAccessError(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class Workspace:
    workspace_id: str
    display_name: str
    root_path: Path
    created_at: datetime


class WorkspaceStore:
    """Workspace catalog restricted to explicitly configured allowed roots."""

    def __init__(self, database_path: str | Path, *, allowed_roots: tuple[Path, ...]) -> None:
        self._allowed_roots = tuple(root.resolve(strict=True) for root in allowed_roots)
        if any(not root.is_dir() for root in self._allowed_roots):
            raise ValueError("Every allowed root must be an existing directory")
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = Lock()
        with self._connection:
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS deck_workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    root_path TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
            """)

    def register(self, root_path: str | Path, *, display_name: str | None = None) -> Workspace:
        resolved = Path(root_path).resolve(strict=True)
        if not resolved.is_dir():
            raise ValueError("A workspace must be a directory")
        if not self._is_allowed(resolved):
            raise WorkspaceAccessError("Workspace is outside the configured allowed roots")
        created_at = datetime.now(UTC)
        workspace = Workspace(
            workspace_id=str(uuid4()),
            display_name=display_name or resolved.name,
            root_path=resolved,
            created_at=created_at,
        )
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT workspace_id, display_name, root_path, created_at FROM deck_workspaces WHERE root_path = ?",
                (str(resolved),),
            ).fetchone()
            if existing is not None:
                return _workspace_from_row(existing)
            self._connection.execute(
                "INSERT INTO deck_workspaces (workspace_id, display_name, root_path, created_at) VALUES (?, ?, ?, ?)",
                (workspace.workspace_id, workspace.display_name, str(workspace.root_path), workspace.created_at.isoformat()),
            )
        return workspace

    def get(self, workspace_id: str) -> Workspace:
        with self._lock:
            row = self._connection.execute(
                "SELECT workspace_id, display_name, root_path, created_at FROM deck_workspaces WHERE workspace_id = ?",
                (workspace_id,),
            ).fetchone()
        if row is None:
            raise KeyError(workspace_id)
        return _workspace_from_row(row)

    def list(self) -> list[Workspace]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT workspace_id, display_name, root_path, created_at FROM deck_workspaces ORDER BY display_name COLLATE NOCASE",
            ).fetchall()
        return [_workspace_from_row(row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _is_allowed(self, candidate: Path) -> bool:
        return any(candidate.is_relative_to(root) for root in self._allowed_roots)


def _workspace_from_row(row: sqlite3.Row) -> Workspace:
    return Workspace(
        workspace_id=row["workspace_id"],
        display_name=row["display_name"],
        root_path=Path(row["root_path"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )
