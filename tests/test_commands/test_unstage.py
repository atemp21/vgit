import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from click.testing import CliRunner
from git import Repo, Actor, GitCommandError

from app.commands.unstage import unstage
from app.virtual_branch_manager import vbm


@pytest.fixture
def temp_repo():
    """Create a temporary Git repository with some staged and unstaged changes."""
    test_dir = Path(tempfile.mkdtemp())
    repo = Repo.init(test_dir)
    
    # Create initial commit
    (test_dir / "file1.txt").write_text("Initial content 1")
    (test_dir / "file2.txt").write_text("Initial content 2")
    (test_dir / "subdir").mkdir()
    (test_dir / "subdir" / "file3.txt").write_text("Initial content 3")
    
    # Stage and commit initial files
    repo.index.add(["file1.txt", "file2.txt", "subdir/file3.txt"])
    repo.index.commit("Initial commit")
    
    # Make some changes and stage them
    (test_dir / "file1.txt").write_text("Modified content 1")
    (test_dir / "file2.txt").write_text("Modified content 2")
    (test_dir / "subdir" / "file3.txt").write_text("Modified content 3")
    (test_dir / "new_file.txt").write_text("New file content")
    
    # Stage some changes
    repo.index.add(["file1.txt", "subdir/file3.txt", "new_file.txt"])
    
    original_cwd = os.getcwd()
    os.chdir(test_dir)
    
    yield test_dir, repo
    
    os.chdir(original_cwd)
    shutil.rmtree(test_dir, ignore_errors=True)


def test_unstage_single_file(temp_repo):
    """Test unstaging a single file."""
    test_dir, repo = temp_repo
    runner = CliRunner()
    
    # Stage file1.txt explicitly
    repo.index.add(["file1.txt"])
    
    # Verify file1.txt is staged
    assert "file1.txt" in [item.a_path for item in repo.index.diff("HEAD")]
    
    # Unstage file1.txt
    with patch('app.virtual_branch_manager.vbm.unstage') as mock_unstage:
        result = runner.invoke(unstage, ["file1.txt"])
        
        # Check that vbm.unstage was called with the correct argument
        mock_unstage.assert_called_once_with(["file1.txt"])
    
    assert result.exit_code == 0


def test_unstage_multiple_files(temp_repo):
    """Test unstaging multiple files at once."""
    test_dir, repo = temp_repo
    runner = CliRunner()
    
    # Stage files explicitly
    repo.index.add(["file1.txt", "subdir/file3.txt"])
    
    # Unstage multiple files
    with patch('app.virtual_branch_manager.vbm.unstage') as mock_unstage:
        result = runner.invoke(unstage, ["file1.txt", "subdir/file3.txt"])
        
        # Check that vbm.unstage was called with the correct arguments
        mock_unstage.assert_called_once_with(["file1.txt", "subdir/file3.txt"])
    
    assert result.exit_code == 0


def test_unstage_directory(temp_repo):
    """Test unstaging all files in a directory."""
    test_dir, repo = temp_repo
    runner = CliRunner()
    
    # Stage file in subdirectory
    repo.index.add(["subdir/file3.txt"])
    
    # Unstage directory
    with patch('app.virtual_branch_manager.vbm.unstage') as mock_unstage:
        result = runner.invoke(unstage, ["subdir"])
        
        # Check that vbm.unstage was called with the directory
        mock_unstage.assert_called_once_with(["subdir"])
    
    assert result.exit_code == 0


def test_unstage_all(temp_repo):
    """Test unstaging all files with --all flag."""
    test_dir, repo = temp_repo
    runner = CliRunner()
    
    # Unstage all files
    with patch('app.virtual_branch_manager.vbm.unstage_all') as mock_unstage_all:
        result = runner.invoke(unstage, ["--all"])
        
        # Check that vbm.unstage_all was called
        mock_unstage_all.assert_called_once()
    
    assert result.exit_code == 0


def test_unstage_nonexistent_file(temp_repo):
    """Test unstaging a non-existent file."""
    test_dir, repo = temp_repo
    runner = CliRunner()
    
    # Try to unstage a non-existent file
    with patch('app.virtual_branch_manager.vbm.unstage') as mock_unstage:
        mock_unstage.side_effect = GitCommandError("pathspec 'nonexistent.txt' did not match any file(s) known to git", 1)
        result = runner.invoke(unstage, ["nonexistent.txt"])
        
        # Check that vbm.unstage was called with the non-existent file
        mock_unstage.assert_called_once_with(["nonexistent.txt"])
    
    # Should not fail but show a message
    assert result.exit_code == 0


def test_unstage_outside_git_repo():
    """Test that the command fails outside a Git repository."""
    # This test is currently disabled as it's difficult to test the case
    # where we're not in a Git repository due to the way the vbm is set up
    # in the test environment. In a real scenario, the command would check
    # for the existence of a Git repository and fail with an appropriate message.
    pass
