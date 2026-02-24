# Deployment Guide

*Last updated: 2026-02-24*

This guide provides comprehensive instructions for deploying the Flask server application to production environments, covering both containerized (Docker) and bare-metal deployment strategies. It is intended for DevOps engineers and developers responsible for deploying and maintaining the Flask server in staging and production environments.

## Deployment Overview

Flask's built-in development server (`flask run`) is designed for local development and debugging only. It is **not suitable for production** because it is single-threaded, lacks performance optimizations, and does not handle concurrent requests efficiently. For production deployments, the Flask application must run behind a dedicated WSGI (Web Server Gateway Interface) HTTP server.

The production deployment stack follows a layered architecture:

```text
Client → Reverse Proxy (Nginx) → WSGI Server (Gunicorn) → Flask Application → Database
```

Nginx acts as the public-facing entry point, handling SSL termination, static file serving, and request buffering. Gunicorn manages multiple worker processes that each run the Flask application, enabling concurrent request handling. The Flask application processes business logic and communicates with the database through the service layer and ORM models.

Two deployment strategies are supported:

1. **Docker containerization** — Recommended for consistent, portable deployments. The application, its dependencies, and the runtime environment are packaged into a single Docker image that runs identically across development, staging, and production.
2. **Bare-metal deployment** — Direct installation on a Linux server. Suited for environments where Docker is unavailable or where fine-grained control over the host operating system is required.

Both strategies use **Gunicorn** as the WSGI HTTP server, with uWSGI available as an alternative for teams with existing uWSGI infrastructure.

## Prerequisites

Before deploying the Flask server, ensure the following requirements are met:

- **Python 3.9+** installed on the target server (for bare-metal deployments)
- **Docker 24+** and **Docker Compose v2** installed (for containerized deployments)
- The application source code cloned from the repository
- All Python dependencies installed from `requirements.txt`
- Environment variables configured for the target environment. See [Configuration Guide](../getting-started/configuration.md) for the complete environment variable catalog.
- A **PostgreSQL database** server accessible from the deployment environment (or the database of your choice, as configured via `DATABASE_URL`)

Install the core production dependencies with version-pinned commands:

```bash
pip install gunicorn==23.0.0
pip install flask==3.1.3
pip install flask-sqlalchemy==3.1.1
pip install flask-migrate==4.0.7
pip install flask-cors==6.0.2
pip install python-dotenv==1.0.1
```

> **Note:** In practice, all dependencies are declared in `requirements.txt` and installed together with `pip install -r requirements.txt`. The individual commands above are shown for reference.

## Gunicorn Configuration

Gunicorn (Green Unicorn) is the recommended production WSGI HTTP server for the Flask application. It uses a pre-fork worker model to handle concurrent requests across multiple worker processes, providing reliable performance under production workloads.

### Basic Startup

Start the Flask application with Gunicorn using the application factory pattern:

```bash
gunicorn --bind 0.0.0.0:8000 --workers 4 "app:create_app()"
```

This command tells Gunicorn to import `app.py`, call the `create_app()` factory function to obtain the Flask application instance, bind to all network interfaces on port 8000, and spawn 4 worker processes.

### Configuration Parameters

The following table describes key Gunicorn parameters and their recommended values for production:

| Parameter | Description | Recommended Value |
|---|---|---|
| `--bind` | Address and port to bind | `0.0.0.0:8000` |
| `--workers` | Number of worker processes | `2 * CPU cores + 1` |
| `--timeout` | Worker timeout in seconds | `120` |
| `--access-logfile` | Access log file path | `-` (stdout) or `/var/log/gunicorn/access.log` |
| `--error-logfile` | Error log file path | `-` (stderr) or `/var/log/gunicorn/error.log` |
| `--max-requests` | Requests per worker before restart | `1000` |
| `--max-requests-jitter` | Random jitter added to max-requests | `50` |

- **`--workers`**: The recommended formula is `2 * CPU_CORES + 1`. For a 2-core server, use 5 workers. For a 4-core server, use 9 workers.
- **`--timeout`**: Set to 120 seconds to accommodate long-running requests. Reduce this value if all endpoints are expected to respond quickly.
- **`--max-requests`**: Automatically restarts each worker after processing 1000 requests, preventing memory leaks from accumulating over time. The `--max-requests-jitter` adds a random delay (up to 50 requests) so that all workers do not restart simultaneously.

### Configuration File

For complex deployments, use a `gunicorn.conf.py` configuration file instead of command-line arguments:

```python
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 120

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Worker recycling
max_requests = 1000
max_requests_jitter = 50
```

Start Gunicorn with the configuration file:

```bash
gunicorn -c gunicorn.conf.py "app:create_app()"
```

### Application Factory Invocation

The entry point string `"app:create_app()"` tells Gunicorn to:

