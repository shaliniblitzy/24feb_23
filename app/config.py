"""Environment-aware configuration module with python-dotenv integration.

Provides hierarchical configuration classes for Flask Application Factory pattern:
- BaseConfig: Shared settings loaded from environment variables for all environments
- DevelopmentConfig: Debug-enabled settings for local development
- TestingConfig: Isolated settings with test database for automated testing
- ProductionConfig: Hardened settings with AWS Secrets Manager integration

Configuration loading order:
1. python-dotenv loads .env file at module level (before class attribute evaluation)
2. os.environ.get() reads each setting with sensible defaults
3. In production, ProductionConfig.init_app() optionally overrides from AWS Secrets Manager

All environment variables documented in .env.example have corresponding config attributes.
No secrets are hardcoded — all sensitive values are loaded from the runtime environment.

Usage::

    from app.config import get_config

    config = get_config("development")
    app.config.from_object(config)
"""

import json
import logging
import os

from dotenv import load_dotenv

# Load .env file before config class attributes are evaluated.
# This enables local development configuration without system-level env vars.
# In production, environment variables are injected by the container orchestrator
# (ECS/Fargate) and .env files are not present.
load_dotenv()

logger = logging.getLogger(__name__)


class BaseConfig:
    """Base configuration shared across all environments.

    All settings are loaded from environment variables with sensible defaults.
    Subclasses override specific attributes per environment requirements.

    Attributes cover six integration domains:
    - Flask core (SECRET_KEY, DEBUG, TESTING)
    - Auth0 authentication (AUTH0_DOMAIN, AUTH0_API_AUDIENCE, AUTH0_ALGORITHMS, AUTH0_ISSUER)
    - MongoDB persistence (MONGODB_URI, MONGODB_DATABASE)
    - AWS S3 file storage (AWS_S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION)
    - LLM providers with 3-tier fallback (PRIMARY, SECONDARY, TERTIARY provider configs)
    - Cross-cutting concerns (CORS_ALLOWED_ORIGINS, LOG_LEVEL)
    """

    # -------------------------------------------------------------------------
    # Flask Core Settings
    # -------------------------------------------------------------------------
    # SECRET_KEY: Cryptographic key for session signing, CSRF tokens, and cookie
    # security. MUST be overridden via environment variable in production.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production")
    DEBUG: bool = False
    TESTING: bool = False

    # -------------------------------------------------------------------------
    # Auth0 Configuration — 6-step JWT Validation Pipeline
    # (presence → RS256 signature via JWKS → issuer → audience → expiration → RBAC)
    # -------------------------------------------------------------------------
    # AUTH0_DOMAIN: Tenant domain used to construct the JWKS endpoint URL.
    AUTH0_DOMAIN: str = os.environ.get("AUTH0_DOMAIN", "")
    # AUTH0_API_AUDIENCE: API Identifier validated against the 'aud' JWT claim.
    AUTH0_API_AUDIENCE: str = os.environ.get("AUTH0_API_AUDIENCE", "")
    # AUTH0_ALGORITHMS: Signing algorithm(s) for JWT verification (comma-separated).
    AUTH0_ALGORITHMS: list = os.environ.get("AUTH0_ALGORITHMS", "RS256").split(",")
    # AUTH0_ISSUER: Expected 'iss' claim in incoming JWTs.
    AUTH0_ISSUER: str = os.environ.get("AUTH0_ISSUER", "")

    # -------------------------------------------------------------------------
    # MongoDB Configuration — Repository Pattern Data Access
    # -------------------------------------------------------------------------
    # MONGODB_URI: Full connection string including replica set members.
    MONGODB_URI: str = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/flask_app")
    # MONGODB_DATABASE: Target database name for application data.
    MONGODB_DATABASE: str = os.environ.get("MONGODB_DATABASE", "flask_app")

    # -------------------------------------------------------------------------
    # AWS S3 Configuration — File Upload/Download Operations
    # -------------------------------------------------------------------------
    # AWS_S3_BUCKET: S3 bucket name for stored files.
    AWS_S3_BUCKET: str = os.environ.get("AWS_S3_BUCKET", "")
    # AWS_ACCESS_KEY_ID: IAM access key (prefer IAM roles in production).
    AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID", "")
    # AWS_SECRET_ACCESS_KEY: IAM secret key paired with access key.
    AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    # AWS_REGION: AWS region where resources are located.
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")

    # -------------------------------------------------------------------------
    # LLM Provider Configuration — Multi-Provider Fallback Chain
    # Primary → Secondary → Tertiary → 503 Service Unavailable
    # Each provider has independent exponential backoff retry logic.
    # -------------------------------------------------------------------------
    # --- Primary LLM Provider ---
    LLM_PRIMARY_PROVIDER: str = os.environ.get("LLM_PRIMARY_PROVIDER", "openai")
    LLM_PRIMARY_API_KEY: str = os.environ.get("LLM_PRIMARY_API_KEY", "")
    LLM_PRIMARY_MODEL: str = os.environ.get("LLM_PRIMARY_MODEL", "gpt-4")

    # --- Secondary LLM Provider (first fallback) ---
    LLM_SECONDARY_PROVIDER: str = os.environ.get("LLM_SECONDARY_PROVIDER", "anthropic")
    LLM_SECONDARY_API_KEY: str = os.environ.get("LLM_SECONDARY_API_KEY", "")
    LLM_SECONDARY_MODEL: str = os.environ.get("LLM_SECONDARY_MODEL", "claude-3-sonnet")

    # --- Tertiary LLM Provider (last resort) ---
    LLM_TERTIARY_PROVIDER: str = os.environ.get("LLM_TERTIARY_PROVIDER", "google")
    LLM_TERTIARY_API_KEY: str = os.environ.get("LLM_TERTIARY_API_KEY", "")
    LLM_TERTIARY_MODEL: str = os.environ.get("LLM_TERTIARY_MODEL", "gemini-pro")

    # -------------------------------------------------------------------------
    # CORS Configuration — Cross-Origin Resource Sharing
    # Supports all six client platforms: React Web, React Native, Electron,
    # iOS/Swift, Android/Kotlin, macOS/Objective-C.
    # -------------------------------------------------------------------------
    # CORS_ALLOWED_ORIGINS: Comma-separated list of allowed origins.
    # Development allows localhost; production restricts to explicit domains.
    CORS_ALLOWED_ORIGINS: str = os.environ.get("CORS_ALLOWED_ORIGINS", "*")

    # -------------------------------------------------------------------------
    # Logging Configuration — Structured JSON for CloudWatch
    # -------------------------------------------------------------------------
    # LOG_LEVEL: Python logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")


