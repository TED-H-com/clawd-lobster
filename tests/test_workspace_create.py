import sys
import importlib.util
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Dynamically import workspace-create.py because of the hyphen
script_path = Path(__file__).resolve().parent.parent / "scripts" / "workspace-create.py"
spec = importlib.util.spec_from_file_location("workspace_create", str(script_path))
workspace_create = importlib.util.module_from_spec(spec)
sys.modules["workspace_create"] = workspace_create
spec.loader.exec_module(workspace_create)


class TestWorkspaceCreateValidation(unittest.TestCase):
    def test_validate_name_valid(self):
        self.assertEqual(workspace_create.validate_name("test-app"), "test-app")
        self.assertEqual(workspace_create.validate_name("app123"), "app123")
        self.assertEqual(workspace_create.validate_name("my-awesome-workspace-1"), "my-awesome-workspace-1")

    def test_validate_name_strip(self):
        self.assertEqual(workspace_create.validate_name("  test-app  "), "test-app")

    def test_validate_name_invalid(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            workspace_create.validate_name("")
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            workspace_create.validate_name("   ")
        with self.assertRaisesRegex(ValueError, "Invalid name"):
            workspace_create.validate_name("test_app") # No underscore
        with self.assertRaisesRegex(ValueError, "Invalid name"):
            workspace_create.validate_name("Test-App") # No uppercase
        with self.assertRaisesRegex(ValueError, "Invalid name"):
            workspace_create.validate_name("-test-app") # No leading hyphen
        with self.assertRaisesRegex(ValueError, "Invalid name"):
            workspace_create.validate_name("test-app-") # No trailing hyphen
        with self.assertRaisesRegex(ValueError, "Invalid name"):
            workspace_create.validate_name("test app") # No spaces

    def test_validate_domain_valid(self):
        self.assertEqual(workspace_create.validate_domain("work"), "work")
        self.assertEqual(workspace_create.validate_domain("personal"), "personal")
        self.assertEqual(workspace_create.validate_domain("hybrid"), "hybrid")

    def test_validate_domain_strip_lower(self):
        self.assertEqual(workspace_create.validate_domain("  WORK  "), "work")
        self.assertEqual(workspace_create.validate_domain("PeRsOnAl"), "personal")

    def test_validate_domain_invalid(self):
        with self.assertRaisesRegex(ValueError, "Invalid domain"):
            workspace_create.validate_domain("unknown")
        with self.assertRaisesRegex(ValueError, "Invalid domain"):
            workspace_create.validate_domain("")

from unittest.mock import patch, MagicMock

class TestCreateWorkspace(unittest.TestCase):

    @patch("workspace_create.resolve_workspace_root")
    @patch("workspace_create.create_directory_structure")
    @patch("workspace_create.create_knowledge_index")
    @patch("workspace_create.create_openspec_project")
    @patch("workspace_create.create_claude_md")
    @patch("workspace_create.create_gitignore")
    @patch("workspace_create.init_memory_db")
    @patch("workspace_create.init_git_repo")
    @patch("workspace_create.register_workspace")
    @patch("workspace_create.TEMPLATES_DIR")
    @patch("shutil.copy2")
    def test_create_workspace_success(self, mock_copy, mock_templates_dir, mock_register, mock_git, mock_memory,
                                     mock_gitignore, mock_claude_md, mock_openspec, mock_knowledge,
                                     mock_mkdir, mock_resolve_root):

        # Setup mocks
        mock_root = MagicMock()
        mock_resolve_root.return_value = mock_root

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_root.__truediv__.return_value = mock_path

        mock_memory.return_value = True
        mock_git.return_value = True
        mock_register.return_value = True

        mock_templates_dir.return_value = MagicMock()

        # Execute
        summary = workspace_create.create_workspace("test-app", "work", "desc", create_repo=False, dry_run=False)

        # Assertions
        self.assertEqual(summary["name"], "test-app")
        self.assertEqual(summary["domain"], "work")
        self.assertEqual(summary["description"], "desc")
        self.assertFalse(summary["dry_run"])
        self.assertTrue(summary["git_initialized"])
        self.assertTrue(summary["memory_initialized"])
        self.assertTrue(summary["registered"])

        # Verify function calls
        mock_resolve_root.assert_called_once()
        mock_mkdir.assert_called_once_with(mock_path, False)
        mock_knowledge.assert_called_once_with(mock_path, "test-app", False)
        mock_openspec.assert_called_once_with(mock_path, "test-app", "desc", False)
        mock_claude_md.assert_called_once_with(mock_path, "test-app", "desc", "work", False)
        mock_gitignore.assert_called_once_with(mock_path, False)
        mock_memory.assert_called_once_with(mock_path, False)
        mock_git.assert_called_once_with(mock_path, "test-app", False)
        mock_register.assert_called_once_with("test-app", mock_path, "work", "", False)


    @patch("workspace_create.resolve_workspace_root")
    def test_create_workspace_already_exists(self, mock_resolve_root):
        # Setup mocks
        mock_root = MagicMock()
        mock_resolve_root.return_value = mock_root

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.iterdir.return_value = [1] # Not empty
        mock_root.__truediv__.return_value = mock_path

        # Execute & Assert
        with self.assertRaisesRegex(FileExistsError, "already exists and is not empty"):
            workspace_create.create_workspace("test-app")


    @patch("workspace_create.resolve_workspace_root")
    @patch("workspace_create.create_directory_structure")
    @patch("workspace_create.create_knowledge_index")
    @patch("workspace_create.create_openspec_project")
    @patch("workspace_create.create_claude_md")
    @patch("workspace_create.create_gitignore")
    @patch("workspace_create.init_memory_db")
    @patch("workspace_create.init_git_repo")
    @patch("workspace_create.create_github_repo")
    @patch("workspace_create.register_workspace")
    @patch("workspace_create.TEMPLATES_DIR")
    @patch("shutil.copy2")
    def test_create_workspace_with_github(self, mock_copy, mock_templates_dir, mock_register, mock_github, mock_git, mock_memory,
                                         mock_gitignore, mock_claude_md, mock_openspec, mock_knowledge,
                                         mock_mkdir, mock_resolve_root):

        # Setup mocks
        mock_root = MagicMock()
        mock_resolve_root.return_value = mock_root

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_root.__truediv__.return_value = mock_path

        mock_github.return_value = "git@github.com:user/test-app.git"

        # Execute
        summary = workspace_create.create_workspace("test-app", create_repo=True)

        # Assertions
        self.assertEqual(summary["github_repo"], "git@github.com:user/test-app.git")
        mock_github.assert_called_once_with(mock_path, "test-app", False)


if __name__ == "__main__":
    unittest.main()
