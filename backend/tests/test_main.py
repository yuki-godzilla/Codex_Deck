import unittest
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from codex_deck.main import create_local_app


class LocalRuntimeTest(unittest.TestCase):
    def test_demo_runtime_uses_sqlite_without_external_app_server(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "allowed"
            workspace = root / "project"
            workspace.mkdir(parents=True)
            (workspace / "README.md").write_text("Read only\n", encoding="utf-8")
            (workspace / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "init", "--quiet", str(workspace)], check=True)
            (workspace / "tracked.txt").write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(workspace), "add", "tracked.txt"], check=True)
            (workspace / "tracked.txt").write_text("after\n", encoding="utf-8")
            app = create_local_app(
                database_path=Path(directory) / "deck.db",
                demo=True,
                allowed_roots=(root,),
                workspace_paths=(workspace,),
            )
            with TestClient(app) as client:
                response = client.post("/api/v1/workspaces/demo/work", json={
                    "workspace_path": "disposable-workspace",
                    "text": "Safe local UI test.",
                    "approval_policy": "untrusted",
                    "sandbox": "read-only",
                })
                listed = client.get("/api/v1/workspaces")
                workspace_id = listed.json()[0]["workspace_id"]
                listed_files = client.get(f"/api/v1/workspaces/{workspace_id}/files")
                text = client.get(f"/api/v1/workspaces/{workspace_id}/file?path=README.md")
                denied = client.get(f"/api/v1/workspaces/{workspace_id}/file?path=.env")
                git_status = client.get(f"/api/v1/workspaces/{workspace_id}/git/status")
                git_diff = client.get(f"/api/v1/workspaces/{workspace_id}/git/diff?path=tracked.txt")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["thread_id"].startswith("demo-thread-"))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)
        self.assertNotIn("root_path", listed.json()[0])
        self.assertEqual(listed_files.json()[0]["name"], "README.md")
        self.assertEqual(text.json()["content"].splitlines(), ["Read only"])
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(git_status.json()["is_repository"])
        self.assertIn("+after", git_diff.json()["content"])


if __name__ == "__main__":
    unittest.main()
