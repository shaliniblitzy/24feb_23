"""AI/LLM query request/response validation schemas.

Pydantic v2 models for AI query submission and result retrieval endpoints.
Supports the multi-provider fallback chain (Primary -> Secondary -> Tertiary -> 503)
with provider metadata tracking.

All request models enforce strict mode to reject unexpected fields.

Used by:
    app/routes/ai.py -- AI Blueprint route handlers
    app/services/ai_service.py -- AI/LLM orchestration service
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AIQueryRequest(BaseModel):
    """Request model for POST /api/ai/query.

    Submits an AI query with optional context document IDs for
    context enrichment. The AI service will construct the prompt,
    enrich with document context, and execute via the LangChain
    fallback chain.

    The context_ids are document IDs used to retrieve context data
    from MongoDB for prompt enrichment. The preferred_provider field
    allows callers to override the default provider selection, while
    max_tokens and temperature tune LLM generation parameters.

    Strict mode is enabled to reject unexpected fields in request payloads.
    """

    model_config = ConfigDict(strict=True)

    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user's AI query text (required)",
    )
    context_ids: list[str] | None = Field(
        default=None,
        description="List of document IDs to use as context for the AI query (optional)",
    )
    preferred_provider: str | None = Field(
        default=None,
        description=(
            "Preferred LLM provider override (optional). "
            "One of: 'openai', 'anthropic', 'google'. "
            "Falls back to configured primary if not specified."
        ),
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        le=32000,
        description="Maximum tokens for the LLM response (optional, provider default if not set)",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="LLM temperature parameter for response randomness (0.0-2.0, optional)",
    )


class ProviderMetadata(BaseModel):
    """Metadata about the LLM provider that fulfilled the request.

    Tracks which provider and model were used, supporting fallback chain
    debugging and observability. The execute_with_fallback mechanism attempts
    providers in order (Primary -> Secondary -> Tertiary); this metadata
    records which one succeeded and how many fallback attempts occurred.

    The fallback_attempts field indicates how many providers were tried
    before success: 0 means the primary provider succeeded on the first
    attempt, 1 means it fell back once to the secondary, and so on.
    """

    model_config = ConfigDict(strict=False)

    provider: str = Field(
        ...,
        description="LLM provider name (e.g., 'openai', 'anthropic', 'google')",
    )
    model: str = Field(
        ...,
        description="Specific model identifier (e.g., 'gpt-4', 'claude-3-sonnet')",
    )
    tokens_used: int | None = Field(
        default=None,
        description="Total tokens consumed by the LLM call",
    )
    latency_ms: float | None = Field(
        default=None,
        description="Round-trip latency in milliseconds",
    )
    fallback_attempts: int = Field(
        default=0,
        ge=0,
        description="Number of provider fallback attempts before success (0 = primary succeeded)",
    )


class AIQueryResponse(BaseModel):
    """Response model for POST /api/ai/query.

    Returns the AI-generated response with provider metadata and
    a result ID for later retrieval. Immediately returned after
    the LLM provider responds.

    The LLM Provider Fallback Chain ensures a response is generated
    or a 503 is returned if all providers fail. The result_id can be
    used with GET /api/ai/results/<id> for subsequent retrieval.

    The provider field contains a nested ProviderMetadata object with
    details about which LLM provider and model fulfilled the request,
    along with token usage and latency metrics.
    """

    model_config = ConfigDict(strict=False)

    result_id: str = Field(
        ...,
        description="Unique identifier for this AI result (for later retrieval)",
    )
    query: str = Field(
        ...,
        description="The original query text that was submitted",
    )
    response: str = Field(
        ...,
        description="The AI-generated response text",
    )
    provider: ProviderMetadata = Field(
        ...,
        description="Metadata about which LLM provider fulfilled this request",
    )
    context_ids: list[str] = Field(
        default_factory=list,
        description="Document IDs that were used as context",
    )
    status: str = Field(
        default="completed",
        description="Result status: 'completed', 'failed', or 'pending'",
    )
    created_at: datetime | None = Field(
        default=None,
        description="When the result was created (UTC)",
    )


class AIResultResponse(BaseModel):
    """Response model for GET /api/ai/results/<id>.

    Returns a previously stored AI result by its ID. Field names align
    with the AIResult domain model in app/models/domain.py, including
    all persistence fields such as request_id, provider, model, and
    TTL-related expires_at for automatic cleanup.

    The status field indicates the processing state of the result:
    'completed' for successful results, 'failed' for errors (with
    error_message populated), and 'pending' for in-progress queries.

    AI results support TTL-based expiry via the expires_at timestamp,
    enabling automatic cleanup of old results from MongoDB.
    """

    model_config = ConfigDict(strict=False)

    id: str = Field(
        ...,
        description="AI result unique identifier",
    )
    request_id: str = Field(
        ...,
        description="Original request identifier",
    )
    query: str = Field(
        ...,
        description="The original query text",
    )
    response: str = Field(
        ...,
        description="The AI-generated response text",
    )
    provider: str = Field(
        ...,
        description="LLM provider name that generated the response",
    )
    model: str = Field(
        ...,
        description="Specific model identifier used",
    )
    context_ids: list[str] = Field(
        default_factory=list,
        description="Document IDs used for context enrichment",
    )
    tokens_used: int | None = Field(
        default=None,
        description="Total tokens consumed",
    )
    latency_ms: float | None = Field(
        default=None,
        description="Round-trip latency in milliseconds",
    )
    status: str = Field(
        ...,
        description="Result status: 'completed', 'failed', or 'pending'",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if status is 'failed'",
    )
    created_at: datetime | None = Field(
        default=None,
        description="When the result was created (UTC)",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="TTL expiration timestamp for automatic cleanup",
    )
    created_by: str | None = Field(
        default=None,
        description="User ID who submitted the query",
    )
