# Testing Guide

*Last updated: 2026-02-24*

This guide provides a comprehensive reference for setting up, writing, and running tests for the Flask server application using pytest and Flask's built-in test client. It is intended for developers writing tests for the Flask application — both newcomers learning the test stack and experienced developers seeking reference patterns for unit tests, integration tests, and API endpoint tests.

## Test Environment Setup

### Prerequisites

Before writing or running tests, ensure the following tools are installed on your system:

| Tool | Minimum Version | Purpose |
|---|---|---|
| Python | 3.9+ | Runtime for the Flask application and test suite |
| pip | Latest | Python package installer |
| virtualenv | 20.0+ | Isolated Python environments (included with Python 3.3+ via `venv`) |

### Installing Test Dependencies

Create and activate a virtual environment, then install the test dependencies with pinned versions:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install the core application and testing packages:

```bash
pip install flask==3.1.3
pip install flask-sqlalchemy==3.1.1
pip install flask-cors==6.0.2
pip install flask-migrate==4.0.7
pip install python-dotenv==1.0.1
pip install pytest==8.3.4
pip install pytest-cov==6.0.0
```

Alternatively, install all dependencies from the project manifest:

```bash
pip install -r requirements.txt
```

### Test Directory Structure

All test files reside in the `tests/` directory at the project root. The directory is organized by the module or layer under test:

```text
tests/
├── conftest.py          # Shared fixtures (app, client, db_session)
├── test_auth.py         # Authentication endpoint tests
├── test_users.py        # User endpoint tests
├── test_services.py     # Service layer unit tests
└── test_models.py       # Model unit tests
```

### Test File Naming Convention

Test files must follow the naming pattern `test_<module>.py` so that pytest's automatic discovery can locate them. Each source module maps to a corresponding test file:

| Source Module | Test File |
|---|---|
| `routes/auth.py` | `tests/test_auth.py` |
| `routes/users.py` | `tests/test_users.py` |
| `services/user_service.py` | `tests/test_services.py` |
| `models/user.py` | `tests/test_models.py` |

Individual test functions within each file must be named `test_<behavior_description>` using lowercase and underscores, describing the specific behavior being verified.

## Pytest Configuration

### Configuration File

Create a `pytest.ini` file at the project root to configure pytest's discovery and output settings:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts = -v --tb=short
```

Alternatively, define the same settings in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
python_classes = ["Test*"]
addopts = "-v --tb=short"
```

### Key Configuration Options

| Option | Description |
|---|---|
| `testpaths` | Directories where pytest searches for test files. Set to `tests` to restrict discovery to the test directory. |
| `python_files` | Filename pattern for test modules. The pattern `test_*.py` matches files like `test_auth.py` and `test_users.py`. |
| `python_functions` | Function name pattern for test cases. The pattern `test_*` matches functions like `test_create_user_success`. |
| `python_classes` | Class name pattern for test classes. The pattern `Test*` matches classes like `TestUserService`. |
| `addopts` | Default command-line options appended to every pytest invocation. `-v` enables verbose output and `--tb=short` produces concise tracebacks. |

### Test-Specific Environment Variables

Configure environment variables for the test environment by creating a `.env.test` file or setting them directly in the test fixtures. The following variables are commonly overridden during testing:

| Variable | Test Value | Purpose |
|---|---|---|
| `FLASK_ENV` | `testing` | Activates the testing configuration profile |
| `DATABASE_URL` | `sqlite:///:memory:` | Uses an in-memory SQLite database for fast, isolated tests |
| `SECRET_KEY` | `test-secret-key` | A non-sensitive key for signing tokens during tests |
| `TESTING` | `True` | Enables Flask's testing mode, which disables error catching for clearer test output |

You can set these variables in the application fixture (shown in the next section) or load them from a dedicated `.env.test` file using `python-dotenv`:

```python
from dotenv import load_dotenv

load_dotenv(".env.test")
```

## Flask Test Client

Flask provides a built-in test client that allows you to send HTTP requests to the application without running a live server. The test client simulates the WSGI environment, making it possible to test the full request/response cycle — including middleware hooks, blueprint route dispatch, service layer invocations, and JSON response formatting — within pytest.

### Core Test Fixtures in conftest.py

The `tests/conftest.py` file defines shared fixtures that are automatically available to all test modules. The following example shows the three foundational fixtures for Flask testing:

