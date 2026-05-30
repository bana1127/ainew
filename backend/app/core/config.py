from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = "ClubAgent"
    APP_ENV: str = "development"
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://clubagent:clubagent@localhost:5433/clubagent"
    )
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @field_validator("UPLOAD_DIR", mode="after")
    @classmethod
    def resolve_upload_dir(cls, value: Path) -> Path:
        if value.is_absolute():
            return value
        return BASE_DIR / value

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
