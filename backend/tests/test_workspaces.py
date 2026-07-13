import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from codex_deck.files import FileAccessError, ReadOnlyFileService
from codex_deck.workspaces import WorkspaceAccessError, WorkspaceStore


class WorkspaceAndFileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "allowed"
        self.workspace_path = self.root / "project"
        self.workspace_path.mkdir(parents=True)
        (self.workspace_path / "src").mkdir()
        (self.workspace_path / "src" / "main.py").write_text("print('safe')\n", encoding="utf-8")
        (self.workspace_path / ".env").write_text("SECRET=value\n", encoding="utf-8")
        (self.workspace_path / "binary.bin").write_bytes(b"\x00not text")
        self.store = WorkspaceStore(Path(self.temporary_directory.name) / "deck.db", allowed_roots=(self.root,))
        self.workspace = self.store.register(self.workspace_path, display_name="Project")
        self.files = ReadOnlyFileService(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary_directory.cleanup()

    def test_registration_stays_under_allowed_root_and_hides_path_from_catalog_contract(self) -> None:
        self.assertEqual(self.store.list()[0].display_name, "Project")
        outside = Path(self.temporary_directory.name) / "outside"
        outside.mkdir()
        with self.assertRaises(WorkspaceAccessError):
            self.store.register(outside)

    def test_file_list_and_read_are_read_only_and_deny_sensitive_paths(self) -> None:
        names = [entry.path for entry in self.files.list_directory(self.workspace.workspace_id)]
        self.assertEqual(names, ["src", "binary.bin"])
        text = self.files.read_text(self.workspace.workspace_id, "src/main.py")
        self.assertEqual(text.line_count, 1)
        self.assertIn("safe", text.content)
        with self.assertRaises(FileAccessError):
            self.files.read_text(self.workspace.workspace_id, ".env")
        with self.assertRaises(FileAccessError):
            self.files.read_text(self.workspace.workspace_id, "../outside/secret.txt")
        with self.assertRaisesRegex(ValueError, "Binary"):
            self.files.read_text(self.workspace.workspace_id, "binary.bin")


if __name__ == "__main__":
    unittest.main()
