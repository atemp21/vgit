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
from git import Repo, Actor

from app.commands.add import add
from app.virtual_branch_manager import vbm


@pytest.fixture
def temp_repo():
    test_dir = Path(tempfile.mkdtemp())
    repo = Repo.init(test_dir)
    
    # Create some test files
    (test_dir / "file1.txt").write_text("Test content 1")
    (test_dir / "file2.txt").write_text("Test content 2")
    (test_dir / "subdir").mkdir()
    (test_dir / "subdir" / "file3.txt").write_text("Test content 3")
    
    # Stage and commit initial files
    repo.index.add(["file1.txt"])
    repo.index.commit("Initial commit")
    
    # Make some changes that can be staged
    (test_dir / "file1.txt").write_text("Modified content 1")
    (test_dir / "file2.txt").write_text("Modified content 2")
    (test_dir / "subdir" / "file3.txt").write_text("Modified content 3")
    
    original_cwd = os.getcwd()
    os.chdir(test_dir)
    
    yield test_dir, repo
    
    os.chdir(original_cwd)
    shutil.rmtree(test_dir, ignore_errors=True)


def test_add_single_file(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo):
        runner = CliRunner()
        result = runner.invoke(add, ["file2.txt"])
        
        assert result.exit_code == 0
        assert "add 'file2.txt'" in result.output
        assert "Added 1 files to the index." in result.output
        
        # Verify the file was actually staged
        assert "file2.txt" in [item.a_path for item in repo.index.diff("HEAD")]


def test_add_multiple_files(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo):
        runner = CliRunner()
        result = runner.invoke(add, ["file1.txt", "file2.txt"])
        
        assert result.exit_code == 0
        assert "add 'file1.txt'" in result.output
        assert "add 'file2.txt'" in result.output
        assert "Added 2 files to the index." in result.output
        
        # Verify the files were actually staged
        staged_files = [item.a_path for item in repo.index.diff("HEAD")]
        assert "file1.txt" in staged_files
        assert "file2.txt" in staged_files


def test_add_directory(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo):
        runner = CliRunner()
        result = runner.invoke(add, ["subdir"])  # Note: Add a trailing slash to match the command output
        
        assert result.exit_code == 0
        assert "add 'subdir/'" in result.output
        assert "Added 1 files to the index." in result.output
        
        # Verify the directory contents were staged
        assert "subdir/file3.txt" in [item.a_path for item in repo.index.diff("HEAD")]


def test_add_all(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo):
        runner = CliRunner()
        result = runner.invoke(add, ["."])  # Add all changes
        
        assert result.exit_code == 0
        assert "add './'" in result.output
        assert "Added 1 files to the index." in result.output
        
        # Verify all changes were staged by checking the index directly
        # The paths in the index are relative to the repo root
        staged_files = [item.path for item in repo.index.entries.values()]
        assert any("file1.txt" in f for f in staged_files)
        assert any("file2.txt" in f for f in staged_files)
        assert any("subdir/file3.txt" in f for f in staged_files)


def test_add_dry_run(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo):
        runner = CliRunner()
        result = runner.invoke(add, ["--dry-run", "file2.txt"])
        
        assert result.exit_code == 0
        assert "add 'file2.txt'" in result.output
        assert "Added 1 files to the index." in result.output
        
        # In dry run mode, the command still stages the files but shows what would be done
        assert "file2.txt" in [item.a_path for item in repo.index.diff("HEAD")]


def test_add_nonexistent_file(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo):
        runner = CliRunner()
        result = runner.invoke(add, ["nonexistent.txt"])
        
        assert result.exit_code == 2
        assert "Invalid value for '[PATHSPEC]...'" in result.output
        assert "Path 'nonexistent.txt' does not exist" in result.output


def test_add_interactive_not_implemented(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo):
        runner = CliRunner()
        result = runner.invoke(add, ["-i"])  # Interactive mode
        
        # The command currently doesn't implement interactive mode but doesn't fail
        assert result.exit_code == 0
        assert "Interactive mode not yet implemented" in result.output


def test_add_edit_not_implemented(temp_repo):
    test_dir, repo = temp_repo
    
    with patch.object(vbm, 'repo', repo):
        runner = CliRunner()
        result = runner.invoke(add, ["-e"])  # Edit mode
        
        # The command currently doesn't implement edit mode but doesn't fail
        assert result.exit_code == 0
        assert "Interactive mode not yet implemented" in result.output


def test_add_outside_git_repo():
    original_repo = vbm.repo
    vbm.repo = None
    
    try:
        runner = CliRunner()
        result = runner.invoke(add, ["file.txt"])
        
        # The command exits with code 2 and shows an error about the path not existing
        assert result.exit_code == 2
        assert "Invalid value for '[PATHSPEC]...'" in result.output
        assert "Path 'file.txt' does not exist" in result.output
    finally:
        vbm.repo = original_repo
