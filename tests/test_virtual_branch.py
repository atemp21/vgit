"""Tests for the VirtualBranch class."""

import pytest
from datetime import datetime
from app.virtual_branch import VirtualBranch, Commit, VGitError


def test_virtual_branch_creation():
    """Test creating a new VirtualBranch instance."""
    branch = VirtualBranch(name="feature/test")
    
    assert branch.name == "feature/test"
    assert branch.base_branch == "main"
    assert branch.commits == []
    assert branch.created_at is not None
    assert branch.updated_at is not None
    # Allow for small differences in timestamps due to execution time
    assert abs(branch.created_at - branch.updated_at) < 0.1


def test_virtual_branch_add_commit():
    """Test adding a commit to a VirtualBranch."""
    branch = VirtualBranch(name="feature/test")
    commit = Commit(
        id="abc123",
        message="Initial commit",
        author="Test User <test@example.com>",
        timestamp=datetime.now().timestamp(),
        parent_ids=[],
        metadata={"key": "value"}
    )
    
    # Add the commit
    branch.add_commit(commit)
    
    # Verify the commit was added
    assert len(branch.commits) == 1
    assert branch.commits[0] == commit
    assert branch.updated_at >= branch.created_at


def test_virtual_branch_get_head_commit():
    """Test getting the head commit of a VirtualBranch."""
    branch = VirtualBranch(name="feature/test")
    
    # Test with no commits
    assert branch.get_head_commit() is None
    
    # Add a commit
    commit = Commit(
        id="abc123",
        message="Initial commit",
        author="Test User <test@example.com>",
        timestamp=datetime.now().timestamp()
    )
    branch.add_commit(commit)
    
    # Test with one commit
    assert branch.get_head_commit() == commit
    
    # Add another commit
    commit2 = Commit(
        id="def456",
        message="Second commit",
        author="Test User <test@example.com>",
        timestamp=datetime.now().timestamp() + 1
    )
    branch.add_commit(commit2)
    
    # Test with multiple commits
    assert branch.get_head_commit() == commit2


def test_virtual_branch_serialization():
    """Test serialization and deserialization of VirtualBranch."""
    # Create a branch with commits
    branch = VirtualBranch(name="feature/test")
    commit = Commit(
        id="abc123",
        message="Initial commit",
        author="Test User <test@example.com>",
        timestamp=datetime.now().timestamp()
    )
    branch.add_commit(commit)
    
    # Convert to dict and back
    branch_dict = branch.model_dump()
    new_branch = VirtualBranch.model_validate(branch_dict)
    
    # Verify the data is preserved
    assert new_branch.name == branch.name
    assert new_branch.base_branch == branch.base_branch
    assert len(new_branch.commits) == 1
    assert new_branch.commits[0].id == commit.id
    assert new_branch.commits[0].message == commit.message
    assert new_branch.commits[0].author == commit.author
    assert new_branch.commits[0].timestamp == commit.timestamp


def test_virtual_branch_from_dict():
    """Test creating a VirtualBranch from a dictionary."""
    data = {
        "name": "feature/test",
        "base_branch": "develop",
        "commits": [
            {
                "id": "abc123",
                "message": "Initial commit",
                "author": "Test User <test@example.com>",
                "timestamp": 1625097600.0,
                "parent_ids": [],
                "metadata": {}
            }
        ],
        "created_at": 1625097600.0,
        "updated_at": 1625097600.0
    }
    
    branch = VirtualBranch.from_dict(data)
    
    assert branch.name == "feature/test"
    assert branch.base_branch == "develop"
    assert len(branch.commits) == 1
    assert branch.commits[0].id == "abc123"
    assert branch.commits[0].message == "Initial commit"
    assert branch.commits[0].author == "Test User <test@example.com>"
    assert branch.commits[0].timestamp == 1625097600.0
    assert branch.created_at == 1625097600.0
    assert branch.updated_at == 1625097600.0
