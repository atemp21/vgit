"""Commit command for VGit."""

import os
import sys


import click

from app.virtual_branch import VGitError

# Get the global virtual branch manager instance
from app.cli import vbm, command_name


@click.command()
@click.option("-m", "--message", help="Commit message")
@click.option("--allow-empty", is_flag=True, help="Allow empty commit")
@click.argument("pathspec", nargs=-1)
def commit(
    message: str | None = None,
    allow_empty: bool | None = None,
    pathspec: tuple[str, ...] = (),
) -> int:
    """Record changes to the repository.
    
    Creates a new commit with the current index state and the provided message.
    
    Usage:
      {cmd} -m "commit message" [<pathspec>...]
      {cmd} --allow-empty -m "empty commit"
    
    Options:
      -m, --message TEXT  The commit message
      --allow-empty       Allow an empty commit (no changes)
    
    If no message is provided, an editor will be opened to enter the message.
    
    Examples:
      {cmd} -m "Fix login bug"
      {cmd} -m "Update docs" README.md
      {cmd} --allow-empty -m "Trigger deployment"
    
    Note: Changes must be staged with `{cmd} add` before committing.
    """.format(
        cmd=command_name()
    )

    if not vbm.repo:
        click.echo(
            "fatal: not a git repository (or any of the parent directories)", err=True
        )
        click.echo(f"fatal: {command_name()}")
        return 1

    # Get the command name for messages
    cmd = command_name()

    # Get the Git repository
    repo = vbm.repo

    # Handle interactive commit if no message is provided
    if not message and not (sys.stdin and not sys.stdin.isatty()):
        # Open the default editor to get the commit message
        edit_msg_path = os.path.join(repo.git_dir, "COMMIT_EDITMSG")
        with open(edit_msg_path, "w") as f:
            f.write(
                "\n# Please enter the commit message for your changes. Lines starting\n"
            )
            f.write(
                "# with '#' will be ignored, and an empty message aborts the commit.\n"
            )
            f.write(f"# On branch {vbm.current_branch or 'main'}\n")

            # Show changes that will be committed
            status = vbm.get_status()
            if status["changes_to_be_committed"]:
                f.write("#\n# Changes to be committed:\n#\n")
                for path in status["changes_to_be_committed"]:
                    f.write(f"#\t{path}\n")

            if status["changes_not_staged"]:
                f.write("#\n# Changes not staged for commit:\n#\n")
                for path in status["changes_not_staged"]:
                    f.write(f"#\t{path}\n")

            if status["untracked_files"]:
                f.write("#\n# Untracked files:\n#\n")
                for path in status["untracked_files"]:
                    f.write(f"#\t{path}\n")

        # Open the editor
        editor = os.environ.get("EDITOR", "vi")
        os.system(f"{editor} {edit_msg_path}")

        # Read the commit message
        with open(edit_msg_path, "r") as f:
            lines = [line for line in f.read().splitlines() if not line.startswith("#")]
        message_str = "\n".join(lines).strip()

        # Clean up
        os.unlink(edit_msg_path)

    # If still no message, check if reading from stdin
    if not message and sys.stdin and not sys.stdin.isatty():
        message = sys.stdin.read().strip()

    # If still no message, show error
    if not message:
        click.echo("Aborting commit due to empty commit message.", err=True)
        click.echo(
            f"Use '{cmd} commit -m \"commit message\"' to specify a commit message.",
            err=True,
        )
        return 1

    try:
        # Handle pathspec if provided
        if pathspec:
            repo.index.add(pathspec)

        # Check if there are any changes to commit
        status = vbm.get_status()
        if not any([status["changes_to_be_committed"], allow_empty]):
            click.echo(f"On branch {status['current_branch'] or 'main'}")
            click.echo("nothing to commit, working tree clean")
            if not allow_empty:
                click.echo(
                    f"use '{cmd} commit --allow-empty' to create an empty commit"
                )
            return 0

        # Create the commit
        commit = vbm.create_commit(message)

        # Show the commit info
        click.echo(
            f"[{status['current_branch'] or 'main'}] {commit.id[:7]} {message.splitlines()[0]}"
        )

        # Show branch info if this is the first commit
        if len(vbm.branches[vbm.current_branch].commits) == 1:  # type: ignore
            click.echo(f"(root-commit) {commit.id}")

        return 0

    except VGitError as e:
        click.echo(f"Error: {e}", err=True)
        return 1
    except Exception as e:
        click.echo(f"{cmd}: unexpected error: {e}", err=True)
        if os.environ.get("DEBUG"):
            import traceback

            traceback.print_exc()
        return 1
