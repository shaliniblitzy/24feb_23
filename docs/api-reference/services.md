# Service Layer Reference

*Last updated: 2026-02-24*

This document provides a comprehensive API reference for the Flask server application's service layer, documenting all business logic service modules with function signatures, parameters, return types, exceptions raised, and usage examples. It is intended for developers implementing route handlers, writing tests, or extending business logic in the Flask application. For standard terminology used throughout this document — including "endpoint," "blueprint," "model," and "service" — see the [Architecture Overview glossary](../architecture/overview.md#glossary).

## Service Layer Overview

The service layer encapsulates all business logic and data access operations for the Flask server application. Services are Python modules located in the `services/` directory, with one file per domain (for example, `user_service.py`, `auth_service.py`, `resource_service.py`). Route handlers in the presentation layer delegate to service functions — they never contain business logic directly.

Services interact with SQLAlchemy model classes for database operations, using the shared `db` session instance from `extensions.py` to manage transactions. On success, services commit the transaction and return serialized results. On failure, services roll back the transaction and raise standard Python exceptions. Route handlers catch these exceptions and translate them into appropriate HTTP responses with JSON error bodies.

See [Architecture Overview](../architecture/overview.md) for the complete system design and where the service layer fits within the layered architecture.

### Conventions

The following conventions apply to all service functions across every service module:

- **Input types** — Service functions accept primitive Python types (`str`, `int`, `dict`) as arguments. They never accept Flask request objects, response objects, or any HTTP-specific data structures.
- **Output types** — Service functions return plain Python dictionaries serialized from ORM model instances via the model's `to_dict()` method. They never return Flask response objects, JSON strings, or raw model instances.
- **Error signaling** — Service functions raise standard Python exceptions for error conditions. `ValueError` signals business rule violations (duplicate data, invalid input, constraint failures). `KeyError` signals resource-not-found conditions. Route handlers translate these into HTTP 400 and 404 responses, respectively.
- **Database session management** — Each service function manages its own database transaction. The function calls `db.session.commit()` on success and `db.session.rollback()` on failure before re-raising the exception.

## User Service

The User Service provides business logic for user management, including CRUD operations, user listing with pagination, and role management. All user-related route handlers in the `users` blueprint delegate to functions in this module.

`Source: services/user_service.py`

### create_user

Creates a new user record in the database after validating that the email address is unique, hashing the password with Werkzeug's security utilities, and verifying that all input constraints are satisfied.

```python
def create_user(email: str, name: str, password: str, role: str = "user") -> dict
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `email` | `str` | Yes | — | User's email address. Must be unique across all users. |
| `name` | `str` | Yes | — | User's display name. Maximum 255 characters. |
| `password` | `str` | Yes | — | User's plain-text password. Minimum 8 characters. Hashed with `werkzeug.security.generate_password_hash()` before storage. |
| `role` | `str` | No | `"user"` | User role. Valid values: `"user"`, `"admin"`. |

**Returns:** `dict` — Serialized user object containing `id`, `email`, `name`, `role`, `is_active`, `created_at`, and `updated_at` fields. The `password_hash` field is excluded from the serialized output. See the [User model serialization](models.md#serialization) for the complete field list.

**Raises:**

| Exception | Condition |
|---|---|
| `ValueError` | Email is already registered in the database |
| `ValueError` | Email format is invalid |
| `ValueError` | Name exceeds 255 characters |
| `ValueError` | Password is shorter than 8 characters |

**Example:**

```python
from services.user_service import create_user

user = create_user(
    email="alice@example.com",
    name="Alice",
    password="securepassword123",
    role="user",
)
# Returns:
# {
#     "id": 1,
#     "email": "alice@example.com",
#     "name": "Alice",
#     "role": "user",
#     "is_active": True,
#     "created_at": "2026-02-24T10:30:00+00:00",
#     "updated_at": "2026-02-24T10:30:00+00:00"
# }
# Note: password_hash is NOT included in the returned dictionary.
```

### get_user_by_id

Retrieves a single user record by its unique identifier.

```python
def get_user_by_id(user_id: int) -> dict
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `user_id` | `int` | Yes | The unique identifier of the user to retrieve. |

**Returns:** `dict` — Serialized user object containing `id`, `email`, `name`, `role`, `is_active`, `created_at`, and `updated_at` fields.

**Raises:**

| Exception | Condition |
|---|---|
| `KeyError` | No user found with the given `user_id` |

**Example:**

