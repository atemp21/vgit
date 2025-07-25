import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from click.testing import CliRunner

from app.commands.push import push
from app.virtual_branch_manager import vbm


@pytest.fixture
def temp_repo():
    test_dir = Path("/tmp/test_vgit_push")
    test_dir.mkdir(exist_ok=True)
    
    # Create a git repo
    os.system(f"git -C {test_dir} init")
    
    # Create a test file and commit it
    (test_dir / "test.txt").write_text("test")
    os.system(f"git -C {test_dir} add .")
    os.system(f"git -C {test_dir} commit -m 'Initial commit'")
    
    # Create a test branch
    os.system(f"git -C {test_dir} checkout -b test-branch")
    
    # Add a remote
    os.system(f"git -C {test_dir} remote add origin https://github.com/test/test.git")
    
    original_cwd = os.getcwd()
    os.chdir(test_dir)
    
    yield test_dir
    
    os.chdir(original_cwd)
    # Clean up
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)


def test_push_success(temp_repo):
    with patch.object(vbm, 'repo', MagicMock()):
        with patch.object(vbm, 'get_current_branch', return_value='test-branch'), \
             patch.object(vbm, 'branch_exists_on_remote', return_value=False), \
             patch.object(vbm, 'push_branch') as mock_push:
            
            runner = CliRunner()
            result = runner.invoke(push, ["origin", "test-branch"])
            
            assert result.exit_code == 0
            assert "set up to track remote branch 'test-branch'" in result.output
            mock_push.assert_called_once_with(
                local_branch='test-branch',
                remote_branch='test-branch',
                force=False
            )


def test_push_force(temp_repo):
    with patch.object(vbm, 'repo', MagicMock()):
        with patch.object(vbm, 'get_current_branch', return_value='test-branch'), \
             patch.object(vbm, 'branch_exists_on_remote', return_value=True), \
             patch.object(vbm, 'push_branch') as mock_push:
            
            runner = CliRunner()
            result = runner.invoke(push, ["--force", "origin", "test-branch"])
            
            assert result.exit_code == 0
            assert "Successfully pushed to origin/test-branch" in result.output
            mock_push.assert_called_once_with(
                local_branch='test-branch',
                remote_branch='test-branch',
                force=True
            )


def test_push_dry_run(temp_repo):
    with patch.object(vbm, 'repo', MagicMock()):
        with patch.object(vbm, 'get_current_branch', return_value='test-branch'):
            
            runner = CliRunner()
            result = runner.invoke(push, ["--dry-run", "origin", "test-branch"])
            
            assert result.exit_code == 0
            assert "Would push 'test-branch' to 'origin'" in result.output


def test_push_current_branch(temp_repo):
    with patch.object(vbm, 'repo', MagicMock()):
        with patch.object(vbm, 'get_current_branch', return_value='current-branch'), \
             patch.object(vbm, 'branch_exists_on_remote', return_value=False), \
             patch.object(vbm, 'push_branch') as mock_push:
            
            runner = CliRunner()
            result = runner.invoke(push, ["origin"])
            
            assert result.exit_code == 0
            assert "set up to track remote branch 'current-branch'" in result.output
            mock_push.assert_called_once_with(
                local_branch='current-branch',
                remote_branch='current-branch',
                force=False
            )


def test_push_not_in_git_repo():
    original_repo = vbm.repo
    vbm.repo = None
    
    try:
        runner = CliRunner()
        result = runner.invoke(push, ["origin", "test-branch"])
        
        # The command exits with code 0 but shows an error message
        assert result.exit_code == 0
        assert "not a git repository" in result.output.lower()
    finally:
        vbm.repo = original_repo


def test_push_no_branch(temp_repo):
    with patch.object(vbm, 'repo', MagicMock()):
        with patch.object(vbm, 'get_current_branch', return_value=None), \
             patch.object(vbm, 'branch_exists_on_remote', return_value=False):
            
            runner = CliRunner()
            result = runner.invoke(push, ["origin"])
            
            # The command exits with code 0 but shows an error message
            assert result.exit_code == 0
            assert "not currently on any branch" in result.output.lower()


def test_push_vgiterror_handling(temp_repo, monkeypatch):
    """Test that VGitError from push_branch is caught and error message is printed."""
    from app.virtual_branch import VGitError
    
    # Mock the system exit to prevent the test from exiting
    def mock_sys_exit(code=0):
        raise RuntimeError(f"SystemExit with code {code}")
    
    with patch.object(vbm, 'repo', MagicMock()):
        with patch.object(vbm, 'get_current_branch', return_value='test-branch'), \
             patch.object(vbm, 'branch_exists_on_remote', return_value=False), \
             patch.object(vbm, 'push_branch', side_effect=VGitError("Push failed")):
            
            # Test the push function directly to verify it returns 1 on error
            return_value = push.callback(force=False, dry_run=False, remote="origin", branch="test-branch")
            assert return_value == 1, f"Expected return value 1, got {return_value}"
            
            # Test with CliRunner to verify error message is printed to stderr
            runner = CliRunner()
            result = runner.invoke(push, ["origin", "test-branch"])
            
            # Verify the error message is in stderr
            assert "error: Push failed" in result.stderr


def test_push_unexpected_error(temp_repo):
    """Test that unexpected errors from push_branch propagate and are handled."""
    with patch.object(vbm, 'repo', MagicMock()):
        with patch.object(vbm, 'get_current_branch', return_value='test-branch'), \
             patch.object(vbm, 'branch_exists_on_remote', return_value=False), \
             patch.object(vbm, 'push_branch', side_effect=Exception("Unexpected error")):
            
            # Test with CliRunner to verify the error is handled
            runner = CliRunner()
            result = runner.invoke(push, ["origin", "test-branch"])
            
            # The error message should be in stderr with 'fatal:' prefix
            assert "fatal: Unexpected error" in result.stderr
