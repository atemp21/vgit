"""Command modules for the VGit CLI."""

# Import all command functions directly from their modules
# These imports are safe now that we've moved command_name to a separate module
from .init import init
from .commit import commit
from .branch import branch
from .status import status
from .add import add
from .push import push
from .log import log
from .unstage import unstage

# Re-export the command functions
__all__ = [
    "init",
    "commit",
    "branch",
    "status",
    "add",
    "push",
    "log",
    "unstage",
]
