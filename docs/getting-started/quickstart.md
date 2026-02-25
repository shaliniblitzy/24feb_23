# Quickstart

*Last updated: 2026-02-24*

This guide walks you through starting the Flask server for the first time, verifying that it is running correctly with a health check, and making your first API call. It is intended for developers who have already completed the [Installation Guide](installation.md) and the [Configuration Guide](configuration.md) and are ready to launch the application and interact with it.

## Prerequisites

Before continuing, confirm that the following setup steps are complete:

- **Python 3 and all dependencies are installed.** If not, follow the [Installation Guide](installation.md) to set up Python, create a virtual environment, and install all project dependencies.
- **Environment variables are configured.** If not, follow the [Configuration Guide](configuration.md) to create your `.env` file with the required settings (at minimum, `SECRET_KEY` and `JWT_SECRET_KEY`).

Run the following commands to verify your environment is ready:

```bash
python --version   # Should output Python 3.9 or higher
flask --version    # Should output Flask 3.1.3
```

If either command fails or shows an unexpected version, revisit the [Installation Guide](installation.md) to resolve the issue before proceeding.

## Starting the Development Server

There are several ways to start the Flask development server. Choose the method that best fits your workflow.

### Using Flask CLI

The Flask CLI is the recommended way to start the development server. Set the required environment variables and run the `flask run` command:

```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

If your `.env` file already contains `FLASK_APP` and `FLASK_ENV` entries (as described in the [Configuration Guide](configuration.md)), the `python-dotenv` integration loads them automatically and the `export` commands above are not required.

You should see output similar to the following:

```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

The server is now running and accepting requests on `http://127.0.0.1:5000`. Press `Ctrl+C` in the terminal to stop the server at any time.

### Using Python Directly

You can also start the server by running the application entry point directly with the Python interpreter:

```bash
python app.py
```

This approach works when the `app.py` module includes a standard `if __name__ == "__main__"` block that calls `app.run()`. The Flask CLI method is preferred because it provides more control over startup options and integrates with the Flask extension ecosystem.

### Specifying Host and Port

By default, the Flask development server binds to `127.0.0.1` on port `5000`. To change the host or port — for example, to allow connections from other devices on the network or to avoid a port conflict — use the `--host` and `--port` flags:

```bash
flask run --host=0.0.0.0 --port=8080
```

This starts the server on all available network interfaces at port `8080`, making it accessible from other machines on the same network at `http://<your-ip>:8080`.

## Verifying the Server

After starting the server, verify that it is running correctly by calling the health check endpoint.

### Health Check Endpoint

The Flask server exposes a `/health` endpoint that returns the application's health status, database connectivity, and a timestamp. Use `curl` to send a request from a new terminal window:

```bash
curl http://localhost:5000/health
```

You should receive a JSON response confirming that the server is healthy and the database is connected:

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-02-24T12:00:00+00:00"
}
```

A `200 OK` status code with `"status": "healthy"` and `"database": "connected"` confirms that the server is running and can reach the database. If the command fails with a "Connection refused" error, verify that the server process is still running in the other terminal window.

### Using Python

You can also verify the server programmatically using the `requests` library:

```python
import requests

response = requests.get("http://localhost:5000/health")
print(response.status_code)  # 200
print(response.json())       # {"status": "healthy", "database": "connected", "timestamp": "..."}
```

This approach is useful when scripting automated health checks or integrating with monitoring tools. The `requests` library is not a project dependency by default — install it with `pip install requests==2.32.3` if it is not already available in your environment.

## Making Your First API Call

With the server verified, you can now interact with the REST API endpoints. The examples below demonstrate registering a user account, listing users, and creating a resource using the API.

### Example: Register a User

Send a `POST` request to the registration endpoint to create a new user account. This endpoint does not require authentication:

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Doe", "email": "jane@example.com", "password": "securepassword123"}'
```

On success, the server responds with the newly created user object and a `201 Created` status code:

```json
{
  "id": 1,
  "email": "jane@example.com",
  "name": "Jane Doe",
  "role": "user",
  "is_active": true,
  "created_at": "2026-02-24T12:00:00+00:00",
  "updated_at": "2026-02-24T12:00:00+00:00"
}
```

The `id` field is assigned automatically by the database. The response contains the full representation of the created user, excluding the password hash for security.

### Example: List Users

To access protected endpoints, first log in to obtain an access token, then send a `GET` request to the users endpoint with the token in the `Authorization` header:

```bash
curl -X GET "http://localhost:5000/api/users/?page=1&per_page=20" \
  -H "Authorization: Bearer <access_token>"
```

The response includes a paginated list of users with flat pagination metadata:

```json
{
  "data": [
    {
      "id": 1,
      "email": "jane@example.com",
      "name": "Jane Doe",
      "role": "user",
      "is_active": true,
      "created_at": "2026-02-24T12:00:00+00:00",
      "updated_at": "2026-02-24T12:00:00+00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1
}
```

The `total` field indicates the total count of records, `page` is the current page number, and `pages` is the total number of pages. As you add users, these values will update accordingly.

