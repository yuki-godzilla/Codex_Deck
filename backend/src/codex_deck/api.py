"""HTTP boundary for the first Deck vertical slice."""

from __future__ import annotations

from datetime import datetime
import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from .bridge import StartWorkRequest
from .events import DeckEvent
from .files import FileAccessError, FileEntry, ReadOnlyFileService, TextFile
from .git import GitAccessError, GitDiff, GitFileStatus, GitStatus, ReadOnlyGitService
from .scheduler import ActiveWork, WorkspaceBusyError
from .service import DeckService
from .workspaces import Workspace, WorkspaceStore


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


class WorkspaceBody(BaseModel):
    workspace_id: str
    display_name: str
    created_at: datetime


class FileEntryBody(BaseModel):
    path: str
    name: str
    kind: str
    size_bytes: int | None


class TextFileBody(BaseModel):
    path: str
    content: str
    size_bytes: int
    line_count: int


class GitFileStatusBody(BaseModel):
    path: str
    index_status: str
    worktree_status: str


class GitStatusBody(BaseModel):
    is_repository: bool
    branch: str | None
    ahead: int
    behind: int
    staged_count: int
    unstaged_count: int
    untracked_count: int
    entries: list[GitFileStatusBody]


class GitDiffBody(BaseModel):
    path: str
    mode: str
    content: str
    truncated: bool


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


def _workspace_body(workspace: Workspace) -> WorkspaceBody:
    return WorkspaceBody(
        workspace_id=workspace.workspace_id,
        display_name=workspace.display_name,
        created_at=workspace.created_at,
    )


def _file_entry_body(entry: FileEntry) -> FileEntryBody:
    return FileEntryBody(path=entry.path, name=entry.name, kind=entry.kind, size_bytes=entry.size_bytes)


def _text_file_body(file: TextFile) -> TextFileBody:
    return TextFileBody(path=file.path, content=file.content, size_bytes=file.size_bytes, line_count=file.line_count)


def _git_status_body(status_value: GitStatus) -> GitStatusBody:
    return GitStatusBody(
        is_repository=status_value.is_repository,
        branch=status_value.branch,
        ahead=status_value.ahead,
        behind=status_value.behind,
        staged_count=status_value.staged_count,
        unstaged_count=status_value.unstaged_count,
        untracked_count=status_value.untracked_count,
        entries=[
            GitFileStatusBody(
                path=entry.path,
                index_status=entry.index_status,
                worktree_status=entry.worktree_status,
            )
            for entry in status_value.entries
        ],
    )


def _git_diff_body(diff: GitDiff) -> GitDiffBody:
    return GitDiffBody(path=diff.path, mode=diff.mode, content=diff.content, truncated=diff.truncated)


def create_app(
    service: DeckService,
    *,
    workspaces: WorkspaceStore | None = None,
    files: ReadOnlyFileService | None = None,
    git: ReadOnlyGitService | None = None,
) -> FastAPI:
    app = FastAPI(title="Codex Deck API", version="0.1.0")

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/workspaces", response_model=list[WorkspaceBody])
    def list_workspaces() -> list[WorkspaceBody]:
        if workspaces is None:
            return []
        return [_workspace_body(workspace) for workspace in workspaces.list()]

    @app.get("/api/v1/workspaces/{workspace_id}/files", response_model=list[FileEntryBody])
    def list_files(workspace_id: str, path: str = "") -> list[FileEntryBody]:
        if files is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="file adapter is not configured")
        try:
            return [_file_entry_body(entry) for entry in files.list_directory(workspace_id, path)]
        except KeyError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workspace not found") from error
        except FileAccessError as error:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="file access denied") from error
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    @app.get("/api/v1/workspaces/{workspace_id}/file", response_model=TextFileBody)
    def read_file(workspace_id: str, path: str = Query(min_length=1)) -> TextFileBody:
        if files is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="file adapter is not configured")
        try:
            return _text_file_body(files.read_text(workspace_id, path))
        except KeyError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workspace not found") from error
        except FileAccessError as error:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="file access denied") from error
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    @app.get("/api/v1/workspaces/{workspace_id}/git/status", response_model=GitStatusBody)
    def get_git_status(workspace_id: str) -> GitStatusBody:
        if git is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="git adapter is not configured")
        try:
            return _git_status_body(git.status(workspace_id))
        except KeyError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workspace not found") from error
        except GitAccessError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    @app.get("/api/v1/workspaces/{workspace_id}/git/diff", response_model=GitDiffBody)
    def get_git_diff(
        workspace_id: str,
        path: str = Query(min_length=1),
        staged: bool = False,
    ) -> GitDiffBody:
        if git is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="git adapter is not configured")
        try:
            return _git_diff_body(git.diff(workspace_id, relative_path=path, staged=staged))
        except KeyError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workspace not found") from error
        except GitAccessError as error:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="git access denied") from error

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

    @app.websocket("/api/v1/events/stream")
    async def stream_events(websocket: WebSocket) -> None:
        after = _non_negative_query(websocket.query_params.get("after"), "after")
        workspace_id = websocket.query_params.get("workspace_id")
        await websocket.accept()
        loop = asyncio.get_running_loop()
        pending: asyncio.Queue[DeckEvent] = asyncio.Queue()

        def on_event(event: DeckEvent) -> None:
            if workspace_id is None or event.workspace_id == workspace_id:
                loop.call_soon_threadsafe(pending.put_nowait, event)

        unsubscribe = service.subscribe_events(on_event)
        try:
            last_sent = after
            for event in service.events_after(after, workspace_id=workspace_id, limit=200):
                await websocket.send_json(_event_body(event).model_dump(mode="json"))
                last_sent = event.event_id
            while True:
                event = await pending.get()
                if event.event_id <= last_sent:
                    continue
                await websocket.send_json(_event_body(event).model_dump(mode="json"))
                last_sent = event.event_id
        except WebSocketDisconnect:
            pass
        finally:
            unsubscribe()

    return app


def _non_negative_query(value: str | None, field: str) -> int:
    try:
        parsed = int(value or "0")
    except ValueError as error:
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION) from error
    if parsed < 0:
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)
    return parsed