```python
from services.user_service import get_user_by_id

user = get_user_by_id(user_id=1)
# Returns:
# {
#     "id": 1,
#     "email": "alice@example.com",
#     "name": "Alice",
#     "role": "user",
#     "is_active": True,
#     "created_at": "2026-02-24T10:30:00+00:00",
#     "updated_at": "2026-02-24T10:30:00+00:00"
# }
```

### get_all_users

Retrieves a paginated list of all user records. Returns both the list of users and pagination metadata.

```python
def get_all_users(page: int = 1, per_page: int = 20) -> dict
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | `int` | No | `1` | Page number for pagination (1-indexed). |
| `per_page` | `int` | No | `20` | Number of records per page. Maximum 100. |

**Returns:** `dict` — Paginated result with the following structure:

| Key | Type | Description |
|---|---|---|
| `users` | `list[dict]` | List of serialized user dictionaries for the requested page |
| `total` | `int` | Total number of user records across all pages |
| `page` | `int` | Current page number |
| `pages` | `int` | Total number of pages |

> **Note:** The service returns user records under the `users` key. The route handler in the presentation layer transforms this to a `data` key in the HTTP response to conform to the API's standard response envelope. See the [Endpoints Reference](endpoints.md) for the final HTTP response format.

**Example:**

```python
from services.user_service import get_all_users

result = get_all_users(page=1, per_page=10)
# Returns:
# {
#     "users": [
#         {"id": 1, "email": "alice@example.com", "name": "Alice", ...},
#         {"id": 2, "email": "bob@example.com", "name": "Bob", ...}
#     ],
#     "total": 42,
#     "page": 1,
#     "pages": 5
# }
```

### update_user

Updates an existing user record with the provided field values. Only the fields included in the `data` dictionary are modified; all other fields retain their current values.

```python
def update_user(user_id: int, data: dict) -> dict
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `user_id` | `int` | Yes | The unique identifier of the user to update. |
| `data` | `dict` | Yes | Dictionary of fields to update. Supported keys: `name`, `email`, `role`, `is_active`. |

**Returns:** `dict` — Updated serialized user object containing `id`, `email`, `name`, `role`, `is_active`, `created_at`, and `updated_at` fields. The `updated_at` timestamp reflects the time of the update.

**Raises:**

| Exception | Condition |
|---|---|
| `KeyError` | No user found with the given `user_id` |
| `ValueError` | Updated email already exists for another user |
| `ValueError` | Invalid field value (for example, name exceeds 255 characters) |

**Example:**

```python
from services.user_service import update_user

updated = update_user(user_id=1, data={"name": "Alice Smith", "role": "admin"})
# Returns:
# {
#     "id": 1,
#     "email": "alice@example.com",
#     "name": "Alice Smith",
#     "role": "admin",
#     "is_active": True,
#     "created_at": "2026-02-24T10:30:00+00:00",
#     "updated_at": "2026-02-24T11:45:00+00:00"
# }
```

### delete_user

Permanently deletes a user record from the database. This operation also cascades to delete any associated resources and refresh tokens owned by the user.

```python
def delete_user(user_id: int) -> None
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `user_id` | `int` | Yes | The unique identifier of the user to delete. |

**Returns:** `None`

**Raises:**

| Exception | Condition |
|---|---|
| `KeyError` | No user found with the given `user_id` |

**Example:**

```python
from services.user_service import delete_user

delete_user(user_id=1)
# No return value. The user and all associated records are removed from the database.
```

## Auth Service

The Auth Service handles authentication operations including credential validation, JWT access token generation, refresh token generation, token decoding, and logout (token revocation). All authentication-related route handlers in the `auth` blueprint delegate to functions in this module. The service uses PyJWT for token encoding and decoding, and `werkzeug.security` for password hashing and verification.

`Source: services/auth_service.py`

### authenticate

Validates a user's email and password credentials against the database. If the credentials are valid and the user account is active, returns the serialized user object. If authentication fails for any reason (wrong password, non-existent email, or inactive account), returns `None` without raising an exception — this prevents information leakage about which credential was incorrect.

```python
def authenticate(email: str, password: str) -> dict | None
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `email` | `str` | Yes | User's email address. |
| `password` | `str` | Yes | User's plain-text password to verify against the stored password hash using `werkzeug.security.check_password_hash()`. |

**Returns:** `dict | None` — Serialized user object if credentials are valid and the account is active, `None` if authentication fails.

**Example:**

```python
from services.auth_service import authenticate

user = authenticate(email="alice@example.com", password="securepassword")
if user:
    print(f"Authenticated: {user['email']}")
    # user contains: {"id": 1, "email": "alice@example.com", "name": "Alice", ...}
else:
    print("Invalid credentials")
```

### generate_access_token

