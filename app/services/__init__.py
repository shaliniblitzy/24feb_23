"""Business logic Service Layer package.

This package implements the Service Layer — the orchestration tier that contains
all business logic, coordinating between the Repository Layer, LangChain AI engine,
and AWS S3 for file operations.

Architecture Rules (§0.7.1):
- Services access MongoDB ONLY through the Repository Layer
- LangChain operates as a parallel service within the Service Layer
- Services are stateless orchestrators — no server-side session state
- Transaction boundary management at the service level

Available services:
- auth_service: JWT claims extraction, user profile enrichment, RBAC permission checking
- document_service: Document CRUD business logic with audit trail creation
- ai_service: AI/LLM orchestration with multi-provider fallback chain
- file_service: S3 file upload, presigned URL generation, deletion
- audit_service: Structured audit record creation with majority write concern
"""
