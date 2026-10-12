"""Settings loaded from environment variables (see .env.example)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap: str = "localhost:19092"
    postgres_dsn: str = "postgresql://fraud:fraud@localhost:5432/fraud"
    model_dir: str = "./models"

    review_threshold: float = 0.30
    decline_threshold: float = 0.80
    redis_timeout_ms: int = 5
    idempotency_ttl_s: int = 86_400
    card_state_ttl_s: int = 30 * 86_400
