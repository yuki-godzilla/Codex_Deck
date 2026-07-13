"""Narrow, testable boundary between Deck and the Codex App Server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .scheduler import ActiveWork, Scheduler


class AppServerClient(Protocol):
    """Only the verified start path required by the first vertical slice."""

    def start_thread(self, *, workspace_path: str, approval_policy: str, sandbox: str) -> str: ...

    def start_turn(self, *, thread_id: str, text: str) -> str: ...


@dataclass(frozen=True, slots=True)
class StartWorkRequest:
    workspace_id: str
    workspace_path: str
    text: str
    approval_policy: str
    sandbox: str


class Bridge:
    """Coordinates start operations without storing Codex Thread contents."""

    def __init__(self, scheduler: Scheduler, app_server: AppServerClient) -> None:
        self._scheduler = scheduler
        self._app_server = app_server

    def start_work(self, request: StartWorkRequest) -> ActiveWork:
        work = self._scheduler.acquire(request.workspace_id)
        try:
            thread_id = self._app_server.start_thread(
                workspace_path=request.workspace_path,
                approval_policy=request.approval_policy,
                sandbox=request.sandbox,
            )
            # The work ownership exists before the remote call.  Update it with
            # the official Thread ID without releasing the workspace lock.
            work = self._scheduler.attach_thread(work.work_id, thread_id)
            turn_id = self._app_server.start_turn(thread_id=thread_id, text=request.text)
            return self._scheduler.attach_turn(work.work_id, turn_id)
        except Exception:
            # A failed start never leaves a phantom lock and must not retry.
            self._scheduler.release(work.work_id)
            raise
