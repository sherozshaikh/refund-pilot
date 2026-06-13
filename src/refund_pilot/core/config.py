from __future__ import annotations

import secrets

from loguru import logger
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5"

    langchain_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_project: str = "refund-pilot"

    database_url: str = "postgresql+psycopg://refund_pilot:password@localhost:5432/refund_pilot"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "changeme-use-secrets-generate-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    frontend_url: str = "http://localhost"
    secret_key: str = "changeme"
    log_level: str = "INFO"
    environment: str = "development"

    admin_username: str = "admin"
    admin_password: str = "changeme"

    @model_validator(mode="after")
    def warn_insecure_secrets(self) -> Settings:
        if self.jwt_secret_key in ("changeme-use-secrets-generate-in-prod", "changeme"):
            generated = secrets.token_hex(32)
            logger.critical(
                "JWT_SECRET_KEY is insecure default. "
                f"Set JWT_SECRET_KEY={generated} in your .env file."
            )
        if self.secret_key == "changeme":
            generated = secrets.token_hex(32)
            logger.critical(
                f"SECRET_KEY is insecure default. Set SECRET_KEY={generated} in your .env file."
            )
        return self


class PipelineConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PIPELINE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_retries: int = 1
    retry_wait_min_seconds: float = 1.0
    retry_wait_max_seconds: float = 10.0

    task_timeout_seconds: int = 60
    claude_api_timeout_seconds: int = 30
    db_query_timeout_seconds: int = 5

    escalation_threshold_usd: float = 500.0
    refund_window_days: int = 30

    max_message_length: int = 2000
    max_customer_id_length: int = 36

    celery_queue_name: str = "refund_requests"
    celery_max_retries: int = 3
    celery_retry_backoff_seconds: int = 5
    celery_concurrency: int = 1

    # Rate limiting
    rate_limit_requests: int = 5
    rate_limit_window_seconds: int = 60

    # SSE stream timeout
    sse_poll_timeout_seconds: int = 120

    fallback_enabled: bool = True

    claude_max_tokens: int = 300
    claude_temperature: float = 0.0

    # Pricing for cost estimation (USD per million tokens, set per model)
    claude_input_cost_per_mtok: float = 1.00  # claude-haiku-4-5
    claude_output_cost_per_mtok: float = 5.00  # claude-haiku-4-5

    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: int = 30

    # Redis cache TTL for immutable customer/order fields (seconds)
    tool_cache_ttl_seconds: int = 1800
