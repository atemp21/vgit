"""Utility functions for command-line interface."""

# Global command name (default to 'vgit')
_command_name = "vgit"


def get_command_name() -> str:
    """Get the current command name."""
    return _command_name


def set_command_name(name: str) -> None:
    """Set the command name for error messages."""
    global _command_name
    _command_name = name
