"""Exercise the Deck approval broker against a real ``codex app-server`` process.

The probe deliberately asks for a harmless command under ``untrusted`` policy,
waits for the server-originated approval request, and sends ``decline`` through
the same JSON-RPC request id.  It stores the audit record in a temporary,
Deck-owned SQLite file and emits only redacted identifiers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend" / "src"))

from codex_deck.approval_audit import SqliteApprovalAuditStore
from codex_deck.approvals import ApprovalBroker
from codex_deck.app_server import ApprovalTransportBinding, StdioJsonRpcTransport, AppServerStdioClient


def _redact(value: str | int) -> str:
    return hashlib.sha256(str(value).encode()).hexdigest()[:12]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the real App Server approval-broker PoC.")
    parser.add_argument("--workspace", required=True, type=Path, help="Existing workspace used only as App Server cwd.")
    parser.add_argument("--timeout", default=90, type=int, help="Approval wait timeout in seconds.")
    parser.add_argument(
        "--scenario", choices=("decline", "server-failure"), default="decline",
        help="Explicitly decline, or terminate App Server while an approval remains pending.",
    )
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        raise SystemExit("--workspace must be an existing directory")

    with TemporaryDirectory(prefix="codex-deck-approval-poc-") as temporary_directory:
        audit = SqliteApprovalAuditStore(Path(temporary_directory) / "approval-audit.sqlite3")
        transport = StdioJsonRpcTransport()
        broker = ApprovalBroker(transport.respond, on_decided=audit.append)
        transport.set_incoming_handler(ApprovalTransportBinding(transport, broker).handle)
        client = AppServerStdioClient(transport)
        try:
            client.connect()
            thread_id = client.start_thread(
                workspace_path=str(workspace), approval_policy="untrusted", sandbox="workspace-write"
            )
            client.start_turn(
                thread_id=thread_id,
                text="Run exactly Get-Date, then reply with its year only.",
            )
            deadline = time.monotonic() + args.timeout
            while not broker.list() and time.monotonic() < deadline:
                time.sleep(0.1)
            pending = broker.list()
            if len(pending) != 1:
                raise RuntimeError(f"Expected exactly one pending approval, received {len(pending)}")
            approval = pending[0]
            if approval.kind != "command":
                raise RuntimeError(f"Expected command approval, received {approval.kind}")
            if args.scenario == "server-failure":
                transport.close()
                records = audit.list()
                print(json.dumps({
                    "status": "passed",
                    "scenario": args.scenario,
                    "approvalKind": approval.kind,
                    "requestIdHash": _redact(approval.request_id),
                    "approvalRemainsPending": len(broker.list()) == 1,
                    "auditRecordCount": len(records),
                    "automaticDecisionOrRetry": False,
                }, ensure_ascii=False))
                return
            broker.decide(approval.request_id, "decline")
            records = audit.list()
            if len(records) != 1:
                raise RuntimeError(f"Expected one audit record, received {len(records)}")
            record = records[0]
            if record.request_id != approval.request_id or record.decision != "decline":
                raise RuntimeError("Approval decision was not stored for the original request id")
            print(json.dumps({
                "status": "passed",
                "scenario": args.scenario,
                "approvalKind": approval.kind,
                "requestIdHash": _redact(approval.request_id),
                "auditRequestIdMatches": record.request_id == approval.request_id,
                "auditDecision": record.decision,
                "threadIdHash": _redact(thread_id),
            }, ensure_ascii=False))
        finally:
            client.close()
            audit.close()


if __name__ == "__main__":
    main()
