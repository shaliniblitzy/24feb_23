# Contributing to Flask Server

> **Last updated:** 2026-02-24

Thank you for your interest in contributing to the Flask Server project! This application is a Python 3 / Flask rewrite of an existing Node.js server, and we welcome contributions that help maintain feature parity, improve code quality, and expand documentation. Whether you are fixing a bug, adding a feature, improving documentation, or reporting an issue, your contribution is valued.

This guide covers everything you need to know to get started as a contributor, including how to set up your development environment, the coding standards we follow, our branching and commit conventions, and the process for submitting pull requests.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Coding Standards](#coding-standards)
- [Branch Naming Convention](#branch-naming-convention)
- [Commit Message Conventions](#commit-message-conventions)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Documentation Contribution](#documentation-contribution)
- [Reporting Issues](#reporting-issues)

## Development Environment Setup

### Prerequisites

Before you begin, ensure you have the following installed on your system:

| Tool | Minimum Version | Purpose |
|---|---|---|
| Python | 3.9+ | Runtime for the Flask application |
| pip | Latest | Python package installer |
| Git | 2.30+ | Version control |
| virtualenv | 20.0+ | Isolated Python environments (included with Python 3.3+ via `venv`) |

### Setting Up Your Development Environment

Follow these steps to set up a local development environment:

**1. Fork and clone the repository:**

```bash
git clone https://github.com/<your-username>/flask-server.git
cd flask-server
```

**2. Create a virtual environment:**

```bash
python -m venv venv
```

**3. Activate the virtual environment:**

On Linux or macOS:

```bash
source venv/bin/activate
```

On Windows:

```powershell
venv\Scripts\activate
```

**4. Install dependencies with pinned versions:**

```bash
pip install -r requirements.txt
```

The `requirements.txt` file contains all dependencies with exact version pins. Key application dependencies include:

```text
flask==3.1.3
flask-cors==5.0.1
flask-sqlalchemy==3.1.1
flask-migrate==4.0.7
python-dotenv==1.0.1
gunicorn==23.0.0
pytest==8.3.4
```

**5. Install development tools:**

```bash
pip install black==24.10.0 flake8==7.1.1 isort==5.13.2 mypy==1.14.1
```

**6. Copy the environment configuration template:**

```bash
cp .env.example .env
```

Open `.env` in your editor and configure your local settings. At minimum, set the following variables:

```dotenv
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-local-secret-key
DATABASE_URL=sqlite:///dev.db
```

**7. Run database migrations:**

```bash
flask db upgrade
```

This applies all pending Alembic migration scripts and sets up your local database schema.

**8. Run the development server:**

```bash
flask run --debug
```

The server starts on `http://localhost:5000` by default with hot-reloading enabled.

**9. Verify the server is running:**

```bash
curl http://localhost:5000/health
```

You should receive a JSON response confirming the server is healthy:

```json
{"status": "healthy"}
```

## Coding Standards

All Python code in this project must adhere to the following standards. These ensure consistency, readability, and maintainability across the entire codebase.

### Python Code Style

Follow [PEP 8](https://peps.python.org/pep-0008/), the official Python style guide. Key points include:

- Use 4 spaces for indentation (never tabs).
- Limit lines to 88 characters (aligned with the Black formatter default).
- Use blank lines to separate top-level definitions and method definitions.
- Use lowercase with underscores for function and variable names (`snake_case`).
- Use CamelCase for class names (`PascalCase`).
- Use UPPER_CASE for constants.

### Code Formatting

Use [Black](https://black.readthedocs.io/) as the code formatter with the default line length of 88 characters:

```bash
black .
```

To check formatting without modifying files:

```bash
black --check .
```

### Linting

Use [flake8](https://flake8.pycqa.org/) for static analysis:

```bash
flake8 .
```

The project uses a `.flake8` configuration file. If you encounter linting errors, fix them before committing. Common rules enforced:

- `E501` — Line length (deferred to Black's 88-character limit via configuration).
- `F401` — Unused imports must be removed.
- `F841` — Unused local variables must be removed.
- `E302` — Expected 2 blank lines before top-level definitions.

### Type Hints

Use Python type annotations for all function signatures, method parameters, and return types. Type hints improve code clarity and enable static analysis with tools like [mypy](https://mypy.readthedocs.io/):

```python
from flask import Flask, Response, jsonify


def create_app(config_name: str = "default") -> Flask:
    """Create and configure the Flask application instance.

    Args:
        config_name: The configuration profile to load.

    Returns:
        A configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(f"config.{config_name}")
    return app


def get_user_by_id(user_id: int) -> dict[str, str | int] | None:
    """Retrieve a user record by its primary key.

    Args:
        user_id: The unique identifier for the user.

    Returns:
        A dictionary containing user data, or None if not found.
    """
    # Implementation retrieves user from database
    ...
```

Run type checking with:

```bash
mypy .
```

### Docstrings

Use [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) for all public functions, classes, and modules. Every public function must include a docstring with at least a summary line, and where applicable, `Args`, `Returns`, and `Raises` sections:

```python
def authenticate_user(email: str, password: str) -> dict[str, str]:
    """Authenticate a user with email and password credentials.

    Validates the provided credentials against stored user records
    and returns an access token upon successful authentication.

    Args:
        email: The user's email address.
        password: The user's plaintext password for verification.

    Returns:
        A dictionary containing the access token and token type:
        {"access_token": "<jwt_token>", "token_type": "bearer"}

    Raises:
        ValueError: If the email format is invalid.
        AuthenticationError: If the credentials do not match.
    """
    ...
```

### Import Ordering

Use [isort](https://pycqa.github.io/isort/) to maintain consistent import ordering. Imports must follow this grouping order:

1. **Standard library** imports (e.g., `os`, `sys`, `json`)
2. **Third-party** imports (e.g., `flask`, `sqlalchemy`)
3. **Local application** imports (e.g., `from routes import auth_bp`)

Each group is separated by a blank line:

```python
import os
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_sqlalchemy import SQLAlchemy

from models.user import User
from services.auth import verify_token
```

Run import sorting with:

```bash
isort .
```

### Flask-Specific Conventions

The following conventions are specific to the Flask framework and must be followed throughout the project:

- **Use Flask blueprints for route grouping.** Every logical group of related endpoints (e.g., authentication, users, resources) must be registered as a separate Flask blueprint:

```python
from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    """Handle user login requests."""
    ...
```

- **Use the application factory pattern.** The Flask application instance must be created inside a `create_app()` factory function, never as a module-level global:

```python
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name: str = "default") -> Flask:
    """Application factory for creating the Flask app."""
    app = Flask(__name__)
    app.config.from_object(f"config.{config_name}")

    db.init_app(app)
    CORS(app)

    from routes.auth import auth_bp
    from routes.users import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)

    return app
```

- **Use Flask-SQLAlchemy for database models.** All ORM models must extend `db.Model` and define columns using SQLAlchemy column types:

```python
from extensions import db


class User(db.Model):
    """User account model."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
```

- **Manage configuration via environment variables and python-dotenv.** Application configuration must be loaded from environment variables using `python-dotenv`. Sensitive values (secret keys, database URIs, API keys) must never be hardcoded:

```python
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration loaded from environment variables."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-dev-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

## Branch Naming Convention

All branches must follow a consistent naming pattern to clearly communicate the purpose of the work. Use lowercase letters and hyphens to separate words within the description.

| Branch Type | Pattern | Example |
|---|---|---|
| Feature | `feature/<short-description>` | `feature/add-user-authentication` |
| Bug fix | `fix/<short-description>` | `fix/database-connection-timeout` |
| Documentation | `docs/<short-description>` | `docs/update-api-reference` |
| Hotfix | `hotfix/<short-description>` | `hotfix/critical-auth-bypass` |
| Refactor | `refactor/<short-description>` | `refactor/extract-service-layer` |

Guidelines for branch names:

- Always branch from `main` for new work.
- Keep descriptions concise but descriptive (3–5 words maximum).
- Use hyphens (`-`) to separate words, never underscores or spaces.
- Delete branches after they are merged.

Example workflow:

```bash
git checkout main
git pull origin main
git checkout -b feature/add-health-endpoint
```

## Commit Message Conventions

This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification. Every commit message must follow a structured format to enable automated changelog generation and clear project history.

### Format

```
<type>: <description>

[optional body]

[optional footer(s)]
```

- **type** — A keyword indicating the category of the change (see below).
- **description** — A concise summary of the change in imperative mood ("add feature" not "added feature"). Do not capitalize the first letter and do not end with a period.
- **body** — An optional detailed explanation of the change, wrapped at 72 characters.
- **footer** — Optional metadata such as `Closes #123` or `BREAKING CHANGE: <description>`.

### Commit Types

| Type | Description |
|---|---|
| `feat` | A new feature or endpoint |
| `fix` | A bug fix |
| `docs` | Documentation changes only |
| `test` | Adding or updating tests |
| `refactor` | Code restructuring without changing behavior |
| `chore` | Maintenance tasks (dependency updates, tooling) |
| `style` | Formatting changes that do not affect code logic |
| `perf` | Performance improvements |
| `ci` | Changes to CI/CD configuration |
| `build` | Changes affecting the build system or dependencies |

### Examples

```
feat: add user authentication endpoint

Implement POST /auth/login and POST /auth/register endpoints
using JWT tokens for session management.

Closes #42
```

```
fix: resolve database connection timeout

Increase SQLAlchemy pool recycle interval to 1800 seconds
to prevent stale connections during low-traffic periods.
```

```
docs: update API reference for /users endpoint
```

```
test: add integration tests for auth service
```

```
refactor: extract database query logic to service layer
```

```
chore: update Flask to 3.1.3
```

## Pull Request Process

Follow this process when submitting changes to the project. All contributions must go through a pull request review before merging into `main`.

### Step-by-Step Process

**1. Create a feature branch from `main`:**

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

**2. Implement your changes** following the coding standards described above.

**3. Write or update tests** to cover your changes. All new features must have corresponding unit tests, and all bug fixes must include regression tests.

**4. Ensure all tests pass locally:**

```bash
pytest
```

**5. Run the full quality check suite:**

```bash
black --check .
flake8 .
isort --check-only .
mypy .
pytest --cov
```

**6. Update documentation** if your changes add or modify API endpoints, configuration options, or user-facing features. Ensure documentation builds cleanly:

```bash
mkdocs build --strict
```

**7. Commit your changes** using the Conventional Commits format and push your branch:

```bash
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

**8. Open a pull request** on GitHub:

- Use a descriptive title following Conventional Commits format.
- In the PR body, describe what the change does and why it is needed.
- Link any related issues using `Closes #<issue-number>` or `Refs #<issue-number>`.
- Add relevant labels (e.g., `enhancement`, `bug`, `documentation`).

**9. Request a code review** from at least one project maintainer.

**10. Address review feedback** by pushing additional commits to your branch. Do not force-push over review comments.

**11. Merge** — Pull requests can be merged only after:

- All continuous integration (CI) checks pass.
- At least one maintainer has approved the changes.
- All review comments have been resolved.

### Pull Request Checklist

Before submitting your pull request, verify the following:

- [ ] Code follows the project's coding standards (PEP 8, Black formatted).
- [ ] All new and existing tests pass (`pytest`).
- [ ] Type hints are present on all new function signatures.
- [ ] Docstrings are present on all new public functions and classes.
- [ ] Documentation is updated for any user-facing changes.
- [ ] `mkdocs build --strict` passes with zero errors (if docs were modified).
- [ ] Commit messages follow Conventional Commits format.
- [ ] Branch is up to date with `main`.

## Testing Requirements

All contributions must include appropriate tests. Untested code will not be accepted into the project.

### Test Framework

The project uses [pytest](https://docs.pytest.org/) as its test framework, combined with Flask's built-in test client for HTTP endpoint testing. Key testing dependencies:

```text
pytest==8.3.4
```

### Writing Tests

**Unit tests** verify individual functions and methods in isolation:

```python
from services.auth import hash_password, verify_password


def test_hash_password_returns_hashed_string():
    """Verify that hash_password produces a non-empty hashed output."""
    result = hash_password("secure-password-123")
    assert result is not None
    assert result != "secure-password-123"


def test_verify_password_with_correct_password():
    """Verify that verify_password returns True for matching credentials."""
    hashed = hash_password("my-password")
    assert verify_password("my-password", hashed) is True


def test_verify_password_with_incorrect_password():
    """Verify that verify_password returns False for non-matching credentials."""
    hashed = hash_password("my-password")
    assert verify_password("wrong-password", hashed) is False
```

**Integration tests** use the Flask test client to verify endpoint behavior:

```python
import pytest

from app import create_app


@pytest.fixture
def client():
    """Create a Flask test client for integration testing."""
    app = create_app("testing")
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_health_endpoint_returns_200(client):
    """Verify the health check endpoint returns a 200 status code."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_login_with_valid_credentials(client):
    """Verify login returns an access token for valid credentials."""
    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "valid-password"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data
```

### Running Tests

Run the full test suite:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

Run tests with coverage reporting:

```bash
pytest --cov
```

Run tests with a detailed coverage report showing uncovered lines:

```bash
pytest --cov --cov-report=term-missing
```

Run a specific test file:

```bash
pytest tests/test_auth.py
```

Run a specific test function:

```bash
pytest tests/test_auth.py::test_health_endpoint_returns_200
```

### Test File Naming and Organization

All test files reside in the `tests/` directory and follow this naming convention:

| Source Module | Test File |
|---|---|
| `routes/auth.py` | `tests/test_auth.py` |
| `routes/users.py` | `tests/test_users.py` |
| `services/auth.py` | `tests/test_auth_service.py` |
| `models/user.py` | `tests/test_user_model.py` |

Guidelines:

- Every test file must be named `test_<module>.py`.
- Every test function must be named `test_<behavior_description>`.
- Use pytest fixtures for reusable test setup (database connections, test clients, mock data).
- Maintain or improve existing test coverage with every contribution. Regressions in coverage are not accepted.

## Documentation Contribution

Project documentation is built with [MkDocs](https://www.mkdocs.org/) using the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme. Documentation source files are written in Markdown and stored in the `docs/` directory.

### Previewing Documentation Locally

Start a local documentation server with live reloading:

```bash
mkdocs serve
```

This serves the documentation at `http://localhost:8000` and automatically refreshes when you edit Markdown files.

### Validating Documentation

Before submitting documentation changes, ensure the build passes with zero warnings and zero errors:

```bash
mkdocs build --strict
```

The `--strict` flag treats all warnings as errors, ensuring that broken internal links, missing files, and invalid navigation references are caught before merge.

### Documentation Standards

- All new API endpoints must be documented in `docs/api-reference/endpoints.md` with HTTP method, URL, parameters, request/response examples, and status codes.
- All architecture diagrams use [Mermaid](https://mermaid.js.org/) syntax embedded in fenced code blocks. Diagrams must render correctly in the MkDocs build.
- Use ATX-style Markdown headers (`#`, `##`, `###`) with no level skipping.
- Follow the existing document structure and formatting conventions.
- Include a last-updated date on any new documentation page.

### Adding a New Documentation Page

1. Create a new Markdown file in the appropriate `docs/` subdirectory.
2. Add the file to the `nav` section of `mkdocs.yml` so it appears in the navigation.
3. Verify the documentation builds cleanly with `mkdocs build --strict`.
4. Preview the page locally with `mkdocs serve` to confirm layout and rendering.

## Reporting Issues

We use GitHub Issues to track bugs, feature requests, and general improvements. Before opening a new issue, search existing issues to avoid duplicates.

### Bug Reports

When reporting a bug, include the following information to help us reproduce and fix the issue efficiently:

- **Summary:** A clear, concise description of the bug.
- **Environment:** Your Python version, Flask version, operating system, and any relevant dependency versions.
- **Steps to reproduce:** A numbered list of actions that reliably trigger the bug.
- **Expected behavior:** What you expected to happen.
- **Actual behavior:** What actually happened, including any error messages or stack traces.
- **Screenshots or logs:** Attach relevant terminal output, log files, or screenshots if applicable.

Example bug report structure:

```markdown
**Summary:** POST /auth/login returns 500 when email field is missing

**Environment:**
- Python 3.12.1
- Flask 3.1.3
- Ubuntu 24.04

**Steps to reproduce:**
1. Start the development server with `flask run --debug`
2. Send a POST request: `curl -X POST http://localhost:5000/auth/login -H "Content-Type: application/json" -d '{"password": "test"}'`
3. Observe the response

**Expected behavior:** A 400 Bad Request response with a validation error message.

**Actual behavior:** A 500 Internal Server Error response with a traceback in the server logs.
```

### Feature Requests

When proposing a new feature, describe the motivation and expected behavior:

- **Problem statement:** What limitation or gap does this feature address?
- **Proposed solution:** A clear description of what you want to happen.
- **Alternatives considered:** Any alternative approaches you evaluated and why they are less suitable.
- **Additional context:** Any mockups, diagrams, or references that clarify the request.

### Security Vulnerabilities

If you discover a security vulnerability, do not open a public issue. Instead, report it privately by emailing the project maintainers directly. Include as much detail as possible so the issue can be assessed and patched promptly.
