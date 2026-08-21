"""Configuration settings for the Resume Screener backend."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {
        "env_file": (
            str(Path(__file__).parent / ".env"),
            str(Path(__file__).parent.parent / ".env"),
            ".env",
        ),
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }

    # --- API Keys ---
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")

    # --- LLM Configuration ---
    gemini_model: str = Field(default="gemini-3.6-flash", alias="GEMINI_MODEL")
    groq_model: str = Field(default="openai/gpt-oss-20b", alias="GROQ_MODEL")
    llm_temperature: float = 0.0
    llm_max_retries: int = 2

    # --- Application ---
    app_name: str = "Smart Resume Screener"
    debug: bool = Field(default=False, alias="DEBUG")
    max_file_size_mb: int = 5
    max_resumes_per_session: int = 10
    allowed_extensions: list[str] = [".pdf", ".txt"]

    # --- Database ---
    database_url: str = Field(
        default="sqlite+aiosqlite:///./resume_screener.db",
        alias="DATABASE_URL",
    )

    # --- CORS ---
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent

    @property
    def upload_dir(self) -> Path:
        d = self.base_dir / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def db_path(self) -> str:
        """Extract the raw SQLite file path from the database URL."""
        return self.database_url.replace("sqlite+aiosqlite:///", "")

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_any_llm(self) -> bool:
        return self.has_gemini or self.has_groq


settings = Settings()
