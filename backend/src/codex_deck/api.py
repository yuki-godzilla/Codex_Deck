"""HTTP boundary for the first Deck vertical slice."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

from .bridge import StartWorkRequest
from .events import DeckEvent
from .scheduler import ActiveWork, WorkspaceBusyError
from .service import DeckService


class StartWorkBody(BaseModel):
    workspace_path: str = Field(min_length=1)
    text: str = Field(min_length=1)
    approval_policy: str = Field(min_length=1)
    sandbox: str = Field(min_length=1)


class ActiveWorkBody(BaseModel):
    work_id: str
    workspace_id: str
    thread_id: str | None
    turn_id: str | None
    state: str


class DeckEventBody(BaseModel):
    event_id: int
    received_at: datetime
    workspace_id: str
    event_type: str
    thread_id: str | None
    turn_id: str | None
    payload: dict[str, Any]


def _work_body(work: ActiveWork) -> ActiveWorkBody:
    return ActiveWorkBody(
        work_id=work.work_id,
        workspace_id=work.workspace_id,
        thread_id=work.thread_id,
        turn_id=work.turn_id,
        state=work.state,
    )


def _event_body(event: DeckEvent) -> DeckEventBody:
    return DeckEventBody(
        event_id=event.event_id,
        received_at=event.received_at,
        workspace_id=event.workspace_id,
        event_type=event.event_type,
        thread_id=event.thread_id,
        turn_id=event.turn_id,
        payload=event.payload,
    )


def create_app(service: DeckService) -> FastAPI:
    app = FastAPI(title="Codex Deck API", version="0.1.0")

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/workspaces/{workspace_id}/active-work", response_model=ActiveWorkBody | None)
    def get_active_work(workspace_id: str) -> ActiveWorkBody | None:
        work = service.active_work(workspace_id)
        return _work_body(work) if work else None

    @app.post(
        "/api/v1/workspaces/{workspace_id}/work",
        response_model=ActiveWorkBody,
        status_code=status.HTTP_201_CREATED,
    )
    def start_work(workspace_id: str, body: StartWorkBody) -> ActiveWorkBody:
        try:
            work = service.start_work(StartWorkRequest(
                workspace_id=workspace_id,
                workspace_path=body.workspace_path,
                text=body.text,
                approval_policy=body.approval_policy,
                sandbox=body.sandbox,
            ))
        except WorkspaceBusyError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "workspace_busy", "activeWork": _work_body(error.active_work).model_dump()},
            ) from error
        return _work_body(work)

    @app.get("/api/v1/events", response_model=list[DeckEventBody])
    def get_events(
        after: int = Query(default=0, ge=0),
        workspace_id: str | None = None,
        limit: int = Query(default=100, ge=1, le=200),
    ) -> list[DeckEventBody]:
        return [_event_body(event) for event in service.events_after(after, workspace_id=workspace_id, limit=limit)]

    return app
