# VGit

VGit is a command-line tool that simplifies Git workflows by introducing virtual branches. It provides a more intuitive interface for Git operations, eliminating the need for complex rebasing and merging.

## Features

- **Virtual Branches**: Work with lightweight virtual branches that don't interfere with your Git history
- **Simplified Commands**: Intuitive commands that make Git easier to use
- **No More Rebasing**: Virtual branches eliminate the need for complex rebase operations
- **Seamless Integration**: Works alongside your existing Git repositories

## Installation

```bash
# Install using pipx (recommended)
pipx install vgit

# Or install directly with pip
pip install --user vgit
```

## Getting Started

### Initialize a new repository
```bash
vgit init
```

### Create a new virtual branch
```bash
vgit branch feature/new-feature
```

### Make changes and commit
```bash
# Stage changes
vgit add .

# Create a commit
vgit commit -m "Add new feature"
```

### Push changes
```bash
vgit push
```

## Development

### Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   poetry install
   ```
3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

### Running Tests
```bash
pytest
```

## License

MIT