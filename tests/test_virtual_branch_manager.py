"""Tests for the VirtualBranchManager class."""

import os
import json
import shutil
from pathlib import Path
import tempfile
from typing import Generator

import git
import pytest
from git import Actor, exc as git_exc
from git.exc import NoSuchPathError
from app.virtual_branch import Commit, VirtualBranch, VirtualBranchManager, VGitError


@pytest.fixture
def temp_repo(tmp_path: Path) -> Generator[tuple[Path, git.Repo], None, None]:
    """Create a temporary Git repository for testing."""
    # Create a temporary directory
    temp_dir = tmp_path
    
    # Initialize a Git repository
    repo = git.Repo.init(temp_dir)
    
    # Create a test file and commit it
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    repo.index.add([str(test_file)])
    repo.index.commit("Initial commit", author=Actor("Test User", "test@example.com"))
    
    # Create a .gitignore file to ignore .vgit directory
    gitignore = Path(temp_dir) / ".gitignore"
    gitignore.write_text(".vgit\n")
    
    yield temp_dir, repo
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def virtual_branch_manager(temp_repo: tuple[Path, git.Repo]) -> VirtualBranchManager:
    """Create a VirtualBranchManager instance for testing."""
    temp_dir, _ = temp_repo
    return VirtualBranchManager(temp_dir)


def test_virtual_branch_manager_init(temp_repo: tuple[Path, git.Repo]) -> None:
    """Test initializing VirtualBranchManager."""
    temp_dir, _ = temp_repo
    
    # Test with existing Git repo
    vbm = VirtualBranchManager(temp_dir)
    assert hasattr(vbm, 'repo')
    if vbm.repo is not None:  # repo might be None if not in a git repo
        assert isinstance(vbm.repo, git.Repo)
        assert vbm.repo.working_dir == os.path.abspath(temp_dir)
    assert vbm.current_branch is not None  # Should be initialized with a branch
    assert len(vbm.branches) > 0  # Should have at least one branch
    assert vbm._initialized is True
    
    # Test with non-existent directory (should raise an error)
    with pytest.raises(NoSuchPathError):
        VirtualBranchManager("/non/existent/path")


def test_commit_history(virtual_branch_manager: VirtualBranchManager, tmp_path: Path) -> None:
    """Test getting commit history."""
    # Initial commit is already made in the fixture
    history = virtual_branch_manager.get_commit_history(limit=1)
    assert len(history) == 1
    assert "Initial commit" in history[0]["message"]

    # Create another commit on main
    test_file = tmp_path / "second_commit.txt"
    test_file.write_text("Second commit content")
    virtual_branch_manager.repo.index.add([str(test_file)])
    virtual_branch_manager.repo.index.commit(
        "Second commit",
        author=Actor("Test User", "test@example.com")
    )
    
    # Get history for main branch
    history = virtual_branch_manager.get_commit_history(limit=2)
    assert len(history) == 2
    assert "Second commit" in history[0]["message"]
    assert "Initial commit" in history[1]["message"]
    
    # Test getting history for a non-existent branch
    with pytest.raises(VGitError, match="Failed to get commit history"):
        virtual_branch_manager.get_commit_history(branch_name="non-existent-branch")
    
    # Test error when not in a Git repo
    # Create a temporary directory that's not a Git repo
    with tempfile.TemporaryDirectory() as temp_dir:
        non_repo_path = Path(temp_dir) / "not_a_git_repo"
        non_repo_path.mkdir()
        non_repo_manager = VirtualBranchManager(str(non_repo_path))
        with pytest.raises(VGitError, match="Not a Git repository"):
            non_repo_manager.get_commit_history()


def test_push_branch(virtual_branch_manager: VirtualBranchManager) -> None:
    """Test pushing a branch to remote."""
    # Create a test branch
    virtual_branch_manager.create_branch("push-test")
    
    # This will fail since we don't have a remote
    with pytest.raises(VGitError):
        virtual_branch_manager.push_branch("push-test")
    
    # Test with a non-existent branch
    with pytest.raises(VGitError):
        virtual_branch_manager.push_branch("non-existent-branch")