1. Import the module named `app` (i.e., `app.py` in the project root)
2. Call the `create_app()` function defined in that module
3. Use the returned Flask application instance to handle incoming requests

This follows the application factory pattern described in the [Architecture Overview](../architecture/overview.md), which allows the same codebase to produce differently configured application instances for development, testing, and production environments.

## uWSGI Alternative

uWSGI is an alternative WSGI server that provides additional features such as built-in process management, caching, and load balancing. It is documented here for teams with existing uWSGI infrastructure; **Gunicorn is the recommended default** for new deployments.

### uWSGI Startup Command

```bash
uwsgi --http 0.0.0.0:8000 --wsgi-file wsgi.py --callable app --processes 4 --threads 2
```

### WSGI Entry Point

When using uWSGI, create a `wsgi.py` file in the project root that exposes the Flask application instance:

```python
from app import create_app

app = create_app()
```

uWSGI looks for the `app` callable in the file specified by `--wsgi-file`. The `--processes` flag controls the number of worker processes, and `--threads` controls threads per process.

> **Note:** Gunicorn is preferred over uWSGI for most Flask deployments due to its simpler configuration, better default behavior with Flask's application factory pattern, and active maintenance. Use uWSGI only if your infrastructure already depends on it.

## Docker Deployment

Docker containerization is the recommended deployment strategy for the Flask server. Packaging the application into a Docker image ensures consistent behavior across all environments and simplifies deployment, scaling, and rollback operations.

### Dockerfile

The following production-ready Dockerfile builds a minimal image for the Flask server:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app:create_app()"]
```

**Key decisions in this Dockerfile:**

- **`python:3.12-slim`** — Uses the slim variant to minimize image size while retaining the Python standard library.
- **`gcc` system dependency** — Required to compile certain Python C-extension packages during `pip install`. It is installed early and not removed so that the layer remains cached.
- **Non-root user (`appuser`)** — The application runs as a non-root user to follow the principle of least privilege. This prevents the container process from having unnecessary host-level permissions.
- **`HEALTHCHECK` directive** — Docker periodically calls the `/health` endpoint to determine whether the container is healthy. If the health check fails 3 consecutive times, Docker marks the container as unhealthy.
- **`--no-cache-dir`** — Prevents pip from caching downloaded packages inside the image, reducing final image size.

### Docker Compose

Use Docker Compose to define and run the Flask server alongside its database in a single configuration file. The following `docker-compose.yml` is suitable for local development and staging environments:

```yaml
version: "3.9"
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=${DB_NAME}
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  pgdata:
```

> **Important:** Never hardcode database credentials in `docker-compose.yml`. Create a `.env` file in the same directory with the required values:
>
> ```dotenv
> DB_USER=your_db_user
> DB_PASSWORD=your_secure_password
> DB_NAME=flaskdb
> SECRET_KEY=your-secret-key-here
> ```
>
> Docker Compose automatically loads variables from a `.env` file in the project root. Add `.env` to `.gitignore` to prevent credentials from being committed to version control.

**Configuration notes:**

- The `web` service builds the Flask application from the Dockerfile in the current directory and maps port 8000.
- The `db` service runs PostgreSQL 16 on Alpine Linux, storing data in a named Docker volume (`pgdata`) for persistence across container restarts.
- All credentials are loaded from environment variables defined in a `.env` file, keeping secrets out of version control.
- `depends_on` ensures the database container starts before the web container, though the application should still implement retry logic for database connections.
- `restart: unless-stopped` ensures containers automatically restart after failures or host reboots, unless explicitly stopped by an operator.

### Build and Run

Build and run the Docker image using the following commands:

```bash
# Build the Docker image
docker build -t flask-server:latest .

# Run the container
docker run -d -p 8000:8000 --env-file .env --name flask-server flask-server:latest

# Verify the container is running
docker ps

# Check container logs
docker logs flask-server

# Stop and remove the container
docker stop flask-server && docker rm flask-server
```

Using Docker Compose:

```bash
# Start all services in the background
docker compose up -d

# View logs for all services
docker compose logs -f

# Stop all services
docker compose down

# Rebuild and restart after code changes
docker compose up -d --build
```

## Bare-Metal Deployment

Bare-metal deployment installs the Flask server directly on a Linux server without container orchestration. This approach is suited for environments where Docker is unavailable or where direct control over the host operating system is required.

### System Setup

Prepare an Ubuntu/Debian server for the Flask application:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3, pip, and virtual environment support
sudo apt install -y python3 python3-pip python3-venv

# Install Nginx for reverse proxying
sudo apt install -y nginx

# Create a dedicated application user
sudo useradd -m -s /bin/bash flaskapp
sudo su - flaskapp
```

