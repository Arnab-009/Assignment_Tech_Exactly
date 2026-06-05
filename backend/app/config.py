"""Application configuration.

All secrets and tunables are loaded from environment variables (or a local
``.env`` file during development) via ``pydantic-settings``. Required values
have no default, so the application fails fast and loudly at startup if it is
misconfigured, rather than surfacing confusing errors at request time.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Google OAuth2 -----------------------------------------------------
    google_client_id: str = Field(..., description="OAuth2 web client ID.")
    google_client_secret: str = Field(..., description="OAuth2 web client secret.")
    google_redirect_uri: str = Field(
        "http://localhost:8080/api/auth/callback",
        description="Redirect URI registered in the Google Cloud Console.",
    )

    # --- Gemini ------------------------------------------------------------
    gemini_api_key: str = Field(..., description="Google Gemini API key.")
    gemini_model: str = Field("gemini-2.5-flash", description="Gemini model id.")

    # --- Session / security ------------------------------------------------
    secret_key: str = Field(
        ...,
        min_length=16,
        description="Key used to sign session cookies. Keep secret.",
    )
    session_cookie: str = Field("docsum_session")
    session_max_age: int = Field(60 * 60 * 8, description="Session TTL in seconds.")
    session_https_only: bool = Field(
        False, description="Set True when served over HTTPS in production."
    )

    # --- Application behaviour --------------------------------------------
    default_folder_id: str = Field(
        "", description="Folder ID pre-filled in the UI for quick testing."
    )
    post_login_redirect: str = Field(
        "http://localhost:8080",
        description="Where the user lands after a successful OAuth login.",
    )
    cors_origins: str = Field(
        "http://localhost:8080,http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins.",
    )

    # --- Limits / tuning ---------------------------------------------------
    max_files_per_run: int = Field(20, ge=1, le=200)
    max_file_size_mb: int = Field(10, ge=1, le=200)
    max_text_chars: int = Field(50_000, ge=1_000)
    llm_concurrency: int = Field(5, ge=1, le=20)
    llm_timeout_seconds: int = Field(120, ge=10, le=600)
    summarize_cooldown_seconds: int = Field(30, ge=0)
    result_ttl_seconds: int = Field(60 * 60, ge=60)

    log_level: str = Field("INFO")

    # --- Derived helpers ---------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def insecure_oauth(self) -> bool:
        """Allow OAuth over plain HTTP for local development only."""
        return self.google_redirect_uri.lower().startswith("http://")


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Cached so the ``.env`` file and environment are read exactly once. Tests
    can clear the cache with ``get_settings.cache_clear()``.
    """
    return Settings()
