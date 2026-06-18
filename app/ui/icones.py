"""Icon helpers for UI assets."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

_ICONES_DIR = Path(__file__).parent / "assets" / "icons"


def icone(nome: str) -> QIcon:
    """QIcon from app/ui/assets/icons/<nome>.svg."""
    return QIcon(str(_ICONES_DIR / f"{nome}.svg"))
