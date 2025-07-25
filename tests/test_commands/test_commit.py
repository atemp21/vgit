import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from click.testing import CliRunner
from git import Repo, Actor

from app.commands.commit import commit
from app.virtual_branch_manager import vbm


@pytest.fixture
def temp_repo():
    test_dir = Path(tempfile.mkdtemp())
    repo = Repo.init(test_dir)
    
    # Configure git user for the test repo
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    
    # Create an initial commit
    (test_dir / "README.md").write_text("# Test Repo")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    
    # Create a test file that we can modify
    (test_dir / "test.txt").write_text("Initial content")
    repo.index.add(["test.txt"])
    repo.index.commit("Add test.txt")
    
    # Make some changes that can be committed
    (test_dir / "test.txt").write_text("Modified content")
    
    original_cwd = os.getcwd()
    os.chdir(test_dir)
    
    yield test_dir, repo
    
    os.chdir(original_cwd)
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)


def test_commit_with_message(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo), \
         patch.object(vbm, 'current_branch', 'main'), \
         patch('app.commands.commit.vbm') as mock_vbm:
        
        # Mock the create_commit method
        mock_commit = MagicMock()
        mock_commit.id = "abc1234"
        mock_vbm.create_commit.return_value = mock_commit
        
        # Mock get_status to show staged changes
        mock_vbm.get_status.return_value = {
            'current_branch': 'main',
            'changes_to_be_committed': ['test.txt'],
            'changes_not_staged': [],
            'untracked_files': []
        }
        
        runner = CliRunner()
        result = runner.invoke(commit, ["-m", "Update test file"])
        
        assert result.exit_code == 0
        assert "[main] abc1234 Update test file" in result.output
        mock_vbm.create_commit.assert_called_once_with("Update test file")


def test_commit_allow_empty(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo), \
         patch.object(vbm, 'current_branch', 'main'), \
         patch('app.commands.commit.vbm') as mock_vbm:
        
        # Mock the create_commit method
        mock_commit = MagicMock()
        mock_commit.id = "def5678"
        mock_vbm.create_commit.return_value = mock_commit
        
        # Mock get_status to show no changes
        mock_vbm.get_status.return_value = {
            'current_branch': 'main',
            'changes_to_be_committed': [],
            'changes_not_staged': [],
            'untracked_files': []
        }
        
        runner = CliRunner()
        result = runner.invoke(commit, ["--allow-empty", "-m", "Empty commit"])
        
        assert result.exit_code == 0
        assert "[main] def5678 Empty commit" in result.output
        mock_vbm.create_commit.assert_called_once_with("Empty commit")


def test_commit_with_pathspec(temp_repo):
    test_dir, repo = temp_repo
    
    # Create a test file to commit
    test_file = test_dir / "test_file.txt"
    test_file.write_text("Test content")
    
    with patch.object(vbm, 'repo', repo), \
         patch.object(vbm, 'current_branch', 'feature'), \
         patch('app.commands.commit.vbm') as mock_vbm:
        
        # Mock the create_commit method
        mock_commit = MagicMock()
        mock_commit.id = "1234567"
        mock_vbm.create_commit.return_value = mock_commit
        
        # Mock get_status to show staged changes
        mock_vbm.get_status.return_value = {
            'current_branch': 'feature',
            'changes_to_be_committed': [str(test_file.relative_to(test_dir))],
            'changes_not_staged': [],
            'untracked_files': []
        }
        
        # Don't try to mock index.add, just run the command
        runner = CliRunner()
        result = runner.invoke(commit, ["-m", "Update specific files", str(test_file.relative_to(test_dir))])
        
        # Verify the commit was created with the right message
        assert result.exit_code == 0
        assert "[feature] 1234567 Update specific files" in result.output
        mock_vbm.create_commit.assert_called_once_with("Update specific files")


def test_commit_no_changes(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo), \
         patch.object(vbm, 'current_branch', 'main'):
        
        # Mock get_status to show no changes
        with patch.object(vbm, 'get_status') as mock_status:
            mock_status.return_value = {
                'current_branch': 'main',
                'changes_to_be_committed': [],
                'changes_not_staged': [],
                'untracked_files': []
            }
            
            runner = CliRunner()
            result = runner.invoke(commit, ["-m", "No changes"])
            
            assert result.exit_code == 0
            assert "On branch main" in result.output
            assert "nothing to commit, working tree clean" in result.output


def test_commit_no_message(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo), \
         patch('sys.stdin.isatty', return_value=True), \
         patch('sys.stdin.isatty', return_value=True), \
         patch('builtins.input', return_value=''), \
         patch('click.edit') as mock_edit:
        
        # Mock the editor to return None (user aborted)
        mock_edit.return_value = None
        
        runner = CliRunner()
        result = runner.invoke(commit)
        
        # The command should exit with code 0 even if no message is provided
        # as it will try to open an editor
        assert result.exit_code == 0
        assert "Aborting commit due to empty commit message." in result.output


def test_commit_outside_git_repo():
    original_repo = vbm.repo
    vbm.repo = None
    
    try:
        runner = CliRunner()
        result = runner.invoke(commit, ["-m", "Test commit"])
        
        # The command exits with code 0 but shows an error message
        assert result.exit_code == 0
        assert "not a git repository" in result.output.lower()
    finally:
        vbm.repo = original_repo