class DevelopmentConfig(BaseConfig):
    """Development environment configuration.

    Enables debug mode with auto-reload and interactive debugger.
    Sets log level to DEBUG for maximum verbosity during local development.
    """

    DEBUG: bool = True
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "DEBUG")


class TestingConfig(BaseConfig):
    """Testing environment configuration.

    Enables TESTING flag for Flask test client detection and uses an isolated
    test database to prevent contamination of development data.
    Debug mode is enabled for detailed error reporting in test output.
    """

    TESTING: bool = True
    DEBUG: bool = True
    MONGODB_URI: str = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/flask_app_test")
    MONGODB_DATABASE: str = os.environ.get("MONGODB_DATABASE", "flask_app_test")


class ProductionConfig(BaseConfig):
    """Production environment configuration with AWS Secrets Manager integration.

    Debug mode is explicitly disabled. Sensitive credentials can be loaded from
    AWS Secrets Manager at application startup via ``init_app()``, overriding
    environment variables for database URIs, API keys, and other secrets.

    The Secrets Manager integration follows zero-trust principles:
    - No secrets in source code or container images
    - Credentials rotated via Secrets Manager without redeployment
    - Fallback to environment variables if Secrets Manager is unavailable
    """

    DEBUG: bool = False

    @classmethod
    def init_app(cls, app):
        """Initialize production-specific settings from AWS Secrets Manager.

        Retrieves a JSON secret bundle from AWS Secrets Manager and overrides
        matching class attributes. Only attributes already defined on the config
        class are updated — unknown keys in the secret are safely ignored.

        If the secret name environment variable is not set, or if retrieval
        fails, the method falls back silently to existing environment variables.
        This ensures the application can still start in degraded mode rather
        than failing hard on a Secrets Manager outage.

        Args:
            app: Flask application instance. Used for logging context.
        """
        secret_name = os.environ.get("AWS_SECRETS_MANAGER_SECRET_NAME")
        if not secret_name:
            logger.debug(
                "AWS_SECRETS_MANAGER_SECRET_NAME not set; " "skipping Secrets Manager integration."
            )
            return

        try:
            import boto3

            client = boto3.client(
                "secretsmanager",
                region_name=cls.AWS_REGION,
            )
            response = client.get_secret_value(SecretId=secret_name)
            secret_string = response.get("SecretString")
            if not secret_string:
                logger.warning(
                    "Secrets Manager returned empty SecretString for '%s'.",
                    secret_name,
                )
                return

            secrets = json.loads(secret_string)
            if not isinstance(secrets, dict):
                logger.warning(
                    "Secrets Manager secret '%s' is not a JSON object; ignoring.",
                    secret_name,
                )
                return

            overridden_count = 0
            for key, value in secrets.items():
                upper_key = key.upper()
                if hasattr(cls, upper_key):
                    setattr(cls, upper_key, value)
                    overridden_count += 1
                    logger.info(
                        "Config key '%s' overridden from Secrets Manager.",
                        upper_key,
                    )

            logger.info(
                "Production config: %d settings overridden from Secrets Manager " "secret '%s'.",
                overridden_count,
                secret_name,
            )

        except ImportError:
            logger.error(
                "boto3 is not installed; cannot fetch secrets from "
                "AWS Secrets Manager. Falling back to environment variables."
            )
        except json.JSONDecodeError as exc:
            logger.error(
                "Failed to parse Secrets Manager secret '%s' as JSON: %s. "
                "Falling back to environment variables.",
                secret_name,
                exc,
            )
        except Exception:
            logger.exception(
                "Unexpected error fetching secrets from AWS Secrets Manager "
                "for secret '%s'. Falling back to environment variables.",
                secret_name,
            )


# ---------------------------------------------------------------------------
# Configuration registry — maps environment names to config classes
# ---------------------------------------------------------------------------
config_map: dict = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name=None):
    """Get the configuration class for the given environment name.

    Looks up the configuration class in ``config_map`` using the provided
    ``config_name``. If no name is given, falls back to the ``FLASK_ENV``
    environment variable, defaulting to ``"development"`` when unset.

    Args:
        config_name: One of ``'development'``, ``'testing'``, ``'production'``.
            Defaults to the ``FLASK_ENV`` environment variable or
            ``'development'`` if neither is provided.

    Returns:
        The configuration class (not an instance) for the resolved environment.
        Falls back to ``DevelopmentConfig`` if the name is unrecognized.

    Examples::

        # Explicit environment selection
        config = get_config("production")

        # Automatic detection from FLASK_ENV
        config = get_config()
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")
    return config_map.get(config_name, DevelopmentConfig)
