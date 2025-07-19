"""Unstage command for VGit."""

import os
import click

from virtual_branch import VGitError
from cli import vbm, command


@command()
@click.argument("pathspec", nargs=-1, required=False)
@click.option("--all", "all_files", is_flag=True, help="Unstage all changes")
def unstage(pathspec: tuple[str, ...] = (), all_files: bool = False) -> int:
    """Unstage changes in the index.

    Moves changes from the index back to the working directory.

    Examples:
      vgit unstage <file>    # Unstage specific file
      vgit unstage .         # Unstage all changes in current directory
      vgit unstage --all     # Unstage all changes
    """
    if not vbm.repo:
        click.echo(
            "fatal: not a git repository (or any of the parent directories)", err=True
        )
        return 1

    if not pathspec and not all_files:
        click.echo(
            "error: nothing specified, use --all or provide file paths", err=True
        )
        return 1

    try:
        # If --all is specified, unstage everything
        if all_files:
            vbm.unstage_all()
            click.echo("All changes unstaged")
            return 0

        # Otherwise, unstage specific paths
        paths = list(pathspec)
        vbm.unstage(paths)

        if len(paths) == 1:
            click.echo(f"Changes unstaged for '{paths[0]}'")
        else:
            click.echo(f"Changes unstaged for {len(paths)} files")

        return 0

    except VGitError as e:
        click.echo(f"error: {e}", err=True)
        return 1
    except Exception as e:
        click.echo(f"error: {e}", err=True)
        if os.environ.get("DEBUG"):
            import traceback

            traceback.print_exc()
        return 1
