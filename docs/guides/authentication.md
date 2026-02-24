# Authentication Guide

*Last updated: 2026-02-24*

This guide provides a comprehensive reference for implementing and using authentication and authorization in the Flask server application. It covers JSON Web Token (JWT) management, middleware setup for token validation, protected route patterns using Flask decorators, token refresh handling, password hashing, and error scenarios. The intended audience is developers implementing authentication features or integrating with the Flask server's protected API endpoints. For standard terminology used throughout this document, see the [glossary in the Architecture Overview](../architecture/overview.md).

## Authentication Overview

The Flask server uses JWT (JSON Web Token) based stateless authentication. In this approach, the server does not store session state between requests. Instead, the server issues a cryptographically signed token upon successful login, and the client presents that token with every subsequent request. The server validates the token's signature and expiration on each request without needing to consult a session store or database.

The authentication flow integrates into the Flask request lifecycle as follows:

1. **Login** — The client sends credentials (email and password) to the login endpoint. The server validates the credentials against the database and, on success, returns a JWT access token and a refresh token.
2. **Authenticated requests** — The client includes the JWT access token in subsequent requests via the `Authorization: Bearer <token>` header.
3. **Token validation** — The server's `before_request` middleware extracts the token from the header, verifies its signature and expiration, and stores the decoded user identity in the Flask request context (`flask.g`).
4. **Route protection** — Individual route handlers use decorators (`@login_required`, `@admin_required`) to enforce authentication and role-based authorization.
5. **Token refresh** — When the access token expires, the client uses the refresh token to obtain a new access token without re-entering credentials.
6. **Logout** — The client sends the refresh token to the logout endpoint to revoke it. The server deletes the refresh token from the database, preventing further token refresh operations.

See [Request Lifecycle](../architecture/request-lifecycle.md) for the complete request processing flow.

## JWT Token Structure

A JSON Web Token consists of three Base64URL-encoded parts separated by dots:

1. **Header** — Contains the token type (`JWT`) and the signing algorithm (for example, `HS256`).
2. **Payload** — Contains claims (key-value pairs) that carry information about the authenticated user and the token's validity period.
3. **Signature** — A cryptographic hash of the header and payload, signed with the server's secret key. The signature ensures that the token has not been tampered with.

The following claims are used in this application's JWT payload:

| Claim | Description | Example Value |
|---|---|---|
| `sub` | Subject — the unique user identifier | `42` |
| `iat` | Issued At — the Unix timestamp when the token was created | `1740000000` |
| `exp` | Expiration — the Unix timestamp after which the token is invalid | `1740003600` |
| `role` | User role for authorization decisions | `"admin"` |

Example decoded JWT payload:

```json
{
  "sub": 42,
  "iat": 1740000000,
  "exp": 1740003600,
  "role": "admin"
}
```

Access tokens expire after a configurable duration. The default expiration is 3600 seconds (1 hour). Once expired, the token is rejected by the validation middleware, and the client must obtain a new access token using the refresh flow described later in this guide.

## Authentication Configuration

The following environment variables control the authentication behavior of the Flask server. All variables are loaded through `python-dotenv` and accessed via the Flask application configuration object.

| Variable | Description | Default | Required |
|---|---|---|---|
| `SECRET_KEY` | Secret key for JWT signing (HMAC-SHA256). Must be a strong, random string of at least 32 characters. | None | Yes |
| `JWT_ACCESS_TOKEN_EXPIRES` | Access token expiry duration in seconds | `3600` (1 hour) | No |
| `JWT_REFRESH_TOKEN_EXPIRES` | Refresh token expiry duration in seconds | `2592000` (30 days) | No |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` | No |

Configuration setup in the application configuration module:

```python
# config.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 2592000))
    JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
```

Example `.env` file with authentication settings:

```bash
SECRET_KEY=your-secret-key-minimum-32-characters-long
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
JWT_ALGORITHM=HS256
```

> **Warning:** Never commit `SECRET_KEY` values to version control. Use environment variables or a secrets manager in all environments.

See [Configuration Guide](../getting-started/configuration.md) for all environment variable options.

## Token Generation

The authentication service module provides functions for generating access tokens and refresh tokens using the PyJWT library. Both functions read signing parameters from the Flask application configuration.

Access token generation:

```python
# services/auth_service.py
import jwt
from datetime import datetime, timedelta, timezone
from flask import current_app


