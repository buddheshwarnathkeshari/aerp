"""
backend/config/settings.py

WHAT IS THIS?
  Central configuration for the entire AERP application.
  All environment variables are read HERE and ONLY here.
  No other file should call os.getenv() directly.

Design Note: Pydantic SETTINGS?
  Pydantic Settings reads from your .env file AND validates types.
  If HITL_RISK_THRESHOLD is supposed to be an int but you put "abc",
  the app CRASHES at startup with a clear error — not silently fails
  in production 3 hours later.

INTERVIEW CONCEPT — "Fail Fast":
  Validating all config at startup is called "failing fast".
  You want config errors to surface immediately, not during a live review.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    Pydantic validates all types on startup.
    """

    # ── Model config ──────────────────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",  # Load from .env file
        env_file_encoding="utf-8",
        case_sensitive=False,  # GOOGLE_API_KEY == google_api_key
        extra="ignore",  # Ignore unknown env vars (don't crash)
    )

    # ── LLM Settings ──────────────────────────────────────────────────────────
    # LLM Settings
    llm_provider: str = Field(default="gemini", description="gemini, openai, anthropic")

    # Gemini
    google_api_key: str
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_embedding_model: str = Field(default="text-embedding-004")

    # OpenAI
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o")

    # Anthropic
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-3-5-sonnet-latest")

    # ── Database Settings ─────────────────────────────────────────────────────
    database_url: str
    postgres_user: str = "aerp"
    postgres_password: str = "aerp_password"
    postgres_db: str = "aerp_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # ── Redis Settings ────────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── GitHub Settings ───────────────────────────────────────────────────────
    github_token: str

    # ── Jira Settings ─────────────────────────────────────────────────────────
    jira_server: str
    jira_email: str
    jira_api_token: str

    # ── JWT Auth Settings ─────────────────────────────────────────────────────
    secret_key: str = "changeme_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── OAuth Client Settings ─────────────────────────────────────────────────
    github_client_id: str = ""
    github_client_secret: str = ""

    jira_client_id: str = ""
    jira_client_secret: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""

    # ── Google Docs Settings (Now using OAuth) ────────────────────────────────
    # We no longer use a service account key file. User connects via OAuth in UI.

    # ── App Settings ──────────────────────────────────────────────────────────
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"

    # ── Agent Behavior Settings ───────────────────────────────────────────────
    # Findings below this confidence threshold are NOT posted as PR comments.
    # They appear only in the internal report.
    # 0.60 = 60% confidence minimum to show engineers.
    min_confidence_for_pr_comment: float = 0.60

    # Maximum number of tool calls an agent can make per run.
    # Prevents infinite loops (LLM calls tool → reads result → calls again → forever).
    agent_max_iterations: int = 10

    # Risk score above which Human-in-the-Loop is triggered.
    # 40 means: if risk > 40/100, pause for human review.
    hitl_risk_threshold: int = 40

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Design Note: @lru_cache
    Settings reads from the .env file. Without caching, every call
    to get_settings() reads and parses the file from disk.
    With @lru_cache, it reads once and returns the same object forever.
    This is the singleton pattern in Python.

    Answer: Cache the settings object at startup using @lru_cache or a
    module-level singleton.
    """
    return Settings()
