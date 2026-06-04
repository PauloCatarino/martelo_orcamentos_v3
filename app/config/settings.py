"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
import sys
from urllib.parse import quote_plus

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]


def find_env_file() -> Path | None:
    """Locate the project `.env` file."""
    current_dir_env = Path.cwd() / ".env"
    if current_dir_env.exists():
        return current_dir_env

    project_env = BASE_DIR / ".env"
    if project_env.exists():
        return project_env

    if getattr(sys, "frozen", False):
        executable_env = Path(sys.executable).resolve().parent / ".env"
        if executable_env.exists():
            return executable_env

    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        bundled_env = Path(bundled_root) / ".env"
        if bundled_env.exists():
            return bundled_env

    return None


class Settings:
    """Runtime settings for the application."""

    def __init__(self, env_file: Path | None = None) -> None:
        self.env_file = env_file or find_env_file()
        if self.env_file is not None:
            load_dotenv(self.env_file, override=False)

        self.APP_NAME = os.getenv("APP_NAME", "Martelo Orcamentos V3")
        self.APP_ENV = os.getenv("APP_ENV", "development")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.DB_DRIVER = os.getenv("DB_DRIVER", "pymysql")
        self.DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
        self.DB_PORT = int(os.getenv("DB_PORT", "3306"))
        self.DB_NAME = os.getenv("DB_NAME", "martelo_orcamentos_v3")
        self.DB_USER = os.getenv("DB_USER", "martelo_v3")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", "")
        self.DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")
        self.DATABASE_URL = os.getenv("DATABASE_URL")

        self.app_name = self.APP_NAME
        self.app_environment = self.APP_ENV
        self.log_level = self.LOG_LEVEL
        self.database_url_override = self.DATABASE_URL
        self.db_driver = self.DB_DRIVER
        self.db_host = self.DB_HOST
        self.db_port = self.DB_PORT
        self.db_name = self.DB_NAME
        self.db_user = self.DB_USER
        self.db_password = self.DB_PASSWORD
        self.db_charset = self.DB_CHARSET

    @property
    def database_url(self) -> str:
        """Return the SQLAlchemy database URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL

        user = quote_plus(self.DB_USER)
        password = f":{quote_plus(self.DB_PASSWORD)}" if self.DB_PASSWORD else ""
        database = quote_plus(self.DB_NAME)

        return (
            f"mysql+{self.DB_DRIVER}://{user}{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{database}?charset={self.DB_CHARSET}"
        )


settings = Settings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the global runtime settings instance."""
    return settings
