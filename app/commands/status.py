"""Status command for VGit."""

import os
import click

from app.virtual_branch import VGitError
from app.virtual_branch_manager import vbm


@click.command()
@click.argument("pathspec", nargs=-1, type=click.Path())
def status(pathspec: tuple[str, ...] = ()) -> int:
    """Show the working tree status.

    Shows which changes are staged, unstaged, and untracked.

    Example:
        On branch main

        Changes to be committed:
        (use "vgit unstage <file>..." to unstage)
                new file:   example.txt

      Changes not staged for commit:
        (use "vgit add <file>..." to update what will be committed)
                modified:   README.md

      Untracked files:
        (use "vgit add <file>..." to include in what will be committed)
                tests/
    """
    if not vbm.repo:
        click.echo(
            "fatal: not a git repository (or any of the parent directories)", err=True
        )
        return 1

    try:
        # Get the repository status
        status = vbm.get_status()

        # Show branch information
        if status.get("current_branch"):
            click.echo(f"On branch {status['current_branch']}")
        else:
            click.echo("Not currently on any branch.")

        click.echo()

        # Show changes to be committed
        staged = status.get("staged", [])
        if staged:
            click.secho("Changes to be committed:", fg="green", bold=True)
            click.echo('  (use "vgit unstage <file>..." to unstage)')
            for path in staged:
                click.echo(f"\t{path}")
            click.echo()

        # Show changes not staged for commit
        unstaged = status.get("unstaged", [])
        if unstaged:
            click.secho("Changes not staged for commit:", fg="red", bold=True)
            click.echo('  (use "vgit add <file>..." to update what will be committed)')
            for path in unstaged:
                click.echo(f"\t{path}")
            click.echo()

        # Show untracked files
        untracked = status.get("untracked", [])
        if untracked:
            click.secho("Untracked files:", fg="red", bold=True)
            click.echo(
                '  (use "vgit add <file>..." to include in what will be committed)'
            )
            for path in untracked:
                click.echo(f"\t{path}")
            click.echo()

        if not any([staged, unstaged, untracked]):
            click.echo("nothing to commit, working tree clean")

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
