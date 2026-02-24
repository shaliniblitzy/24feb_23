# API Endpoints Reference

*Last updated: 2026-02-24*

This document provides a complete catalog of all REST API endpoints exposed by the Flask server application. Each endpoint is documented with its HTTP method, URL pattern, request parameters, request and response JSON schemas, authentication requirements, HTTP status codes, and executable examples using both curl and Python. The intended audience includes API consumers (frontend developers, third-party integrators) and backend developers implementing or testing endpoints. For standard terminology used throughout this document — including *endpoint*, *blueprint*, *model*, and *service* — see the [glossary in the Architecture Overview](../architecture/overview.md#glossary).

## API Overview

The Flask server exposes a RESTful JSON API for managing users, resources, and authentication. All endpoints listed below share the following conventions.

**Base URL:**

```
http://localhost:5000/api
```

**Content-Type:** All request bodies must be sent as `application/json`. All responses are returned as `application/json`.

**Authentication:** Endpoints marked as requiring authentication expect a valid JWT Bearer token in the `Authorization` header. See the [Authentication](#authentication) section below for header format details.

### Standard Response Envelope

Successful responses follow this structure:

```json
{
    "status": "success",
    "data": { },
    "message": "Operation completed"
}
```

Error responses follow this structure:

```json
{
    "status": "error",
    "message": "Error description",
    "errors": ["Detail 1", "Detail 2"]
}
```

Individual endpoint documentation below shows the exact response body for each operation. Not all endpoints wrap their response in the envelope — token endpoints return the token payload directly, and paginated list endpoints return the pagination wrapper directly.

### Endpoint Summary

The following table lists every endpoint exposed by the Flask server:

| Method | Path | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/login` | Authenticate user and receive tokens | No |
| `POST` | `/api/auth/register` | Register a new user account | No |
| `POST` | `/api/auth/refresh` | Refresh an expired access token | No |
| `GET` | `/api/users/` | List all users (paginated) | Yes |
| `GET` | `/api/users/<id>` | Get a specific user by ID | Yes |
| `PUT` | `/api/users/<id>` | Update a user's information | Yes |
| `DELETE` | `/api/users/<id>` | Delete a user account | Yes (Admin) |
| `GET` | `/api/resources/` | List all resources (paginated) | Yes |
| `POST` | `/api/resources/` | Create a new resource | Yes |
| `GET` | `/api/resources/<id>` | Get a specific resource by ID | Yes |
| `PUT` | `/api/resources/<id>` | Update a resource | Yes |
| `DELETE` | `/api/resources/<id>` | Delete a resource | Yes |
| `GET` | `/health` | Health check endpoint | No |

---

## Authentication Endpoints

Authentication endpoints are grouped under the `auth` blueprint with URL prefix `/api/auth`. These endpoints handle user login, registration, and token refresh. No authentication token is required to access any endpoint in this group.

`Source: routes/auth.py`

### POST /api/auth/login

Authenticates a user with email and password credentials and returns a JWT access token and a refresh token. The access token is used to authorize subsequent API requests by including it in the `Authorization` header. The refresh token is used to obtain a new access token after the original expires.

**Authentication:** Not required

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `email` | `string` | Yes | User's registered email address |
| `password` | `string` | Yes | User's password |

**Request Body Example:**

```json
{
    "email": "alice@example.com",
    "password": "securepassword"
}
```

**Success Response (200 OK):**

```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `400` | Missing email or password | `{"error": "Email and password are required"}` |
| `401` | Invalid credentials | `{"error": "Invalid credentials"}` |

**curl Example:**

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "securepassword"}'
```

**Python Example:**

```python
import requests

response = requests.post(
    "http://localhost:5000/api/auth/login",
    json={"email": "alice@example.com", "password": "securepassword"},
)
data = response.json()
access_token = data["access_token"]
```

### POST /api/auth/register

Registers a new user account with the provided email, name, and password. On success, the server creates the user record in the database and returns the newly created user object. The response does not include tokens — the client must call the login endpoint after registration to obtain authentication tokens.

**Authentication:** Not required

**Request Body:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `email` | `string` | Yes | — | Unique email address |
| `name` | `string` | Yes | — | User's display name (max 255 characters) |
| `password` | `string` | Yes | — | Password (minimum 8 characters) |
| `role` | `string` | No | `"user"` | User role: `"user"` or `"admin"` |

**Request Body Example:**

```json
{
    "email": "bob@example.com",
    "name": "Bob",
    "password": "strongpassword123"
}
```

**Success Response (201 Created):**

```json
{
    "id": 2,
    "email": "bob@example.com",
    "name": "Bob",
    "role": "user",
    "is_active": true,
    "created_at": "2026-02-24T12:00:00+00:00",
    "updated_at": "2026-02-24T12:00:00+00:00"
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `400` | Missing required fields | `{"errors": ["Email is required", "Name is required"]}` |
| `409` | Email already registered | `{"error": "User with email bob@example.com already exists"}` |

**curl Example:**

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "name": "Bob", "password": "strongpassword123"}'
```

**Python Example:**

```python
import requests

response = requests.post(
    "http://localhost:5000/api/auth/register",
    json={"email": "bob@example.com", "name": "Bob", "password": "strongpassword123"},
)
print(response.status_code)  # 201
print(response.json())
```

### POST /api/auth/refresh

Exchanges a valid, non-expired refresh token for a new JWT access token. This endpoint allows clients to maintain an authenticated session without requiring the user to re-enter credentials when the short-lived access token expires. The refresh token itself is not rotated — the same refresh token can be reused until it expires.

**Authentication:** Not required (uses refresh token in the request body)

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `refresh_token` | `string` | Yes | A valid, non-expired JWT refresh token obtained from the login endpoint |

**Request Body Example:**

```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Success Response (200 OK):**

```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `400` | Missing refresh_token field | `{"error": "Refresh token is required"}` |
| `401` | Invalid or expired refresh token | `{"error": "Invalid refresh token"}` |

**curl Example:**

```bash
curl -X POST http://localhost:5000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIs..."}'
```

**Python Example:**

```python
import requests

response = requests.post(
    "http://localhost:5000/api/auth/refresh",
    json={"refresh_token": "eyJhbGciOiJIUzI1NiIs..."},
)
data = response.json()
new_access_token = data["access_token"]
```

---

## User Endpoints

User endpoints are grouped under the `users` blueprint with URL prefix `/api/users`. These endpoints provide CRUD operations for user accounts. All user endpoints require a valid JWT Bearer token in the `Authorization` header. The delete operation additionally requires the `admin` role.

`Source: routes/users.py`

### GET /api/users/

Returns a paginated list of all user accounts. Results are ordered by creation date in descending order (newest first). Pagination parameters control which page of results is returned and how many records appear per page.

**Authentication:** Required (Bearer token)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | `integer` | No | `1` | Page number (1-indexed) |
| `per_page` | `integer` | No | `20` | Number of results per page (maximum 100) |

**Success Response (200 OK):**

```json
{
    "data": [
        {
            "id": 1,
            "email": "alice@example.com",
            "name": "Alice",
            "role": "admin",
            "is_active": true,
            "created_at": "2026-02-24T10:00:00+00:00",
            "updated_at": "2026-02-24T10:00:00+00:00"
        }
    ],
    "total": 42,
    "page": 1,
    "pages": 3
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `401` | Missing or invalid token | `{"error": "Missing authentication token"}` |

**curl Example:**

```bash
curl -X GET "http://localhost:5000/api/users/?page=1&per_page=10" \
  -H "Authorization: Bearer <access_token>"
```

**Python Example:**

```python
import requests

response = requests.get(
    "http://localhost:5000/api/users/",
    params={"page": 1, "per_page": 10},
    headers={"Authorization": f"Bearer {access_token}"},
)
data = response.json()
users = data["data"]
total_count = data["total"]
```

### GET /api/users/\<id\>

Returns a single user account identified by the integer user ID in the URL path. The response includes the complete user object with all fields.

**Authentication:** Required (Bearer token)

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | `integer` | Yes | Unique user identifier |

**Success Response (200 OK):**

```json
{
    "id": 1,
    "email": "alice@example.com",
    "name": "Alice",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-02-24T10:00:00+00:00",
    "updated_at": "2026-02-24T10:00:00+00:00"
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `401` | Missing or invalid token | `{"error": "Missing authentication token"}` |
| `404` | User not found | `{"error": "User not found"}` |

**curl Example:**

```bash
curl -X GET http://localhost:5000/api/users/1 \
  -H "Authorization: Bearer <access_token>"
```

**Python Example:**

```python
import requests

user_id = 1
response = requests.get(
    f"http://localhost:5000/api/users/{user_id}",
    headers={"Authorization": f"Bearer {access_token}"},
)
user = response.json()
```

### PUT /api/users/\<id\>

Updates an existing user's information. Only the fields included in the request body are updated; omitted fields remain unchanged. The response returns the complete updated user object.

**Authentication:** Required (Bearer token)

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | `integer` | Yes | Unique user identifier |

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | No | Updated display name (max 255 characters) |
| `email` | `string` | No | Updated email address (must be unique) |
| `role` | `string` | No | Updated role: `"user"` or `"admin"` |
| `is_active` | `boolean` | No | Updated active status |

**Request Body Example:**

```json
{
    "name": "Alice Smith",
    "role": "admin"
}
```

**Success Response (200 OK):**

```json
{
    "id": 1,
    "email": "alice@example.com",
    "name": "Alice Smith",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-02-24T10:00:00+00:00",
    "updated_at": "2026-02-24T14:30:00+00:00"
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `400` | Invalid request data | `{"error": "Invalid input data"}` |
| `401` | Missing or invalid token | `{"error": "Missing authentication token"}` |
| `404` | User not found | `{"error": "User not found"}` |
| `409` | Email already in use | `{"error": "User with email alice@example.com already exists"}` |

**curl Example:**

```bash
curl -X PUT http://localhost:5000/api/users/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"name": "Alice Smith", "role": "admin"}'
```

**Python Example:**

```python
import requests

user_id = 1
response = requests.put(
    f"http://localhost:5000/api/users/{user_id}",
    json={"name": "Alice Smith", "role": "admin"},
    headers={"Authorization": f"Bearer {access_token}"},
)
updated_user = response.json()
```

### DELETE /api/users/\<id\>

Deletes a user account permanently. This operation requires the `admin` role — only administrators can delete user accounts. On success, the server returns an empty response with a `204 No Content` status code.

**Authentication:** Required (Bearer token, admin role only)

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | `integer` | Yes | Unique user identifier |

**Success Response (204 No Content):**

No response body.

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `401` | Missing or invalid token | `{"error": "Missing authentication token"}` |
| `403` | Authenticated but not admin | `{"error": "Admin access required"}` |
| `404` | User not found | `{"error": "User not found"}` |

**curl Example:**

```bash
curl -X DELETE http://localhost:5000/api/users/2 \
  -H "Authorization: Bearer <access_token>"
```

**Python Example:**

```python
import requests

user_id = 2
response = requests.delete(
    f"http://localhost:5000/api/users/{user_id}",
    headers={"Authorization": f"Bearer {access_token}"},
)
print(response.status_code)  # 204
```

---

## Resource Endpoints

Resource endpoints are grouped under the `resources` blueprint with URL prefix `/api/resources`. These endpoints provide full CRUD operations for application resources. All resource endpoints require a valid JWT Bearer token. Update operations are restricted to the resource owner, and delete operations are permitted for the resource owner or an administrator.

`Source: routes/resources.py`

### GET /api/resources/

Returns a paginated list of all resources. Results are ordered by creation date in descending order (newest first). Each resource object includes the `owner_id` field identifying the user who created it.

**Authentication:** Required (Bearer token)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | `integer` | No | `1` | Page number (1-indexed) |
| `per_page` | `integer` | No | `20` | Number of results per page (maximum 100) |

**Success Response (200 OK):**

```json
{
    "data": [
        {
            "id": 1,
            "name": "Project Alpha",
            "description": "First project resource",
            "is_public": true,
            "owner_id": 1,
            "created_at": "2026-02-24T10:00:00+00:00",
            "updated_at": "2026-02-24T10:00:00+00:00"
        }
    ],
    "total": 15,
    "page": 1,
    "pages": 1
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `401` | Missing or invalid token | `{"error": "Missing authentication token"}` |

**curl Example:**

```bash
curl -X GET "http://localhost:5000/api/resources/?page=1&per_page=10" \
  -H "Authorization: Bearer <access_token>"
```

**Python Example:**

```python
import requests

response = requests.get(
    "http://localhost:5000/api/resources/",
    params={"page": 1, "per_page": 10},
    headers={"Authorization": f"Bearer {access_token}"},
)
data = response.json()
resources = data["data"]
```

### POST /api/resources/

Creates a new resource owned by the authenticated user. The `owner_id` field is automatically set to the ID of the user identified by the JWT token and cannot be overridden in the request body.

**Authentication:** Required (Bearer token)

**Request Body:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | `string` | Yes | — | Resource name (max 255 characters) |
| `description` | `string` | No | `null` | Resource description |
| `is_public` | `boolean` | No | `false` | Whether the resource is publicly visible |

**Request Body Example:**

```json
{
    "name": "Project Alpha",
    "description": "First project resource",
    "is_public": true
}
```

**Success Response (201 Created):**

```json
{
    "id": 1,
    "name": "Project Alpha",
    "description": "First project resource",
    "is_public": true,
    "owner_id": 1,
    "created_at": "2026-02-24T12:00:00+00:00",
    "updated_at": "2026-02-24T12:00:00+00:00"
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `400` | Missing required name field | `{"error": "Resource name is required"}` |
| `401` | Missing or invalid token | `{"error": "Missing authentication token"}` |

**curl Example:**

```bash
curl -X POST http://localhost:5000/api/resources/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"name": "Project Alpha", "description": "First project resource", "is_public": true}'
```

**Python Example:**

```python
import requests

response = requests.post(
    "http://localhost:5000/api/resources/",
    json={
        "name": "Project Alpha",
        "description": "First project resource",
        "is_public": True,
    },
    headers={"Authorization": f"Bearer {access_token}"},
)
print(response.status_code)  # 201
print(response.json())
```

### GET /api/resources/\<id\>

Returns a single resource identified by the integer resource ID in the URL path. The response includes the complete resource object with all fields.

**Authentication:** Required (Bearer token)

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | `integer` | Yes | Unique resource identifier |

**Success Response (200 OK):**

```json
{
    "id": 1,
    "name": "Project Alpha",
    "description": "First project resource",
    "is_public": true,
    "owner_id": 1,
    "created_at": "2026-02-24T10:00:00+00:00",
    "updated_at": "2026-02-24T10:00:00+00:00"
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `401` | Missing or invalid token | `{"error": "Missing authentication token"}` |
| `404` | Resource not found | `{"error": "Resource not found"}` |

**curl Example:**

```bash
curl -X GET http://localhost:5000/api/resources/1 \
  -H "Authorization: Bearer <access_token>"
```

**Python Example:**

```python
import requests

resource_id = 1
response = requests.get(
    f"http://localhost:5000/api/resources/{resource_id}",
    headers={"Authorization": f"Bearer {access_token}"},
)
resource = response.json()
```

### PUT /api/resources/\<id\>

Updates an existing resource. Only the resource owner can perform this operation. Only the fields included in the request body are updated; omitted fields remain unchanged. The response returns the complete updated resource object.

**Authentication:** Required (Bearer token, resource owner only)

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | `integer` | Yes | Unique resource identifier |

**Request Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | No | Updated resource name (max 255 characters) |
| `description` | `string` | No | Updated resource description |
| `is_public` | `boolean` | No | Updated visibility flag |

**Request Body Example:**

```json
{
    "name": "Project Alpha v2",
    "is_public": false
}
```

**Success Response (200 OK):**

```json
{
    "id": 1,
    "name": "Project Alpha v2",
    "description": "First project resource",
    "is_public": false,
    "owner_id": 1,
    "created_at": "2026-02-24T10:00:00+00:00",
    "updated_at": "2026-02-24T15:00:00+00:00"
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `400` | Invalid request data | `{"error": "Invalid input data"}` |
| `401` | Missing or invalid token | `{"error": "Missing authentication token"}` |
| `403` | Not the resource owner | `{"error": "Permission denied"}` |
| `404` | Resource not found | `{"error": "Resource not found"}` |

**curl Example:**

```bash
curl -X PUT http://localhost:5000/api/resources/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"name": "Project Alpha v2", "is_public": false}'
```

**Python Example:**

```python
import requests

resource_id = 1
response = requests.put(
    f"http://localhost:5000/api/resources/{resource_id}",
    json={"name": "Project Alpha v2", "is_public": False},
    headers={"Authorization": f"Bearer {access_token}"},
)
updated_resource = response.json()
```

### DELETE /api/resources/\<id\>

Deletes a resource permanently. This operation is permitted for the resource owner or any user with the `admin` role. On success, the server returns an empty response with a `204 No Content` status code.

**Authentication:** Required (Bearer token, resource owner or admin)

**Path Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | `integer` | Yes | Unique resource identifier |

**Success Response (204 No Content):**

No response body.

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `401` | Missing or invalid token | `{"error": "Missing authentication token"}` |
| `403` | Not the owner and not admin | `{"error": "Permission denied"}` |
| `404` | Resource not found | `{"error": "Resource not found"}` |

**curl Example:**

```bash
curl -X DELETE http://localhost:5000/api/resources/1 \
  -H "Authorization: Bearer <access_token>"
```

**Python Example:**

```python
import requests

resource_id = 1
response = requests.delete(
    f"http://localhost:5000/api/resources/{resource_id}",
    headers={"Authorization": f"Bearer {access_token}"},
)
print(response.status_code)  # 204
```

---

## Health Check Endpoint

The health check endpoint is registered at the application root level (outside any blueprint) and provides a mechanism for load balancers, orchestrators, and monitoring tools to verify that the server is running and can connect to its database.

`Source: app.py`

### GET /health

Returns the current health status of the application, including whether the database connection is active. This endpoint does not require authentication and should be used by infrastructure monitoring systems to determine service availability.

**Authentication:** Not required

**Success Response (200 OK):**

```json
{
    "status": "healthy",
    "database": "connected",
    "timestamp": "2026-02-24T12:00:00+00:00"
}
```

**Degraded Response (503 Service Unavailable):**

```json
{
    "status": "degraded",
    "database": "disconnected",
    "timestamp": "2026-02-24T12:00:00+00:00"
}
```

**Error Responses:**

| Status | Condition | Response Body |
|---|---|---|
| `503` | Database unreachable | `{"status": "degraded", "database": "disconnected", "timestamp": "..."}` |

**curl Example:**

```bash
curl http://localhost:5000/health
```

**Python Example:**

```python
import requests

response = requests.get("http://localhost:5000/health")
health = response.json()
print(health["status"])    # "healthy"
print(health["database"])  # "connected"
```

---

## HTTP Status Codes

The following table lists all HTTP status codes used across the API and their meanings:

| Status Code | Meaning | Usage |
|---|---|---|
| `200` | OK | Successful `GET` or `PUT` request returning data |
| `201` | Created | Successful `POST` request that created a new resource |
| `204` | No Content | Successful `DELETE` request with no response body |
| `400` | Bad Request | Invalid request body, missing required fields, or malformed parameters |
| `401` | Unauthorized | Missing, invalid, or expired authentication token |
| `403` | Forbidden | Authenticated user lacks the required role or ownership permission |
| `404` | Not Found | The requested resource does not exist |
| `409` | Conflict | Resource conflict such as a duplicate email address |
| `500` | Internal Server Error | Unexpected server-side error; details are logged server-side |

---

## Authentication

All protected endpoints require a valid JWT access token in the `Authorization` header. The token must be prefixed with `Bearer` followed by a single space.

**Header Format:**

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Obtaining Tokens:**

1. Send user credentials to `POST /api/auth/login` to receive an `access_token` and a `refresh_token`.
2. Include the `access_token` in the `Authorization` header of every subsequent request to a protected endpoint.
3. When the access token expires (default: 3600 seconds), send the `refresh_token` to `POST /api/auth/refresh` to obtain a new access token without re-entering credentials.

**Example — Authenticated Request:**

```bash
curl -X GET http://localhost:5000/api/users/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Common Authentication Errors:**

| Error | Cause | Resolution |
|---|---|---|
| `401 Missing authentication token` | No `Authorization` header provided | Include the header with a valid Bearer token |
| `401 Invalid token` | Token signature verification failed | Re-authenticate using the login endpoint |
| `401 Token has expired` | Access token's `exp` claim is in the past | Use the refresh endpoint to obtain a new access token |
| `403 Admin access required` | Token is valid but user role is not `admin` | Use an account with the `admin` role |

See [Authentication Guide](../guides/authentication.md) for complete authentication setup documentation, including JWT structure, token lifecycle, middleware configuration, and role-based access control.

---

## Pagination

All list endpoints (`GET /api/users/`, `GET /api/resources/`) support offset-based pagination using query parameters. Pagination controls which subset of records is returned in the response.

**Query Parameters:**

| Parameter | Type | Default | Maximum | Description |
|---|---|---|---|---|
| `page` | `integer` | `1` | — | The page number to retrieve (1-indexed) |
| `per_page` | `integer` | `20` | `100` | The number of records to return per page |

**Paginated Response Structure:**

Every paginated response includes the following fields alongside the `data` array:

| Field | Type | Description |
|---|---|---|
| `data` | `array` | The array of records for the current page |
| `total` | `integer` | The total number of records across all pages |
| `page` | `integer` | The current page number |
| `pages` | `integer` | The total number of pages |

**Example — Retrieving Page 2 with 10 Results Per Page:**

```bash
curl "http://localhost:5000/api/users/?page=2&per_page=10" \
  -H "Authorization: Bearer <access_token>"
```

**Example Response:**

```json
{
    "data": [
        {
            "id": 11,
            "email": "user11@example.com",
            "name": "User Eleven",
            "role": "user",
            "is_active": true,
            "created_at": "2026-02-20T09:00:00+00:00",
            "updated_at": "2026-02-20T09:00:00+00:00"
        }
    ],
    "total": 42,
    "page": 2,
    "pages": 5
}
```

**Python Pagination Example:**

```python
import requests

page = 1
all_users = []

while True:
    response = requests.get(
        "http://localhost:5000/api/users/",
        params={"page": page, "per_page": 20},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    data = response.json()
    all_users.extend(data["data"])
    if page >= data["pages"]:
        break
    page += 1
```

---

## See Also

- [Authentication Guide](../guides/authentication.md) — JWT token management, middleware configuration, and auth setup
- [Models Reference](models.md) — Data model definitions, field types, and relationships
- [Service Layer Reference](services.md) — Business logic functions invoked by endpoints
- [Architecture Overview](../architecture/overview.md) — System design, blueprints, and routing layer description
- [Request Lifecycle](../architecture/request-lifecycle.md) — How requests flow through the Flask application
- [Migration Guide](../guides/migration-from-nodejs.md) — Route mapping from Express to Flask
