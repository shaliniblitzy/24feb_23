# =============================================================================
# Dockerfile — Multi-Stage Docker Build for Flask Backend
# =============================================================================
#
# Production-ready multi-stage Dockerfile for the Flask backend API server.
# Uses two stages (builder + runtime) to minimise the final image size by
# discarding build-time dependencies such as compilers and header files.
#
# Build:
#   docker build -t flask-backend .
#
# Run (production):
#   docker run -p 8000:8000 --env-file .env flask-backend
#
# The entrypoint uses Gunicorn (gunicorn.conf.py → wsgi:app) — the Flask
# development server must never be used in production or staging.
#
# Recommended .dockerignore contents (create a .dockerignore file):
#   .env
#   .env.*
#   !.env.example
#   .venv/
#   venv/
#   __pycache__/
#   *.pyc
#   .git/
#   .github/
#   tests/
#   .pytest_cache/
#   .ruff_cache/
#   htmlcov/
#   .coverage
#   *.egg-info/
#   dist/
#   build/
#   docs/
#   *.md
#   docker-compose*.yml
#   Dockerfile
#   .flake8
#   ruff.toml
#   mkdocs.yml
# =============================================================================


# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python dependencies into an isolated prefix
# ---------------------------------------------------------------------------
# This stage is discarded in the final image.  Only the installed packages
# (under /install) are carried forward, keeping build-time artefacts (pip
# cache, wheel files, compilers) out of the production image.
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS builder

WORKDIR /app

# Copy only the requirements file first to leverage Docker's layer caching.
# Dependency layers are rebuilt only when requirements.txt changes, not when
# application source code changes.
COPY requirements.txt .

# Install production dependencies into a dedicated prefix (/install) so they
# can be copied cleanly into the runtime stage.  --no-cache-dir avoids
# storing the pip download cache inside the image layer.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------------------------------------------------------------------------
# Stage 2: Runtime — minimal production image
# ---------------------------------------------------------------------------
# Uses the same python:3.14-slim base for consistency.  The image contains
# only the Python runtime, installed packages, and application source code.
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS runtime

# ---- Environment variables ------------------------------------------------
# PYTHONDONTWRITEBYTECODE: Prevent Python from writing .pyc bytecode files
#   to the filesystem inside the container (keeps image layers clean).
# PYTHONUNBUFFERED: Force stdout/stderr to be unbuffered so that log output
#   appears immediately in Docker logs and CloudWatch.
# FLASK_ENV: Default to production — overridden via docker-compose or
#   --env-file for development and testing environments.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

# ---- Install runtime system dependencies ----------------------------------
# curl is required for the Docker HEALTHCHECK directive below.
# Cleanup apt caches in the same RUN layer to keep the image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Create non-root user -------------------------------------------------
# Running the application as a non-root user is a security best practice.
# The user "appuser" has a home directory for any runtime file needs.
RUN useradd --create-home appuser

WORKDIR /app

# ---- Copy installed packages from the builder stage -----------------------
# The /install prefix from the builder maps onto /usr/local so that
# site-packages, scripts, and shared libraries land in the correct system
# paths without manual PYTHONPATH manipulation.
COPY --from=builder /install /usr/local

# ---- Copy application source code -----------------------------------------
# Application code is copied last so that source-code-only changes do not
# invalidate the (slower) dependency installation layers above.
COPY . .

# ---- Set ownership ---------------------------------------------------------
# Ensure the appuser owns all application files so it can read source code,
# configuration files, and write to any temporary directories if needed.
RUN chown -R appuser:appuser /app

# ---- Expose Gunicorn port -------------------------------------------------
# Gunicorn binds to 0.0.0.0:8000 (configured in gunicorn.conf.py).
EXPOSE 8000

# ---- Switch to non-root user ----------------------------------------------
USER appuser

# ---- Docker health check ---------------------------------------------------
# The health check targets the /api/health liveness endpoint for container
# orchestration integration (ECS/Fargate, Docker Compose, Kubernetes).
# --interval: time between checks (30 s)
# --timeout:  maximum time to wait for a response (10 s)
# --start-period: grace period during container startup (40 s)
# --retries: consecutive failures before marking unhealthy (3)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# ---- Entrypoint ------------------------------------------------------------
# Start the Gunicorn WSGI server using the configuration file and the WSGI
# application object defined in wsgi.py.  Flask's development server must
# never be used in production or staging environments.
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
