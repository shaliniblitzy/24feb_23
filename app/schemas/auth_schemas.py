"""Authentication request/response validation schemas.

Pydantic v2 models for Auth0 JWT validation and user profile endpoints.
All request models enforce strict mode to reject unexpected fields per AAP §0.7.3.

Covers the following API endpoints:
    - POST /api/auth/validate — Token validation (TokenValidationRequest / TokenValidationResponse)
    - GET /api/auth/profile — User profile retrieval (UserProfileResponse)

The JWTClaimsModel represents decoded Auth0 JWT claims after the 6-step
validation pipeline: presence → signature → issuer → audience → expiration → RBAC.

Used by:
    app/routes/auth.py — Auth Blueprint route handlers
    app/services/auth_service.py — Auth business logic
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TokenValidationRequest(BaseModel):
    """Request model for POST /api/auth/validate.

    Validates an Auth0 JWT token sent by client applications.
    The token field accepts the raw Bearer token string extracted
    from the Authorization header by the client.

    Strict mode is enabled per AAP §0.7.3 to reject any unexpected
    fields in the request payload, ensuring only the token is accepted.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    token: str = Field(
        ...,
        min_length=10,
        description="Auth0 JWT Bearer token to validate",
    )


class JWTClaimsModel(BaseModel):
    """Model representing decoded JWT token claims from Auth0.

    Contains standard OIDC claims and Auth0-specific fields after
    the 6-step JWT validation pipeline (presence → signature → issuer
    → audience → expiration → RBAC).

    Per AAP §0.5.3, the Auth0 JWT Verification Flow validates these
    fields sequentially. This model captures the decoded payload for
    downstream processing by the auth service and middleware.

    Standard OIDC Claims:
        sub: Subject identifier (Auth0 user ID)
        iss: Token issuer (Auth0 domain URL)
        aud: Intended audience (API identifier)
        exp: Expiration timestamp (Unix epoch)
        iat: Issued-at timestamp (Unix epoch)

    Auth0-Specific Claims:
        azp: Authorized party (client ID)
        scope: Granted OAuth2 scopes
        permissions: RBAC permission strings
    """

    model_config = ConfigDict(strict=False)  # Response model, flexible for Auth0 payload

    sub: str = Field(
        ...,
        description="Subject — Auth0 user ID (e.g., 'auth0|abc123')",
    )
    iss: str = Field(
        ...,
        description="Issuer — Auth0 domain URL",
    )
    aud: str | list[str] = Field(
        ...,
        description="Audience — API identifier or list of audiences",
    )
    exp: int = Field(
        ...,
        description="Expiration — Unix timestamp when token expires",
    )
    iat: int = Field(
        ...,
        description="Issued At — Unix timestamp when token was issued",
    )
    azp: str | None = Field(
        None,
        description="Authorized Party — Client ID that requested the token",
    )
    scope: str | None = Field(
        None,
        description="Scope — Space-separated list of granted scopes",
    )
    permissions: list[str] | None = Field(
        default=None,
        description="RBAC permissions — List of permissions granted to the user",
    )


class UserProfileResponse(BaseModel):
    """Response model for GET /api/auth/profile.

    Returns the decoded JWT claims for the authenticated user,
    enriched with additional profile metadata extracted from
    the token and optionally from Auth0's user info endpoint.

    Per AAP §0.6.1 (auth_service.py): "JWT claims extraction, user profile
    enrichment, RBAC permission checking logic"

    Fields are mapped from decoded JWT claims:
        user_id ← sub claim
        issuer ← iss claim
        permissions ← permissions claim (RBAC)
        issued_at ← iat claim (converted to datetime)
        expires_at ← exp claim (converted to datetime)
        email, name, picture ← profile claims (if present)
    """

    model_config = ConfigDict(strict=False)  # Response model

    user_id: str = Field(
        ...,
        description="Auth0 user identifier (sub claim)",
    )
    email: str | None = Field(
        None,
        description="User email address if available",
    )
    name: str | None = Field(
        None,
        description="User display name if available",
    )
    picture: str | None = Field(
        None,
        description="User avatar URL if available",
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="RBAC permissions granted to this user",
    )
    issuer: str = Field(
        ...,
        description="Token issuer (Auth0 domain)",
    )
    issued_at: datetime | None = Field(
        None,
        description="When the token was issued",
    )
    expires_at: datetime | None = Field(
        None,
        description="When the token expires",
    )
    raw_claims: dict[str, Any] | None = Field(
        default=None,
        description="Full decoded JWT claims dictionary for debugging",
    )


class TokenValidationResponse(BaseModel):
    """Response model for POST /api/auth/validate.

    Returns the validation result for a submitted JWT token. If the
    token is valid, includes decoded user_id, RBAC permissions, and
    expiration timestamp. If invalid, includes an error message
    explaining the validation failure reason.

    Complements TokenValidationRequest for the POST /api/auth/validate
    endpoint, enabling client applications to verify token validity
    before making authenticated API calls.
    """

    model_config = ConfigDict(strict=False)  # Response model

    valid: bool = Field(
        ...,
        description="Whether the token is valid",
    )
    user_id: str | None = Field(
        None,
        description="Auth0 user ID if token is valid",
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="RBAC permissions if token is valid",
    )
    expires_at: datetime | None = Field(
        None,
        description="Token expiration if valid",
    )
    message: str | None = Field(
        None,
        description="Validation message (e.g., error reason)",
    )
