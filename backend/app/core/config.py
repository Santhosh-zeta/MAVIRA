"""Runtime configuration. All secrets come from environment variables only."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MAVIRA"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://mavira:mavira@localhost:5432/mavira"
    redis_url: str = "redis://localhost:6379/0"

    # inline = run assessments in a background thread of the API process
    # rq     = enqueue to Redis and let the worker container execute
    worker_mode: str = "inline"

    # OSINT ----------------------------------------------------------------
    # DEMO = cached OSINT snapshot shipped with the repo (no network)
    # LIVE = configured search provider + live fetching
    osint_mode: str = "DEMO"
    search_provider: str = "none"          # tavily | serper | brave | none
    tavily_api_key: str | None = None
    serper_api_key: str | None = None
    brave_api_key: str | None = None
    fetch_timeout_seconds: float = 12.0
    fetch_max_bytes: int = 3_000_000
    fetch_retries: int = 2
    per_domain_min_interval_seconds: float = 1.5
    user_agent: str = "Team MAVIRA devo1@dropwinggroups.com (third-party risk assessment; respects robots.txt)"
    source_cache_ttl_hours: int = 24 * 7
    demo_step_delay_ms: int = 150          # visible pacing only; 0 in tests

    # LLM ------------------------------------------------------------------
    # none = deterministic rule-based analyzer (no data leaves the environment)
    llm_provider: str = "none"             # none | openai | azure | anthropic | gemini | ollama
    llm_model: str | None = None
    llm_api_base: str | None = None
    llm_temperature: float = 0.0

    # Security -------------------------------------------------------------
    api_key: str | None = None             # optional shared key for the API
    max_upload_mb: int = 10
    cors_origins: str = "http://localhost:3000"
    upload_rate_per_minute: int = 20

    assessor_team: str = "Team MAVIRA"
    methodology_path: Path = APP_DIR / "config" / "methodology.yaml"
    demo_cache_path: Path = APP_DIR / "demo_data" / "osint_cache.json"
    storage_dir: Path = Path("/tmp/mavira-storage")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    return s
