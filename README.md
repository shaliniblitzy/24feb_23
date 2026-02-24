# Flask Server

> **Last updated:** 2026-02-24

A production-ready Python 3 web server built with Flask that serves as a complete rewrite of the original Node.js server application, preserving all original functionalities with full feature parity. This project replaces the Express.js-based server with a modern Flask application, leveraging Python's ecosystem for routing, authentication, database access, and deployment.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.x-green?logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Table of Contents

- [Technology Stack](#technology-stack)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Project Structure](#project-structure)
- [API Overview](#api-overview)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.9+ |
| Web Framework | Flask | 3.1.x |
| ORM | SQLAlchemy (via Flask-SQLAlchemy) | 3.1.x |
| Database Migrations | Flask-Migrate (Alembic) | 4.0.x |
| CORS | Flask-CORS | 5.0.x |
| WSGI Server | Gunicorn | 23.x |
| Environment Management | python-dotenv | 1.0.x |
| Testing | pytest | 8.3.x |

## Features

- **REST API Endpoints** — Complete set of RESTful endpoints organized into Flask blueprints, mirroring all original Node.js Express routes
- **Authentication and Authorization** — Secure token-based authentication with role-based access control, implemented through Flask before-request hooks and decorators
- **Database Integration** — Full SQLAlchemy ORM integration via Flask-SQLAlchemy for robust, Pythonic database access with connection pooling and session management
- **Database Migrations** — Version-controlled schema migrations powered by Flask-Migrate and Alembic, supporting upgrade and downgrade operations
- **CORS Support** — Cross-Origin Resource Sharing configuration via Flask-CORS, preserving the same CORS policies from the original server
- **Request Logging** — Structured request and response logging with configurable log levels and output formats
- **Error Handling** — Centralized error handling with consistent JSON error responses and appropriate HTTP status codes
- **Configuration Management** — Environment-based configuration using python-dotenv, supporting development, staging, and production profiles

## Prerequisites

Ensure the following tools are installed on your system before proceeding:

| Tool | Minimum Version | Purpose |
|---|---|---|
| Python | 3.9+ | Runtime for the Flask application |
| pip | Latest | Python package installer |
| virtualenv | 20.0+ (recommended) | Isolated Python environments (included with Python 3.3+ via `venv`) |
| Git | 2.30+ | Version control |

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-org/flask-server.git
cd flask-server
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

Activate the virtual environment:

```bash
# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

The `requirements.txt` includes all pinned dependencies. Key packages installed:

```text
flask==3.1.3
flask-cors==6.0.2
flask-sqlalchemy==3.1.1
flask-migrate==4.0.7
python-dotenv==1.0.1
gunicorn==23.0.0
pytest==8.3.4
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your local configuration:

```ini
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db
```

### 5. Run database migrations

```bash
flask db upgrade
```

## Quickstart

### Start the development server

```bash
flask run
```

The server starts on `http://localhost:5000` by default. Alternatively, run the application directly:

```bash
python app.py
```

### Verify the server is running

```bash
curl http://localhost:5000/health
```

Expected response:

```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

### Make your first API call

```bash
curl -X GET http://localhost:5000/api/v1/users \
  -H "Content-Type: application/json"
```

Example response:

```json
{
  "data": [],
  "total": 0,
  "page": 1,
  "per_page": 20
}
```

## Project Structure

```text
flask-server/
├── app.py                  # Application entry point and factory
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies (pinned versions)
├── .env.example            # Environment variable template
├── routes/                 # Flask blueprints and route handlers
│   ├── __init__.py
│   ├── auth.py             # Authentication endpoints
│   ├── users.py            # User management endpoints
│   └── health.py           # Health check endpoint
├── models/                 # SQLAlchemy ORM models
│   ├── __init__.py
│   └── user.py             # User model definition
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── auth_service.py     # Authentication service
│   └── user_service.py     # User service
├── middleware/              # Request middleware
│   ├── __init__.py
│   ├── auth.py             # Authentication middleware
│   └── logging.py          # Request logging middleware
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Shared pytest fixtures
│   ├── test_auth.py        # Authentication tests
│   └── test_users.py       # User endpoint tests
├── migrations/             # Alembic migration scripts
├── docs/                   # Project documentation (MkDocs)
├── mkdocs.yml              # Documentation configuration
├── CONTRIBUTING.md          # Contribution guidelines
└── CHANGELOG.md             # Version history
```

## API Overview

The Flask server exposes a RESTful API organized into the following endpoint groups:

| Endpoint Group | Base Path | Description |
|---|---|---|
| Health | `/health` | Server health check and status |
| Authentication | `/api/v1/auth` | Login, logout, token refresh, and registration |
| Users | `/api/v1/users` | User CRUD operations and profile management |
| Resources | `/api/v1/resources` | Core resource management endpoints |

All endpoints return JSON responses and use standard HTTP status codes. Authentication-protected endpoints require a valid bearer token in the `Authorization` header.

For the complete API reference with request and response schemas, status codes, and example payloads, see the [API Reference](docs/api-reference/endpoints.md).

## Documentation

Comprehensive project documentation is available in the `docs/` directory and can be built into a browsable site using MkDocs.

### Build and serve documentation locally

```bash
pip install mkdocs==1.6.1 mkdocs-material==9.7.2 mkdocs-mermaid2-plugin==1.1.1
mkdocs serve --dev-addr 127.0.0.1:8000
```

### Documentation guides

| Guide | Path | Description |
|---|---|---|
| Installation Guide | [docs/getting-started/installation.md](docs/getting-started/installation.md) | Python, Flask, and dependency setup |
| Quickstart Guide | [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) | First run and server verification |
| Configuration Guide | [docs/getting-started/configuration.md](docs/getting-started/configuration.md) | Environment variables and config files |
| Architecture Overview | [docs/architecture/overview.md](docs/architecture/overview.md) | System design and component diagrams |
| API Reference | [docs/api-reference/endpoints.md](docs/api-reference/endpoints.md) | Complete REST API endpoint catalog |
| Migration Guide | [docs/guides/migration-from-nodejs.md](docs/guides/migration-from-nodejs.md) | Node.js to Flask migration mapping |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup and coding standards |
| Changelog | [CHANGELOG.md](CHANGELOG.md) | Version history and release notes |

## Contributing

Contributions are welcome! Whether you are fixing a bug, adding a feature, improving documentation, or reporting an issue, your contribution helps maintain feature parity and improve the Flask server.

Please read the [Contributing Guide](CONTRIBUTING.md) for detailed instructions on setting up your development environment, coding standards, branch naming conventions, commit message format, and the pull request process.

## License

This project is licensed under the MIT License.