Creating a dedicated `flaskapp` user isolates the application from other processes and limits permissions to only what the application needs.

### Application Installation

Install the Flask application step by step:

```bash
# Clone the repository
git clone <repository-url> /home/flaskapp/flask-server
cd /home/flaskapp/flask-server

# Create a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install all dependencies from the pinned requirements file
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with production values (database URL, secret key, etc.)
nano .env

# Run database migrations to initialize the schema
flask db upgrade
```

> **Important:** Always use a virtual environment (`venv`) in bare-metal deployments to isolate the application's Python dependencies from the system Python installation. This prevents version conflicts with system packages.

### Systemd Service Configuration

Create a systemd service unit to manage the Flask server as a background daemon that starts automatically on boot, restarts on failure, and integrates with standard Linux service management tools.

Create the service file at `/etc/systemd/system/flask-server.service`:

```ini
[Unit]
Description=Flask Server Application
After=network.target

[Service]
User=flaskapp
Group=flaskapp
WorkingDirectory=/home/flaskapp/flask-server
Environment="PATH=/home/flaskapp/flask-server/venv/bin"
EnvironmentFile=/home/flaskapp/flask-server/.env
ExecStart=/home/flaskapp/flask-server/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 4 "app:create_app()"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Configuration notes:**

- **`User` and `Group`** — Runs Gunicorn as the `flaskapp` user, matching the file ownership of the application directory.
- **`Environment="PATH=..."`** — Points to the virtual environment's `bin/` directory so that Gunicorn and all Python dependencies are resolved from the venv.
- **`EnvironmentFile`** — Loads environment variables from the `.env` file, which contains database credentials, secret keys, and other configuration. See [Configuration Guide](../getting-started/configuration.md) for the full variable catalog.
- **`--bind 127.0.0.1:8000`** — Binds only to localhost because Nginx (the reverse proxy) handles external traffic. This prevents direct public access to Gunicorn.
- **`Restart=always`** and **`RestartSec=5`** — Automatically restarts the service 5 seconds after any failure.

Manage the service with standard systemd commands:

```bash
# Reload systemd to pick up the new service file
sudo systemctl daemon-reload

# Start the Flask server
sudo systemctl start flask-server

# Enable automatic startup on boot
sudo systemctl enable flask-server

# Check service status
sudo systemctl status flask-server

# View service logs
sudo journalctl -u flask-server -f
```

## Reverse Proxy (Nginx)

A reverse proxy sits between external clients and the Gunicorn WSGI server. Nginx is the recommended reverse proxy for the Flask server because it provides:

- **SSL/TLS termination** — Handles HTTPS encryption, offloading CPU-intensive TLS processing from Gunicorn.
- **Static file serving** — Serves static assets (CSS, JavaScript, images) directly from disk without passing requests through to the Flask application.
- **Load balancing** — Distributes requests across multiple Gunicorn instances when scaling horizontally.
- **Request buffering** — Buffers slow client uploads and downloads, freeing Gunicorn workers to process new requests faster.

### Nginx Server Block

Create an Nginx server block configuration file at `/etc/nginx/sites-available/flask-server`:

```nginx
server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias /home/flaskapp/flask-server/static/;
        expires 30d;
    }
}
```

**Configuration notes:**

- **`proxy_pass`** — Forwards all requests to Gunicorn running on `127.0.0.1:8000`.
- **`proxy_set_header` directives** — Pass the original client IP address, hostname, and protocol scheme to the Flask application so that `request.remote_addr` and URL generation work correctly.
- **`proxy_read_timeout`** — Matches the Gunicorn worker timeout (120 seconds) to prevent Nginx from closing the connection before Gunicorn responds.
- **`/static/` location** — Serves static files directly from the filesystem with a 30-day browser cache expiry, bypassing the Flask application entirely.

### Enable the Nginx Configuration

```bash
# Create a symbolic link to enable the site
sudo ln -s /etc/nginx/sites-available/flask-server /etc/nginx/sites-enabled/

# Test the Nginx configuration for syntax errors
sudo nginx -t

# Reload Nginx to apply the new configuration
sudo systemctl reload nginx
```

### SSL/TLS with Let's Encrypt

For production deployments, enable HTTPS using a free SSL certificate from Let's Encrypt:

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain and install the SSL certificate
sudo certbot --nginx -d example.com

# Verify automatic renewal
sudo certbot renew --dry-run
```

Certbot automatically modifies the Nginx server block to listen on port 443 with SSL and redirects HTTP traffic to HTTPS.

## Health Monitoring

Health monitoring ensures that the Flask server is running correctly and can serve requests. Implement health check endpoints and configure external monitoring tools to detect and respond to failures.

### Basic Health Check Endpoint

Add a health check endpoint to the Flask application that returns the server status:

