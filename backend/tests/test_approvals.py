import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient
from codex_deck.api import create_app
from codex_deck.approvals import ApprovalBroker
from codex_deck.approval_audit import SqliteApprovalAuditStore
from codex_deck.bridge import Bridge
from codex_deck.events import EventStore
from codex_deck.scheduler import Scheduler
from codex_deck.service import DeckService

class FakeAppServer:
    def start_thread(self, **_: str) -> str: return "thread"
    def start_turn(self, **_: str) -> str: return "turn"

class ApprovalTest(unittest.TestCase):
    def test_command_approval_requires_explicit_supported_decision(self) -> None:
        responses = []
        broker = ApprovalBroker(lambda request_id, result: responses.append((request_id, result)))
        approval = broker.receive({"id": 9, "method": "item/commandExecution/requestApproval", "params": {
            "threadId": "thread", "turnId": "turn", "itemId": "item", "command": "Get-Date", "cwd": "workspace"}})
        self.assertIsNotNone(approval)
        service = DeckService(bridge=Bridge(Scheduler(), FakeAppServer()), scheduler=Scheduler(), events=EventStore())
        api = TestClient(create_app(service, approvals=broker))
        self.assertEqual(api.get("/api/v1/approvals").json()[0]["kind"], "command")
        response = api.post("/api/v1/approvals/9/decision", json={"decision": "decline"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(responses, [(9, {"decision": "decline"})])
        self.assertEqual(api.get("/api/v1/approvals").json(), [])

    def test_decision_audit_persists_without_command_content(self) -> None:
        with TemporaryDirectory() as directory:
            audit = SqliteApprovalAuditStore(Path(directory) / "deck.db")
            broker = ApprovalBroker(lambda _id, _result: None, on_decided=audit.append)
            broker.receive({"id": 4, "method": "item/fileChange/requestApproval", "params": {"threadId": "t", "turnId": "u", "itemId": "i", "reason": "write"}})
            broker.decide(4, "accept")
            records = audit.list()
            audit.close()
        self.assertEqual(records[0].decision, "accept")
        self.assertEqual(records[0].kind, "fileChange")

    def test_failed_explicit_decision_keeps_approval_pending_without_audit(self) -> None:
        with TemporaryDirectory() as directory:
            audit = SqliteApprovalAuditStore(Path(directory) / "deck.db")
            broker = ApprovalBroker(
                lambda _id, _result: (_ for _ in ()).throw(RuntimeError("transport unavailable")),
                on_decided=audit.append,
            )
            broker.receive({"id": 7, "method": "item/commandExecution/requestApproval", "params": {
                "threadId": "t", "turnId": "u", "itemId": "i", "command": "Get-Date",
            }})
            with self.assertRaisesRegex(RuntimeError, "transport unavailable"):
                broker.decide(7, "decline")
            self.assertEqual([item.request_id for item in broker.list()], [7])
            self.assertEqual(audit.list(), [])
            audit.close()

if __name__ == "__main__": unittest.main()
