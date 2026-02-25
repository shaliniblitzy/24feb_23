"""Structured JSON logging setup with request ID correlation and CloudWatch compatibility.

Provides the foundational logging infrastructure used across the entire Flask backend
application — services, middleware, routes, and repositories. All log output is
JSON-formatted for CloudWatch Logs Insights compatibility, with ISO 8601 UTC timestamps,
request ID correlation, and structured exception serialization.

Key components:
    - JSONFormatter: Custom logging.Formatter producing single-line JSON log entries
    - setup_logging: Configures root logger with JSON formatting and environment-aware levels
    - request_id_var: Thread-safe ContextVar for request ID correlation across log entries
    - generate_request_id / set_request_id / get_request_id: Request ID lifecycle management
    - get_logger: Convenience factory for named logger instances

Usage:
    from app.utils.logging import get_logger, setup_logging, set_request_id, get_request_id

    setup_logging(log_level="INFO")
    logger = get_logger(__name__)
    logger.info("Server started", extra={"port": 8000})
"""

import json
import logging
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Request ID correlation
# ---------------------------------------------------------------------------
# Thread-safe context variable storing the active request's correlation ID.
# Set by middleware at request entry; automatically included in every log line
# emitted during that request's lifecycle without explicit parameter passing.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# ---------------------------------------------------------------------------
# Standard LogRecord attributes to exclude from extra-field passthrough.
# Any attribute on the LogRecord *not* in this set (and not prefixed with '_')
# is forwarded into the JSON payload, enabling callers to attach arbitrary
# structured data via the ``extra`` keyword argument.
# ---------------------------------------------------------------------------
_STANDARD_RECORD_ATTRS: frozenset[str] = frozenset(
    {
        "name",
        "msg",
        "args",
        "created",
        "relativeCreated",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "pathname",
        "filename",
        "module",
        "levelno",
        "levelname",
        "message",
        "msecs",
        "thread",
        "threadName",
        "process",
        "processName",
        "taskName",
    }
)


class JSONFormatter(logging.Formatter):
    """Custom JSON log formatter for CloudWatch-compatible structured logging.

    Produces single-line JSON objects per log record with the following fields:

    - **timestamp** — ISO 8601 UTC timestamp (e.g. ``2026-02-25T12:34:56.789012+00:00``)
    - **level** — Log level name (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``)
    - **logger** — Logger name (typically the dotted module path)
    - **message** — Formatted log message text
    - **request_id** — Correlation ID for request tracing (included only when set)
    - **module** — Python module name where the log call originated
    - **function** — Function name where the log call originated
    - **line** — Source line number where the log call originated
    - **exception** — Structured exception data (included only when ``exc_info`` is present)
    - *extra fields* — Any additional key/value pairs passed via ``extra={}``

    The output is designed for ingestion by AWS CloudWatch Logs and is queryable
    via CloudWatch Logs Insights using field-level filters.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a single-line JSON string.

        Args:
            record: The ``logging.LogRecord`` instance to format.

        Returns:
            A JSON-serialised string (no trailing newline) representing the log
            entry.  Non-serialisable values are coerced to strings via the
            ``default=str`` fallback in :func:`json.dumps`.
        """
        # Build the core log data dictionary with deterministic key order.
        log_data: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach request ID correlation when available.  The ContextVar is set
        # by middleware at request entry; checking for a truthy value avoids
        # polluting logs emitted outside of a request context (e.g. startup).
        req_id = request_id_var.get("")
        if req_id:
            log_data["request_id"] = req_id

        # Serialise exception information into a structured sub-object so that
        # CloudWatch Logs Insights can query on exception type and message
        # independently, while the full traceback is still available.
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Forward any caller-supplied extra fields (passed via ``extra={}``).
        # Standard LogRecord attributes are excluded to avoid duplication.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_"):
                log_data[key] = value

        return json.dumps(log_data, default=str)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging for the application.

    Sets up the root logger with :class:`JSONFormatter` on a
    :class:`logging.StreamHandler` writing to *stdout*.  Existing handlers on the
    root logger are replaced to prevent duplicate output when ``setup_logging`` is
    called more than once (e.g. during testing).

    Third-party loggers known to be excessively verbose at ``DEBUG`` level
    (urllib3, pymongo, boto3, botocore) are capped at ``WARNING`` to avoid
    flooding CloudWatch with connection-level diagnostics.

    Args:
        log_level: String log level name — one of ``DEBUG``, ``INFO``,
            ``WARNING``, ``ERROR``, ``CRITICAL``.  Defaults to ``"INFO"``.
            Invalid values fall back to ``INFO``.

    Example::

        # During Flask create_app():
        setup_logging(app.config.get("LOG_LEVEL", "INFO"))
    """
    # Resolve the string level name to its numeric constant.  If the caller
    # passes an unrecognised name, fall back to INFO rather than raising.
    numeric_level: int = getattr(logging, log_level.upper(), logging.INFO)

    # Create and configure a StreamHandler with JSON formatting.
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    # Configure the root logger — all child loggers inherit this setup.
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Replace (not append) handlers to avoid duplicates across calls.
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers that emit high volumes of DEBUG/INFO
    # output during normal operation.  These are capped at WARNING so that
    # genuine warnings and errors still surface.
    for noisy_logger_name in ("urllib3", "pymongo", "boto3", "botocore"):
        logging.getLogger(noisy_logger_name).setLevel(logging.WARNING)


def generate_request_id() -> str:
    """Generate a unique request ID for request correlation.

    Returns a UUID version 4 string suitable for use as a correlation ID
    across log entries and inter-service calls.  The generated ID is compact
    and globally unique without requiring coordination.

    Returns:
        A UUID4 string (e.g. ``'550e8400-e29b-41d4-a716-446655440000'``).
    """
    return str(uuid.uuid4())


def set_request_id(request_id: str | None = None) -> str:
    """Set the request ID in the context variable for the current request.

    Should be called by middleware at the very start of request processing.
    When an ``X-Request-ID`` header is present on the incoming request, the
    header value should be passed here to preserve upstream correlation.  If
    no value is provided, a new UUID4 is generated automatically.

    Args:
        request_id: Optional request ID string.  If ``None``, a new ID is
            generated via :func:`generate_request_id`.

    Returns:
        The request ID that was set (either the provided value or the
        newly generated one).
    """
    if request_id is None:
        request_id = generate_request_id()
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> str:
    """Get the current request ID from the context variable.

    Returns the correlation ID for the active request, or an empty string
    if no request context is active (e.g. during application startup or in
    background tasks).

    Returns:
        Current request ID, or ``""`` if not set.
    """
    return request_id_var.get("")


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance.

    Convenience wrapper around :func:`logging.getLogger` that follows the
    application's structured logging configuration set up by
    :func:`setup_logging`.  Callers typically pass ``__name__`` to get a
    logger named after the calling module.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance configured via the root logger's
        handlers and level.

    Example::

        from app.utils.logging import get_logger

        logger = get_logger(__name__)
        logger.info("Document created", extra={"doc_id": doc_id})
    """
    return logging.getLogger(name)
