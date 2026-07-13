"""Explicit handling of stable App Server command/file approval requests."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Callable

APPROVAL_METHODS = {
    "item/commandExecution/requestApproval": "command",
    "item/fileChange/requestApproval": "fileChange",
}
DECISIONS = {"accept", "acceptForSession", "decline", "cancel"}


@dataclass(frozen=True, slots=True)
class PendingApproval:
    request_id: int
    kind: str
    thread_id: str
    turn_id: str
    item_id: str
    reason: str | None
    command: str | None
    cwd: str | None
    received_at: datetime


class ApprovalBroker:
    """Holds pending approvals until a human sends an official decision."""

    def __init__(self, responder: Callable[[int, dict[str, str]], None]) -> None:
        self._responder = responder
        self._pending: dict[int, PendingApproval] = {}
        self._lock = Lock()

    def receive(self, message: dict[str, Any]) -> PendingApproval | None:
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params")
        if method not in APPROVAL_METHODS or not isinstance(request_id, int) or not isinstance(params, dict):
            return None
        required = ("threadId", "turnId", "itemId")
        if not all(isinstance(params.get(key), str) and params[key] for key in required):
            return None
        approval = PendingApproval(
            request_id=request_id,
            kind=APPROVAL_METHODS[method],
            thread_id=params["threadId"], turn_id=params["turnId"], item_id=params["itemId"],
            reason=_safe_text(params.get("reason")),
            command=_safe_text(params.get("command")),
            cwd=_safe_text(params.get("cwd")),
            received_at=datetime.now(UTC),
        )
        with self._lock:
            self._pending[request_id] = approval
        return approval

    def list(self) -> list[PendingApproval]:
        with self._lock:
            return sorted(self._pending.values(), key=lambda item: item.received_at)

    def decide(self, request_id: int, decision: str) -> PendingApproval:
        if decision not in DECISIONS:
            raise ValueError("Decision is not supported by the current Deck approval UI")
        with self._lock:
            approval = self._pending.pop(request_id, None)
        if approval is None:
            raise KeyError(request_id)
        self._responder(request_id, {"decision": decision})
        return approval


def _safe_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.replace("\n", " ")[:1000]
