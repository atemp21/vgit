import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from click.testing import CliRunner
from git import Repo, Actor

from app.commands.log import log
from app.virtual_branch_manager import vbm


@pytest.fixture
def temp_repo():
    test_dir = Path(tempfile.mkdtemp())
    repo = Repo.init(test_dir)

    author = Actor("Test User", "test@example.com")

    (test_dir / "README.md").write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit", author=author)

    (test_dir / "test.txt").write_text("Test content")
    repo.index.add(["test.txt"])
    repo.index.commit("Add test file", author=author)

    original_cwd = os.getcwd()
    os.chdir(test_dir)

    yield test_dir, repo

    os.chdir(original_cwd)
    shutil.rmtree(test_dir, ignore_errors=True)


@patch("app.commands.log.vbm.get_commit_history")
def test_log_with_no_commits(mock_get_commit_history):
    mock_get_commit_history.return_value = []

    runner = CliRunner()
    result = runner.invoke(log)

    assert result.exit_code == 0
    assert "No commits yet" in result.output


@patch("app.commands.log.vbm.get_commit_history")
def test_log_basic(mock_get_commit_history, temp_repo):
    mock_commits = [
        {
            "id": "abc1234",
            "author": "Test User <test@example.com>",
            "date": "2023-01-01 12:00:00 -0700",
            "message": "Second commit",
        },
        {
            "id": "def5678",
            "author": "Test User <test@example.com>",
            "date": "2023-01-01 10:00:00 -0700",
            "message": "Initial commit",
        },
    ]
    mock_get_commit_history.return_value = mock_commits

    runner = CliRunner()
    result = runner.invoke(log)

    assert result.exit_code == 0
    assert "commit abc1234" in result.output
    assert "Author: Test User <test@example.com>" in result.output
    assert "Second commit" in result.output
    assert "commit def5678" in result.output
    assert "Initial commit" in result.output


@patch("app.commands.log.vbm.get_commit_history")
def test_log_oneline(mock_get_commit_history, temp_repo):
    mock_commits = [
        {
            "id": "abc1234",
            "author": "Test User <test@example.com>",
            "date": "2023-01-01 12:00:00 -0700",
            "message": "Second commit",
        }
    ]
    mock_get_commit_history.return_value = mock_commits

    runner = CliRunner()
    result = runner.invoke(log, ["--oneline"])

    assert result.exit_code == 0
    assert "abc1234 Second commit" in result.output


@patch("app.commands.log.vbm.get_commit_history")
def test_log_with_max_count(mock_get_commit_history, temp_repo):
    # Create a side effect function that respects the limit parameter
    def get_commit_history_side_effect(limit=100):
        mock_commits = [
            {
                "id": f"commit{i}",
                "author": "Test",
                "date": "2023-01-01",
                "message": f"Commit {i}",
            }
            for i in range(5)
        ]
        return mock_commits[:limit] if limit else mock_commits

    mock_get_commit_history.side_effect = get_commit_history_side_effect

    runner = CliRunner()
    result = runner.invoke(log, ["-n", "3"])

    # Verify the limit was passed to get_commit_history
    mock_get_commit_history.assert_called_once_with(limit=3)

    # Verify the output contains exactly 3 commits
    assert result.exit_code == 0
    assert result.output.count("commit commit") == 3  # Should only show 3 commits


@patch("app.commands.log.vbm.get_commit_history")
def test_log_with_stat(mock_get_commit_history, temp_repo):
    mock_commits = [
        {
            "id": "abc1234",
            "author": "Test User <test@example.com>",
            "date": "2023-01-01 12:00:00 -0700",
            "message": "Second commit",
        }
    ]
    mock_get_commit_history.return_value = mock_commits

    runner = CliRunner()
    result = runner.invoke(log, ["--stat"])

    assert result.exit_code == 0
    assert "stat output not implemented" in result.output


@patch("app.commands.log.vbm.repo", None)
def test_log_outside_git_repo():
    runner = CliRunner()
    result = runner.invoke(log)

    # The implementation returns 0 even when not in a git repo
    assert result.exit_code == 0
    assert "not a git repository" in result.output.lower()
