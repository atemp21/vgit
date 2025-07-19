"""Log command for VGit."""

import click
from datetime import datetime

from cli import vbm, command
from virtual_branch import VGitError


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


@command()
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
        # Get commit history
        commits = vbm.get_commit_history(
            max_count=max_count, revision_range=revision_range
        )

        if not commits:
            click.echo("No commits yet")
            return 0

        # Display commits
        for i, commit in enumerate(commits):
            if oneline:
                # Show abbreviated hash and first line of message
                short_hash = commit["hash"][:7]
                first_line = commit["message"].strip().split("\n")[0]
                click.echo(f"{short_hash} {first_line}")
            else:
                click.echo(format_commit(commit))

            # Show stats if requested
            if stat and "stats" in commit:
                stats = commit["stats"]
                for file, changes in stats.items():
                    click.echo(
                        f" {changes.get('insertions', 0):>3} +| {changes.get('deletions', 0):<3} | {file}"
                    )
                click.echo()

        return 0

    except VGitError as e:
        click.echo(f"error: {e}", err=True)
        return 1
