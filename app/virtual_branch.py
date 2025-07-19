from __future__ import annotations
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
import json
import git
from git import Actor, Repo
from typing import Any


class VGitError(Exception):
    """Base exception for VGit errors."""

    pass


class Commit(BaseModel):
    """Represents a commit in a virtual branch."""

    id: str
    message: str
    author: str
    timestamp: float
    parent_ids: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert commit to a dictionary for serialization."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "Commit":
        """Create a Commit from a dictionary."""
        return cls.model_validate(data)


class VirtualBranch(BaseModel):
    """Represents a virtual branch in the repository."""

    name: str
    base_branch: str = "main"
    commits: list[Commit] = Field(default_factory=list)
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp())

    def add_commit(self, commit: Commit) -> None:
        """Add a commit to this branch."""
        self.commits.append(commit)
        self.updated_at = datetime.now().timestamp()

    def get_head_commit(self) -> Commit | None:
        """Get the most recent commit on this branch."""
        return self.commits[-1] if self.commits else None

    def to_dict(self) -> dict:
        """Convert branch to a dictionary for serialization."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "VirtualBranch":
        """Create a VirtualBranch from a dictionary."""
        if "commits" in data:
            data["commits"] = [
                Commit.model_validate(commit_data)
                for commit_data in data.get("commits", [])
            ]
        return cls.model_validate(data)


class VirtualBranchManager:
    """Manages virtual branches in a Git repository."""

    VGIT_DIR = ".vgit"
    BRANCHES_FILE = "branches.json"
    CONFIG_FILE = "config.json"

    def __init__(self, repo_path: str | None = None):
        """Initialize the VirtualBranchManager.

        Args:
            repo_path: Path to the Git repository. If None, uses current working directory.
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.vgit_dir = self.repo_path / self.VGIT_DIR
        self.branches: dict[str, VirtualBranch] = {}
        self.current_branch: str | None = None
        self._initialized = False

        try:
            self.repo: Repo | None = git.Repo(self.repo_path)
            self._load_state()
        except git.InvalidGitRepositoryError:
            pass

    def _ensure_vgit_dir(self) -> None:
        """Ensure the .vgit directory exists."""
        if not self.vgit_dir.exists():
            self.vgit_dir.mkdir(exist_ok=True)

    def _save_state(self) -> None:
        """Save the current state to disk."""
        if not self._initialized:
            return

        self._ensure_vgit_dir()

        # Save branches
        branches_data = {
            "current_branch": self.current_branch,
            "branches": {
                name: branch.to_dict() for name, branch in self.branches.items()
            },
        }

        with open(self.vgit_dir / self.BRANCHES_FILE, "w") as f:
            json.dump(branches_data, f, indent=2)

    def _load_state(self) -> None:
        """Load the saved state from disk."""
        branches_file = self.vgit_dir / self.BRANCHES_FILE

        if branches_file.exists():
            try:
                with open(branches_file, "r") as f:
                    data = json.load(f)

                self.branches = {
                    name: VirtualBranch.from_dict(branch_data)
                    for name, branch_data in data.get("branches", {}).items()
                }
                self.current_branch = data.get("current_branch")
            except (json.JSONDecodeError, KeyError) as e:
                # If loading fails, start with a clean slate
                self.branches = {}
                self.current_branch = None
        else:
            # Initialize with a main branch if none exists
            if not self.branches:
                self.branches["main"] = VirtualBranch(name="main")
                self.current_branch = "main"

        self._initialized = True

    def initialize_repo(self) -> None:
        """Initialize a new Git repository if one doesn't exist."""
        if self.repo is None:
            try:
                self.repo = git.Repo.init(self.repo_path)
                # Create an initial commit if the repo is empty
                if not self.repo.head.is_valid():
                    self.repo.index.commit("Initial commit")

                # Initialize virtual branches
                if not self._initialized:
                    self.branches["main"] = VirtualBranch(name="main")
                    self.current_branch = "main"
                    self._initialized = True
                    self._save_state()

            except Exception as e:
                raise VGitError(f"Failed to initialize repository: {e}")

    def create_branch(self, branch_name: str, base_branch: str = "main") -> None:
        """Create a new virtual branch.

        Args:
            branch_name: Name of the new branch
            base_branch: Name of the branch to base the new branch on

        Raises:
            VGitError: If the branch already exists or the base branch doesn't exist
        """
        if branch_name in self.branches:
            raise VGitError(f"A branch named '{branch_name}' already exists.")

        if base_branch not in self.branches:
            raise VGitError(f"Base branch '{base_branch}' does not exist.")

        # Create a new branch with the same commits as the base branch
        base_branch_obj = self.branches[base_branch]
        new_branch = VirtualBranch(
            name=branch_name,
            base_branch=base_branch,
            commits=base_branch_obj.commits.copy(),
            created_at=datetime.now().timestamp(),
        )

        self.branches[branch_name] = new_branch
        self.current_branch = branch_name
        self._save_state()

    def switch_branch(self, branch_name: str) -> None:
        """Switch to an existing virtual branch.

        Args:
            branch_name: Name of the branch to switch to

        Raises:
            VGitError: If the branch doesn't exist
        """
        if branch_name not in self.branches:
            raise VGitError(f"Branch '{branch_name}' does not exist.")

        self.current_branch = branch_name
        self._save_state()

        # In a real implementation, this would update the working directory
        # to match the state of the virtual branch

    def create_commit(self, message: str, author: Actor | None = None) -> Commit:
        """Create a new commit on the current branch.

        Args:
            message: Commit message
            author: Optional author information. If not provided, uses Git config.

        Returns:
            The created commit

        Raises:
            VGitError: If no branch is checked out or if there are no changes to commit
        """
        if not self.current_branch:
            raise VGitError("No branch is currently checked out.")

        if not self.repo:
            raise VGitError("Not a Git repository.")

        # Check for changes
        if not self.repo.index.diff(None) and not self.repo.untracked_files:
            raise VGitError("No changes added to commit.")

        # Stage all changes
        self.repo.git.add(A=True)

        # Create commit with proper Actor objects
        if not author:
            name = str(self.repo.config_reader().get_value("user", "name", ""))
            email = str(self.repo.config_reader().get_value("user", "email", ""))
            author = Actor(name, email)

        commit = self.repo.index.commit(message, author=author)

        # Create virtual commit
        virtual_commit = Commit(
            id=commit.hexsha,
            message=message,
            author=author.name,  # type: ignore
            timestamp=commit.committed_date,
            parent_ids=[p.hexsha for p in commit.parents],
            metadata={
                "git_commit": commit.hexsha,
                "committer": commit.committer.name,
                "committer_email": commit.committer.email,
                "authored_date": commit.authored_date,
                "committed_date": commit.committed_date,
            },
        )

        # Add to current branch
        self.branches[self.current_branch].add_commit(virtual_commit)
        self._save_state()

        return virtual_commit

    def get_status(self) -> dict[str, Any]:
        """Get the current repository status.

        Returns:
            A dictionary containing status information including:
            - current_branch: Name of the current branch
            - untracked_files: List of untracked files
            - changes_not_staged: List of modified files not staged for commit
            - changes_to_be_committed: List of changes staged for commit
            - ahead/behind: Number of commits ahead/behind upstream
        """
        if not self.repo:
            return {"status": "not_a_git_repo"}

        status: dict[str, Any] = {
            "current_branch": self.current_branch,
            "untracked_files": [],
            "changes_not_staged": [],
            "changes_to_be_committed": [],
            "ahead": 0,
            "behind": 0,
        }

        try:
            # Get untracked files
            status["untracked_files"] = self.repo.untracked_files

            # Get changes not staged for commit
            status["changes_not_staged"] = [
                diff.a_path for diff in self.repo.index.diff(None)
            ]

            # Get changes to be committed
            status["changes_to_be_committed"] = [
                diff.a_path for diff in self.repo.index.diff("HEAD")
            ]

            # Get ahead/behind info for the current branch
            if self.current_branch:
                head = self.repo.heads[self.current_branch]
                if head.tracking_branch():
                    # Count commits ahead/behind
                    commits_ahead = list(
                        self.repo.iter_commits(
                            f"{head.tracking_branch().name}..{head.name}"  # type: ignore
                        )
                    )
                    commits_behind = list(
                        self.repo.iter_commits(
                            f"{head.name}..{head.tracking_branch().name}"  # type: ignore
                        )
                    )

                    status["ahead"] = len(commits_ahead)
                    status["behind"] = len(commits_behind)

        except Exception as e:
            # If there's any error getting the status, just return what we have
            status["error"] = str(e)

        return status

    def unstage_all(self) -> None:
        """Unstage all changes in the index."""
        if not self.repo:
            raise VGitError("Not a Git repository.")
        self.repo.git.reset()

    def unstage(self, paths: list[str]) -> None:
        """Unstage specific files from the index.

        Args:
            paths: List of file paths to unstage
        """
        if not self.repo:
            raise VGitError("Not a Git repository.")
        self.repo.git.reset("--", *paths)

    def get_current_branch(self) -> str | None:
        """Get the name of the current branch.

        Returns:
            Name of the current branch, or None if not on any branch
        """
        return self.current_branch

    def branch_exists_on_remote(self, branch_name: str) -> bool:
        """Check if a branch exists on the remote.

        Args:
            branch_name: Name of the branch to check

        Returns:
            True if the branch exists on the remote, False otherwise
        """
        if not self.repo:
            return False

        try:
            remote_refs = self.repo.git.ls_remote(
                "--heads", "origin", branch_name
            ).split()
            return bool(remote_refs)
        except Exception:
            return False

    def push_branch(
        self, local_branch: str, remote_branch: str | None = None, force: bool = False
    ) -> None:
        """Push a branch to the remote repository.

        Args:
            local_branch: Name of the local branch to push
            remote_branch: Name of the remote branch (defaults to same as local_branch)
            force: Whether to force push

        Raises:
            VGitError: If there's an error pushing to the remote
        """
        if not self.repo:
            raise VGitError("Not a Git repository.")

        remote_branch = remote_branch or local_branch
        try:
            if force:
                self.repo.git.push(
                    "origin", f"{local_branch}:{remote_branch}", "--force"
                )
            else:
                self.repo.git.push("origin", f"{local_branch}:{remote_branch}")
        except Exception as e:
            raise VGitError(f"Failed to push branch: {str(e)}")

    def get_commit_history(
        self, branch_name: str | None = None, limit: int = 100
    ) -> list[dict]:
        """Get the commit history for a branch.

        Args:
            branch_name: Name of the branch to get history for (defaults to current branch)
            limit: Maximum number of commits to return

        Returns:
            List of commit dictionaries with id, message, author, and date
        """
        if not self.repo:
            raise VGitError("Not a Git repository.")

        branch_name = branch_name or self.current_branch
        if not branch_name:
            raise VGitError("No branch is currently checked out.")

        try:
            commits = list(self.repo.iter_commits(branch_name, max_count=limit))
            return [
                {
                    "id": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                }
                for commit in commits
            ]
        except Exception as e:
            raise VGitError(f"Failed to get commit history: {str(e)}")
