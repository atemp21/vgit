"""Add file contents to the index."""

import os

import click

from app.virtual_branch import VGitError
from app.virtual_branch_manager import vbm
from app.utils.command_utils import get_command_name


@click.command()
@click.option(
    "-i", "--interactive", is_flag=True, help="Interactive mode (not implemented)"
)
@click.option(
    "-e", "--edit", is_flag=True, help="Edit current diff and apply (not implemented)"
)
@click.option("-v", "--verbose", is_flag=True, help="Be verbose")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Don't actually add the file(s), just show if they exist.",
)
@click.argument("pathspec", nargs=-1, type=click.Path(exists=True))
def add(
    interactive: bool = False,
    edit: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
    pathspec: tuple[str, ...] = (),
) -> int:
    """Add file contents to the staging area.
    
    Stages changes from the working directory to be included in the next commit.
    
    Usage:
      {cmd} add [<pathspec>...]
      {cmd} add .
      {cmd} add -i
      {cmd} add -e
    
    Options:
      -i, --interactive  Interactive mode (not implemented)
      -e, --edit        Edit current diff and apply (not implemented)
    
    If no <pathspec> is provided, all changes in the working directory will be staged.
    Use '.' to explicitly stage all changes in the current directory.
    
    Examples:
      {cmd} add                 # Stage all changes
      {cmd} add file.txt        # Stage specific file
      {cmd} add src/ tests/     # Stage all changes in directories
    
    Note: This is a simplified version of git-add. For more advanced features,
    please use the git command directly.
    """.format(
        cmd=get_command_name()
    )

    if not vbm.repo:
        click.echo(
            "fatal: not a git repository (or any of the parent directories)", err=True
        )
        return 1

    cmd = get_command_name()

    try:
        # Handle interactive/patch mode
        if interactive or edit:
            click.echo("Interactive mode not yet implemented.", err=True)
            return 1

        # Convert pathspec tuple to list
        file_paths = list(pathspec)

        # If no pathspec and not in interactive/edit mode, default to adding all changes
        if not file_paths and not (interactive or edit):
            file_paths = ["."]

        # Process each path
        repo = vbm.repo
        index = repo.index

        added_files = []
        for path in file_paths:
            # Handle directory paths
            if os.path.isdir(path):
                click.echo(f"add '{path}/'")
                index.add([path])
                added_files.append(f"{path}/")
            # Handle file paths
            elif os.path.exists(path):
                click.echo(f"add '{path}'")
                index.add([path])
                added_files.append(path)
            # Handle missing files
            else:
                click.echo(
                    f"fatal: pathspec '{path}' did not match any files", err=True
                )
                return 1

        # Write the index
        if added_files:
            index.write()
            click.echo(f"Added {len(added_files)} files to the index.")

        return 0

    except VGitError as e:
        click.echo(f"error: {e}", err=True)
        return 1
    except Exception as e:
        click.echo(f"{cmd}: unexpected error: {e}", err=True)
        if os.environ.get("DEBUG"):
            import traceback

            traceback.print_exc()
        return 1