```python
import pytest
from app import create_app
from extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """Create the Flask application instance for the test session.

    Uses the application factory to create a fresh app configured for
    testing. The in-memory SQLite database is created once per session
    and torn down after all tests complete.
    """
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key",
    })

    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Provide a Flask test client for sending HTTP requests.

    The test client is function-scoped, creating a fresh client for
    each test function to prevent state leakage between tests.
    """
    return app.test_client()


@pytest.fixture()
def db_session(app):
    """Provide a database session with automatic rollback after each test.

    This fixture yields the SQLAlchemy session and rolls back all
    changes after the test completes, ensuring complete isolation
    between test functions.
    """
    with app.app_context():
        yield _db.session
        _db.session.rollback()
```

### Fixture Descriptions

| Fixture | Scope | Purpose |
|---|---|---|
| `app` | Session | Creates a single Flask application instance configured for testing. The in-memory database is initialized once and shared across all tests in the session for performance. |
| `client` | Function | Returns a Flask test client bound to the application. A new client is created for each test function to prevent request state from leaking between tests. |
| `db_session` | Function | Provides the SQLAlchemy session with automatic rollback. All database changes made during a test are rolled back when the fixture tears down, guaranteeing test isolation. |

## Fixture Patterns

Fixtures are reusable setup and teardown functions that pytest injects into test functions by name. This section covers common fixture patterns used throughout the Flask server's test suite.

### Authentication Fixture

Many endpoint tests require authenticated requests. The following fixture generates a valid JWT token and returns it as an HTTP header dictionary ready for use with the test client:

```python
@pytest.fixture()
def auth_headers():
    """Provide HTTP headers with a valid authentication token.

    Creates a test JWT token for an admin user and returns it in
    the format expected by the Authorization header.
    """
    token = create_test_token(user_id=1, role="admin")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
```

Use this fixture in endpoint tests that require authentication:

```python
def test_protected_endpoint(client, auth_headers):
    response = client.get("/api/users/", headers=auth_headers)
    assert response.status_code == 200
```

### Sample Data Fixture

Database-dependent tests need seed data. The following fixture creates a sample user record in the test database and returns the model instance for assertions:

```python
@pytest.fixture()
def sample_user(db_session):
    """Create and persist a sample user record for testing.

    Inserts a user into the test database and returns the model
    instance. The record is automatically rolled back after the
    test completes via the db_session fixture.
    """
    from models.user import User

    user = User(
        email="test@example.com",
        name="Test User",
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    return user
```

### Cleanup and Fixture Scoping

Pytest fixtures support different scopes that control when setup and teardown occur:

| Scope | Lifecycle | Use Case |
|---|---|---|
| `function` | Runs before and after each test function | Database sessions, test clients — any state that must be isolated per test |
| `class` | Runs once per test class | Shared setup for a group of related tests within a single class |
| `module` | Runs once per test module (file) | Expensive resources shared across all tests in a file |
| `session` | Runs once per entire test session | Application instance, database schema creation |

The recommended pattern for database test isolation uses a **session-scoped application fixture** combined with a **function-scoped database session fixture**. The application and schema are created once for performance, while each test gets a fresh database session that rolls back after completion:

```python
@pytest.fixture(scope="session")
def app():
    """Session-scoped: create the app and schema once."""
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture()
def db_session(app):
    """Function-scoped: fresh session with rollback per test."""
    with app.app_context():
        yield _db.session
        _db.session.rollback()
```

This approach ensures that database state never leaks between tests while avoiding the overhead of recreating the entire database schema for every individual test function.

## Unit Tests

Unit tests verify individual functions and methods in isolation, ensuring that each piece of business logic produces the correct output for given inputs. In the Flask server architecture, unit tests primarily target the service layer — the Python modules in `services/` that encapsulate business rules and data transformations.

### Writing Unit Tests

Each unit test function should focus on a single behavior and follow the Arrange-Act-Assert pattern:

1. **Arrange** — Set up any required preconditions (fixtures, mock data).
2. **Act** — Call the function under test.
3. **Assert** — Verify the result matches the expected outcome.

### Service Layer Unit Test Example

```python
# tests/test_services.py
import pytest


def test_create_user_success(app, db_session):
    """Verify that create_user returns a dictionary with the new user's data."""
    from services.user_service import create_user

    with app.app_context():
        result = create_user(email="new@example.com", name="New User")

        assert result["email"] == "new@example.com"
        assert result["name"] == "New User"
        assert "id" in result


def test_create_user_duplicate_email(app, db_session, sample_user):
    """Verify that create_user raises ValueError for duplicate email addresses."""
    from services.user_service import create_user

    with app.app_context():
        with pytest.raises(ValueError, match="already registered"):
            create_user(email="test@example.com", name="Duplicate")


def test_create_user_assigns_default_role(app, db_session):
    """Verify that create_user assigns the default 'user' role when none is specified."""
    from services.user_service import create_user

    with app.app_context():
        result = create_user(email="default@example.com", name="Default Role User")

        assert result["role"] == "user"
```

