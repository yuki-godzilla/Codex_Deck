import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from codex_deck.main import create_local_app


class LocalRuntimeTest(unittest.TestCase):
    def test_demo_runtime_uses_sqlite_without_external_app_server(self) -> None:
        with TemporaryDirectory() as directory:
            app = create_local_app(database_path=Path(directory) / "deck.db", demo=True)
            with TestClient(app) as client:
                response = client.post("/api/v1/workspaces/demo/work", json={
                    "workspace_path": "disposable-workspace",
                    "text": "Safe local UI test.",
                    "approval_policy": "untrusted",
                    "sandbox": "read-only",
                })

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["thread_id"].startswith("demo-thread-"))


if __name__ == "__main__":
    unittest.main()
