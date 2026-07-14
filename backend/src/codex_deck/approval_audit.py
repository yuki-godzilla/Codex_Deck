"""Deck-owned, minimal audit trail for explicit approval decisions."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from threading import Lock

from .approvals import PendingApproval

@dataclass(frozen=True, slots=True)
class ApprovalAuditRecord:
    audit_id: int; request_id: int; kind: str; thread_id: str; turn_id: str; item_id: str; decision: str; decided_at: datetime

class SqliteApprovalAuditStore:
    def __init__(self, database_path: str | Path) -> None:
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row; self._lock = Lock()
        with self._connection:
            self._connection.execute("""CREATE TABLE IF NOT EXISTS deck_approval_audit (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER NOT NULL, kind TEXT NOT NULL,
                thread_id TEXT NOT NULL, turn_id TEXT NOT NULL, item_id TEXT NOT NULL,
                decision TEXT NOT NULL, decided_at TEXT NOT NULL)""")

    def append(self, approval: PendingApproval, decision: str) -> ApprovalAuditRecord:
        decided_at = datetime.now(UTC)
        with self._lock, self._connection:
            cursor = self._connection.execute("""INSERT INTO deck_approval_audit
                (request_id, kind, thread_id, turn_id, item_id, decision, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (approval.request_id, approval.kind, approval.thread_id, approval.turn_id, approval.item_id, decision, decided_at.isoformat()))
        return ApprovalAuditRecord(cursor.lastrowid, approval.request_id, approval.kind, approval.thread_id, approval.turn_id, approval.item_id, decision, decided_at)

    def list(self, *, limit: int = 100) -> list[ApprovalAuditRecord]:
        with self._lock:
            rows = self._connection.execute("SELECT * FROM deck_approval_audit ORDER BY audit_id DESC LIMIT ?", (limit,)).fetchall()
        return [ApprovalAuditRecord(row["audit_id"], row["request_id"], row["kind"], row["thread_id"], row["turn_id"], row["item_id"], row["decision"], datetime.fromisoformat(row["decided_at"])) for row in rows]

    def close(self) -> None:
        with self._lock: self._connection.close()
