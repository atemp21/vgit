"""Initialize a new VGit repository."""

import os


import click
from git import Repo

from app.cli import vbm, command_name


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
        cmd=command_name()
    )
    cmd = command_name()

    try:
        # If directory is provided, use it as the repo path
        if directory:
            repo_path = os.path.abspath(directory)
            if not os.path.exists(repo_path):
                os.makedirs(repo_path, exist_ok=True)
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
        vbm.initialize_repo()

        click.echo(f"Initialized empty VGit repository in {repo_path}/")
        return 0

    except Exception as e:
        click.echo(f"{cmd}: {e}", err=True)
        return 1
