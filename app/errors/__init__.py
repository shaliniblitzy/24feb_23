"""Error handling package with custom application exception classes.

Defines a hierarchy of application-specific exceptions that map to the five
error categories defined in the specification:

    1. Authentication (401) — JWT validation failures
    2. Authorization (403) — RBAC permission failures
    3. Validation (400) — Input validation errors
    4. Database (500) — MongoDB operation failures
    5. LLM/AI (503) — AI provider exhaustion
    6. Infrastructure (500/503) — S3, network, system errors

All exceptions carry status_code, error_type, and message attributes
for structured JSON error response construction by handlers.py:

    {"error": {"code": 401, "type": "AUTHENTICATION_ERROR", "message": "..."}}

Usage:
    from app.errors import AuthenticationError, ValidationError
    raise AuthenticationError("Token expired")
    raise ValidationError("Invalid document ID format")
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error class.

    All custom application exceptions inherit from this class.
    Carries structured error information for the centralized error handler.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code for the error response.
        error_type: Error category type string (e.g., "AUTHENTICATION_ERROR").
        details: Optional dictionary with additional error context.
    """

    def __init__(
        self,
        message: str = "An application error occurred",
        status_code: int = 500,
        error_type: str = "INTERNAL_SERVER_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.details = details


class AuthenticationError(AppError):
    """Authentication failure — HTTP 401.

    Raised when JWT token validation fails at any step of the 6-step
    pipeline: presence, signature, issuer, audience, expiration, or
    initial RBAC check.

    Per specification §0.5.3: Maps to AUTHENTICATION_ERROR category.

    Examples:
        raise AuthenticationError("Token expired")
        raise AuthenticationError("Invalid token signature")
        raise AuthenticationError("Missing Authorization header")
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_type="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(AppError):
    """Authorization failure — HTTP 403.

    Raised when an authenticated user lacks the required RBAC permission
    to access a resource or perform an action.

    Per specification §0.5.3: Maps to AUTHORIZATION_ERROR category.
    Part of the Authentication error category but uses 403 status.

    Examples:
        raise AuthorizationError("Insufficient permissions")
        raise AuthorizationError("Admin role required", details={"required": "admin:write"})
    """

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=403,
            error_type="AUTHORIZATION_ERROR",
            details=details,
        )


class ValidationError(AppError):
    """Input validation failure — HTTP 400.

    Raised for business-logic validation errors that are NOT caught
    by Pydantic's built-in validation (which has its own handler).
    Use for custom validation like invalid ObjectId formats, business
    rule violations, or semantic validation errors.

    Per specification §0.5.3: Maps to VALIDATION_ERROR category.

    Note: Pydantic's ValidationError is handled separately by the
    Pydantic-specific error handler in handlers.py.

    Examples:
        raise ValidationError("Invalid document ID format")
        raise ValidationError("Document title already exists")
    """

    def __init__(
        self,
        message: str = "Validation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_type="VALIDATION_ERROR",
            details=details,
        )


class NotFoundError(AppError):
    """Resource not found — HTTP 404.

    Raised when a requested resource does not exist in the database
    or cannot be located.

    Examples:
        raise NotFoundError("Document not found")
        raise NotFoundError("AI result not found", details={"id": "abc123"})
    """

    def __init__(
        self,
        message: str = "Resource not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=404,
            error_type="NOT_FOUND_ERROR",
            details=details,
        )


class DatabaseError(AppError):
    """Database operation failure — HTTP 500.

    Raised when MongoDB operations fail due to connection issues,
    query errors, timeout, or replica set problems.

    Per specification §0.5.3: Maps to DATABASE_ERROR category.

    Examples:
        raise DatabaseError("MongoDB connection failed")
        raise DatabaseError("Query timeout exceeded", details={"collection": "documents"})
    """

    def __init__(
        self,
        message: str = "Database operation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_type="DATABASE_ERROR",
            details=details,
        )


class AIServiceError(AppError):
    """AI/LLM service failure — HTTP 503.

    Raised when all LLM providers in the fallback chain are exhausted
    (Primary → Secondary → Tertiary → 503).

    Per specification §0.5.3: Maps to AI_SERVICE_ERROR category.
    Per specification §0.5.3 LLM Fallback: When all three providers fail,
    this exception triggers a 503 Service Unavailable response.

    Examples:
        raise AIServiceError("All LLM providers exhausted")
        raise AIServiceError(
            "AI query failed",
            details={"providers_attempted": ["openai", "anthropic", "google"]}
        )
    """

    def __init__(
        self,
        message: str = "AI service unavailable",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_type="AI_SERVICE_ERROR",
            details=details,
        )


class InfrastructureError(AppError):
    """Infrastructure failure — HTTP 500 or 503.

    Raised for AWS S3 failures, network issues, and other
    infrastructure-level errors.

    Per specification §0.5.3: Maps to INFRASTRUCTURE_ERROR category.
    Status code varies: 500 for permanent failures, 503 for transient.

    Examples:
        raise InfrastructureError("S3 upload failed")
        raise InfrastructureError(
            "S3 service unavailable",
            status_code=503,
            details={"service": "s3", "operation": "upload"},
        )
    """

    def __init__(
        self,
        message: str = "Infrastructure error",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_type="INFRASTRUCTURE_ERROR",
            details=details,
        )


class ServiceUnavailableError(AppError):
    """Generic service unavailable — HTTP 503.

    Raised when a dependent service is temporarily unavailable
    and the request cannot be fulfilled.

    Examples:
        raise ServiceUnavailableError("Service temporarily unavailable")
    """

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_type="SERVICE_UNAVAILABLE_ERROR",
            details=details,
        )


__all__ = [
    "AppError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "NotFoundError",
    "DatabaseError",
    "AIServiceError",
    "InfrastructureError",
    "ServiceUnavailableError",
]
