"""Central configuration. Values come from environment / .env file, with sane defaults."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "LeadForge"
    app_env: Literal["develop", "staging", "production"] = "develop"
    debug: bool = True

    secret_key: str = "dev-secret-change-me"
    auth_tokens: str = "dev-token-123"  # comma-separated accepted API tokens
    admin_tokens: str = "dev-token-123"

    database_url: str = "sqlite:///data/leadforge.db"
    log_level: str = "INFO"

    @property
    def database_dir(self):
        from pathlib import Path
        if self.database_url.startswith("sqlite:///") and ":memory:" not in self.database_url:
            return Path(self.database_url.replace("sqlite:///", "")).resolve().parent
        return BASE_DIR / "data"

    default_mode: Literal["dry_run", "live"] = "dry_run"
    force_dry_run: bool = True
    enable_live_modes: str = ""  # comma list of channels allowed live: email,voice

    dnc_provider: str = "none"
    dnc_api_key: str | None = None
    call_hours_window: str = "10:00-18:00"
    call_days: str = "mon,tue,wed,thu,fri"
    bounce_rate_pause_threshold: float = 0.05
    spam_complaint_pause_threshold: float = 0.001
    default_daily_email_cap: int = 20
    default_daily_call_cap: int = 10
    warmup_start_daily_email: int = 5

    sender_name: str = "LeadForge Demo Studio"
    sender_email: str = "hello@leads.example.com"
    sender_physical_address: str = "123 Orchard Road, #05-00, Singapore 238867"
    unsubscribe_base_url: str = "http://localhost:8000"

    email_provider: Literal["smtp", "brevo", "resend", "file"] = "file"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    brevo_api_key: str = ""
    resend_api_key: str = ""

    voice_provider: Literal["mock", "vapi", "retell", "bland"] = "mock"
    voice_api_key: str = ""
    voice_dry_run: bool = True

    places_api_key: str = ""
    osm_enabled: bool = True
    overpass_base_url: str = "https://overpass-api.de/api/interpreter"

    llm_provider: Literal["mock", "ollama", "openai", "anthropic"] = "mock"
    llm_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    hosting_provider: Literal["local", "cloudflare_pages", "netlify"] = "local"
    hosting_api_key: str = ""
    netlify_site_name_prefix: str = "leadforge-"

    def token_list(self) -> list[str]:
        return [t.strip() for t in self.auth_tokens.split(",") if t.strip()]

    def admin_token_list(self) -> list[str]:
        return [t.strip() for t in self.admin_tokens.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
