"""Initialize a new VGit repository."""

import os
import click
from git import Repo
from app.virtual_branch_manager import vbm
from app.utils.command_utils import get_command_name


@click.command()
@click.argument("directory", type=click.Path(), required=False)
def init(directory: str | None) -> int:
    """Initialize a new VGit repository.
    
    Creates an empty Git repository with VGit-specific configuration.
    
    Usage:
      vgit init [<directory>]
    
    If <directory> is provided, creates the repository there.
    Otherwise, initializes in the current directory.
    
    The command is safe to run multiple times in the same directory.
    It will not overwrite an existing repository.
    
    Examples:
      {cmd}           # Initialize in current directory
      {cmd} myproject  # Initialize in myproject directory
    """.format(
        cmd=get_command_name()
    )
    cmd = get_command_name()

    try:
        # If directory is provided, use it as the repo path
        if directory:
            repo_path = os.path.abspath(directory)
            try:
                os.makedirs(repo_path, exist_ok=True)
            except OSError as e:
                click.echo(f"{cmd}: {e}", err=True)
                return 1
        else:
            repo_path = os.getcwd()

        # Check if already a git repository
        if os.path.exists(os.path.join(repo_path, ".git")):
            click.echo(f"Reinitialized existing VGit repository in {repo_path}/.vgit/")
            return 0

        # Initialize the Git repository
        repo = Repo.init(repo_path)

        # Initialize the VGit repository
        vbm.repo = repo

        # Create .vgit directory if it doesn't exist
        vgit_dir = os.path.join(repo_path, ".vgit")
        try:
            os.makedirs(vgit_dir, exist_ok=True)
        except OSError as e:
            click.echo(f"{cmd}: Failed to create .vgit directory: {e}", err=True)
            return 1

        # Initialize the VGit repository
        try:
            vbm.initialize_repo()
        except Exception as e:
            click.echo(f"{cmd}: Failed to initialize VGit repository: {e}", err=True)
            return 1

        # Create an initial commit if the repository is empty
        try:
            if not repo.heads:
                repo.index.commit("Initial commit")
        except Exception as e:
            click.echo(f"{cmd}: Failed to create initial commit: {e}", err=True)
            return 1

        click.echo(f"Initialized empty VGit repository in {repo_path}/")
        return 0

    except Exception as e:
        click.echo(f"{cmd}: {e}", err=True)
        return 1
