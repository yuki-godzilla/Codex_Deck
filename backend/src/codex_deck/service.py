"""Application service composition independent of HTTP and the App Server process."""

from __future__ import annotations

from .bridge import Bridge, StartWorkRequest
from .events import DeckEvent, EventRepository, EventSubscriber, Unsubscribe
from .scheduler import ActiveWork, Scheduler


class DeckService:
    def __init__(self, *, bridge: Bridge, scheduler: Scheduler, events: EventRepository) -> None:
        self._bridge = bridge
        self._scheduler = scheduler
        self._events = events

    def start_work(self, request: StartWorkRequest) -> ActiveWork:
        work = self._bridge.start_work(request)
        self._events.append(
            workspace_id=work.workspace_id,
            event_type="work.started",
            thread_id=work.thread_id,
            turn_id=work.turn_id,
            payload={"workId": work.work_id, "state": work.state},
        )
        return work

    def active_work(self, workspace_id: str) -> ActiveWork | None:
        return self._scheduler.get(workspace_id)

    def events_after(self, event_id: int, *, workspace_id: str | None, limit: int) -> list[DeckEvent]:
        return self._events.after(event_id, workspace_id=workspace_id, limit=limit)

    def subscribe_events(self, subscriber: EventSubscriber) -> Unsubscribe:
        return self._events.subscribe(subscriber)
