"""Gunicorn WSGI server configuration for production deployment.

This module configures the Gunicorn HTTP/WSGI server used to serve the Flask
backend application in production and staging environments. It is referenced
by the Dockerfile CMD directive as: gunicorn -c gunicorn.conf.py wsgi:app

Configuration is tuned to meet the following performance targets:
  - JWT validation        < 5 ms
  - Route dispatch        < 10 ms
  - End-to-end (no AI)   < 200 ms
  - End-to-end (with AI) < 15 s

The timeout is set to 120 s to provide a safety margin above the 15-second
AI-inclusive latency budget, accommodating LLM provider retries and the
3-tier fallback strategy (Primary → Secondary → Tertiary → 503).
"""

import multiprocessing

# ---------------------------------------------------------------------------
# Server Socket
# ---------------------------------------------------------------------------
# Bind to all network interfaces on port 8000 so the application is
# accessible from within the Docker container and via the host-mapped port.
bind = "0.0.0.0:8000"

# ---------------------------------------------------------------------------
# Worker Processes
# ---------------------------------------------------------------------------
# The recommended Gunicorn formula for CPU-bound synchronous workers is
# (2 × CPU cores) + 1.  This balances throughput with memory consumption
# when running inside ECS/Fargate tasks sized at 1–4 vCPUs.
workers = multiprocessing.cpu_count() * 2 + 1

# ---------------------------------------------------------------------------
# Worker Class
# ---------------------------------------------------------------------------
# Standard synchronous workers are used.  The Flask application performs
# blocking I/O (PyMongo, boto3, HTTP to LLM providers) so sync workers
# with an adequate worker count are the simplest correct choice.
worker_class = "sync"

# ---------------------------------------------------------------------------
# Timeout Settings
# ---------------------------------------------------------------------------
# `timeout` — Maximum seconds a worker can spend handling a single request
# before it is forcibly killed and restarted.  Set to 120 s to accommodate
# the worst-case LLM provider fallback chain (3 providers × up to 3 retries
# each with exponential back-off, capped at ~15 s total) with headroom.
timeout = 120

# `graceful_timeout` — Seconds to wait for workers to finish serving
# requests after receiving a SIGTERM before they are forcibly killed.
# 30 s allows in-flight requests to complete during rolling deployments.
graceful_timeout = 30

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Direct access and error logs to stdout / stderr so they are captured by
# Docker's logging driver and forwarded to CloudWatch Logs when running on
# ECS/Fargate.
accesslog = "-"
errorlog = "-"

# Log level for Gunicorn's own internal messages.  "info" provides
# worker lifecycle events without the noise of "debug".
loglevel = "info"

# ---------------------------------------------------------------------------
# Process Naming
# ---------------------------------------------------------------------------
# Sets the process title visible in `ps` and monitoring tools.
proc_name = "flask-backend"

# ---------------------------------------------------------------------------
# Security — Request Limits
# ---------------------------------------------------------------------------
# Maximum size of the HTTP request line (method + URI + protocol) in bytes.
# 8190 is the Gunicorn default and comfortably handles long query strings.
limit_request_line = 8190

# Maximum number of HTTP header fields allowed per request.  100 is the
# Gunicorn default and sufficient for standard REST API traffic including
# Authorization, CORS, and tracing headers.
limit_request_fields = 100

# ---------------------------------------------------------------------------
# Server Mechanics
# ---------------------------------------------------------------------------
# Load the Flask application before forking worker processes so that
# application code and static data are shared via copy-on-write memory,
# reducing per-worker RSS.  This also causes import-time errors to surface
# immediately at startup rather than on the first request.
preload_app = True
