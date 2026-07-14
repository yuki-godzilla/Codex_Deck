import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from codex_deck.git import GitAccessError, ReadOnlyGitService
from codex_deck.workspaces import WorkspaceStore


class GitAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "allowed"
        self.workspace_path = self.root / "project"
        self.workspace_path.mkdir(parents=True)
        subprocess.run(["git", "init", "--quiet", str(self.workspace_path)], check=True)
        (self.workspace_path / "tracked.txt").write_text("first\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.workspace_path), "add", "tracked.txt"], check=True)
        (self.workspace_path / "tracked.txt").write_text("second\n", encoding="utf-8")
        (self.workspace_path / ".env").write_text("SECRET=value\n", encoding="utf-8")
        (self.workspace_path / "asset.bin").write_bytes(b"\x00before")
        subprocess.run(["git", "-C", str(self.workspace_path), "add", "asset.bin"], check=True)
        (self.workspace_path / "asset.bin").write_bytes(b"\x00after")
        self.store = WorkspaceStore(Path(self.temporary_directory.name) / "deck.db", allowed_roots=(self.root,))
        self.workspace = self.store.register(self.workspace_path)
        self.git = ReadOnlyGitService(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary_directory.cleanup()

    def test_status_and_diff_are_read_only_and_filter_denied_paths(self) -> None:
        status = self.git.status(self.workspace.workspace_id)
        self.assertTrue(status.is_repository)
        self.assertEqual(status.staged_count, 2)
        self.assertEqual(status.unstaged_count, 2)
        self.assertEqual([entry.path for entry in status.entries], ["asset.bin", "tracked.txt"])

        diff = self.git.diff(self.workspace.workspace_id, relative_path="tracked.txt")
        self.assertEqual(diff.mode, "unstaged")
        self.assertIn("+second", diff.content)
        with self.assertRaises(GitAccessError):
            self.git.diff(self.workspace.workspace_id, relative_path=".env")
        with self.assertRaises(GitAccessError):
            self.git.diff(self.workspace.workspace_id, relative_path="../outside.txt")

        binary = self.git.diff(self.workspace.workspace_id, relative_path="asset.bin")
        self.assertTrue(binary.is_binary)


if __name__ == "__main__":
    unittest.main()
