from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    environment: str = "development"
    app_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-luna"
    ai_rate_limit_requests: int = Field(
        default=10,
        ge=1,
        le=1000,
    )
    ai_rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        le=3600,
    )
    rag_database_directory: Path = Path("data/chroma")
    rag_snapshot_s3_bucket: str = ""
    rag_snapshot_s3_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
