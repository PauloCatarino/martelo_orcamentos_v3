"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the application."""

    app_name: str
    app_environment: str
    log_level: str
    database_url_override: str | None
    db_driver: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_charset: str

    @property
    def database_url(self) -> str:
        """Return the SQLAlchemy database URL."""
        if self.database_url_override:
            return self.database_url_override

        user = quote_plus(self.db_user)
        password = f":{quote_plus(self.db_password)}" if self.db_password else ""
        database = quote_plus(self.db_name)

        return (
            f"mysql+{self.db_driver}://{user}{password}"
            f"@{self.db_host}:{self.db_port}/{database}?charset={self.db_charset}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings from `.env` and process environment variables."""
    load_dotenv(ENV_FILE, override=False)

    return Settings(
        app_name=os.getenv("APP_NAME", "Martelo Orçamentos V3"),
        app_environment=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        database_url_override=os.getenv("DATABASE_URL"),
        db_driver=os.getenv("DB_DRIVER", "pymysql"),
        db_host=os.getenv("DB_HOST", "127.0.0.1"),
        db_port=int(os.getenv("DB_PORT", "3306")),
        db_name=os.getenv("DB_NAME", "martelo_orcamentos_v3"),
        db_user=os.getenv("DB_USER", "martelo_v3"),
        db_password=os.getenv("DB_PASSWORD", ""),
        db_charset=os.getenv("DB_CHARSET", "utf8mb4"),
    )
