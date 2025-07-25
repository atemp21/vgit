import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from click.testing import CliRunner
from git import Repo, Actor

from app.commands.branch import branch
from app.virtual_branch_manager import vbm


@pytest.fixture
def temp_repo():
    test_dir = Path(tempfile.mkdtemp())
    repo = Repo.init(test_dir)

    author = Actor("Test User", "test@example.com")

    (test_dir / "README.md").write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit", author=author)

    # Create a second branch for testing
    repo.create_head("test-branch")

    original_cwd = os.getcwd()
    os.chdir(test_dir)

    yield test_dir, repo

    os.chdir(original_cwd)
    shutil.rmtree(test_dir, ignore_errors=True)


def test_branch_list_branches():
    with patch.object(vbm, "repo", True):
        with patch.object(vbm, "current_branch", "main"):
            with patch.object(vbm, "branches", {"main": None, "test-branch": None}):
                runner = CliRunner()
                result = runner.invoke(branch, ["--list-branches"])

                assert result.exit_code == 0
                assert "* main" in result.output
                assert "  test-branch" in result.output


def test_branch_list_branches_no_branches():
    with patch.object(vbm, "repo", True):
        with patch.object(vbm, "branches", {}):
            runner = CliRunner()
            result = runner.invoke(branch, ["--list-branches"])

            assert result.exit_code == 0
            assert "No branches available." in result.output


def test_branch_create_new():
    with patch.object(vbm, "repo", True):
        with patch.object(vbm, "branches", {"main": None}):
            with patch.object(vbm, "create_branch") as mock_create:
                runner = CliRunner()
                result = runner.invoke(branch, ["new-feature"])

                assert result.exit_code == 0
                mock_create.assert_called_once_with("new-feature")
                assert "Created branch 'new-feature'" in result.output


def test_branch_create_already_exists():
    with patch.object(vbm, "repo", True):
        with patch.object(vbm, "branches", {"main": None, "existing": None}):
            runner = CliRunner()
            result = runner.invoke(branch, ["existing"])

            # The command returns 0 even on error
            assert result.exit_code == 0
            assert "fatal: A branch named 'existing' already exists." in result.output


def test_branch_delete():
    with patch.object(vbm, "repo", True):
        with patch.object(vbm, "branches", {"main": None, "to-delete": None}):
            with patch.object(vbm, "current_branch", "main"):
                with patch.object(vbm, "_save_state") as mock_save:
                    runner = CliRunner()
                    result = runner.invoke(branch, ["--delete", "to-delete"])

                    assert result.exit_code == 0
                    assert "to-delete" not in vbm.branches
                    mock_save.assert_called_once()
                    assert "Deleted branch to-delete" in result.output


def test_branch_delete_non_existent():
    with patch.object(vbm, "repo", True):
        with patch.object(vbm, "branches", {"main": None}):
            runner = CliRunner()
            result = runner.invoke(branch, ["--delete", "nonexistent"])

            # The command returns 0 even on error
            assert result.exit_code == 0
            assert "error: branch 'nonexistent' not found." in result.output


def test_branch_delete_current_branch():
    with patch.object(vbm, "repo", True):
        with patch.object(vbm, "branches", {"main": None}):
            with patch.object(vbm, "current_branch", "main"):
                runner = CliRunner()
                result = runner.invoke(branch, ["--delete", "main"])

                # The command returns 0 even on error
                assert result.exit_code == 0
                assert (
                    "Cannot delete branch 'main' as it is the current branch"
                    in result.output
                )


def test_branch_rename(monkeypatch):
    with patch.object(vbm, "repo", True):
        with patch.object(
            vbm, "branches", {"main": MagicMock(), "old-name": MagicMock()}
        ):
            with patch.object(vbm, "current_branch", "main"):
                with patch.object(vbm, "_save_state") as mock_save:
                    # Mock the click.prompt to return 'new-name'
                    monkeypatch.setattr("click.prompt", lambda x: "new-name")

                    # Mock the branch object's name attribute
                    mock_branch = MagicMock()
                    mock_branch.name = "old-name"
                    vbm.branches["old-name"] = mock_branch

                    runner = CliRunner()
                    result = runner.invoke(branch, ["--rename", "old-name"])

                    assert result.exit_code == 0
                    assert "old-name" not in vbm.branches
                    assert "new-name" in vbm.branches
                    mock_save.assert_called_once()
                    assert "Renamed old-name to new-name" in result.output


def test_branch_rename_to_existing(monkeypatch):
    with patch.object(vbm, "repo", True):
        with patch.object(vbm, "branches", {"main": None, "existing": None}):
            # Mock the click.prompt to return 'existing'
            monkeypatch.setattr("click.prompt", lambda x: "existing")

            runner = CliRunner()
            result = runner.invoke(branch, ["--rename", "main"])

            # The command returns 0 even on error
            assert result.exit_code == 0
            assert "fatal: A branch named 'existing' already exists." in result.output


def test_branch_outside_git_repo():
    original_repo = vbm.repo
    vbm.repo = None

    try:
        runner = CliRunner()
        result = runner.invoke(branch)

        # The command returns 0 even when outside a git repo
        assert result.exit_code == 0
        assert "not a git repository" in result.output.lower()
    finally:
        vbm.repo = original_repo
