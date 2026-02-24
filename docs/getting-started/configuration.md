*Last updated: 2026-02-24*

# Configuration

This guide documents every environment variable, configuration file, and application setting used by the Flask server application. It covers the `.env` file format, the configuration class hierarchy, required versus optional settings, and secret key generation. Read this guide after completing the [Installation Guide](installation.md) and before proceeding to the [Quickstart Guide](quickstart.md).

## Overview

The Flask server uses [python-dotenv](https://pypi.org/project/python-dotenv/) to load environment variables from a `.env` file located in the project root. These environment variables drive all runtime configuration, from database connection strings to authentication secrets and logging behavior.

Configuration values are resolved through a three-level hierarchy, where each level overrides the one below it:

1. **System environment variables** — Variables set directly in the shell or by the hosting platform take the highest precedence. Any value defined at the system level overrides the corresponding value from the `.env` file or the application defaults.
2. **`.env` file values** — Variables defined in the project's `.env` file are loaded by `python-dotenv` at application startup. These override the default values hard-coded in the configuration classes but are themselves overridden by system environment variables.
3. **Application defaults in `config.py`** — Default values specified in the configuration class attributes serve as fallbacks when a variable is not set in either the environment or the `.env` file.

The application uses the **application factory pattern** with environment-specific configuration classes. The factory function `create_app()` accepts a configuration name (such as `"development"`, `"testing"`, or `"production"`) and loads the corresponding configuration class, which inherits from a shared `Config` base class.

The following code block illustrates the basic configuration loading pattern used by the Flask server:

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "default-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

> **Note:** The `load_dotenv()` call reads the `.env` file and injects its values into `os.environ`. Subsequent `os.environ.get()` calls then retrieve values from the merged environment, respecting the hierarchy described above.

## Environment Variables

This section catalogs every environment variable recognized by the Flask server, organized by functional area. Each table lists the variable name, a description of its purpose, whether it is required, its default value (if any), and an example value.

### Application Settings

These variables control the Flask application's core behavior, including the entry point, environment mode, session security, and debug output.

| Variable | Description | Required | Default | Example |
|---|---|---|---|---|
| `FLASK_APP` | Flask application entry point. Tells the `flask` CLI which module contains the application instance or factory. | Yes | `app.py` | `app.py` |
| `FLASK_ENV` | Application environment name. Determines which configuration class is loaded by the application factory. Accepted values: `development`, `testing`, `production`. | No | `production` | `development` |
| `SECRET_KEY` | Secret key used by Flask for session cookie signing, CSRF token generation, and any other cryptographic signing operation. Must be a long, random, unpredictable string in production. | Yes | None | `a3f1b9c7e2d04685...` |
| `DEBUG` | Enable or disable Flask debug mode. When set to `True`, the server provides interactive tracebacks and automatic code reloading. Must be `False` in production. | No | `False` | `True` |

### Database Settings

These variables configure the database connection used by Flask-SQLAlchemy and the SQLAlchemy connection pool. The `DATABASE_URL` variable is the primary connection string that tells the ORM where and how to connect to the database engine.

| Variable | Description | Required | Default | Example |
|---|---|---|---|---|
| `DATABASE_URL` | Database connection URI following the SQLAlchemy URL format. Supports SQLite, PostgreSQL, MySQL, and other SQLAlchemy-compatible backends. Required for production; the default SQLite URI is suitable for local development only. | Yes | `sqlite:///app.db` | `postgresql://user:pass@localhost:5432/flaskdb` |
| `SQLALCHEMY_POOL_SIZE` | Maximum number of persistent database connections maintained in the SQLAlchemy connection pool. Higher values support more concurrent database operations but consume more server memory. Ignored when using SQLite. | No | `5` | `10` |
| `SQLALCHEMY_POOL_TIMEOUT` | Maximum number of seconds to wait when acquiring a connection from the pool before raising a timeout error. Increase this value if the application experiences intermittent connection timeout errors under load. | No | `30` | `60` |

### Server Settings

These variables control the network interface, port, and process concurrency for the Flask development server and the Gunicorn production WSGI server.

| Variable | Description | Required | Default | Example |
|---|---|---|---|---|
| `HOST` | IP address the server binds to. Use `127.0.0.1` to accept connections from the local machine only, or `0.0.0.0` to accept connections from any network interface. | No | `127.0.0.1` | `0.0.0.0` |
| `PORT` | TCP port number the server listens on. Must be an available port not in use by another process. | No | `5000` | `8080` |
| `WORKERS` | Number of Gunicorn worker processes. Each worker handles requests independently. A common starting point is `2 * CPU_CORES + 1`. This variable is only used by the Gunicorn production server and has no effect on the Flask development server. | No | `4` | `8` |

### Authentication Settings

These variables configure JWT (JSON Web Token) authentication. The Flask server uses JWTs for stateless authentication, where the server issues a signed token upon successful login and clients include it in the `Authorization` header of subsequent requests.

| Variable | Description | Required | Default | Example |
|---|---|---|---|---|
| `JWT_SECRET_KEY` | Secret key used exclusively for signing and verifying JWT access tokens. Must be a long, random, unpredictable string and must differ from `SECRET_KEY` for defense-in-depth. | Yes | None | `jwt-a8e4c1f73b...` |
| `JWT_ACCESS_TOKEN_EXPIRES` | Lifetime of an access token in seconds. After this duration, the token becomes invalid and the client must re-authenticate or use a refresh token. | No | `3600` | `7200` |
| `JWT_ALGORITHM` | Cryptographic algorithm used to sign JWT tokens. `HS256` (HMAC with SHA-256) is the default symmetric signing algorithm. Change only if your deployment requires asymmetric keys (e.g., `RS256`). | No | `HS256` | `HS256` |

### CORS Settings

These variables configure Cross-Origin Resource Sharing (CORS) behavior, managed by the Flask-CORS extension. CORS controls which external web origins are allowed to make requests to the Flask server's API endpoints.

| Variable | Description | Required | Default | Example |
|---|---|---|---|---|
| `CORS_ORIGINS` | Comma-separated list of allowed origins. Use `*` to allow all origins (suitable for development) or specify exact origins for production security. Each origin must include the scheme and host (e.g., `https://app.example.com`). | No | `*` | `http://localhost:3000,https://app.example.com` |
| `CORS_METHODS` | Comma-separated list of HTTP methods permitted in cross-origin requests. Restricting methods in production reduces the attack surface for cross-origin abuse. | No | `GET,POST,PUT,DELETE,OPTIONS` | `GET,POST` |

### Logging Settings

These variables control the application's logging behavior, including the verbosity level and the output format. Flask's built-in logger and Python's standard `logging` module are configured based on these values.

| Variable | Description | Required | Default | Example |
|---|---|---|---|---|
| `LOG_LEVEL` | Minimum severity level for log messages. Messages below this level are discarded. Accepted values in order of increasing severity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. | No | `INFO` | `DEBUG` |
| `LOG_FORMAT` | Python logging format string controlling the layout of each log line. Uses standard `logging` format specifiers. Set to `json` to enable structured JSON log output (requires a JSON logging formatter). | No | `%(asctime)s %(levelname)s %(message)s` | `json` |

## Configuration File

The Flask server reads configuration from a `.env` file placed in the project root directory. This file contains key-value pairs — one per line — using the format `VARIABLE_NAME=value`. Lines starting with `#` are treated as comments and ignored.

The `.env` file is the recommended way to manage environment-specific settings during local development. It keeps sensitive values out of source code and allows each developer to maintain their own configuration without affecting others.

### Creating the .env File

The project includes a `.env.example` template that contains every recognized variable with placeholder or default values. Copy this template to create your own local `.env` file:

```bash
cp .env.example .env
```

Open the newly created `.env` file in your editor and replace placeholder values (such as `change-this-to-a-random-secret-key`) with real values appropriate for your development environment. At minimum, you must set `SECRET_KEY` and `JWT_SECRET_KEY` to unique random strings before starting the server. See the [Generating Secret Keys](#generating-secret-keys) section below for instructions.

### Important Security Notes

- **Never commit `.env` to version control.** The `.gitignore` file includes an entry for `.env` to prevent accidental commits. The `.env` file may contain secrets such as database passwords, API keys, and signing keys that must not appear in the repository history.
- **Always commit `.env.example`.** The example template is safe to commit because it contains only placeholder values. It serves as living documentation of every environment variable the application recognizes.
- **Use distinct values per environment.** Development, staging, and production environments must each use unique secret keys and database credentials. Never reuse production secrets in development or testing.

## Sample .env File

The following is a complete, annotated sample `.env` file that sets every recognized environment variable. Copy this content into your `.env` file and modify the values to match your environment.

```bash
# =============================================================================
# Flask Application Settings
# =============================================================================
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=change-this-to-a-random-secret-key
DEBUG=True

# =============================================================================
# Database Configuration
# =============================================================================
DATABASE_URL=sqlite:///app.db
# For PostgreSQL:
# DATABASE_URL=postgresql://username:password@localhost:5432/flask_server
SQLALCHEMY_POOL_SIZE=5
SQLALCHEMY_POOL_TIMEOUT=30

# =============================================================================
# Server Configuration
# =============================================================================
HOST=127.0.0.1
PORT=5000

# =============================================================================
# Authentication
# =============================================================================
JWT_SECRET_KEY=change-this-to-a-random-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_ALGORITHM=HS256

# =============================================================================
# CORS
# =============================================================================
CORS_ORIGINS=http://localhost:3000
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS

# =============================================================================
# Logging
# =============================================================================
LOG_LEVEL=DEBUG
LOG_FORMAT=%(asctime)s %(levelname)s %(message)s
```

> **Reminder:** Replace `change-this-to-a-random-secret-key` and `change-this-to-a-random-jwt-secret` with cryptographically secure random strings before running the application. See [Generating Secret Keys](#generating-secret-keys) for instructions.

## Configuration Classes

The Flask server organizes configuration into a class hierarchy defined in `config.py`. A base `Config` class holds settings shared across all environments, and environment-specific subclasses override or extend those settings as needed. The application factory function `create_app()` selects the appropriate class based on the `FLASK_ENV` environment variable.

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration shared across all environments."""
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    SQLALCHEMY_POOL_SIZE = int(os.environ.get("SQLALCHEMY_POOL_SIZE", 10))


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
```

### When Each Configuration Class Is Used

- **`DevelopmentConfig`** — Activated when `FLASK_ENV=development`. Enables Flask debug mode (`DEBUG = True`) for automatic code reloading and interactive error pages. Enables SQLAlchemy query logging (`SQLALCHEMY_ECHO = True`) so that every SQL statement is printed to the console, which is invaluable for debugging database interactions during development.

- **`TestingConfig`** — Activated when `FLASK_ENV=testing`. Sets `TESTING = True`, which causes Flask to propagate exceptions rather than handling them with error pages, making test failures more visible. Uses an in-memory SQLite database (`sqlite:///:memory:`) so that every test run starts with a clean database and no persistent state leaks between tests.

- **`ProductionConfig`** — Activated when `FLASK_ENV=production` (the default if `FLASK_ENV` is not set). Disables debug mode (`DEBUG = False`) to prevent exposing internal application details. Configures a larger connection pool (`SQLALCHEMY_POOL_SIZE = 10` by default) to handle production-level concurrency.

### Selecting a Configuration at Startup

The application factory reads `FLASK_ENV` and looks up the matching class in the `config_by_name` dictionary:

```python
# app.py (application factory pattern)
from flask import Flask
from config import config_by_name

def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "production")
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    # Initialize extensions, register blueprints, attach middleware...
    return app
```

If `FLASK_ENV` is set to an unrecognized value, the `config_by_name` lookup raises a `KeyError`. Always use one of the three recognized values: `development`, `testing`, or `production`.

## Required vs Optional Settings

The table below categorizes every environment variable as required or optional. Required variables have no safe default and must be explicitly set before the application starts. Optional variables include sensible defaults that are suitable for local development.

### Required Variables

These variables **must** be set before the application can start. If any of these are missing, the application will either fail to start or operate insecurely.

| Variable | Reason |
|---|---|
| `SECRET_KEY` | Used for session cookie signing and CSRF protection. Without a strong, unique key, sessions are vulnerable to tampering and forgery. |
| `JWT_SECRET_KEY` | Used for signing JWT access tokens. Without this key, the authentication system cannot issue or verify tokens. |
| `DATABASE_URL` (production) | The default `sqlite:///app.db` is acceptable for local development but is not suitable for production. A production-grade database URI (e.g., PostgreSQL) must be provided. |

> **Warning:** If `SECRET_KEY` or `JWT_SECRET_KEY` is not set, the application will raise a configuration error on startup. Never run a production server without explicitly setting these values to cryptographically secure random strings.

### Optional Variables

These variables have safe defaults suitable for development. Override them as needed for staging or production environments.

| Variable | Default | Notes |
|---|---|---|
| `FLASK_APP` | `app.py` | Only change if your application entry point uses a different filename. |
| `FLASK_ENV` | `production` | Set to `development` for local work to enable debug mode and query logging. |
| `DEBUG` | `False` | Automatically set to `True` by `DevelopmentConfig`. Avoid enabling in production. |
| `HOST` | `127.0.0.1` | Change to `0.0.0.0` when the server must accept connections from external hosts. |
| `PORT` | `5000` | Change if port 5000 is already in use or your deployment requires a different port. |
| `WORKERS` | `4` | Adjust based on available CPU cores for production Gunicorn deployments. |
| `SQLALCHEMY_POOL_SIZE` | `5` | Increase for production workloads with high database concurrency. |
| `SQLALCHEMY_POOL_TIMEOUT` | `30` | Increase if the application experiences connection timeout errors under load. |
| `JWT_ACCESS_TOKEN_EXPIRES` | `3600` (1 hour) | Shorten for higher security; lengthen for better user experience. |
| `JWT_ALGORITHM` | `HS256` | Change only for asymmetric key deployments (e.g., `RS256`). |
| `CORS_ORIGINS` | `*` | Restrict to specific origins in production for security. |
| `CORS_METHODS` | `GET,POST,PUT,DELETE,OPTIONS` | Restrict to only the methods your API exposes. |
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` during development for verbose output; `WARNING` or `ERROR` in production to reduce noise. |
| `LOG_FORMAT` | `%(asctime)s %(levelname)s %(message)s` | Set to `json` for structured logging in production log aggregation systems. |

## Generating Secret Keys

Both `SECRET_KEY` and `JWT_SECRET_KEY` must be set to long, random, unpredictable strings. Using weak or predictable keys compromises session security and authentication integrity.

Generate a cryptographically secure 64-character hexadecimal key using Python's built-in `secrets` module:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

This command produces output similar to:

```
a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2
```

Run the command twice to generate separate keys for `SECRET_KEY` and `JWT_SECRET_KEY`. Copy each output into the corresponding variable in your `.env` file:

```bash
SECRET_KEY=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2
JWT_SECRET_KEY=f0e1d2c3b4a5968778695a4b3c2d1e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
```

> **Important:** Generate fresh keys for every environment (development, staging, production). Never share keys between environments and never commit real keys to version control.

## Next Steps

With the application configured, continue to the next guides:

- [Quickstart Guide](quickstart.md) — Start the Flask development server and verify that it responds to requests using the configuration you just set up.
- [Architecture Overview](../architecture/overview.md) — Understand the layered system design, module responsibilities, and design principles that govern the Flask server.
- [Deployment Guide](../guides/deployment.md) — Configure the application for production deployment with Gunicorn, Docker, and environment-specific settings.
