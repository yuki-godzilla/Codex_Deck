import unittest

from codex_deck.app_server import AppServerStdioClient, ApprovalTransportBinding, IncomingMessage
from codex_deck.approvals import ApprovalBroker


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def request(self, method: str, params: dict[str, object]) -> dict[str, object]:
        self.calls.append(("request", method))
        if method == "initialize":
            return {"platformFamily": "windows"}
        if method == "thread/start":
            self.thread_params = params
            return {"thread": {"id": "thread-1"}}
        if method == "turn/start":
            self.turn_params = params
            return {"turn": {"id": "turn-1"}}
        raise AssertionError(method)

    def notify(self, method: str, _: dict[str, object]) -> None:
        self.calls.append(("notify", method))

    def close(self) -> None:
        self.closed = True


class AppServerClientTest(unittest.TestCase):
    def test_initialize_then_start_thread_and_turn(self) -> None:
        transport = FakeTransport()
        client = AppServerStdioClient(transport)

        initialize = client.connect()
        thread_id = client.start_thread(
            workspace_path="disposable-workspace",
            approval_policy="untrusted",
            sandbox="read-only",
        )
        turn_id = client.start_turn(thread_id=thread_id, text="One safe request.")
        client.close()

        self.assertTrue(transport.started)
        self.assertEqual(initialize["platformFamily"], "windows")
        self.assertEqual(thread_id, "thread-1")
        self.assertEqual(turn_id, "turn-1")
        self.assertEqual(
            transport.calls,
            [
                ("request", "initialize"),
                ("notify", "initialized"),
                ("request", "thread/start"),
                ("request", "turn/start"),
            ],
        )
        self.assertTrue(transport.closed)

    def test_start_is_rejected_before_initialize(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Call connect"):
            AppServerStdioClient(FakeTransport()).start_thread(
                workspace_path="workspace",
                approval_policy="untrusted",
                sandbox="read-only",
            )

    def test_binding_forwards_server_request_and_preserves_request_id(self) -> None:
        responses = []
        class Transport:
            def respond(self, request_id, result): responses.append((request_id, result))
        broker = ApprovalBroker(Transport().respond)
        binding = ApprovalTransportBinding(Transport(), broker)
        binding.handle(IncomingMessage({"id": 42, "method": "item/fileChange/requestApproval", "params": {
            "threadId": "thread", "turnId": "turn", "itemId": "item"}}))
        broker.decide(42, "decline")
        self.assertEqual(responses, [(42, {"decision": "decline"})])


if __name__ == "__main__":
    unittest.main()
