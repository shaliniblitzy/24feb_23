*Last updated: 2026-02-24*

# Installation

This guide covers everything needed to set up a local development environment for the Flask server application. It walks through Python installation, virtual environment creation, dependency installation with pinned versions, and verification steps to confirm a working setup. Whether you are joining the project for the first time or setting up a fresh machine, follow each section in order to have a fully functional development environment.

## Prerequisites

Before beginning installation, ensure the following software is available on your system:

- **Python 3.9 or higher** — Flask 3.1.x requires Python 3.9 as the minimum supported version. Python 3.13 or later is recommended for best compatibility and performance.
- **pip** — The Python package installer. It ships with Python 3.9+ and is used to install all project dependencies.
- **Git** — Required for cloning the project repository and managing source code.
- **virtualenv** (optional) — Python 3 includes the built-in `venv` module for creating virtual environments. A standalone `virtualenv` package is not required unless your workflow specifically depends on it.

### Verifying Python Installation

Open a terminal and run the following commands to confirm that Python and pip are installed and meet the minimum version requirements:

```bash
python3 --version
# Expected output: Python 3.9.x or higher (e.g., Python 3.13.12)

pip3 --version
# Expected output: pip 24.x.x from /path/to/pip (python 3.x)
```

> **Note:** On Linux and macOS, the Python 3 interpreter is typically invoked as `python3` and the package installer as `pip3`. On Windows, the commands are usually `python` and `pip` (without the `3` suffix) after adding Python to the system PATH during installation.

## Installing Python

If Python 3.9 or higher is not yet installed, follow the instructions for your operating system below.

### macOS

