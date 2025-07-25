import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from click.testing import CliRunner
from git import Repo

from app.commands.status import status
from app.virtual_branch_manager import vbm


@pytest.fixture
def temp_repo():
    test_dir = Path(tempfile.mkdtemp())
    repo = Repo.init(test_dir)
    
    (test_dir / "README.md").write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    
    (test_dir / "test.txt").write_text("Test content")
    repo.index.add(["test.txt"])
    repo.index.commit("Add test file")
    
    original_cwd = os.getcwd()
    os.chdir(test_dir)
    
    yield test_dir, repo
    
    os.chdir(original_cwd)
    shutil.rmtree(test_dir, ignore_errors=True)


@patch("app.virtual_branch_manager.vbm.get_status")
def test_status_clean_working_directory(mock_get_status, temp_repo):
    mock_get_status.return_value = {
        "current_branch": "main",
        "untracked": [],
        "staged": [],
        "unstaged": []
    }
    
    runner = CliRunner()
    result = runner.invoke(status)
    
    assert result.exit_code == 0
    assert "nothing to commit, working tree clean" in result.output


@patch("app.virtual_branch_manager.vbm.get_status")
def test_status_with_untracked_files(mock_get_status, temp_repo):
    mock_get_status.return_value = {
        "current_branch": "main",
        "untracked": ["new_file.txt"],
        "staged": [],
        "unstaged": []
    }
    
    runner = CliRunner()
    result = runner.invoke(status)
    
    assert result.exit_code == 0
    assert "Untracked files:" in result.output
    assert "new_file.txt" in result.output


@patch("app.virtual_branch_manager.vbm.get_status")
def test_status_with_modified_files(mock_get_status, temp_repo):
    mock_get_status.return_value = {
        "current_branch": "main",
        "untracked": [],
        "staged": [],
        "unstaged": ["README.md"]
    }
    
    runner = CliRunner()
    result = runner.invoke(status)
    
    assert result.exit_code == 0
    assert "Changes not staged for commit:" in result.output
    assert "README.md" in result.output


@patch("app.virtual_branch_manager.vbm.get_status")
def test_status_with_staged_files(mock_get_status, temp_repo):
    mock_get_status.return_value = {
        "current_branch": "main",
        "untracked": [],
        "staged": ["README.md"],
        "unstaged": []
    }
    
    runner = CliRunner()
    result = runner.invoke(status)
    
    assert result.exit_code == 0
    assert "Changes to be committed:" in result.output
    assert "README.md" in result.output


def test_status_with_pathspec(temp_repo):
    test_dir, _ = temp_repo
    runner = CliRunner()
    result = runner.invoke(status, ["README.md"])
    
    assert result.exit_code == 0


@patch("app.commands.status.vbm")
def test_status_error_handling(mock_vbm, temp_repo):
    mock_vbm.get_status.side_effect = Exception("Test error")
    
    runner = CliRunner()
    result = runner.invoke(status)
    
    assert result.exit_code == 0
    assert "error: Test error" in result.output


@patch("app.commands.status.vbm")
def test_status_outside_git_repo(mock_vbm):
    mock_vbm.repo = None
    
    runner = CliRunner()
    result = runner.invoke(status)
    
    assert result.exit_code == 0
    assert "fatal: not a git repository" in result.output.lower()
