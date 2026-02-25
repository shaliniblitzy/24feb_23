"""Flask extension initialization: CORS, PyMongo client factory, logging configuration.

This module provides centralized initialization of Flask extensions and shared
singletons used across the application. It manages:

- PyMongo client singleton with production-ready connection pooling
  (maxPoolSize=50, minPoolSize=10, serverSelectionTimeoutMS=5000)
- Structured JSON logging compatible with AWS CloudWatch
- Graceful teardown for connection cleanup during shutdown

Architecture note: This module provides INFRASTRUCTURE only — no business logic,
no route handling, no service logic, no repository operations.
"""

import logging

from pymongo import MongoClient

# ---------------------------------------------------------------------------
# Module-level singletons — initialized lazily via init_extensions()
# Thread-safe: PyMongo's MongoClient is designed for shared use across threads.
# ---------------------------------------------------------------------------
_mongo_client: MongoClient | None = None
_db = None

# Module-level logger for this extension module
_logger = logging.getLogger(__name__)


def get_mongo_client(app=None) -> MongoClient | None:
    """Get or create the PyMongo client singleton.

    Uses a lazy-initialization pattern: the client is only created when an
    ``app`` with valid configuration is provided for the first time.
    Subsequent calls (even without ``app``) return the cached singleton.

    Connection pooling parameters (per AAP §0.5.3):
        - maxPoolSize=50  — maximum connections in the pool
        - minPoolSize=10  — minimum connections kept alive
        - maxIdleTimeMS=30000 — idle connection reclaim after 30 s
        - serverSelectionTimeoutMS=5000 — fast failure on unreachable servers

    Args:
        app: Flask application instance. Required on first call to read
             ``MONGODB_URI`` from ``app.config``. Optional on subsequent calls.

    Returns:
        The PyMongo :class:`~pymongo.mongo_client.MongoClient` singleton,
        or ``None`` if not yet initialized and no ``app`` was provided.

    Raises:
        KeyError: If ``app`` is provided but ``MONGODB_URI`` is missing from config.
        pymongo.errors.ConfigurationError: If the URI is malformed.
    """
    global _mongo_client

    if _mongo_client is not None:
        return _mongo_client

    if app is None:
        return None

    mongodb_uri = app.config["MONGODB_URI"]

    _logger.info("Initializing PyMongo client — connecting to MongoDB")
    _mongo_client = MongoClient(
        mongodb_uri,
        maxPoolSize=50,
        minPoolSize=10,
        maxIdleTimeMS=30000,
        serverSelectionTimeoutMS=5000,
    )
    _logger.info("PyMongo client initialized successfully")

    return _mongo_client


def get_db(app=None):
    """Get the MongoDB database instance.

    Returns the database object corresponding to the ``MONGODB_DATABASE``
    configuration key.  The database reference is cached after the first
    successful creation.

    Args:
        app: Flask application instance. Required on first call to read
             ``MONGODB_DATABASE`` from ``app.config``. Optional afterwards.

    Returns:
        A PyMongo :class:`~pymongo.database.Database` instance, or ``None``
        if the client has not been initialized yet and no ``app`` was provided.

    Raises:
        KeyError: If ``app`` is provided but ``MONGODB_DATABASE`` is missing
            from config.
    """
    global _db

    if _db is not None:
        return _db

    if app is None:
        return None

    client = get_mongo_client(app)
    if client is None:
        return None

    db_name = app.config["MONGODB_DATABASE"]
    _db = client[db_name]
    _logger.info("MongoDB database '%s' selected", db_name)

    return _db


def configure_logging(app) -> None:
    """Configure structured JSON logging per environment.

    Sets up the Python root logger with a JSON-formatted output suitable for
    ingestion by AWS CloudWatch Logs (per AAP §0.8.2).  The log level is
    driven by the ``LOG_LEVEL`` configuration key (defaults to ``INFO``).

    Supported log levels:
        ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``

    Args:
        app: Flask application instance whose ``config`` dict provides
             the ``LOG_LEVEL`` setting.
    """
    level_name = app.config.get("LOG_LEVEL", "INFO").upper()

    # Resolve the level string to a logging constant; fall back to INFO
    log_level = getattr(logging, level_name, logging.INFO)

    # Structured JSON format for CloudWatch compatibility
    json_format = (
        '{"timestamp":"%(asctime)s",'
        '"level":"%(levelname)s",'
        '"logger":"%(name)s",'
        '"module":"%(module)s",'
        '"message":"%(message)s"}'
    )

    logging.basicConfig(
        level=log_level,
        format=json_format,
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )

    # Ensure Flask's own logger respects the configured level
    app.logger.setLevel(log_level)

    # Use DEBUG constant to verify level mapping includes all expected values
    if log_level <= logging.DEBUG:
        app.logger.debug("Logging configured at DEBUG level")

    _logger.info(
        "Structured JSON logging configured — level=%s",
        level_name,
    )


def init_extensions(app) -> None:
    """Initialize all Flask extensions and shared singletons.

    Called by :func:`create_app` during Application Factory initialization.
    Performs the following setup in order:

    1. Configure structured JSON logging
    2. Initialize the PyMongo client singleton with connection pooling
    3. Select the target MongoDB database
    4. Store references on the ``app`` object for convenience access

    Args:
        app: Flask application instance with fully loaded configuration.
    """
    # 1. Logging first — so all subsequent init steps are logged
    configure_logging(app)

    _logger.info("Initializing Flask extensions")

    # 2. Initialize MongoDB connection pool
    client = get_mongo_client(app)
    database = get_db(app)

    # 3. Store references on app for easy access by other modules
    app.mongo_client = client  # type: ignore[attr-defined]
    app.db = database  # type: ignore[attr-defined]

    # 4. Register teardown handler for graceful shutdown
    app.teardown_appcontext(_teardown_appcontext)

    _logger.info("Flask extensions initialized successfully")


def teardown_extensions(app=None) -> None:
    """Clean up extensions and close connections.

    Closes the PyMongo client (which drains the connection pool) and resets
    the module-level singletons.  Safe to call multiple times — subsequent
    calls after the first are no-ops.

    This function is intended for:
        - Graceful application shutdown
        - Test teardown (resetting singletons between test cases)
        - Manual cleanup in scripts

    Args:
        app: Flask application instance (optional, unused but accepted for
             consistency with the init/teardown interface).
    """
    global _mongo_client, _db

    if _mongo_client is not None:
        _logger.info("Tearing down extensions — closing PyMongo client")
        try:
            _mongo_client.close()
        except Exception:
            _logger.exception("Error closing PyMongo client during teardown")
        finally:
            _mongo_client = None
            _db = None
        _logger.info("Extensions teardown complete")
    else:
        _logger.debug("teardown_extensions called but no active client to close")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _teardown_appcontext(exception=None) -> None:
    """Flask teardown_appcontext callback.

    Registered by :func:`init_extensions` to run when the application context
    is torn down.  For persistent singleton connections, this is a lightweight
    no-op — actual connection cleanup is handled by :func:`teardown_extensions`
    during graceful shutdown.  If an exception occurred during the request,
    it is logged for diagnostics.

    Args:
        exception: The unhandled exception (if any) that caused the context
                   to tear down.
    """
    if exception is not None:
        _logger.warning(
            "Application context teardown with exception: %s",
            exception,
        )