Generates a short-lived JWT access token for an authenticated user. The token payload includes the user's ID as the `sub` (subject) claim, the user's role, the token type (`"access"`), and standard `iat` (issued at) and `exp` (expiration) claims. The default expiration is 1 hour from issuance.

```python
def generate_access_token(user_id: int, role: str = "user") -> str
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `user_id` | `int` | Yes | — | The unique identifier of the authenticated user. |
| `role` | `str` | No | `"user"` | The user's role, included in the JWT payload for authorization decisions. |

**Returns:** `str` — Encoded JWT access token string signed with the application's `SECRET_KEY` using the HS256 algorithm.

**Example:**

```python
from services.auth_service import generate_access_token

token = generate_access_token(user_id=1, role="admin")
# Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
# Decoded payload:
# {
#     "sub": 1,
#     "role": "admin",
#     "type": "access",
#     "iat": 1740393000,
#     "exp": 1740396600
# }
```

### generate_refresh_token

Generates a long-lived JWT refresh token for an authenticated user. The refresh token has a longer expiration period (typically 30 days) than the access token and includes `type: "refresh"` in its payload to distinguish it from access tokens during validation. The generated token is persisted in the `refresh_tokens` database table via the [RefreshToken model](models.md#refreshtoken).

```python
def generate_refresh_token(user_id: int) -> str
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `user_id` | `int` | Yes | The unique identifier of the authenticated user. |

**Returns:** `str` — Encoded JWT refresh token string with `type: "refresh"` in the payload. The token is also stored in the database for server-side validation and revocation support.

**Example:**

```python
from services.auth_service import generate_refresh_token

refresh = generate_refresh_token(user_id=1)
# Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
# Decoded payload:
# {
#     "sub": 1,
#     "type": "refresh",
#     "iat": 1740393000,
#     "exp": 1742985000
# }
```

### decode_token

Decodes and validates a JWT token string (either access or refresh). The function verifies the token's signature using the application's `SECRET_KEY`, checks that the token has not expired, and returns the decoded payload dictionary. If the token is invalid, expired, or has been tampered with, the function returns `None`.

```python
def decode_token(token: str) -> dict | None
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `token` | `str` | Yes | Encoded JWT token string to decode and validate. |

**Returns:** `dict | None` — Decoded JWT payload dictionary containing `sub` (user ID), `role`, `type` (access or refresh), `iat`, and `exp` claims if the token is valid. Returns `None` if the token is expired, malformed, or has an invalid signature.

**Example:**

```python
from services.auth_service import decode_token

payload = decode_token(token="eyJhbGciOiJIUzI1NiIs...")
if payload:
    print(f"User ID: {payload['sub']}, Role: {payload['role']}")
    # payload contains: {"sub": 1, "role": "admin", "type": "access", "iat": ..., "exp": ...}
else:
    print("Token is invalid or expired")
```

### logout

Revokes a refresh token by removing it from the database. After a successful logout, the refresh token can no longer be used to generate new access tokens. The function locates the refresh token record in the database, deletes it, and commits the transaction. If the provided token does not exist or has already been revoked, a `ValueError` is raised.

```python
def logout(refresh_token: str) -> None
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `refresh_token` | `str` | Yes | The refresh token string to revoke. Must match an existing token in the `refresh_tokens` table. |

**Returns:** `None` — The function has no return value. A successful call means the token has been revoked.

**Raises:**

| Exception | Condition |
|---|---|
| `ValueError` | The provided refresh token does not exist in the database or has already been revoked |

**Example:**

```python
from services.auth_service import logout

# Revoke a refresh token on user logout
logout(refresh_token="eyJhbGciOiJIUzI1NiIs...")
# The refresh token is now deleted from the database
# and can no longer be used to obtain new access tokens.
```

## Resource Service

The Resource Service manages application resources (items, posts, or other domain-specific entities) owned by users. This service implements the standard CRUD pattern used across all resource services in the application. All resource-related route handlers in the `resources` blueprint delegate to functions in this module.

`Source: services/resource_service.py`

### create_resource

Creates a new resource record in the database, associated with the specified owner. Validates that the owner exists and that the resource name is not empty before persisting the record.

