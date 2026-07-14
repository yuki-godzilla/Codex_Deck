"""Codex App Server stdio JSON-RPC adapter.

The adapter is intentionally a process-local boundary.  It never opens an App
Server WebSocket listener and it never decides an approval on Deck's behalf.
"""

from __future__ import annotations

import json
import queue
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock, Thread
from typing import Any, Protocol


JsonObject = dict[str, Any]


class JsonRpcTransport(Protocol):
    def start(self) -> None: ...

    def request(self, method: str, params: JsonObject) -> JsonObject: ...

    def notify(self, method: str, params: JsonObject) -> None: ...

    def close(self) -> None: ...


class AppServerStdioClient:
    """Verified Thread/Turn start path backed by a JSON-RPC transport."""

    def __init__(self, transport: JsonRpcTransport) -> None:
        self._transport = transport
        self._connected = False

    def connect(self) -> JsonObject:
        if self._connected:
            raise RuntimeError("App Server client is already connected")
        self._transport.start()
        result = self._transport.request("initialize", {
            "clientInfo": {"name": "codex-deck", "version": "0.1.0"},
            "capabilities": {"experimentalApi": False},
        })
        self._transport.notify("initialized", {})
        self._connected = True
        return result

    def start_thread(self, *, workspace_path: str, approval_policy: str, sandbox: str) -> str:
        self._require_connection()
        result = self._transport.request("thread/start", {
            "cwd": workspace_path,
            "approvalPolicy": approval_policy,
            "sandbox": sandbox,
        })
        thread_id = result.get("thread", {}).get("id")
        if not isinstance(thread_id, str) or not thread_id:
            raise RuntimeError("App Server thread/start returned no thread id")
        return thread_id

    def start_turn(self, *, thread_id: str, text: str) -> str:
        self._require_connection()
        result = self._transport.request("turn/start", {
            "threadId": thread_id,
            "input": [{"type": "text", "text": text}],
        })
        turn_id = result.get("turn", {}).get("id")
        if not isinstance(turn_id, str) or not turn_id:
            raise RuntimeError("App Server turn/start returned no turn id")
        return turn_id

    def close(self) -> None:
        self._connected = False
        self._transport.close()

    def _require_connection(self) -> None:
        if not self._connected:
            raise RuntimeError("Call connect before using the App Server client")


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    message: JsonObject


class StdioJsonRpcTransport:
    """Line-delimited JSON-RPC transport for ``codex app-server --stdio``.

    Server-originated requests are surfaced through ``on_incoming``.  No default
    approval response exists: the future API/UI must send the official decision
    explicitly using ``respond``.
    """

    def __init__(
        self,
        *,
        on_incoming: Callable[[IncomingMessage], None] | None = None,
        command: tuple[str, ...] = ("codex", "app-server", "--stdio"),
        request_timeout_seconds: float = 30.0,
    ) -> None:
        self._on_incoming = on_incoming or (lambda _: None)
        self._command = command
        self._request_timeout_seconds = request_timeout_seconds
        self._process: subprocess.Popen[str] | None = None
        self._next_id = 1
        self._pending: dict[int, queue.Queue[JsonObject]] = {}
        self._lock = Lock()
        self._reader: Thread | None = None

    def start(self) -> None:
        if self._process is not None:
            raise RuntimeError("App Server process is already running")
        self._process = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self._reader = Thread(target=self._read_stdout, daemon=True)
        self._reader.start()

    def request(self, method: str, params: JsonObject) -> JsonObject:
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
            response_queue: queue.Queue[JsonObject] = queue.Queue(maxsize=1)
            self._pending[request_id] = response_queue
            self._write({"id": request_id, "method": method, "params": params})
        try:
            response = response_queue.get(timeout=self._request_timeout_seconds)
        except queue.Empty as error:
            with self._lock:
                self._pending.pop(request_id, None)
            raise TimeoutError(f"Timed out waiting for App Server response: {method}") from error
        if "error" in response:
            raise RuntimeError(f"App Server {method} failed: {response['error']}")
        return response.get("result", {})

    def notify(self, method: str, params: JsonObject) -> None:
        self._write({"method": method, "params": params})

    def respond(self, request_id: int, result: JsonObject) -> None:
        """Respond to a server request after an explicit Deck user decision."""
        self._write({"id": request_id, "result": result})

    def set_incoming_handler(self, handler: Callable[[IncomingMessage], None]) -> None:
        """Install the Bridge handler before starting the stdio process."""
        if self._process is not None:
            raise RuntimeError("Set the incoming handler before starting App Server")
        self._on_incoming = handler

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.stdin:
            process.stdin.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for response_queue in pending:
            response_queue.put({"error": "transport closed"})

    def _write(self, message: JsonObject) -> None:
        process = self._process
        if process is None or process.stdin is None:
            raise RuntimeError("App Server process is not running")
        process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        process.stdin.flush()

    def _read_stdout(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            message_id = message.get("id")
            if isinstance(message_id, int) and "method" not in message:
                with self._lock:
                    response_queue = self._pending.pop(message_id, None)
                if response_queue is not None:
                    response_queue.put(message)
                    continue
            self._on_incoming(IncomingMessage(message=message))


class ApprovalTransportBinding:
    """Connect stable server approval requests to an explicit approval broker."""

    def __init__(self, transport: "ApprovalResponseTransport", broker: "ApprovalReceiver") -> None:
        self._transport = transport
        self._broker = broker

    def handle(self, incoming: IncomingMessage) -> None:
        self._broker.receive(incoming.message)


class ApprovalResponseTransport(Protocol):
    def respond(self, request_id: int, result: JsonObject) -> None: ...


class ApprovalReceiver(Protocol):
    def receive(self, message: JsonObject) -> object: ...