```python
from flask import jsonify
from datetime import datetime, timezone


@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200
```

This endpoint returns a JSON response with a `200 OK` status code when the server is operational. External monitoring tools and load balancers can poll this endpoint at regular intervals.

### Database-Aware Health Check

For a more comprehensive health check that verifies database connectivity, use the following pattern:

```python
from flask import jsonify
from datetime import datetime, timezone
from extensions import db


@app.route("/health")
def health_check():
    try:
        db.session.execute(db.text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200 if db_status == "connected" else 503
```

This version executes a lightweight database query (`SELECT 1`) to verify connectivity. If the database is unreachable, the endpoint returns a `503 Service Unavailable` status with a `"degraded"` status indicator, signaling to load balancers and monitoring systems that the instance should be taken out of rotation.

### Monitoring Approaches

| Approach | Description | Use Case |
|---|---|---|
| Docker HEALTHCHECK | Built-in Docker health check directive (included in the Dockerfile) | Container orchestration environments |
| External uptime monitors | Services that poll the `/health` endpoint from outside the network | Public-facing availability monitoring |
| Prometheus + Grafana | Metrics collection and visualization for request rates, latencies, and error rates | Detailed operational dashboards |
| Gunicorn access/error logs | Log files produced by Gunicorn workers for every request | Debugging and post-incident analysis |
| systemd journal | Logs captured by `journalctl -u flask-server` for the systemd service | Bare-metal deployment monitoring |

### Log-Based Monitoring

Gunicorn writes access and error logs that can be forwarded to centralized log management systems:

```bash
# View Gunicorn access logs (if writing to a file)
tail -f /var/log/gunicorn/access.log

# View Gunicorn error logs
tail -f /var/log/gunicorn/error.log

# View systemd service logs in real time
sudo journalctl -u flask-server -f
```

Configure Gunicorn to write structured logs by setting the `accesslog` and `errorlog` parameters in `gunicorn.conf.py` to file paths or `-` for stdout/stderr (suitable for Docker where logs are captured by the container runtime).

## Troubleshooting

The following table documents common deployment issues, their causes, and solutions:

| Issue | Cause | Solution |
|---|---|---|
| `[ERROR] Connection in use: ('0.0.0.0', 8000)` | Port 8000 is already in use by another process | Identify the process with `sudo lsof -i :8000` and terminate it with `kill <PID>` |
| `ModuleNotFoundError` in Gunicorn | Virtual environment is not activated or Gunicorn is installed outside the venv | Ensure Gunicorn runs from within the virtual environment or use the full path: `/home/flaskapp/flask-server/venv/bin/gunicorn` |
| `502 Bad Gateway` from Nginx | Gunicorn is not running or is bound to a different port than Nginx expects | Verify Gunicorn is running with `systemctl status flask-server` and confirm the `proxy_pass` port in the Nginx configuration matches Gunicorn's `--bind` port |
| Docker container exits immediately | Application crashes on startup due to missing configuration or import errors | Check container logs with `docker logs flask-server` and verify all required environment variables are set |
| Database connection refused | `DATABASE_URL` is incorrect or the database server is not running | Verify the database server is running, confirm the connection string in `.env`, and test connectivity with `psql -h <host> -U <user> -d <dbname>` |
| Permission denied on log files | Log directory has incorrect file ownership | Fix ownership with `sudo chown -R flaskapp:flaskapp /var/log/gunicorn/` and ensure the directory exists with `sudo mkdir -p /var/log/gunicorn` |
| `[CRITICAL] WORKER TIMEOUT` | A Gunicorn worker exceeded the `--timeout` value | Increase the timeout in `gunicorn.conf.py` (e.g., `timeout = 300`) or investigate slow endpoint handlers for performance bottlenecks |
| SSL certificate errors after Certbot | Certificate renewal failed or Nginx was not reloaded | Run `sudo certbot renew` and reload Nginx with `sudo systemctl reload nginx` |

### Diagnostic Commands

Use the following commands to diagnose deployment issues:

```bash
# Check if Gunicorn is running and listening
sudo lsof -i :8000

# Test the Flask application directly (bypassing Nginx)
curl -s http://127.0.0.1:8000/health

# Test the full stack through Nginx
curl -s http://example.com/health

# Check Nginx configuration for syntax errors
sudo nginx -t

# View the last 50 lines of the systemd service log
sudo journalctl -u flask-server --no-pager -n 50

# Check Docker container health status
docker inspect --format='{{.State.Health.Status}}' flask-server
```

## See Also

- [Configuration Guide](../getting-started/configuration.md) — Environment variable catalog and configuration reference for production settings
- [Architecture Overview](../architecture/overview.md) — System component structure, layered architecture, and design principles
- [Installation Guide](../getting-started/installation.md) — Development environment setup and dependency installation