```python
def create_resource(name: str, description: str, owner_id: int, is_public: bool = False) -> dict
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | `str` | Yes | — | Resource name. Maximum 255 characters. Must not be empty. |
| `description` | `str` | Yes | — | Detailed description of the resource. Pass an empty string if no description is needed. |
| `owner_id` | `int` | Yes | — | ID of the user who owns this resource. Must reference an existing user. |
| `is_public` | `bool` | No | `False` | Whether the resource is publicly visible. When `True`, the resource can be viewed by any authenticated user; when `False`, only the owner can access it. |

**Returns:** `dict` — Serialized resource object containing `id`, `name`, `description`, `owner_id`, `is_public`, `created_at`, and `updated_at` fields. See the [Resource model serialization](models.md#serialization_1) for the complete field list.

**Raises:**

| Exception | Condition |
|---|---|
| `ValueError` | Resource name is empty or exceeds 255 characters |
| `KeyError` | No user found with the given `owner_id` |

**Example:**

```python
from services.resource_service import create_resource

resource = create_resource(
    name="Project Alpha",
    description="A sample project resource",
    owner_id=1,
    is_public=True,
)
# Returns:
# {
#     "id": 42,
#     "name": "Project Alpha",
#     "description": "A sample project resource",
#     "owner_id": 1,
#     "is_public": True,
#     "created_at": "2026-02-24T10:30:00+00:00",
#     "updated_at": "2026-02-24T10:30:00+00:00"
# }
```

### get_resource_by_id

Retrieves a single resource record by its unique identifier.

```python
def get_resource_by_id(resource_id: int) -> dict
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `resource_id` | `int` | Yes | The unique identifier of the resource to retrieve. |

**Returns:** `dict` — Serialized resource object containing `id`, `name`, `description`, `owner_id`, `is_public`, `created_at`, and `updated_at` fields.

**Raises:**

| Exception | Condition |
|---|---|
| `KeyError` | No resource found with the given `resource_id` |

**Example:**

```python
from services.resource_service import get_resource_by_id

resource = get_resource_by_id(resource_id=42)
# Returns:
# {
#     "id": 42,
#     "name": "Project Alpha",
#     "description": "A sample project resource",
#     "owner_id": 1,
#     "is_public": False,
#     "created_at": "2026-02-24T10:30:00+00:00",
#     "updated_at": "2026-02-24T10:30:00+00:00"
# }
```

### get_all_resources

Retrieves a paginated list of all resource records. Returns both the list of resources and pagination metadata.

```python
def get_all_resources(page: int = 1, per_page: int = 20) -> dict
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | `int` | No | `1` | Page number for pagination (1-indexed). |
| `per_page` | `int` | No | `20` | Number of records per page. Maximum 100. |

**Returns:** `dict` — Paginated result with the following structure:

| Key | Type | Description |
|---|---|---|
| `resources` | `list[dict]` | List of serialized resource dictionaries for the requested page |
| `total` | `int` | Total number of resource records across all pages |
| `page` | `int` | Current page number |
| `pages` | `int` | Total number of pages |

> **Note:** The service returns resource records under the `resources` key. The route handler in the presentation layer transforms this to a `data` key in the HTTP response to conform to the API's standard response envelope. See the [Endpoints Reference](endpoints.md) for the final HTTP response format.

**Example:**

```python
from services.resource_service import get_all_resources

result = get_all_resources(page=1, per_page=10)
# Returns:
# {
#     "resources": [
#         {"id": 42, "name": "Project Alpha", "owner_id": 1, ...},
#         {"id": 43, "name": "Project Beta", "owner_id": 2, ...}
#     ],
#     "total": 85,
#     "page": 1,
#     "pages": 9
# }
```

### update_resource

Updates an existing resource record with the provided field values. Only the fields included in the `data` dictionary are modified; all other fields retain their current values.

```python
def update_resource(resource_id: int, data: dict) -> dict
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `resource_id` | `int` | Yes | The unique identifier of the resource to update. |
| `data` | `dict` | Yes | Dictionary of fields to update. Supported keys: `name`, `description`, `is_public`. |

**Returns:** `dict` — Updated serialized resource object containing `id`, `name`, `description`, `owner_id`, `is_public`, `created_at`, and `updated_at` fields. The `updated_at` timestamp reflects the time of the update.

**Raises:**

| Exception | Condition |
|---|---|
| `KeyError` | No resource found with the given `resource_id` |
| `ValueError` | Resource name is empty or exceeds 255 characters |

**Example:**

```python
from services.resource_service import update_resource

updated = update_resource(
    resource_id=42,
    data={"name": "Project Alpha v2", "is_public": True},
)
# Returns:
# {
#     "id": 42,
#     "name": "Project Alpha v2",
#     "description": "A sample project resource",
#     "owner_id": 1,
#     "is_public": True,
#     "created_at": "2026-02-24T10:30:00+00:00",
#     "updated_at": "2026-02-24T14:00:00+00:00"
# }
```

### delete_resource

Permanently deletes a resource record from the database.

