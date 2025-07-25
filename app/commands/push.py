"""Push command for VGit.

Pushes the current virtual branch to a remote repository.
If the branch doesn't exist on the remote, it will be created and set up to track.
"""

import click
from app.virtual_branch import VGitError
from app.cli import vbm


@click.command()
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
    try:
        if not vbm.repo:
            click.echo(
                "fatal: not a git repository (or any of the parent directories)", err=True
            )
            return 1

        # Get current virtual branch
        current_branch = vbm.get_current_branch()
        if not current_branch:
            click.echo("error: not currently on any branch", err=True)
            return 1

        # Use provided branch or current branch
        target_branch = branch or current_branch

        # Check if branch exists on remote
        branch_exists = vbm.branch_exists_on_remote(target_branch)

        if dry_run:
            click.echo(f"Would push '{target_branch}' to '{remote}'")
            return 0

        # Push the branch
        vbm.push_branch(
            local_branch=target_branch, remote_branch=target_branch, force=force
        )

        if not branch_exists:
            click.echo(
                f"Branch '{target_branch}' set up to track remote branch '{target_branch}' from '{remote}'."
            )
        else:
            click.echo(f"Successfully pushed to {remote}/{target_branch}")

        return 0

    except VGitError as e:
        # If the error message doesn't already start with 'error:' or 'fatal:', add 'error:'
        error_msg = str(e)
        if not (error_msg.startswith('error:') or error_msg.startswith('fatal:')):
            error_msg = f"error: {error_msg}"
        click.echo(error_msg, err=True)
        return 1
    except Exception as e:
        # Handle any other exceptions
        click.echo(f"fatal: {str(e)}", err=True)
        return 1