def generate_access_token(user_id, role="user"):
    """Generate a JWT access token for the given user.

    Args:
        user_id: The unique identifier of the authenticated user.
        role: The user's role for authorization (default: "user").

    Returns:
        A signed JWT string containing the user's identity and role.
    """
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(
            seconds=current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
        ),
        "role": role,
    }
    return jwt.encode(
        payload,
        current_app.config["SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )
```

Refresh token generation:

```python
def generate_refresh_token(user_id):
    """Generate a JWT refresh token for the given user.

    Args:
        user_id: The unique identifier of the authenticated user.

    Returns:
        A signed JWT string with a longer expiration for token refresh.
    """
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(
            seconds=current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
        ),
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        current_app.config["SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )
```

The `type` claim in the refresh token payload distinguishes it from access tokens. The token refresh endpoint verifies this claim to prevent access tokens from being used as refresh tokens.

## Token Validation Middleware

Token validation is implemented as a `before_request` hook that executes on every incoming request. The middleware extracts the JWT from the `Authorization` header, decodes and verifies it, and stores the authenticated user identity in `flask.g.current_user` for use by route handlers and services.

Token decoding utility:

```python
# middleware/auth.py
import jwt
from flask import request, g, jsonify, current_app


def decode_token(token):
    """Decode and verify a JWT token.

    Args:
        token: The JWT string to decode.

    Returns:
        The decoded payload dictionary if the token is valid, or None
        if the token is expired, malformed, or has an invalid signature.
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=[current_app.config["JWT_ALGORITHM"]],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
```

Authentication middleware hook:

```python
def register_auth_middleware(app):
    """Register the authentication before_request hook on the Flask app.

    Args:
        app: The Flask application instance.
    """

    @app.before_request
    def authenticate_request():
        # Skip authentication for public endpoints
        public_endpoints = ["auth.login", "auth.register", "health_check"]
        if request.endpoint in public_endpoints:
            return None

        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"error": "Missing authentication token"}), 401

        payload = decode_token(token)
        if payload is None:
            return jsonify({"error": "Invalid or expired token"}), 401

        g.current_user = {
            "id": payload["sub"],
            "role": payload.get("role", "user"),
        }
```

Key behaviors of the authentication middleware:

- **Public endpoint bypass** — Endpoints listed in `public_endpoints` (such as login, registration, and health check) skip token validation entirely, allowing unauthenticated access.
- **Token extraction** — The middleware reads the `Authorization` header, strips the `Bearer ` prefix, and passes the raw token string to `decode_token()`.
- **Early return on failure** — If the token is missing or invalid, the middleware returns a `401 Unauthorized` JSON response immediately. Flask stops processing the request — no subsequent `before_request` hooks or route handlers execute.
- **Identity injection** — On successful validation, the decoded user identity (ID and role) is stored in `flask.g.current_user`. This value is available to all route handlers and services for the duration of the request. See [Request Lifecycle](../architecture/request-lifecycle.md) for details on `before_request` hook execution order and error short-circuiting.

## Protecting Routes with Decorators

In addition to the global `before_request` middleware, individual routes can enforce authentication and authorization requirements using Python decorators. Two decorators are provided: `@login_required` for endpoints that require any authenticated user, and `@admin_required` for endpoints restricted to users with the `admin` role.

Decorator definitions:

```python
# middleware/auth.py
from functools import wraps
from flask import g, jsonify


def login_required(f):
    """Decorator that restricts access to authenticated users.

    Returns a 401 response if no authenticated user is present
    in the request context.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, "current_user") or g.current_user is None:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator that restricts access to users with the admin role.

    Returns a 401 response if the user is not authenticated, or a
    403 response if the user does not have the admin role.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, "current_user") or g.current_user is None:
            return jsonify({"error": "Authentication required"}), 401
        if g.current_user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function
```

Usage examples on blueprint routes:

```python
# routes/users.py
from flask import Blueprint, jsonify, g
from middleware.auth import login_required, admin_required
from services import user_service

users_bp = Blueprint("users", __name__)


@users_bp.route("/profile", methods=["GET"])
@login_required
def get_profile():
    """Return the authenticated user's profile."""
    user = user_service.get_user_by_id(g.current_user["id"])
    return jsonify({"status": "success", "data": user}), 200


@users_bp.route("/", methods=["DELETE"])
@admin_required
def delete_all_users():
    """Delete all users. Restricted to admin role."""
    user_service.delete_all()
    return "", 204
```

The decorators work in conjunction with the `before_request` middleware. The middleware populates `g.current_user` for valid tokens, and the decorators verify that the populated identity meets the route's requirements. If the middleware already rejected the request (missing or invalid token), the route handler and its decorators never execute.

## Authentication Flows

### Login Flow

The login endpoint accepts user credentials, validates them against the database, and returns a JWT access token and refresh token on success.

Login endpoint implementation:

```python
# routes/auth.py
from flask import Blueprint, request, jsonify
from services import auth_service

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return JWT tokens.

    Request body:
        email (str): The user's email address.
        password (str): The user's password.

    Returns:
        200: JSON object with access_token, refresh_token, token_type,
             and expires_in.
        400: If email or password is missing.
        401: If credentials are invalid.
    """
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = auth_service.authenticate(email, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = auth_service.generate_access_token(user["id"], user["role"])
    refresh_token = auth_service.generate_refresh_token(user["id"])

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }), 200
```

Example login request using curl:

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword"}'
```

Example successful response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Token Refresh Flow

When the access token expires, the client uses the refresh token to obtain a new access token without requiring the user to re-enter their credentials. The refresh flow works as follows:

1. The client detects that the access token has expired (either by checking the `exp` claim or by receiving a `401` response from the server).
2. The client sends the refresh token to the refresh endpoint.
3. The server validates the refresh token and issues a new access token.
4. The client replaces the expired access token with the new one and retries the original request.

Refresh endpoint implementation:

```python
@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """Issue a new access token using a valid refresh token.

    Request body:
        refresh_token (str): A valid, non-expired refresh token.

    Returns:
        200: JSON object with a new access_token, token_type, and expires_in.
        400: If the refresh_token field is missing.
        401: If the refresh token is invalid, expired, or not a refresh type.
    """
    data = request.get_json()
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400

    payload = auth_service.decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        return jsonify({"error": "Invalid refresh token"}), 401

    new_access_token = auth_service.generate_access_token(
        payload["sub"], payload.get("role", "user")
    )
    return jsonify({
        "access_token": new_access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }), 200
```

Example refresh request using curl:

```bash
curl -X POST http://localhost:5000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

Example successful response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Logout Flow

The logout endpoint invalidates a refresh token, preventing it from being used to generate new access tokens. This is the server-side mechanism for ending a user session. After a successful logout, the client should discard both the access token and the refresh token.

The logout flow works as follows:

1. The client sends the refresh token to the logout endpoint along with a valid access token in the `Authorization` header.
2. The server validates the access token and verifies the refresh token exists in the database.
3. The server deletes the refresh token record from the database, revoking it permanently.
4. The client discards both tokens from local storage.

> **Note:** The access token remains technically valid until it expires (since JWTs are stateless), but the refresh token is immediately and permanently revoked. Clients should discard the access token upon logout to prevent further use.

Logout endpoint implementation:

```python
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Invalidate a refresh token to log the user out.

    Requires a valid access token in the Authorization header.

    Request body:
        refresh_token (str): The refresh token to revoke.

    Returns:
        200: JSON object with a success message.
        400: If the refresh_token field is missing.
        401: If the access token is missing or invalid,
             or if the refresh token does not exist.
    """
    data = request.get_json()
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400

    try:
        auth_service.logout(refresh_token)
    except ValueError:
        return jsonify({"error": "Invalid refresh token"}), 401

    return jsonify({"message": "Successfully logged out"}), 200
```

Example logout request using curl:

```bash
curl -X POST http://localhost:5000/api/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIs..."}'
```

Example successful response:

```json
{
  "message": "Successfully logged out"
}
```

## Error Scenarios

The following table documents all authentication-related error responses returned by the Flask server. Client applications should handle each scenario appropriately.

| Scenario | HTTP Status | Response Body |
|---|---|---|
| Missing `Authorization` header on a protected endpoint | 401 | `{"error": "Missing authentication token"}` |
| Invalid token format or signature | 401 | `{"error": "Invalid or expired token"}` |
| Expired access token | 401 | `{"error": "Invalid or expired token"}` |
| Expired refresh token | 401 | `{"error": "Invalid refresh token"}` |
| Refresh endpoint called with an access token (not a refresh token) | 401 | `{"error": "Invalid refresh token"}` |
| Valid token but insufficient role for the requested resource | 403 | `{"error": "Admin access required"}` |
| Invalid login credentials (wrong email or password) | 401 | `{"error": "Invalid credentials"}` |
| Missing required login fields (email or password not provided) | 400 | `{"error": "Email and password are required"}` |

Example client-side error handling in Python using the `requests` library:

```python
import requests

response = requests.get(
    "http://localhost:5000/api/users/profile",
    headers={"Authorization": f"Bearer {access_token}"},
)

if response.status_code == 401:
    error = response.json()
    if error.get("error") == "Invalid or expired token":
        # Attempt to refresh the access token
        refresh_response = requests.post(
            "http://localhost:5000/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        if refresh_response.status_code == 200:
            new_token = refresh_response.json()["access_token"]
            # Retry the original request with the new token
        else:
            print(f"Token refresh failed: {refresh_response.status_code}")
            print("Redirecting user to login page")
elif response.status_code == 403:
    print(f"Access denied: user does not have the required role")
    print(f"Response: {response.json()}")
```

## Password Hashing

Passwords are never stored in plain text. The Flask server uses Werkzeug's built-in security utilities for password hashing and verification. Werkzeug is a core dependency of Flask and does not require separate installation.

Hashing a password during user registration:

```python
from werkzeug.security import generate_password_hash, check_password_hash


# During user registration — hash the password before storing
hashed = generate_password_hash("securepassword")
# Store `hashed` in the user's `password_hash` database column
```

Verifying a password during login authentication:

```python
# services/auth_service.py
from werkzeug.security import check_password_hash
from models.user import User


def authenticate(email, password):
    """Verify user credentials and return the user dictionary on success.

    Args:
        email: The user's email address.
        password: The plain-text password to verify.

    Returns:
        A dictionary representation of the user if credentials are valid,
        or None if the email is not found or the password does not match.
    """
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        return user.to_dict()
    return None
```

Key security practices:

- **Never store plain-text passwords.** Always hash passwords with `generate_password_hash()` before persisting them to the database.
- **Use Werkzeug defaults.** The `generate_password_hash()` function uses the `scrypt` algorithm by default (as of Werkzeug 2.3+), which is a memory-hard hashing function resistant to brute-force and hardware-accelerated attacks.
- **Constant-time comparison.** The `check_password_hash()` function performs constant-time comparison to prevent timing attacks.
- **Salt is included automatically.** Werkzeug generates a unique salt for each password hash, ensuring that identical passwords produce different hash values.

## Troubleshooting

The following table lists common authentication issues, their likely causes, and recommended solutions.

| Issue | Cause | Solution |
|---|---|---|
| `401 Unauthorized` on all requests | Missing or malformed `Authorization` header | Ensure the header format is exactly `Authorization: Bearer <token>` with a single space after `Bearer` and no extra whitespace |
| Token valid but `403 Forbidden` returned | User role does not match the required role for the endpoint | Check the `role` claim in the JWT payload. Use `@admin_required` only on endpoints that require admin access |
| Token expired immediately after login | Server clock skew or misconfigured `JWT_ACCESS_TOKEN_EXPIRES` value | Verify the server's system clock is synchronized (use NTP). Confirm `JWT_ACCESS_TOKEN_EXPIRES` is set to a reasonable value in seconds (default: `3600`) |
| `SECRET_KEY` error on startup | `SECRET_KEY` environment variable not set | Set `SECRET_KEY` in the `.env` file. The value must be a strong, random string of at least 32 characters. Generate one with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| Token works in development but not production | Different `SECRET_KEY` values in each environment | Ensure the same `SECRET_KEY` is used across all environments where tokens need to be valid. Tokens signed with one key cannot be verified with another |
| `jwt.DecodeError` in server logs | Token string is corrupted or truncated | Verify the full token string is transmitted. Check for URL encoding issues or header size limits in reverse proxies |
| Refresh token rejected with `Invalid refresh token` | Access token sent to the refresh endpoint instead of a refresh token | Ensure the client stores access and refresh tokens separately and sends the correct token to each endpoint |

## See Also

- [Request Lifecycle](../architecture/request-lifecycle.md) — How authentication integrates into the `before_request` middleware chain and the complete request processing flow
- [Configuration Guide](../getting-started/configuration.md) — Environment variable catalog including all authentication-related settings
- [API Reference](../api-reference/endpoints.md) — Authentication endpoint documentation with request and response schemas
- [Architecture Overview](../architecture/overview.md) — Middleware layer overview and glossary of standard project terminology
