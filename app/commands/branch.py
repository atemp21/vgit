import click

from app.virtual_branch import VGitError
from app.cli import vbm, command_name
import os
import sys


@click.command()
@click.argument("branchname", required=False)
@click.option("-d", "--delete", is_flag=True, help="Delete a branch")
@click.option("-r", "--rename", is_flag=True, help="Rename a branch")
@click.option(
    "-l", "--list-branches", "list_branches", is_flag=True, help="List all branches"
)
def branch(
    branchname: str | None = None,
    delete: bool = False,
    rename: bool = False,
    list_branches: bool = False,
) -> int:
    """List, create, delete, or rename branches.
    
    With no arguments, lists all existing branches with the current branch
    highlighted with an asterisk (*).
    
    Commands:
      <branchname>         Create a new branch with the given name
      -l, --list-branches  List all branches (default)
      -d, --delete <name>  Delete the specified branch
      -r, --rename <name>  Rename a branch (will prompt for new name)
    
    Examples:
      {cmd} branch              # List all branches
      {cmd} branch new-feature  # Create a new branch
      {cmd} branch -d old-branch  # Delete a branch
      {cmd} branch -r old-branch  # Rename a branch (interactive)
    
    Note: Branch names must follow git's naming conventions.
    """.format(
        cmd=command_name()
    )

    if not vbm.repo:
        click.echo(
            "fatal: not a git repository (or any of the parent directories)", err=True
        )
        return 1

    try:
        # List branches (default action)
        if list_branches or not any([delete, rename, branchname]):
            current_branch = vbm.current_branch
            all_branches = list(vbm.branches.keys())

            if not all_branches:
                click.echo("No branches available.")
                return 0

            # Show local branches
            for branch_name in sorted(all_branches):
                prefix = "* " if branch_name == current_branch else "  "
                click.echo(f"{prefix}{branch_name}")
            return 0

        # Handle branch creation (just provide a branch name)
        if branchname and not (delete or rename):
            if branchname in vbm.branches:
                click.echo(
                    f"fatal: A branch named '{branchname}' already exists.", err=True
                )
                return 1

            vbm.create_branch(branchname)
            click.echo(f"Created branch '{branchname}'")
            return 0

        # Handle branch deletion
        if delete and branchname:
            if branchname not in vbm.branches:
                click.echo(f"error: branch '{branchname}' not found.", err=True)
                return 1

            if branchname == vbm.current_branch:
                click.echo(
                    f"error: Cannot delete branch '{branchname}' as it is the current branch"
                )
                return 1

            # Remove the branch
            del vbm.branches[branchname]
            vbm._save_state()
            click.echo(f"Deleted branch {branchname}")
            return 0

        # Handle branch renaming
        if rename and branchname:
            new_name = click.prompt("Enter new branch name")

            if not new_name:
                click.echo("fatal: new branch name cannot be empty", err=True)
                return 1

            if new_name in vbm.branches:
                click.echo(
                    f"fatal: A branch named '{new_name}' already exists.", err=True
                )
                return 1

            if branchname not in vbm.branches:
                click.echo(f"fatal: branch '{branchname}' not found.", err=True)
                return 1

            # Rename the branch
            branch = vbm.branches.pop(branchname)
            branch.name = new_name
            vbm.branches[new_name] = branch

            # Update current branch if needed
            if vbm.current_branch == branchname:
                vbm.current_branch = new_name

            vbm._save_state()
            click.echo(f"Renamed {branchname} to {new_name}")
            return 0

        # If we get here, the command wasn't recognized
        click.echo(f"fatal: unknown command: {sys.argv}", err=True)
        return 1

    except VGitError as e:
        click.echo(f"error: {e}", err=True)
        return 1
    except Exception as e:
        click.echo(f"{command_name()}: unexpected error: {e}", err=True)
        if os.environ.get("DEBUG"):
            import traceback

            traceback.print_exc()
        return 1
