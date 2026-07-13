"""Deck-owned event sequencing for browser reconnects.

Codex Thread and Item remain authoritative.  These events only represent what
Deck received and the monotonically increasing cursor a browser can replay.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class DeckEvent:
    event_id: int
    received_at: datetime
    workspace_id: str
    event_type: str
    thread_id: str | None
    turn_id: str | None
    payload: dict[str, Any]


EventSubscriber = Callable[[DeckEvent], None]
Unsubscribe = Callable[[], None]


class EventRepository(Protocol):
    def append(
        self,
        *,
        workspace_id: str,
        event_type: str,
        thread_id: str | None = None,
        turn_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> DeckEvent: ...

    def after(self, event_id: int, *, workspace_id: str | None = None, limit: int = 100) -> list[DeckEvent]: ...

    def subscribe(self, subscriber: EventSubscriber) -> Unsubscribe: ...


class EventStore:
    """Bounded in-memory event store for deterministic tests."""

    def __init__(self, *, maximum_events: int = 2_000) -> None:
        if maximum_events < 1:
            raise ValueError("maximum_events must be positive")
        self._events: deque[DeckEvent] = deque(maxlen=maximum_events)
        self._next_event_id = 1
        self._lock = Lock()
        self._subscribers: dict[int, EventSubscriber] = {}
        self._next_subscriber_id = 1

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
            subscribers = list(self._subscribers.values())
        _notify(subscribers, event)
        return event

    def after(self, event_id: int, *, workspace_id: str | None = None, limit: int = 100) -> list[DeckEvent]:
        if event_id < 0 or not 1 <= limit <= 200:
            raise ValueError("event_id must be non-negative and limit must be 1 through 200")
        with self._lock:
            return [
                event for event in self._events
                if event.event_id > event_id and (workspace_id is None or event.workspace_id == workspace_id)
            ][:limit]

    def subscribe(self, subscriber: EventSubscriber) -> Unsubscribe:
        with self._lock:
            subscriber_id = self._next_subscriber_id
            self._next_subscriber_id += 1
            self._subscribers[subscriber_id] = subscriber

        def unsubscribe() -> None:
            with self._lock:
                self._subscribers.pop(subscriber_id, None)

        return unsubscribe


class SqliteEventStore:
    """SQLite event store for restart-safe HTTP replay and WebSocket delivery."""

    def __init__(self, database_path: str | Path) -> None:
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = Lock()
        self._subscribers: dict[int, EventSubscriber] = {}
        self._next_subscriber_id = 1
        with self._connection:
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS deck_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    received_at TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    thread_id TEXT,
                    turn_id TEXT,
                    payload_json TEXT NOT NULL
                )
            """)
            self._connection.execute("""
                CREATE INDEX IF NOT EXISTS deck_events_workspace_event_id
                ON deck_events(workspace_id, event_id)
            """)

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
        received_at = datetime.now(UTC)
        payload_copy = dict(payload or {})
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """INSERT INTO deck_events
                (received_at, workspace_id, event_type, thread_id, turn_id, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (received_at.isoformat(), workspace_id, event_type, thread_id, turn_id, json.dumps(payload_copy)),
            )
            event = DeckEvent(
                event_id=cursor.lastrowid,
                received_at=received_at,
                workspace_id=workspace_id,
                event_type=event_type,
                thread_id=thread_id,
                turn_id=turn_id,
                payload=payload_copy,
            )
            subscribers = list(self._subscribers.values())
        _notify(subscribers, event)
        return event

    def after(self, event_id: int, *, workspace_id: str | None = None, limit: int = 100) -> list[DeckEvent]:
        if event_id < 0 or not 1 <= limit <= 200:
            raise ValueError("event_id must be non-negative and limit must be 1 through 200")
        query = """SELECT event_id, received_at, workspace_id, event_type, thread_id, turn_id, payload_json
                   FROM deck_events WHERE event_id > ?"""
        parameters: list[object] = [event_id]
        if workspace_id is not None:
            query += " AND workspace_id = ?"
            parameters.append(workspace_id)
        query += " ORDER BY event_id ASC LIMIT ?"
        parameters.append(limit)
        with self._lock:
            rows = self._connection.execute(query, parameters).fetchall()
        return [_event_from_row(row) for row in rows]

    def subscribe(self, subscriber: EventSubscriber) -> Unsubscribe:
        with self._lock:
            subscriber_id = self._next_subscriber_id
            self._next_subscriber_id += 1
            self._subscribers[subscriber_id] = subscriber

        def unsubscribe() -> None:
            with self._lock:
                self._subscribers.pop(subscriber_id, None)

        return unsubscribe

    def close(self) -> None:
        with self._lock:
            self._connection.close()
            self._subscribers.clear()


def _event_from_row(row: sqlite3.Row) -> DeckEvent:
    return DeckEvent(
        event_id=row["event_id"],
        received_at=datetime.fromisoformat(row["received_at"]),
        workspace_id=row["workspace_id"],
        event_type=row["event_type"],
        thread_id=row["thread_id"],
        turn_id=row["turn_id"],
        payload=json.loads(row["payload_json"]),
    )


def _notify(subscribers: list[EventSubscriber], event: DeckEvent) -> None:
    for subscriber in subscribers:
        try:
            subscriber(event)
        except Exception:
            # A disconnected browser must not roll back a persisted Deck event.
            continue