### Model Unit Test Example

```python
# tests/test_models.py
def test_user_to_dict(app, db_session):
    """Verify that User.to_dict() returns a correctly structured dictionary."""
    from models.user import User

    with app.app_context():
        user = User(email="dict@example.com", name="Dict User", role="admin")
        db_session.add(user)
        db_session.commit()

        data = user.to_dict()

        assert data["email"] == "dict@example.com"
        assert data["name"] == "Dict User"
        assert data["role"] == "admin"
        assert "id" in data
        assert "created_at" in data
```

## Integration Tests

Integration tests verify that multiple components work together correctly. Unlike unit tests that isolate a single function, integration tests exercise the interaction between services, models, and the database layer to confirm that data flows correctly through the system.

### Writing Integration Tests

Integration tests typically call a service function that internally queries or mutates the database, then verify the end-to-end result. These tests use the `app` and `db_session` fixtures to provide a real (in-memory) database context.

### Service-to-Database Integration Example

```python
# tests/test_integration.py
def test_user_lifecycle(app, db_session):
    """Verify the full create-then-retrieve lifecycle for a user record."""
    from services.user_service import create_user, get_user_by_id

    with app.app_context():
        created = create_user(
            email="lifecycle@example.com",
            name="Lifecycle User",
        )
        fetched = get_user_by_id(created["id"])

        assert fetched is not None
        assert fetched["email"] == "lifecycle@example.com"
        assert fetched["name"] == "Lifecycle User"


def test_user_update_persists(app, db_session):
    """Verify that updating a user record persists changes to the database."""
    from services.user_service import create_user, update_user, get_user_by_id

    with app.app_context():
        created = create_user(
            email="update@example.com",
            name="Original Name",
        )
        update_user(created["id"], name="Updated Name")
        fetched = get_user_by_id(created["id"])

        assert fetched["name"] == "Updated Name"
```

## API Endpoint Tests

API endpoint tests verify the full HTTP request/response cycle using Flask's test client. These tests exercise the complete stack — middleware hooks, blueprint route dispatch, service layer invocations, database operations, and JSON response formatting — ensuring that the API behaves correctly from the client's perspective.

### Writing Endpoint Tests

Endpoint tests use the `client` fixture to send HTTP requests and assert on the response status code, headers, and JSON body. Each test should target a single endpoint behavior (success case, validation error, not found, unauthorized access).

### Endpoint Test Examples

```python
# tests/test_users.py


def test_list_users(client, sample_user):
    """Verify GET /api/users/ returns a list containing the sample user."""
    response = client.get("/api/users/")

    assert response.status_code == 200
    data = response.get_json()
    assert "data" in data
    assert len(data["data"]) >= 1


def test_create_user(client, auth_headers):
    """Verify POST /api/users/ creates a new user and returns 201."""
    response = client.post(
        "/api/users/",
        json={"email": "api@example.com", "name": "API User"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["email"] == "api@example.com"
    assert data["name"] == "API User"


def test_create_user_missing_fields(client, auth_headers):
    """Verify POST /api/users/ returns 400 when required fields are missing."""
    response = client.post(
        "/api/users/",
        json={},
        headers=auth_headers,
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data


def test_get_user_not_found(client):
    """Verify GET /api/users/<id> returns 404 for a non-existent user ID."""
    response = client.get("/api/users/99999")

    assert response.status_code == 404


def test_create_user_unauthorized(client):
    """Verify POST /api/users/ returns 401 when no auth token is provided."""
    response = client.post(
        "/api/users/",
        json={"email": "noauth@example.com", "name": "No Auth"},
    )

    assert response.status_code == 401
```

## Running Tests

This section documents the pytest commands for executing the test suite. Multiple command variations are provided for different testing scenarios.

### Run All Tests

Execute the entire test suite by running pytest from the project root directory:

```bash
pytest
```

This discovers and runs all test files matching `test_*.py` inside the `tests/` directory. The default options defined in `pytest.ini` (verbose output, short tracebacks) are applied automatically.

### Run with Verbose Output and Coverage

Generate a code coverage report alongside test results to identify untested code paths:

```bash
pytest --cov=app --cov-report=term-missing -v
```

This command runs all tests with verbose output (`-v`), measures code coverage for the `app` package (`--cov=app`), and displays a terminal report highlighting the specific line numbers not covered by tests (`--cov-report=term-missing`).

### Run a Specific Test File

Target a single test module when working on a specific feature or debugging a failure:

```bash
pytest tests/test_users.py -v
```

This runs only the tests in `tests/test_users.py` with verbose output, providing faster feedback during focused development.

### Run Tests Matching a Keyword

Filter tests by name using the `-k` option to run a subset of tests matching a keyword expression:

