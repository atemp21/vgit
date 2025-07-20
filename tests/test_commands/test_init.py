"""Tests for the init command."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from git import Repo

from app.commands.init import init
from app.virtual_branch_manager import vbm


@pytest.fixture
def temp_dir():
    """Create and clean up a temporary directory for tests."""
    test_dir = Path(tempfile.mkdtemp())
    original_cwd = os.getcwd()
    os.chdir(test_dir)

    # Reset the VBM state
    vbm.repo = None
    if hasattr(vbm, "_initialized"):
        delattr(vbm, "_initialized")

    yield test_dir

    # Cleanup
    os.chdir(original_cwd)
    shutil.rmtree(test_dir, ignore_errors=True)


def test_init_in_current_directory(temp_dir):
    """Test initializing in the current directory."""
    runner = CliRunner()
    result = runner.invoke(init, [])
    assert result.exit_code == 0
    assert "Initialized empty VGit repository" in result.output
    assert (temp_dir / ".git").exists()
    assert (temp_dir / ".vgit").exists()


def test_init_in_specified_directory(temp_dir):
    """Test initializing in a specified directory."""
    runner = CliRunner()
    repo_dir = temp_dir / "test_repo"
    result = runner.invoke(init, [str(repo_dir)])

    assert result.exit_code == 0
    assert "Initialized empty VGit repository" in result.output
    assert (repo_dir / ".git").exists()
    assert (repo_dir / ".vgit").exists()


def test_reinitialize_existing_repo(temp_dir):
    """Test reinitializing an existing repository."""
    runner = CliRunner()
    # First initialization
    result1 = runner.invoke(init, [])
    assert result1.exit_code == 0

    # Reinitialize
    result2 = runner.invoke(init, [])
    assert result2.exit_code == 0
    assert "Reinitialized existing VGit repository" in result2.output


def test_init_in_non_existent_directory(temp_dir):
    """Test initializing in a non-existent directory."""
    runner = CliRunner()
    repo_dir = temp_dir / "non_existent" / "repo"
    result = runner.invoke(init, [str(repo_dir)])

    assert result.exit_code == 0
    assert "Initialized empty VGit repository" in result.output
    assert (repo_dir / ".git").exists()
    assert (repo_dir / ".vgit").exists()


@patch("app.commands.init.Repo.init")
@patch("app.commands.init.os.makedirs")
def test_init_git_error(mock_makedirs, mock_repo_init, temp_dir):
    """Test handling of Git repository initialization errors."""
    runner = CliRunner()
    mock_repo_init.side_effect = Exception("Git initialization failed")

    result = runner.invoke(init, [])
    assert result.exit_code == 0  # Command returns 0 even on error
    assert "Git initialization failed" in str(result.output)


@patch("app.commands.init.os.makedirs")
def test_init_directory_creation_error(mock_makedirs, temp_dir):
    """Test handling of directory creation errors."""
    runner = CliRunner()
    mock_makedirs.side_effect = OSError("Permission denied")

    result = runner.invoke(init, ["test_repo"])
    assert result.exit_code == 0  # Command returns 0 even on error
    assert "Permission denied" in str(result.output)


def test_init_creates_initial_commit(temp_dir):
    """Test that initializing creates an initial commit."""
    runner = CliRunner()
    result = runner.invoke(init, [])
    assert result.exit_code == 0

    repo = Repo(".")
    assert not repo.bare
    assert len(list(repo.iter_commits())) > 0  # At least one commit exists
