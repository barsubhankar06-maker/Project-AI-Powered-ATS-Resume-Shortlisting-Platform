"""Application configuration.

All secrets and environment-specific values live here and are read from the
environment (or a local .env file). Nothing sensitive is ever shipped to the
browser: the frontend only ever talks to our own API.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    # --- Core ---
    app_name: str = "TalentLens ATS"
    environment: str = "development"
    debug: bool = True
    secret_key: str = Field(default="dev-insecure-secret-key-change-me-please-1234")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Database ---
    database_url: str = "sqlite:///./ats.db"

    # --- Storage ---
    storage_backend: str = "local"
    storage_dir: str = "./storage"
    max_upload_mb: int = 10
    signed_url_ttl_seconds: int = 300
    aws_s3_bucket: str = ""
    aws_region: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # --- LLM ---
    llm_enabled: bool = False
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 45
    llm_max_retries: int = 2

    # --- OCR ---
    ocr_enabled: bool = False
    tesseract_cmd: str = "tesseract"

    # --- Processing ---
    processing_mode: str = "background"
    worker_threads: int = 2

    # --- Abuse protection ---
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 20

    # --- Fairness / privacy ---
    blind_screening_default: bool = False
    resume_retention_days: int = 365

    @field_validator("environment")
    @classmethod
    def _lower_env(cls, v: str) -> str:
        return v.lower()

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_enabled and self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
