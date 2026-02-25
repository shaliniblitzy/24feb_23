"""Domain data models for MongoDB document structures.

This module defines the core data models used throughout the application.
Models are plain Python dataclasses (not ORMs) that represent the structure
of documents stored in MongoDB. They are used by the Repository Layer for
document structure and by the Schemas Layer for serialization.

Architecture: These models are the foundational data layer. The dependency
flow is: Routes → Services → Repositories → Models (this module).
Schemas also reference these models for field definitions.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware).

    All timestamp fields across domain models use this helper to ensure
    consistent UTC timezone-aware datetime values. This avoids naive
    datetime objects which cause issues with MongoDB's date handling
    and cross-timezone comparisons.

    Returns:
        A timezone-aware datetime set to the current UTC time.
    """
    return datetime.now(UTC)


def _new_id() -> str:
    """Generate a new unique identifier string using UUID4.

    Used as the default_factory for document ID fields (BaseDocument.id
    and AIResult.request_id). UUID4 provides cryptographically random
    identifiers suitable for distributed systems without coordination.

    Returns:
        A string representation of a new UUID4 value.
    """
    return str(uuid.uuid4())


@dataclass
class BaseDocument:
    """Base document model with common fields shared by all MongoDB documents.

    Every document stored in MongoDB inherits these common fields:
    - id: Unique identifier (maps to MongoDB _id)
    - created_at: Timestamp when the document was first created
    - updated_at: Timestamp of the most recent modification
    - created_by: User ID (from JWT claims) of the creator

    This base class provides to_dict() and from_dict() methods for
    MongoDB serialization/deserialization via PyMongo. The to_dict()
    method maps the Python-friendly 'id' field to MongoDB's '_id'
    convention, while from_dict() performs the reverse mapping.

    Subclasses (AuditLogEntry, AIResult) inherit both the common fields
    and the serialization methods, ensuring consistent behavior across
    all document types stored in MongoDB.

    Usage:
        # Create a new document
        doc = BaseDocument(created_by="user-123")

        # Serialize for MongoDB insertion
        mongo_doc = doc.to_dict()
        collection.insert_one(mongo_doc)

        # Deserialize from MongoDB query result
        result = collection.find_one({"_id": some_id})
        doc = BaseDocument.from_dict(result)
    """

    id: str | None = field(default_factory=_new_id)
    created_at: datetime | None = field(default_factory=_utcnow)
    updated_at: datetime | None = field(default_factory=_utcnow)
    created_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the model to a MongoDB-compatible dictionary.

        Performs two transformations for MongoDB compatibility:
        1. Maps the 'id' field to '_id' (MongoDB's document identifier convention)
        2. Removes keys with None values to avoid storing unnecessary null fields
           and to allow MongoDB server-side defaults to take effect

        Returns:
            A dictionary suitable for PyMongo insert_one/update_one operations.
            The dictionary uses '_id' instead of 'id' and excludes None-valued keys.
        """
        data = asdict(self)
        # Map Python 'id' to MongoDB '_id' convention
        if "id" in data:
            data["_id"] = data.pop("id")
        # Remove None values to let MongoDB handle defaults and keep documents clean
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseDocument | None:
        """Create a model instance from a MongoDB document dictionary.

        Performs the reverse mapping of to_dict():
        1. Maps MongoDB '_id' back to the Python-friendly 'id' field
        2. Converts the '_id' value to a string (handles ObjectId and other types)
        3. Filters dictionary keys to only those recognized by the dataclass,
           preventing TypeErrors from unexpected fields in the MongoDB document

        Args:
            data: Dictionary from a PyMongo query result (e.g., find_one()).
                  May be None if the query returned no results.

        Returns:
            A new instance of the class populated from the dictionary,
            or None if the input data is None.
        """
        if data is None:
            return None
        doc = dict(data)
        # Map MongoDB '_id' back to Python 'id'
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        # Filter to only known dataclass fields to avoid unexpected keyword arguments
        known_fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in doc.items() if k in known_fields})


@dataclass
class AuditLogEntry(BaseDocument):
    """Audit log model for structured audit records.

    Per AAP §0.5.3 and §0.7.2: "Audit logs with majority write concern —
    All write operations that modify user data must generate audit log entries
    written with MongoDB majority write concern for durability."

    Per AAP §0.6.1 (audit_repository.py): "Enforces majority write concern,
    structured audit log insertion, query by entity/timestamp."

    This model captures the who, what, when, and where of every write operation
    that modifies user data, enabling compliance auditing and security forensics.

    Fields:
        entity_type: The type of entity affected (e.g., "document", "file", "ai_result").
        entity_id: The unique ID of the affected entity.
        action: The operation performed — one of "CREATE", "UPDATE", "DELETE", "READ".
        user_id: The authenticated user who performed the action (extracted from JWT claims).
        timestamp: When the action occurred (UTC). Separate from created_at to capture
                   the logical time of the action vs. when the log entry was persisted.
        details: Additional context about the change (e.g., changed fields, old/new values).
                 Stored as a flexible dict to accommodate varying audit detail structures.
        ip_address: Client IP address for security auditing and anomaly detection (optional).

    Inherits from BaseDocument:
        id, created_at, updated_at, created_by, to_dict(), from_dict()

    Usage:
        entry = AuditLogEntry(
            entity_type="document",
            entity_id="doc-abc-123",
            action="UPDATE",
            user_id="user-456",
            details={"changed_fields": ["title", "content"]},
            ip_address="192.168.1.100",
        )
        audit_collection.insert_one(entry.to_dict())
    """

    entity_type: str = ""
    entity_id: str = ""
    action: str = ""  # CREATE, UPDATE, DELETE, READ
    user_id: str = ""
    timestamp: datetime | None = field(default_factory=_utcnow)
    details: dict[str, Any] | None = field(default_factory=dict)
    ip_address: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditLogEntry | None:
        """Create an AuditLogEntry from a MongoDB document dictionary.

        Maps MongoDB '_id' to 'id' and filters to known dataclass fields,
        then constructs an AuditLogEntry instance with the extracted values.

        Args:
            data: Dictionary from a PyMongo query result. May be None if
                  the query returned no results.

        Returns:
            An AuditLogEntry instance populated from the dictionary,
            or None if the input data is None.
        """
        if data is None:
            return None
        doc = dict(data)
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        known_fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in doc.items() if k in known_fields})


@dataclass
class AIResult(BaseDocument):
    """AI result model for LLM query results.

    Per AAP §0.6.1 (ai_result_repository.py): "AI result persistence,
    query by request ID, TTL indexing for result expiry."

    Per AAP §0.5.3: LLM Provider Fallback Chain with multi-provider support
    (Primary → Secondary → Tertiary → 503). The provider and model fields
    track which LLM provider fulfilled the request, enabling debugging of
    the fallback chain and provider-level performance analysis.

    This model captures the full lifecycle of an AI query: from the original
    user query, through prompt construction and context enrichment, to the
    LLM response including performance metrics and error states.

    Fields:
        request_id: Unique identifier for the AI query request. Used for
                    query-by-request-ID lookups in ai_result_repository.py.
        query: The original user query text as submitted.
        prompt: The constructed prompt sent to the LLM provider after context
                enrichment and template application.
        response: The LLM's generated response text.
        provider: Which LLM provider was used (e.g., "openai", "anthropic", "google").
        model: The specific model identifier (e.g., "gpt-4", "claude-3-sonnet").
        context_ids: List of document IDs used for context enrichment during
                     prompt construction.
        tokens_used: Total tokens consumed by the LLM call (prompt + completion).
                     Used for cost tracking and quota management.
        latency_ms: Round-trip latency in milliseconds for the LLM API call.
                    Used for performance monitoring and provider comparison.
        status: Result status — one of "pending", "completed", "failed".
                Defaults to "pending" when the query is first submitted.
        error_message: Error details if the query failed (e.g., provider timeout,
                       rate limit exceeded, all providers exhausted).
        expires_at: TTL expiration timestamp for automatic cleanup via MongoDB
                    TTL index. Enables automatic garbage collection of old results.

    Inherits from BaseDocument:
        id, created_at, updated_at, created_by, to_dict(), from_dict()

    Usage:
        result = AIResult(
            query="Summarize this document",
            provider="openai",
            model="gpt-4",
            context_ids=["doc-123", "doc-456"],
            status="completed",
            response="The document discusses...",
            tokens_used=350,
            latency_ms=1245.5,
        )
        ai_results_collection.insert_one(result.to_dict())
    """

    request_id: str = field(default_factory=_new_id)
    query: str = ""
    prompt: str = ""
    response: str = ""
    provider: str = ""
    model: str = ""
    context_ids: list[str] = field(default_factory=list)
    tokens_used: int | None = None
    latency_ms: float | None = None
    status: str = "pending"  # pending, completed, failed
    error_message: str | None = None
    expires_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AIResult | None:
        """Create an AIResult from a MongoDB document dictionary.

        Maps MongoDB '_id' to 'id' and filters to known dataclass fields,
        then constructs an AIResult instance with the extracted values.

        Args:
            data: Dictionary from a PyMongo query result. May be None if
                  the query returned no results.

        Returns:
            An AIResult instance populated from the dictionary,
            or None if the input data is None.
        """
        if data is None:
            return None
        doc = dict(data)
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        known_fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in doc.items() if k in known_fields})
