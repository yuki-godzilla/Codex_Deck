"""Explicit local runtime composition for development and UI verification."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn

from .api import create_app
from .bridge import Bridge
from .events import SqliteEventStore
from .scheduler import Scheduler
from .service import DeckService


class _DemoAppServer:
    """Deterministic local-only fake; never enabled unless explicitly requested."""

    def __init__(self) -> None:
        self._thread_number = 0
        self._turn_number = 0

    def start_thread(self, **_: str) -> str:
        self._thread_number += 1
        return f"demo-thread-{self._thread_number}"

    def start_turn(self, **_: str) -> str:
        self._turn_number += 1
        return f"demo-turn-{self._turn_number}"


class _UnavailableAppServer:
    def start_thread(self, **_: str) -> str:
        raise RuntimeError("App Server runtime is not configured")

    def start_turn(self, **_: str) -> str:
        raise AssertionError("turn/start must not run after unavailable thread/start")


def create_local_app(*, database_path: str | Path, demo: bool = False):
    """Create a local API without opening an App Server network listener."""
    scheduler = Scheduler()
    events = SqliteEventStore(database_path)
    service = DeckService(
        bridge=Bridge(scheduler, _DemoAppServer() if demo else _UnavailableAppServer()),
        scheduler=scheduler,
        events=events,
    )
    try:
        app = create_app(service)
        app.router.on_shutdown.append(events.close)
        return app
    except Exception:
        events.close()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Codex Deck backend.")
    parser.add_argument("--demo", action="store_true", help="Use deterministic fake App Server responses.")
    parser.add_argument("--database", default="codex-deck.db", help="Deck-owned SQLite event database path.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    demo = args.demo or os.getenv("CODEX_DECK_DEMO") == "1"
    uvicorn.run(create_local_app(database_path=args.database, demo=demo), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
