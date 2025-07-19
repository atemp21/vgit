"""Log command for VGit."""

import click
from datetime import datetime

from app.cli import vbm
from app.virtual_branch import VGitError


def format_commit(commit: dict) -> str:
    """Format a single commit for display."""
    # Format timestamp
    timestamp = datetime.fromtimestamp(commit["timestamp"]).strftime(
        "%a %b %d %H:%M:%S %Y"
    )

    # Format author line
    author = f"{commit['author']} <{commit['email']}>"

    # Format commit message (handle multi-line messages)
    message = commit["message"].strip().split("\n")[0]  # Just first line of message

    # Format the output
    return (
        f"commit {commit['hash']}\n"
        f"Author: {author}\n"
        f"Date:   {timestamp}\n\n"
        f"    {message}\n"
    )


@click.command()
@click.option("-n", "--max-count", type=int, help="Limit number of commits to show")
@click.option("--oneline", is_flag=True, help="Show each commit on a single line")
@click.option("--stat", is_flag=True, help="Show stats about files changed")
@click.argument("revision_range", required=False)
def log(
    max_count: int | None = None,
    oneline: bool = False,
    stat: bool = False,
    revision_range: str | None = None,
) -> int:
    """Show commit logs.

    Shows the commit history for the current branch.

    Examples:
      vgit log               # Show full commit history
      vgit log -n 5          # Show last 5 commits
      vgit log --oneline     # Show compact one-line-per-commit
      vgit log --stat        # Show stats about files changed
    """
    if not vbm.repo:
        click.echo(
            "fatal: not a git repository (or any of the parent directories)", err=True
        )
        return 1

    try:
        # Get commit history for the current branch
        commits = vbm.get_commit_history(limit=max_count or 100)

        if not commits:
            click.echo("No commits yet")
            return 0

        # Display commits
        for commit in commits:
            if oneline:
                # Show abbreviated hash and first line of message
                click.echo(f"{commit['id'][:7]} {commit['message'].splitlines()[0]}")
            elif stat:
                # Show stats about changes (simplified version)
                click.echo(f"commit {commit['id']}")
                click.echo(f"Author: {commit['author']}")
                click.echo(f"Date:   {commit['date']}\n")

                # Note: Full diff stats would require more complex git operations
                # This is a simplified version
                click.echo("  (stat output not implemented in this version)\n")
            else:
                # Show full commit details (simplified)
                click.echo(f"commit {commit['id']}")
                click.echo(f"Author: {commit['author']}")
                click.echo(f"Date:   {commit['date']}\n")
                click.echo(f"    {commit['message'].splitlines()[0]}\n")

        return 0

    except VGitError as e:
        click.echo(f"error: {e}", err=True)
        return 1
