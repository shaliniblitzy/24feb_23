"""Domain data models package.

This package contains domain data models defining the structure of documents
stored in MongoDB. Models are plain Python dataclasses (not ORMs) and serve
as the foundational data structure layer used by repositories and schemas.
"""

from app.models.domain import AIResult, AuditLogEntry, BaseDocument

__all__ = [
    "BaseDocument",
    "AuditLogEntry",
    "AIResult",
]
