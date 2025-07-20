import os
import sys
from collections.abc import Callable
from typing import Any, TypeVar

import click

from app.virtual_branch import VGitError
from app.virtual_branch_manager import vbm
from app.utils.command_utils import get_command_name, set_command_name

T = TypeVar("T", bound=Callable[..., Any])


def format_help_text(text: str) -> str:
    return text.replace("vgit", get_command_name())


from typing import TypeVar, Callable, Any, cast

# Define the command function type variable
F = TypeVar("F", bound=Callable[..., Any])


def command(*args: Any, **kwargs: Any) -> Callable[[F], F]:
    """Decorator to register a command with the CLI."""

    def decorator(f: F) -> F:
        return cast(F, f)

    return decorator


def ensure_initialized() -> bool:
    if not vbm.repo:
        click.echo("fatal: not a git repository (or any of the parent directories)")
        click.echo(f"Run '{get_command_name()} init' to initialize a new repository.")
        return False

    if not hasattr(vbm, "_initialized") or not vbm._initialized:
        try:
            vbm.initialize_repo()
        except VGitError as e:
            click.echo(f"Error: {e}", err=True)
            return False

    return True


# Define command aliases at module level
command_aliases = {
    "status": ["s"],
    "add": ["a"],
    "commit": ["c"],
    "branch": ["b"],
    "push": ["p"],
    "log": ["l"],
    "unstage": ["u"],
}


class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        # Try to get the command normally first
        cmd = click.Group.get_command(self, ctx, cmd_name)
        if cmd is not None:
            return cmd

        # Check if the command has any aliases
        for cmd_name_actual, aliases in command_aliases.items():
            if cmd_name in aliases:
                return click.Group.get_command(self, ctx, cmd_name_actual)
        return None


def create_cli() -> click.Group:
    # Create the main CLI group with our custom AliasedGroup
    cli = AliasedGroup(
        context_settings={
            "help_option_names": ["-h", "--help"],
            "max_content_width": 100,
        },
        invoke_without_command=True,
    )

    @click.pass_context
    def process_context(ctx: click.Context) -> None:
        # Set the command name for error messages
        cmd_name = ""
        if ctx.parent and ctx.parent.info_name:
            cmd_name += f"{ctx.parent.info_name} "
        if ctx.info_name:
            cmd_name += ctx.info_name
        set_command_name(cmd_name or get_command_name())

        # Show help if no command is provided
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            ctx.exit()

        # Initialize repo for all commands except 'init'
        if ctx.invoked_subcommand != "init":
            if not ensure_initialized():
                ctx.exit(1)

    # Import all commands directly
    from .commands import (
        init as init_cmd,
        commit as commit_cmd,
        branch as branch_cmd,
        status as status_cmd,
        add as add_cmd,
        push as push_cmd,
        log as log_cmd,
        unstage as unstage_cmd,
    )

    # Register all commands
    cli.add_command(init_cmd, name="init")
    cli.add_command(commit_cmd, name="commit")
    cli.add_command(branch_cmd, name="branch")
    cli.add_command(status_cmd, name="status")
    cli.add_command(add_cmd, name="add")
    cli.add_command(push_cmd, name="push")
    cli.add_command(log_cmd, name="log")
    cli.add_command(unstage_cmd, name="unstage")

    return cli


cli = create_cli()


def main() -> None:
    prog_name = os.path.basename(sys.argv[0])
    if prog_name in ("__main__.py", "__main__.pyc"):
        prog_name = "python -m vgit"
    set_command_name(prog_name.split()[-1])
    sys.argv[0] = prog_name

    try:
        sys.exit(cli.main(prog_name=prog_name))
    except VGitError as e:
        click.echo(f"error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"{get_command_name()}: unexpected error: {e}", err=True)
        if os.environ.get("DEBUG"):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
