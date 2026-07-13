"""Codex Deck backend domain layer.

This package deliberately has no web framework or Codex runtime dependency yet.
The first implementation slice establishes the scheduler and Bridge contracts that
protect the App Server boundary.
"""

from .app_server import AppServerStdioClient, StdioJsonRpcTransport
from .bridge import Bridge, StartWorkRequest
from .scheduler import ActiveWork, Scheduler, WorkspaceBusyError, WorkState

__all__ = [
    "ActiveWork",
    "AppServerStdioClient",
    "Bridge",
    "Scheduler",
    "StartWorkRequest",
    "StdioJsonRpcTransport",
    "WorkState",
    "WorkspaceBusyError",
]
