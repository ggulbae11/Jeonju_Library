from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Jeonju Library Map API"
    api_prefix: str = "/api/v1"
    jwt_secret_key: str = "change-this-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    database_path: str = "data/library.db"
    booklist_csv_path: str = "data/booklist.csv"
    user_csv_path: str = "data/user.csv"
    auto_import_books: bool = True
    import_chunk_size: int = 25_000
    backend_cors_origins: str = (
        "http://localhost:8501,"
        "http://127.0.0.1:8501,"
        "http://localhost:8000,"
        "http://127.0.0.1:8000"
    )
    streamlit_backend_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, list):
            return ",".join(str(item).strip() for item in value if str(item).strip())
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]

    @property
    def database_file(self) -> Path:
        return BASE_DIR / self.database_path

    @property
    def booklist_file(self) -> Path:
        return BASE_DIR / self.booklist_csv_path

    @property
    def user_csv_file(self) -> Path:
        return BASE_DIR / self.user_csv_path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
