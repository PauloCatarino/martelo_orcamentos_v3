"""Basic import checks for the project foundation."""

from __future__ import annotations


def test_core_imports() -> None:
    from app.config.settings import get_settings
    from app.db.base import Base
    from app.db.database import get_engine
    from app.db.session import SessionLocal
    from app.main import main
    from app.ui.main_window import MainWindow

    settings = get_settings()

    assert settings.database_url.startswith("mysql+pymysql://")
    assert Base.metadata is not None
    assert get_engine() is not None
    assert SessionLocal is not None
    assert callable(main)
    assert MainWindow is not None

