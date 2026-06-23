"""Icon helpers for UI assets."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

_ICONES_DIR = Path(__file__).parent / "assets" / "icons"
_RAIZ_ICONS = Path(__file__).resolve().parents[2] / "icons"


def icone(nome: str) -> QIcon:
    """QIcon from app/ui/assets/icons/<nome>.svg."""
    return QIcon(str(_ICONES_DIR / f"{nome}.svg"))


def icone_ficheiro(nome_ficheiro: str) -> QIcon:
    """QIcon a partir de <raiz>/icons/<nome_ficheiro> (ex.: 'icon_cleaner.ico')."""
    return QIcon(str(_RAIZ_ICONS / nome_ficheiro))
