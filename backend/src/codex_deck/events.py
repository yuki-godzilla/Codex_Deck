"""Deck-owned event sequencing for browser reconnects.

Codex Thread and Item remain authoritative.  These events only represent what
Deck received and the monotonically increasing cursor a browser can replay.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any


@dataclass(frozen=True, slots=True)
class DeckEvent:
    event_id: int
    received_at: datetime
    workspace_id: str
    event_type: str
    thread_id: str | None
    turn_id: str | None
    payload: dict[str, Any]


class EventStore:
    """Bounded in-memory event store; SQLite persistence is a later slice."""

    def __init__(self, *, maximum_events: int = 2_000) -> None:
        if maximum_events < 1:
            raise ValueError("maximum_events must be positive")
        self._events: deque[DeckEvent] = deque(maxlen=maximum_events)
        self._next_event_id = 1
        self._lock = Lock()

    def append(
        self,
        *,
        workspace_id: str,
        event_type: str,
        thread_id: str | None = None,
        turn_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> DeckEvent:
        if not workspace_id or not event_type:
            raise ValueError("workspace_id and event_type are required")
        with self._lock:
            event = DeckEvent(
                event_id=self._next_event_id,
                received_at=datetime.now(UTC),
                workspace_id=workspace_id,
                event_type=event_type,
                thread_id=thread_id,
                turn_id=turn_id,
                payload=dict(payload or {}),
            )
            self._next_event_id += 1
            self._events.append(event)
            return event

    def after(self, event_id: int, *, workspace_id: str | None = None, limit: int = 100) -> list[DeckEvent]:
        if event_id < 0 or not 1 <= limit <= 200:
            raise ValueError("event_id must be non-negative and limit must be 1 through 200")
        with self._lock:
            return [
                event for event in self._events
                if event.event_id > event_id and (workspace_id is None or event.workspace_id == workspace_id)
            ][:limit]
