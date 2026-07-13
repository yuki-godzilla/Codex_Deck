"""Codex Deck backend domain layer.

This package deliberately has no web framework or Codex runtime dependency yet.
The first implementation slice establishes the scheduler and Bridge contracts that
protect the App Server boundary.
"""

from .app_server import AppServerStdioClient, StdioJsonRpcTransport
from .api import create_app
from .bridge import Bridge, StartWorkRequest
from .events import DeckEvent, EventStore, SqliteEventStore
from .files import ReadOnlyFileService
from .git import ReadOnlyGitService
from .scheduler import ActiveWork, Scheduler, WorkspaceBusyError, WorkState
from .service import DeckService
from .workspaces import WorkspaceStore

__all__ = [
    "ActiveWork",
    "AppServerStdioClient",
    "Bridge",
    "create_app",
    "DeckEvent",
    "DeckService",
    "EventStore",
    "ReadOnlyFileService",
    "ReadOnlyGitService",
    "Scheduler",
    "StartWorkRequest",
    "StdioJsonRpcTransport",
    "SqliteEventStore",
    "WorkspaceStore",
    "WorkState",
    "WorkspaceBusyError",
]
