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
        subprocess.run(["git", "-C", str(self.workspace_path), "config", "user.email", "deck@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.workspace_path), "config", "user.name", "Codex Deck Test"], check=True)
        (self.workspace_path / "tracked.txt").write_text("first\n", encoding="utf-8")
        (self.workspace_path / "rename-source.txt").write_text("rename\n", encoding="utf-8")
        (self.workspace_path / "deleted.txt").write_text("delete\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.workspace_path), "add", "tracked.txt", "rename-source.txt", "deleted.txt"], check=True)
        subprocess.run(["git", "-C", str(self.workspace_path), "commit", "--quiet", "-m", "initial"], check=True)
        (self.workspace_path / "tracked.txt").write_text("second\n", encoding="utf-8")
        (self.workspace_path / ".env").write_text("SECRET=value\n", encoding="utf-8")
        (self.workspace_path / "asset.bin").write_bytes(b"\x00before")
        subprocess.run(["git", "-C", str(self.workspace_path), "add", "asset.bin"], check=True)
        (self.workspace_path / "asset.bin").write_bytes(b"\x00after")
        subprocess.run(["git", "-C", str(self.workspace_path), "mv", "rename-source.txt", "renamed.txt"], check=True)
        (self.workspace_path / "deleted.txt").unlink()
        subprocess.run(["git", "-C", str(self.workspace_path), "remote", "add", "origin", "https://example.invalid/deck.git"], check=True)
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
        self.assertEqual(status.unstaged_count, 3)
        self.assertEqual(status.remotes, ["origin"])
        self.assertEqual([entry.path for entry in status.entries], ["asset.bin", "deleted.txt", "renamed.txt", "tracked.txt"])
        renamed = next(entry for entry in status.entries if entry.path == "renamed.txt")
        self.assertEqual(renamed.original_path, "rename-source.txt")

        diff = self.git.diff(self.workspace.workspace_id, relative_path="tracked.txt")
        self.assertEqual(diff.mode, "unstaged")
        self.assertIn("+second", diff.content)
        with self.assertRaises(GitAccessError):
            self.git.diff(self.workspace.workspace_id, relative_path=".env")
        with self.assertRaises(GitAccessError):
            self.git.diff(self.workspace.workspace_id, relative_path="../outside.txt")

        binary = self.git.diff(self.workspace.workspace_id, relative_path="asset.bin")
        self.assertTrue(binary.is_binary)

    def test_diff_can_be_fetched_in_bounded_chunks(self) -> None:
        (self.workspace_path / "tracked.txt").write_text("x\n" * 500, encoding="utf-8")
        git = ReadOnlyGitService(self.store, maximum_diff_bytes=120)
        first = git.diff(self.workspace.workspace_id, relative_path="tracked.txt", limit=80)
        self.assertTrue(first.truncated)
        self.assertEqual(first.offset, 0)
        self.assertEqual(len(first.content), 80)
        self.assertIsNotNone(first.next_offset)
        second = git.diff(self.workspace.workspace_id, relative_path="tracked.txt", offset=first.next_offset, limit=80)
        self.assertEqual(second.offset, 80)
        self.assertGreater(second.total_characters, len(first.content))


if __name__ == "__main__":
    unittest.main()