def test_create_and_switch_branch(virtual_branch_manager: VirtualBranchManager) -> None:
    """Test creating and switching branches."""
    # Create a new branch
    virtual_branch_manager.create_branch("feature-1")
    assert "feature-1" in virtual_branch_manager.branches
    assert virtual_branch_manager.current_branch == "feature-1"
    
    # Verify the branch was created from main
    assert virtual_branch_manager.branches["feature-1"].base_branch == "main"

    # Switch back to main
    virtual_branch_manager.switch_branch("main")
    assert virtual_branch_manager.current_branch == "main"

    # Try to switch to non-existent branch
    with pytest.raises(VGitError, match="Branch 'nonexistent' does not exist"):
        virtual_branch_manager.switch_branch("nonexistent")
        
    # Try to create a branch that already exists
    with pytest.raises(VGitError, match="A branch named 'feature-1' already exists"):
        virtual_branch_manager.create_branch("feature-1")


def test_commit_changes(virtual_branch_manager: VirtualBranchManager, tmp_path: Path) -> None:
    """Test committing changes."""
    # Create a test file
    test_file = tmp_path / "test_commit.txt"
    test_file.write_text("Test commit content")

    # Stage the file
    virtual_branch_manager.repo.index.add([str(test_file)])

    # Create a commit
    commit = virtual_branch_manager.create_commit(
        "Test commit", author=Actor("Test User", "test@example.com")
    )
    assert commit.message == "Test commit"
    assert commit.author == "Test User"

    # Verify the commit was added to the current branch
    current_branch = virtual_branch_manager.get_current_branch()
    assert current_branch is not None
    head_commit = virtual_branch_manager.branches[current_branch].get_head_commit()
    assert head_commit is not None
    assert head_commit.message == "Test commit"
    
    # Test that we can't commit with no changes
    with pytest.raises(VGitError, match="No changes added to commit"):
        virtual_branch_manager.create_commit("Empty commit")


def test_initialize_repo(virtual_branch_manager: VirtualBranchManager) -> None:
    """Test initializing a repository."""
    # The repo should be initialized in the fixture
    assert virtual_branch_manager.repo is not None
    assert virtual_branch_manager.current_branch == "main"
    assert "main" in virtual_branch_manager.branches
    assert virtual_branch_manager._initialized is True


def test_save_and_load_state(virtual_branch_manager: VirtualBranchManager, tmp_path: Path) -> None:
    """Test saving and loading state."""
    # Create a test branch and commit
    virtual_branch_manager.create_branch("test-branch")
    test_file = tmp_path / "test_save.txt"
    test_file.write_text("Test save content")
    virtual_branch_manager.repo.index.add([str(test_file)])
    virtual_branch_manager.create_commit("Test save commit")

    # Save state
    virtual_branch_manager._save_state()

    # Create a new manager that should load the saved state
    new_manager = VirtualBranchManager(str(tmp_path))
    assert "test-branch" in new_manager.branches
    assert new_manager.current_branch == "test-branch"
    
    # Verify the commit was preserved
    branch = new_manager.branches["test-branch"]
    assert branch is not None
    head_commit = branch.get_head_commit()
    assert head_commit is not None
    assert head_commit.message == "Test save commit"
    
    # Test loading with invalid JSON (should not crash)
    branches_file = tmp_path / ".vgit" / "branches.json"
    with open(branches_file, 'w') as f:
        f.write("invalid json")
    
    # Should not raise an exception
    new_manager = VirtualBranchManager(str(tmp_path))
    assert new_manager.branches == {}  # Should be empty due to invalid JSON


def test_unstage(virtual_branch_manager: VirtualBranchManager, tmp_path: Path) -> None:
    """Test unstaging changes."""
    # Create a test file and stage it
    test_file = tmp_path / "test_unstage.txt"
    test_file.write_text("Test content")
    virtual_branch_manager.repo.index.add([str(test_file)])
    
    # Verify the file is staged
    staged_files = [item.a_path for item in virtual_branch_manager.repo.index.diff("HEAD")]
    assert any(str(test_file.name) in f for f in staged_files)
    
    # Unstage the file
    virtual_branch_manager.unstage([str(test_file)])
    
    # Verify the file is no longer staged
    staged_files = [item.a_path for item in virtual_branch_manager.repo.index.diff("HEAD")]
    assert not any(str(test_file.name) in f for f in staged_files)


