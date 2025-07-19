"""Command modules for the VGit CLI."""

# Import all command modules here so they can be registered
from .init import init
from .commit import commit
from .branch import branch
from .status import status
from .add import add
from .push import push

__all__ = [
    "init",
    "commit",
    "branch",
    "status",
    "add",
    "push",
]
