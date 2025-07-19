"""Push command for VGit.

Pushes the current virtual branch to a remote repository.
If the branch doesn't exist on the remote, it will be created and set up to track.
"""

import click
from virtual_branch import VGitError
from cli import vbm, command


@command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force updates, overwrite remote branch if it exists",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be pushed without actually pushing"
)
@click.argument("remote", default="origin")
@click.argument("branch", required=False)
def push(force: bool, dry_run: bool, remote: str, branch: str | None) -> int:
    """Push the current branch to the specified remote.

    If the branch doesn't exist on the remote, it will be created from main
    and set up to track the remote branch.

    Args:
        force: If True, force push the branch
        dry_run: If True, show what would be pushed without actually pushing
        remote: The remote to push to (default: origin)
        branch: The branch to push (default: current branch)
    """
    if not vbm.repo:
        click.echo(
            "fatal: not a git repository (or any of the parent directories)", err=True
        )
        return 1

    try:
        # Get current virtual branch
        current_branch = vbm.get_current_branch()
        if not current_branch:
            click.echo("error: not currently on any branch", err=True)
            return 1

        # Use provided branch or current branch
        target_branch = branch or current_branch

        # Check if branch exists on remote
        branch_exists = vbm.branch_exists_on_remote(target_branch, remote)

        # Push the branch
        result = vbm.push_branch(
            branch=target_branch,
            remote=remote,
            force=force,
            dry_run=dry_run,
            setup_tracking=not branch_exists,
        )

        if dry_run:
            click.echo("Dry run. Would push the following commits:")
            for commit in result.get("commits", []):
                click.echo(
                    f"  {commit['hash'][:7]} {commit['message'].splitlines()[0]}"
                )
            return 0

        if result.get("success", False):
            if branch_exists:
                click.echo(f"Successfully pushed to {remote}/{target_branch}")
            else:
                click.echo(
                    f"Created new branch {target_branch} on {remote} and set up tracking"
                )
            return 0
        else:
            click.echo(
                f"Failed to push to {remote}: {result.get('error', 'Unknown error')}",
                err=True,
            )
            return 1

    except VGitError as e:
        click.echo(f"error: {e}", err=True)
        return 1
