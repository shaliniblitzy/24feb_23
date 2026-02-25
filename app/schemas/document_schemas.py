"""Document CRUD request/response validation schemas.

Pydantic v2 models for document management endpoints including
create, read, update, delete, and list with pagination.
All request models enforce strict mode to reject unexpected fields.

Used by:
    app/routes/documents.py — Document Blueprint route handlers
    app/services/document_service.py — Document business logic
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreateRequest(BaseModel):
    """Request model for POST /api/documents.

    Creates a new document. The title is required; content and metadata
    are optional. The created_by field is automatically populated from
    the JWT claims by the route handler.

    Per AAP §0.7.3: strict=True rejects unexpected fields.
    """

    model_config = ConfigDict(strict=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Document title (required)",
    )
    content: str | None = Field(
        None,
        description="Document content body (optional, can be empty for draft)",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional metadata key-value pairs (optional)",
    )
    tags: list[str] | None = Field(
        default=None,
        description="List of tags for categorization (optional)",
    )


class DocumentUpdateRequest(BaseModel):
    """Request model for PUT /api/documents/<id>.

    Updates an existing document. All fields are optional — only provided
    fields are updated (partial update semantics). The updated_at timestamp
    is automatically set by the service layer.

    Per AAP §0.7.3: strict=True rejects unexpected fields.
    """

    model_config = ConfigDict(strict=True)

    title: str | None = Field(
        None,
        min_length=1,
        max_length=500,
        description="Updated document title",
    )
    content: str | None = Field(
        None,
        description="Updated document content body",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Updated metadata key-value pairs (replaces existing)",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Updated list of tags (replaces existing)",
    )


class DocumentResponse(BaseModel):
    """Response model for single document retrieval.

    Used as the response for GET /api/documents/<id>, POST /api/documents,
    PUT /api/documents/<id>, and DELETE /api/documents/<id>.

    Field names align with app/models/domain.py BaseDocument fields:
    id, created_at, updated_at, created_by.
    """

    model_config = ConfigDict(strict=False)

    id: str = Field(..., description="Document unique identifier")
    title: str = Field(..., description="Document title")
    content: str | None = Field(None, description="Document content body")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional metadata key-value pairs",
    )
    tags: list[str] = Field(default_factory=list, description="Document tags")
    created_at: datetime | None = Field(None, description="Creation timestamp (UTC)")
    updated_at: datetime | None = Field(None, description="Last update timestamp (UTC)")
    created_by: str | None = Field(None, description="User ID of document creator")


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses.

    Provides cursor-based or offset-based pagination information
    for document list endpoints.
    """

    model_config = ConfigDict(strict=False)

    page: int = Field(1, ge=1, description="Current page number (1-indexed)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")
    total: int = Field(0, ge=0, description="Total number of documents matching the query")
    total_pages: int = Field(0, ge=0, description="Total number of pages")


class DocumentListResponse(BaseModel):
    """Response model for GET /api/documents (list).

    Returns a paginated list of documents with pagination metadata.

    Per AAP §0.6.1: DocumentListResponse includes pagination support.
    """

    model_config = ConfigDict(strict=False)

    documents: list[DocumentResponse] = Field(
        default_factory=list,
        description="List of documents for the current page",
    )
    pagination: PaginationMeta = Field(
        default_factory=PaginationMeta,
        description="Pagination metadata",
    )


class DocumentQueryParams(BaseModel):
    """Query parameters model for GET /api/documents (list).

    Validates pagination and filtering query parameters.
    Used to parse and validate URL query string parameters.
    """

    model_config = ConfigDict(strict=False)

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page (max 100)")
    sort_by: str | None = Field(
        "created_at",
        description="Field to sort by (created_at, updated_at, title)",
    )
    sort_order: str | None = Field(
        "desc",
        description="Sort direction: 'asc' or 'desc'",
    )
    search: str | None = Field(
        None,
        description="Text search query to filter documents",
    )
    tag: str | None = Field(
        None,
        description="Filter by tag name",
    )
