import unittest

from fastapi.testclient import TestClient

from codex_deck.api import create_app
from codex_deck.bridge import Bridge, StartWorkRequest
from codex_deck.events import EventStore
from codex_deck.scheduler import Scheduler
from codex_deck.service import DeckService


class FakeAppServer:
    def start_thread(self, **_: str) -> str:
        return "thread-1"

    def start_turn(self, **_: str) -> str:
        return "turn-1"


def service() -> DeckService:
    scheduler = Scheduler()
    service = DeckService(
        bridge=Bridge(scheduler, FakeAppServer()),
        scheduler=scheduler,
        events=EventStore(),
    )
    return service


def client() -> TestClient:
    return TestClient(create_app(service()))


class ApiTest(unittest.TestCase):
    def test_health_and_start_work_with_event_replay(self) -> None:
        api = client()
        self.assertEqual(api.get("/healthz").json(), {"status": "ok"})

        started = api.post("/api/v1/workspaces/demo/work", json={
            "workspace_path": "disposable-workspace",
            "text": "This text must not be copied to Deck events.",
            "approval_policy": "untrusted",
            "sandbox": "read-only",
        })
        self.assertEqual(started.status_code, 201)
        self.assertEqual(started.json()["thread_id"], "thread-1")

        event = api.get("/api/v1/events?after=0&workspace_id=demo").json()[0]
        self.assertEqual(event["event_type"], "work.started")
        self.assertNotIn("text", event["payload"])

    def test_same_workspace_returns_active_work_conflict(self) -> None:
        api = client()
        body = {
            "workspace_path": "disposable-workspace",
            "text": "Safe request.",
            "approval_policy": "untrusted",
            "sandbox": "read-only",
        }
        self.assertEqual(api.post("/api/v1/workspaces/demo/work", json=body).status_code, 201)
        conflict = api.post("/api/v1/workspaces/demo/work", json=body)

        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["detail"]["code"], "workspace_busy")

    def test_websocket_replays_and_streams_workspace_events(self) -> None:
        deck_service = service()
        api = TestClient(create_app(deck_service))
        with api.websocket_connect("/api/v1/events/stream?after=0&workspace_id=demo") as socket:
            deck_service.start_work(StartWorkRequest(
                workspace_id="demo",
                workspace_path="disposable-workspace",
                text="Safe request.",
                approval_policy="untrusted",
                sandbox="read-only",
            ))
            event = socket.receive_json()

        self.assertEqual(event["event_type"], "work.started")
        self.assertEqual(event["workspace_id"], "demo")

    def test_websocket_replays_existing_events_from_cursor(self) -> None:
        deck_service = service()
        deck_service.start_work(StartWorkRequest(
            workspace_id="replay",
            workspace_path="disposable-workspace",
            text="Safe request.",
            approval_policy="untrusted",
            sandbox="read-only",
        ))
        api = TestClient(create_app(deck_service))

        with api.websocket_connect("/api/v1/events/stream?after=0&workspace_id=replay") as socket:
            event = socket.receive_json()

        self.assertEqual(event["event_id"], 1)
        self.assertEqual(event["workspace_id"], "replay")


if __name__ == "__main__":
    unittest.main()