The recommended approach on macOS is to use [Homebrew](https://brew.sh/):

```bash
brew install python@3.13
```

After installation, verify the version:

```bash
python3 --version
# Expected output: Python 3.13.x
```

### Ubuntu / Debian

On Ubuntu and Debian-based distributions, use the system package manager:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

After installation, verify the version:

```bash
python3 --version
# Expected output: Python 3.x.x (3.9 or higher)
```

### Windows

1. Download the latest Python 3 installer from [https://www.python.org/downloads/](https://www.python.org/downloads/).
2. Run the installer. On the first screen, check the box labeled **"Add Python to PATH"** before clicking "Install Now."
3. After installation completes, open a new Command Prompt or PowerShell window and verify:

```bash
python --version
# Expected output: Python 3.13.x
```

> **Note:** The project supports Python 3.9 and above, but Python 3.13 or later is recommended for best compatibility with the current dependency set and for access to the latest language features.

## Cloning the Repository

Clone the project repository and change into the project directory:

```bash
git clone <repository-url>
cd flask-server
```

Replace `<repository-url>` with the actual URL of the project's Git repository. All subsequent commands in this guide assume you are working from the project root directory.

## Setting Up a Virtual Environment

A virtual environment creates an isolated Python installation for this project, ensuring that its dependencies do not conflict with packages installed globally or by other projects on the same machine. Using a virtual environment is strongly recommended for all development work.

### Creating the Virtual Environment

Run the following command from the project root directory to create a virtual environment named `venv`:

```bash
python3 -m venv venv
```

This creates a `venv/` directory containing a self-contained Python interpreter and a clean `site-packages` directory where project dependencies will be installed.

### Activating the Virtual Environment

Activate the virtual environment so that the `python` and `pip` commands point to the isolated installation:

**Linux / macOS:**

```bash
source venv/bin/activate
```

**Windows (Command Prompt):**

```bash
venv\Scripts\activate
```

**Windows (PowerShell):**

```bash
venv\Scripts\Activate.ps1
```

After activation, your terminal prompt typically changes to show the environment name (for example, `(venv)`). Verify the active Python path:

```bash
which python
# Expected: /path/to/project/venv/bin/python
```

On Windows, use `where python` instead of `which python`.

### Deactivating the Virtual Environment

When you are finished working on the project, deactivate the virtual environment to return to the system Python:

```bash
deactivate
```

## Installing Dependencies

With the virtual environment activated, install all project dependencies. Two methods are available: installing from the `requirements.txt` manifest (recommended) or installing packages individually with pinned versions.

### Using requirements.txt

The project includes a `requirements.txt` file that lists all dependencies with pinned version numbers. Install everything in a single command:

```bash
pip install -r requirements.txt
```

This is the preferred method because it ensures that every developer installs the exact same package versions, producing a consistent and reproducible environment.

### Manual Installation with Pinned Versions

If you need to install dependencies individually — for example, when adding a new package or troubleshooting a specific dependency — use the following commands. Every package is pinned to an explicit version to ensure reproducible builds across all environments.

**Core application dependencies:**

```bash
pip install flask==3.1.3
pip install flask-cors==5.0.1
pip install flask-sqlalchemy==3.1.1
pip install flask-migrate==4.0.7
pip install python-dotenv==1.0.1
pip install gunicorn==23.0.0
```

**Testing dependencies:**

```bash
pip install pytest==8.3.4
```

**Documentation dependencies:**

```bash
pip install mkdocs==1.6.1
pip install mkdocs-material==9.7.2
pip install mkdocs-mermaid2-plugin==1.1.1
```

### Dependency Reference

The table below provides a complete summary of all project dependencies, their pinned versions, and their purpose:

| Package | Version | Purpose |
|---|---|---|
| flask | 3.1.3 | Core web application framework |
| flask-cors | 5.0.1 | Cross-Origin Resource Sharing support |
| flask-sqlalchemy | 3.1.1 | SQLAlchemy ORM integration for Flask |
| flask-migrate | 4.0.7 | Database schema migration with Alembic |
| python-dotenv | 1.0.1 | Environment variable loading from `.env` files |
| gunicorn | 23.0.0 | Production WSGI HTTP server |
| pytest | 8.3.4 | Python test framework |
| mkdocs | 1.6.1 | Static site documentation generator |
| mkdocs-material | 9.7.2 | Material Design theme for MkDocs |
| mkdocs-mermaid2-plugin | 1.1.1 | Mermaid diagram rendering in docs |

## Verifying the Installation

After installing all dependencies, run the following verification steps to confirm that the environment is correctly configured.

### Checking Flask Version

```bash
flask --version
# Expected output:
# Python 3.13.x
# Flask 3.1.3
# Werkzeug 3.1.x
```

The output confirms that Flask and its core dependency Werkzeug are installed at the expected versions.

### Running a Quick Test

Run a one-line Python command to import Flask and confirm the installed version programmatically:

```bash
python -c "import flask; print(f'Flask {flask.__version__} installed successfully')"
# Expected output: Flask 3.1.3 installed successfully
```

### Verifying All Dependencies

List installed packages and filter for the project's key dependencies:

```bash
pip list | grep -E "Flask|SQLAlchemy|python-dotenv|gunicorn|pytest|mkdocs"
```

Review the output to confirm that each package from the dependency reference table appears at the correct version. If any package is missing or shows an unexpected version, reinstall it using the pinned version command from the manual installation section above.

## Upgrading Dependencies

When a new version of a dependency is released and the team decides to adopt it, upgrade the specific package by specifying the new version explicitly:

```bash
pip install --upgrade flask==<new-version>
```

Replace `<new-version>` with the target version number (for example, `3.2.0`). After upgrading:

1. Update the version pin in `requirements.txt` to match the newly installed version.
2. Run the full test suite to verify that nothing is broken by the upgrade:

```bash
pytest
```

3. Commit both the updated `requirements.txt` and any code changes required by the new version.

> **Important:** Never leave `requirements.txt` out of sync with the actual installed versions. Every version pin in the manifest must match the version installed in the virtual environment.

## Troubleshooting

This section covers common issues encountered during installation and their resolutions.

**`pip: command not found`**

The `pip` executable is not on the system PATH. Use the module invocation form instead:

```bash
python3 -m pip install -r requirements.txt
```

If `python3 -m pip` also fails, pip may not be installed. On Ubuntu/Debian, install it with `sudo apt install python3-pip`.

**Permission denied errors**

If you receive permission errors during `pip install`, the most likely cause is attempting to install packages into the system Python without administrator privileges. Ensure the virtual environment is activated before running `pip install`:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

If the virtual environment is already active and you still encounter permission errors, try installing with the `--user` flag as a fallback:

```bash
pip install --user -r requirements.txt
```

**`ModuleNotFoundError: No module named 'flask'`**

This error means Python cannot find the Flask package in its current environment. The most common cause is that the virtual environment is not activated. Activate it and try again:

```bash
source venv/bin/activate
python -c "import flask; print(flask.__version__)"
```

If the error persists after activation, reinstall Flask:

```bash
pip install flask==3.1.3
```

**Python version mismatch**

If you see errors indicating that a package requires a newer Python version, verify that the active Python meets the minimum requirement of 3.9:

```bash
python3 --version
```

If the reported version is below 3.9, install a supported Python version following the platform-specific instructions in the [Installing Python](#installing-python) section above.

**SSL certificate errors on macOS**

After installing Python from the official installer on macOS, you may encounter SSL certificate verification errors when pip tries to download packages. Resolve this by running the certificate installation command that ships with the Python installer:

```bash
/Applications/Python\ 3.13/Install\ Certificates.command
```

Adjust the path to match the Python version you installed. After running this command, retry the `pip install` operation.

## Next Steps

With the development environment fully installed and verified, continue with the following guides:

- [Configuration Guide](configuration.md) — Set up environment variables and application configuration for development, testing, and production environments.
- [Quickstart Guide](quickstart.md) — Start the Flask development server and make your first API call.
- [Architecture Overview](../architecture/overview.md) — Understand the project's layered architecture, module responsibilities, and design principles.
