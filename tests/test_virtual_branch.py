import tempfile
import unittest
from unittest.mock import patch

from vgit.virtual_branch import VirtualBranch, VirtualBranchManager


class TestVirtualBranch(unittest.TestCase):
    def test_virtual_branch_creation(self):
        branch = VirtualBranch("test-branch")
        self.assertEqual(branch.name, "test-branch")
        self.assertEqual(branch.base_branch, "main")
        self.assertEqual(len(branch.commits), 0)

    def test_add_commit(self):
        branch = VirtualBranch("test-branch")
        branch.add_commit("Initial commit")
        self.assertEqual(len(branch.commits), 1)
        self.assertEqual(branch.commits[0], "Initial commit")


class TestVirtualBranchManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = VirtualBranchManager(self.temp_dir)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("git.Repo")
    def test_initialize_repo(self, mock_repo):
        self.manager.initialize_repo()
        self.assertIsNotNone(self.manager.repo)

    def test_create_branch(self):
        self.manager.initialize_repo()
        self.manager.create_branch("feature/test")
        self.assertIn("feature/test", self.manager.branches)
        self.assertEqual(self.manager.current_branch, "feature/test")

    def test_switch_branch(self):
        self.manager.initialize_repo()
        self.manager.create_branch("feature/test")
        self.manager.switch_branch("main")
        self.assertEqual(self.manager.current_branch, "main")

    def test_commit(self):
        self.manager.initialize_repo()
        self.manager.create_branch("feature/test")
        self.manager.commit("Test commit")
        self.assertEqual(len(self.manager.branches["feature/test"].commits), 1)


if __name__ == "__main__":
    unittest.main()