### Example: Create a Resource

Send an authenticated `POST` request to create a new resource:

```bash
curl -X POST http://localhost:5000/api/resources/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"name": "Project Alpha", "description": "A sample project resource", "is_public": true}'
```

On success, the server responds with the newly created resource and a `201 Created` status code:

```json
{
  "id": 1,
  "name": "Project Alpha",
  "description": "A sample project resource",
  "is_public": true,
  "owner_id": 1,
  "created_at": "2026-02-24T12:00:00+00:00",
  "updated_at": "2026-02-24T12:00:00+00:00"
}
```

The `owner_id` is automatically set to the authenticated user's ID based on the JWT token.

For a complete catalog of all available endpoints, including authentication, resource management, and detailed request/response schemas, see the [API Reference](../api-reference/endpoints.md).

## Debug Mode

Flask's debug mode enables two features that accelerate development:

- **Automatic reloading** — The server watches for file changes and restarts itself whenever you save a modified source file, eliminating the need to manually stop and restart the server after each edit.
- **Interactive debugger** — When an unhandled exception occurs, Flask displays an interactive traceback in the browser. You can inspect local variables and execute Python expressions at any frame in the call stack.

To start the server in debug mode, use the `--debug` flag:

```bash
flask run --debug
```

> **⚠️ Warning:** Never enable debug mode in a production environment. The interactive debugger allows arbitrary code execution on the server, which represents a critical security vulnerability if exposed to untrusted users. Debug mode is strictly for local development. For production deployment, see the [Deployment Guide](../guides/deployment.md).

## Running Tests

Running the test suite is a quick way to confirm that the application is functioning correctly after setup. The project uses `pytest` as its test framework.

Execute the full test suite from the project root directory:

```bash
pytest
```

For more detailed output showing each individual test and its result, use the verbose flag:

```bash
pytest -v
```

To run tests for a specific module or file, pass the path as an argument:

```bash
pytest tests/test_auth.py -v
```

All tests should pass on a correctly configured environment. If any tests fail, verify that your `.env` file is properly configured (especially `DATABASE_URL` and `SECRET_KEY`) and that all dependencies are installed at the correct versions.

For comprehensive testing documentation including fixture patterns, Flask test client usage, coverage targets, and advanced pytest configuration, see the [Testing Guide](../guides/testing.md).

## Next Steps

Now that the server is running and you have verified it with a health check and API calls, explore the following resources to deepen your understanding of the application:

- [Architecture Overview](../architecture/overview.md) — Understand the system design, layered architecture, and module responsibilities
- [API Reference](../api-reference/endpoints.md) — Complete REST API endpoint catalog with request/response schemas and examples
- [Authentication Guide](../guides/authentication.md) — Set up JWT authentication, manage tokens, and protect endpoints
- [Database Guide](../guides/database.md) — Learn about ORM setup, schema migrations, and query patterns
- [Deployment Guide](../guides/deployment.md) — Deploy the Flask server to production with Gunicorn, Docker, and reverse proxy configuration

## Troubleshooting

This section covers common issues encountered when starting the Flask server for the first time and their solutions.

**Port already in use**

If you see an error message indicating that port 5000 is already in use, another process is occupying that port. Either stop the other process or start Flask on a different port:

```bash
flask run --port=5001
```

To identify the process using port 5000, run `lsof -i :5000` on Linux/macOS or `netstat -ano | findstr :5000` on Windows, then terminate it if appropriate.

**Module not found errors**

An `ImportError` or `ModuleNotFoundError` when starting the server typically means the virtual environment is not activated or dependencies are not installed. Verify that the virtual environment is active (your terminal prompt should show `(venv)`) and reinstall dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Database connection errors**

If the server starts but API calls return database-related errors, verify the `DATABASE_URL` variable in your `.env` file. For local development with SQLite, the default value `sqlite:///app.db` should work without additional setup. For PostgreSQL or MySQL, confirm that the database server is running and that the credentials in the connection URI are correct:

```bash
# Test PostgreSQL connectivity
psql -h localhost -U your_username -d your_database -c "SELECT 1;"
```

See the [Configuration Guide](configuration.md) for the full list of database-related environment variables and their expected formats.

**CORS errors in browser**

If a frontend application making requests to the Flask server receives CORS errors in the browser console, verify that Flask-CORS is properly configured. Check that `CORS_ORIGINS` in your `.env` file includes the origin of the frontend application (for example, `http://localhost:3000` for a React development server). During development, setting `CORS_ORIGINS=*` permits requests from all origins:

```bash
# In your .env file
CORS_ORIGINS=http://localhost:3000
```

See the [Configuration Guide](configuration.md) for all CORS-related settings.

**Flask CLI not recognized**

If running `flask run` produces a "command not found" error, ensure that Flask is installed in the active virtual environment and that the virtual environment's `bin` directory is on your `PATH`. Reactivating the environment typically resolves this:

```bash
source venv/bin/activate
flask --version
```

If the problem persists, reinstall Flask with the pinned version:

```bash
pip install flask==3.1.3
```