```bash
pytest -k "test_create" -v
```

This runs all test functions whose names contain `test_create`, regardless of which test file they reside in. Keyword expressions support boolean operators: `pytest -k "test_create and not duplicate"`.

### Run with Parallel Execution

Speed up the test suite by distributing tests across multiple CPU cores using `pytest-xdist`:

```bash
pytest -n auto
```

The `-n auto` flag automatically detects the number of available CPU cores and distributes tests evenly across them. Install the `pytest-xdist` package (`pip install pytest-xdist==3.5.0`) to enable parallel execution.

### Run and Stop at First Failure

Exit immediately after the first test failure to accelerate the debugging cycle:

```bash
pytest -x
```

The `-x` flag stops test execution as soon as a single test fails, allowing you to focus on fixing one issue at a time without waiting for the remaining tests to complete.

### Run a Specific Test Function

Target an individual test function by specifying the file path and function name separated by `::`:

```bash
pytest tests/test_auth.py::test_health_endpoint_returns_200
```

This is useful for re-running a single failing test during debugging.

## Coverage Targets

The project enforces minimum code coverage thresholds to ensure that critical application logic is adequately tested. Coverage is measured using `pytest-cov` with branch coverage enabled.

### Minimum Coverage Requirements

| Layer | Target Coverage | Rationale |
|---|---|---|
| Service layer (`services/`) | 90% branch coverage | Services contain core business logic; high coverage ensures correctness of critical operations |
| Route handlers (`routes/`) | 85% coverage | Endpoint handlers are the API surface; coverage ensures all request paths and error cases are tested |
| Models (`models/`) | 80% coverage | Model methods (serialization, validation) must be tested; schema definitions have limited testable logic |
| Overall project | 80% minimum | Baseline coverage threshold applied across the entire codebase |

### Generating Coverage Reports

**Terminal report with missing lines:**

```bash
pytest --cov=app --cov-report=term-missing
```

This prints a coverage summary table to the terminal with line numbers for uncovered code.

**HTML report for detailed analysis:**

```bash
pytest --cov=app --cov-report=html
```

This generates an interactive HTML report in the `htmlcov/` directory. Open `htmlcov/index.html` in your browser to browse coverage data file by file with highlighted source lines.

**Enforcing minimum coverage in CI:**

```bash
pytest --cov=app --cov-fail-under=80
```

The `--cov-fail-under=80` flag causes pytest to exit with a non-zero status code if overall coverage falls below 80%, making it suitable for continuous integration pipelines that must block merges when coverage regresses.

See [Contributing Guide](../../CONTRIBUTING.md) for team testing requirements and PR review expectations.

## Troubleshooting

This section documents common issues encountered when setting up or running the test suite, along with their causes and solutions.

| Issue | Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | Pytest is not running from the project root directory, so Python cannot locate the application package. | Run `pytest` from the project root directory where `app.py` resides. Alternatively, ensure the project root is on `PYTHONPATH`: `PYTHONPATH=. pytest`. |
| Tests fail with `OperationalError: no such table` | Database tables were not created in the test fixture before running queries. | Ensure `_db.create_all()` is called inside the `app` fixture within `app.app_context()` before the `yield` statement. |
| `RuntimeError: Working outside of application context` | Flask features (such as `db.session`, `current_app`, or `url_for`) are accessed outside an active application context. | Wrap the operation in `with app.app_context():` or ensure the test function uses a fixture that provides an active context. |
| Fixture not found | The `conftest.py` file is missing from the `tests/` directory, or the fixture is defined with the wrong scope. | Verify that `conftest.py` exists in `tests/` and that the fixture name matches the parameter name in your test function. |
| Database state leaking between tests | The `db_session` fixture is missing the rollback teardown, causing data from one test to persist into the next. | Use a function-scoped `db_session` fixture that calls `_db.session.rollback()` after the `yield` statement, as shown in the [Flask Test Client](#flask-test-client) section. |
| `ImportError: cannot import name 'create_app'` | The application factory function is not defined or is not importable from the `app` module. | Verify that `app.py` exports a `create_app()` function and that the virtual environment is activated with all dependencies installed. |
| Coverage report shows 0% for all files | The `--cov` argument points to the wrong package name. | Ensure the `--cov` value matches the top-level package name (for example, `--cov=app` if the application code is in the `app` package). |

## See Also

- [Contributing Guide](../../CONTRIBUTING.md) — Testing requirements for contributions, PR checklist, and quality standards
- [API Reference](../api-reference/endpoints.md) — Complete REST API endpoint catalog for writing targeted API tests
- [Architecture Overview](../architecture/overview.md) — System component structure, layered architecture, and glossary of standard terminology