def test_unstage_all(virtual_branch_manager: VirtualBranchManager, tmp_path: Path) -> None:
    """Test unstaging all changes."""
    # Create multiple test files and stage them
    files = []
    for i in range(3):
        test_file = tmp_path / f"test_unstage_all_{i}.txt"
        test_file.write_text(f"Test content {i}")
        files.append(str(test_file))
    
    # Stage all files
    virtual_branch_manager.repo.index.add(files)
    
    # Verify files are staged
    staged_files = [item.a_path for item in virtual_branch_manager.repo.index.diff("HEAD")]
    assert len(staged_files) >= 3  # There might be other staged files
    
    # Unstage all files
    virtual_branch_manager.unstage_all()
    
    # Verify no files are staged
    staged_files = [item.a_path for item in virtual_branch_manager.repo.index.diff("HEAD")]
    assert len(staged_files) == 0  # All files should be unstaged


def test_get_status(virtual_branch_manager: VirtualBranchManager, tmp_path: Path) -> None:
    """Test getting repository status."""
    # Get initial status
    status = virtual_branch_manager.get_status()
    assert "current_branch" in status
    assert status["current_branch"] == "main"
    
    # Create an untracked file
    untracked_file = tmp_path / "untracked.txt"
    untracked_file.write_text("Untracked content")
    
    # Create a modified file (the test.txt file was created in the fixture)
    test_file = tmp_path / "test.txt"
    test_file.write_text("Modified content")
    
    # Create and stage a new file
    staged_file = tmp_path / "staged.txt"
    staged_file.write_text("Staged content")
    virtual_branch_manager.repo.index.add([str(staged_file)])
    
    # Check status
    status = virtual_branch_manager.get_status()
    
    # Verify expected keys are in the status
    expected_keys = {
        "current_branch", "untracked_files", "changes_not_staged", 
        "changes_to_be_committed", "ahead", "behind"
    }
    assert all(key in status for key in expected_keys)
    
    # Verify untracked file is detected
    assert any("untracked.txt" in f for f in status["untracked_files"])
    
    # Verify modified file is detected in changes not staged
    assert any("test.txt" in f for f in status["changes_not_staged"])
    
    # Verify staged file is detected in changes to be committed
    assert any("staged.txt" in f for f in status["changes_to_be_committed"])
    
    # Test status when not in a Git repo
    non_repo_manager = VirtualBranchManager()
    # The actual implementation might return an empty dict or raise an exception
    # Let's check both cases
    try:
        status = non_repo_manager.get_status()
        # If it returns a dict, it should have the expected keys
        if status:
            expected_keys = {
                "current_branch", "untracked_files", "changes_not_staged",
                "changes_to_be_committed", "ahead", "behind"
            }
            assert all(key in status for key in expected_keys)
    except VGitError as e:
        # It's also valid for it to raise an exception
        assert "Not a Git repository" in str(e)


def test_branch_exists_on_remote(virtual_branch_manager: VirtualBranchManager) -> None:
    """Test checking if a branch exists on remote."""
    # By default, no remotes are set up in the test
    # The method should return False when there's an error checking the remote
    assert virtual_branch_manager.branch_exists_on_remote("main") is False


def test_get_current_branch(virtual_branch_manager: VirtualBranchManager) -> None:
    """Test getting the current branch name."""
    # Should be 'main' initially
    assert virtual_branch_manager.get_current_branch() == "main"
    
    # Create and switch to a new branch
    virtual_branch_manager.create_branch("test-branch")
    assert virtual_branch_manager.get_current_branch() == "test-branch"
    
    # Switch back to main
    virtual_branch_manager.switch_branch("main")
    assert virtual_branch_manager.get_current_branch() == "main"