```python
def delete_resource(resource_id: int) -> None
```

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `resource_id` | `int` | Yes | The unique identifier of the resource to delete. |

**Returns:** `None`

**Raises:**

| Exception | Condition |
|---|---|
| `KeyError` | No resource found with the given `resource_id` |

**Example:**

```python
from services.resource_service import delete_resource

delete_resource(resource_id=42)
# No return value. The resource record is permanently removed from the database.
```

## Error Handling Patterns

All service modules follow a consistent error handling strategy that separates business rule violations from resource-not-found conditions and ensures that database transactions are properly rolled back on failure. This section documents the standard patterns used across every service function.

### Exception Types

Services use two standard Python exception types to signal error conditions:

| Exception | HTTP Status | Usage |
|---|---|---|
| `ValueError` | 400 Bad Request | Business rule violations: duplicate data, invalid input, constraint failures, malformed values |
| `KeyError` | 404 Not Found | Resource-not-found conditions: no record exists with the requested identifier |

### Database Error Handling

When a database operation fails due to a constraint violation (such as a unique key conflict), the service catches the SQLAlchemy exception, rolls back the transaction to restore the session to a clean state, and re-raises the error as a `ValueError` with a descriptive message. This pattern ensures that the database session is never left in a broken state.

```python
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
from extensions import db
from models.user import User


def create_user(email: str, name: str, password: str, role: str = "user") -> dict:
    try:
        password_hash = generate_password_hash(password)
        user = User(email=email, name=name, password_hash=password_hash, role=role)
        db.session.add(user)
        db.session.commit()
        return user.to_dict()
    except IntegrityError:
        db.session.rollback()
        raise ValueError(f"User with email {email} already exists")
```

### Route Handler Translation

Route handlers translate service exceptions into structured HTTP error responses. The pattern below shows how a typical route handler wraps a service call with exception handling to produce consistent JSON error bodies and appropriate HTTP status codes:

```python
from flask import Blueprint, request, jsonify
from services import user_service

users_bp = Blueprint("users", __name__)


@users_bp.route("/", methods=["POST"])
def create_user_endpoint():
    data = request.get_json()
    try:
        user = user_service.create_user(**data)
        return jsonify(user), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
```

This pattern is applied consistently across all route handlers. The service layer raises the exception, and the route handler catches it and maps it to the correct HTTP status code. This separation keeps business logic in the service layer and HTTP concerns in the presentation layer.

### Error Propagation Flow

The following sequence illustrates how an error flows from the database through the service layer to the client:

1. A service function attempts a database operation (for example, inserting a record with a duplicate email).
2. SQLAlchemy raises an `IntegrityError` when the database constraint is violated.
3. The service function catches the `IntegrityError`, calls `db.session.rollback()`, and raises a `ValueError` with a human-readable message.
4. The route handler catches the `ValueError` and returns a `400 Bad Request` JSON response containing the error message.
5. The client receives the structured error response and can display or handle the message.

## Service Conventions

The following table summarizes all conventions that apply across every service module in the application. These conventions ensure consistency, testability, and clean separation between the service layer and the HTTP transport layer.

| Convention | Description |
|---|---|
| Input types | Primitive Python types (`str`, `int`, `dict`), never Flask request objects |
| Output types | Python `dict` (serialized from ORM models via `to_dict()`), never Flask response objects |
| Error signaling | Standard Python exceptions (`ValueError` for business rule violations, `KeyError` for not-found) |
| Database sessions | Managed within each service function; `db.session.commit()` on success, `db.session.rollback()` on failure |
| Naming | Functions named with verb-noun pattern: `create_user`, `get_all_users`, `delete_resource` |
| Location | Each service module in the `services/` directory, one file per domain: `user_service.py`, `auth_service.py`, `resource_service.py` |
| Pagination | List functions accept `page` and `per_page` parameters and return a dictionary with items, `total`, `page`, and `pages` keys |
| Idempotency | Delete functions are idempotent in intent but raise `KeyError` if the target record does not exist |
| Transaction scope | Each function operates within a single database transaction; no function spans multiple commits |

## See Also

- [Architecture Overview](../architecture/overview.md) — Service layer within the layered architecture and glossary of standard terminology
- [Endpoints Reference](endpoints.md) — REST API endpoint catalog that invokes these service functions
- [Models Reference](models.md) — ORM model classes used by service functions for data access and serialization
- [Data Flow](../architecture/data-flow.md) — How data moves between the API layer, service layer, and database layer
- [Testing Guide](../guides/testing.md) — How to write unit tests for service functions using pytest and Flask's test client
