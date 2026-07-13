import unittest

from codex_deck.bridge import Bridge, StartWorkRequest
from codex_deck.scheduler import Scheduler, WorkspaceBusyError


class FakeAppServer:
    def __init__(self, *, fail_at: str | None = None) -> None:
        self.fail_at = fail_at
        self.calls: list[str] = []

    def start_thread(self, **_: str) -> str:
        self.calls.append("thread/start")
        if self.fail_at == "thread":
            raise RuntimeError("thread start failed")
        return "thread-1"

    def start_turn(self, **_: str) -> str:
        self.calls.append("turn/start")
        if self.fail_at == "turn":
            raise RuntimeError("turn start failed")
        return "turn-1"


def request() -> StartWorkRequest:
    return StartWorkRequest(
        workspace_id="workspace-a",
        workspace_path="disposable-workspace",
        text="Summarize one fact.",
        approval_policy="untrusted",
        sandbox="read-only",
    )


class BridgeTest(unittest.TestCase):
    def test_starts_verified_thread_and_turn_path(self) -> None:
        server = FakeAppServer()
        scheduler = Scheduler()
        work = Bridge(scheduler, server).start_work(request())

        self.assertEqual(server.calls, ["thread/start", "turn/start"])
        self.assertEqual(work.thread_id, "thread-1")
        self.assertEqual(work.turn_id, "turn-1")
        with self.assertRaises(WorkspaceBusyError):
            scheduler.acquire("workspace-a")

    def test_failure_releases_lock_without_retrying(self) -> None:
        server = FakeAppServer(fail_at="turn")
        scheduler = Scheduler()

        with self.assertRaisesRegex(RuntimeError, "turn start failed"):
            Bridge(scheduler, server).start_work(request())

        self.assertEqual(server.calls, ["thread/start", "turn/start"])
        self.assertIsNone(scheduler.get("workspace-a"))


if __name__ == "__main__":
    unittest.main()
