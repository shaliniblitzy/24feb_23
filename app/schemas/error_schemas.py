"""Unified error response validation schemas.

Pydantic v2 models for structured JSON error responses used across all API
endpoints. Implements the consistent error format defined in the specification:

    {"error": {"code": 401, "type": "AUTHENTICATION_ERROR", "message": "Token expired"}}

Covers all five error categories:
    - Authentication (401, 403)
    - Validation (400)
    - Database (500)
    - LLM/AI (503)
    - Infrastructure (500, 503)

And all registered HTTP error codes: 400, 401, 403, 404, 405, 500, 503.

Used by:
    app/errors/handlers.py — Centralized Flask error handler registration
    All route handlers — For consistent error response formatting
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorType(StrEnum):
    """Error type enumeration covering the five error categories.

    Maps the five specification-defined error categories to specific error type
    constants, plus additional types for common HTTP error codes. Inherits from
    both ``str`` and ``Enum`` so that enum values serialise directly to their
    string representation in JSON responses.

    Category → ErrorType mapping:
        - Authentication → AUTHENTICATION_ERROR (HTTP 401)
        - Authorization  → AUTHORIZATION_ERROR  (HTTP 403)
        - Validation     → VALIDATION_ERROR     (HTTP 400)
        - Database       → DATABASE_ERROR       (HTTP 500)
        - LLM/AI        → AI_SERVICE_ERROR      (HTTP 503)
        - Infrastructure → INFRASTRUCTURE_ERROR  (HTTP 500, 503)

    Additional HTTP error types:
        - NOT_FOUND_ERROR          (HTTP 404)
        - METHOD_NOT_ALLOWED_ERROR (HTTP 405)
        - INTERNAL_SERVER_ERROR    (HTTP 500)
        - SERVICE_UNAVAILABLE_ERROR (HTTP 503)
    """

    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    """Token missing, expired, or signature invalid (HTTP 401)."""

    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    """Valid token but insufficient RBAC permissions (HTTP 403)."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    """Request payload fails Pydantic schema validation (HTTP 400)."""

    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    """Requested resource does not exist (HTTP 404)."""

    METHOD_NOT_ALLOWED_ERROR = "METHOD_NOT_ALLOWED_ERROR"
    """HTTP method not supported on the target endpoint (HTTP 405)."""

    DATABASE_ERROR = "DATABASE_ERROR"
    """MongoDB operation failure — connection, query, or write concern error (HTTP 500)."""

    AI_SERVICE_ERROR = "AI_SERVICE_ERROR"
    """All LLM providers exhausted after fallback chain (HTTP 503)."""

    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"
    """Non-database infrastructure failure — S3, Secrets Manager, etc. (HTTP 500/503)."""

    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    """Unhandled server-side exception (HTTP 500)."""

    SERVICE_UNAVAILABLE_ERROR = "SERVICE_UNAVAILABLE_ERROR"
    """Dependent service temporarily unavailable (HTTP 503)."""


class ErrorDetail(BaseModel):
    """Inner error detail model.

    Represents the structured error information nested inside the top-level
    :class:`ErrorResponse`.  This is the ``error`` object in the canonical
    JSON structure::

        {"error": {"code": 401, "type": "AUTHENTICATION_ERROR", "message": "..."}}

    All error responses follow this consistent JSON structure across the entire
    API surface.  The three required fields (``code``, ``type``, ``message``)
    provide the minimum information needed by any client to interpret the error.

    Optional fields extend the detail for advanced use-cases:

    * ``details`` — additional context such as field-level validation errors,
      the LLM provider name for AI errors, or a ``retry-after`` value for 503s.
    * ``timestamp`` — when the error occurred (UTC).
    * ``request_id`` — correlation identifier for log tracing.

    Note:
        ``strict=False`` is set intentionally because this is a **response**
        model constructed internally by error handlers, not a request model
        that needs to reject unexpected input fields.
    """

    model_config = ConfigDict(strict=False)

    code: int = Field(
        ...,
        description="HTTP status code (e.g., 400, 401, 403, 404, 405, 500, 503)",
    )
    type: str = Field(
        ...,
        description=("Error type category from ErrorType enum " "(e.g., 'AUTHENTICATION_ERROR')"),
    )
    message: str = Field(
        ...,
        description="Human-readable error message describing what went wrong",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Additional error details (e.g., field validation errors, "
            "provider name for AI errors, retry-after for 503)"
        ),
    )
    timestamp: datetime | None = Field(
        default=None,
        description="When the error occurred (UTC)",
    )
    request_id: str | None = Field(
        default=None,
        description="Correlation ID for request tracing and log correlation",
    )


class ErrorResponse(BaseModel):
    """Top-level error response model.

    The outermost wrapper for **all** API error responses.  Every error path
    in the application — whether triggered by Flask error handlers, validation
    failures, or service-layer exceptions — must produce a response matching
    this schema::

        {"error": {"code": 401, "type": "AUTHENTICATION_ERROR", "message": "Token expired"}}

    The single ``error`` field contains an :class:`ErrorDetail` instance with
    the structured error information.  This nesting allows the top-level
    response envelope to be extended in the future (e.g., adding a
    ``meta`` field) without altering the error detail contract.

    Registered Flask error handlers for the following HTTP codes all return
    this model:  400, 401, 403, 404, 405, 500, 503.

    Five error categories are covered:
        - Authentication  (401, 403)
        - Validation      (400)
        - Database        (500)
        - LLM/AI         (503)
        - Infrastructure  (500, 503)

    Usage by ``app/errors/handlers.py``::

        response = ErrorResponse(
            error=ErrorDetail(
                code=401,
                type=ErrorType.AUTHENTICATION_ERROR.value,
                message="Token expired",
            )
        )
        return response.model_dump(), 401

    Note:
        ``strict=False`` is set intentionally because this is a **response**
        model constructed internally by error handlers, not a request model.
    """

    model_config = ConfigDict(strict=False)

    error: ErrorDetail = Field(
        ...,
        description="Structured error detail object",
    )
