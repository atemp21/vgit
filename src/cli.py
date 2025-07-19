import os
import sys
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import click

from virtual_branch import VGitError, VirtualBranchManager

T = TypeVar("T", bound=Callable[..., Any])

vbm = VirtualBranchManager()

_command_name = "vgit"


def command_name() -> str:
    return _command_name


def set_command_name(name: str) -> None:
    global _command_name
    _command_name = name


def format_help_text(text: str) -> str:
    return text.replace("vgit", _command_name)


def command(*args: Any, **kwargs: Any) -> Callable[[T], T]:
    if "help" in kwargs:
        kwargs["help"] = format_help_text(kwargs["help"])

    def decorator(f: T) -> T:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return f(*args, **kwargs)

        return wrapper

    return click.command(*args, **kwargs)(decorator)


def ensure_initialized() -> bool:
    if not vbm.repo:
        click.echo("fatal: not a git repository (or any of the parent directories)")
        click.echo(f"Run '{command_name()} init' to initialize a new repository.")
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

    @cli.pass_context
    def process_context(ctx: click.Context) -> None:
        # Set the command name for error messages
        if ctx.parent is not None:
            set_command_name(f"{ctx.parent.info_name} {ctx.info_name}")
        else:
            set_command_name(ctx.info_name)

        # Show help if no command is provided
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            ctx.exit()

        # Initialize repo for all commands except 'init'
        if ctx.invoked_subcommand != "init":
            if not ensure_initialized():
                ctx.exit(1)

    from .commands import (
        init,
        commit,
        branch,
        status,
        add,
        unstage,
        push,
        log,
    )

    cli.add_command(init.init)
    cli.add_command(commit.commit)
    cli.add_command(branch.branch)
    cli.add_command(status.status)
    cli.add_command(add.add)
    cli.add_command(unstage.unstage)
    cli.add_command(push.push)
    cli.add_command(log.log)

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
        click.echo(f"{command_name()}: unexpected error: {e}", err=True)
        if os.environ.get("DEBUG"):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
