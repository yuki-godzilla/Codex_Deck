"""Workspace-scoped logical exclusion for Codex work.

The App Server permits more than one read-only Turn in the same cwd.  Deck must
therefore enforce its product rule before asking the App Server to start work.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import RLock
from uuid import uuid4


class WorkState(StrEnum):
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    WAITING_FOR_ANSWER = "waiting_for_answer"
    STOPPING = "stopping"


@dataclass(frozen=True, slots=True)
class ActiveWork:
    """The small amount of Deck-owned state needed to protect one workspace."""

    work_id: str
    workspace_id: str
    thread_id: str | None
    turn_id: str | None
    state: WorkState


class WorkspaceBusyError(RuntimeError):
    """Raised instead of silently queueing or interrupting existing work."""

    def __init__(self, active_work: ActiveWork) -> None:
        super().__init__(f"Workspace already has active work: {active_work.workspace_id}")
        self.active_work = active_work


class Scheduler:
    """In-memory MVP scheduler with explicit workspace ownership.

    Persistence and crash recovery are intentionally deferred to the Deck state
    store.  This class never starts a second work item, kills the first item, or
    queues work implicitly.
    """

    def __init__(self) -> None:
        self._active_by_workspace: dict[str, ActiveWork] = {}
        self._lock = RLock()

    def acquire(self, workspace_id: str, *, thread_id: str | None = None) -> ActiveWork:
        if not workspace_id:
            raise ValueError("workspace_id is required")
        with self._lock:
            current = self._active_by_workspace.get(workspace_id)
            if current is not None:
                raise WorkspaceBusyError(current)
            work = ActiveWork(
                work_id=str(uuid4()),
                workspace_id=workspace_id,
                thread_id=thread_id,
                turn_id=None,
                state=WorkState.RUNNING,
            )
            self._active_by_workspace[workspace_id] = work
            return work

    def attach_turn(self, work_id: str, turn_id: str) -> ActiveWork:
        if not turn_id:
            raise ValueError("turn_id is required")
        with self._lock:
            workspace_id, current = self._find(work_id)
            updated = ActiveWork(
                work_id=current.work_id,
                workspace_id=current.workspace_id,
                thread_id=current.thread_id,
                turn_id=turn_id,
                state=current.state,
            )
            self._active_by_workspace[workspace_id] = updated
            return updated

    def attach_thread(self, work_id: str, thread_id: str) -> ActiveWork:
        if not thread_id:
            raise ValueError("thread_id is required")
        with self._lock:
            workspace_id, current = self._find(work_id)
            updated = ActiveWork(
                work_id=current.work_id,
                workspace_id=current.workspace_id,
                thread_id=thread_id,
                turn_id=current.turn_id,
                state=current.state,
            )
            self._active_by_workspace[workspace_id] = updated
            return updated

    def set_state(self, work_id: str, state: WorkState) -> ActiveWork:
        with self._lock:
            workspace_id, current = self._find(work_id)
            updated = ActiveWork(
                work_id=current.work_id,
                workspace_id=current.workspace_id,
                thread_id=current.thread_id,
                turn_id=current.turn_id,
                state=state,
            )
            self._active_by_workspace[workspace_id] = updated
            return updated

    def get(self, workspace_id: str) -> ActiveWork | None:
        with self._lock:
            return self._active_by_workspace.get(workspace_id)

    def release(self, work_id: str) -> None:
        with self._lock:
            workspace_id, _ = self._find(work_id)
            del self._active_by_workspace[workspace_id]

    def _find(self, work_id: str) -> tuple[str, ActiveWork]:
        for workspace_id, work in self._active_by_workspace.items():
            if work.work_id == work_id:
                return workspace_id, work
        raise KeyError(f"Unknown active work: {work_id}")
