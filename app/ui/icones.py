"""Icon helpers for UI assets."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def _raiz_icons() -> Path:
    """Pasta ``icons`` da raiz, resolvida tanto em dev como no .exe empacotado.

    No executável (PyInstaller) os dados são desempacotados em ``sys._MEIPASS``;
    o .spec copia a pasta para ``<_MEIPASS>/icons``. Em desenvolvimento, é a
    pasta ``icons`` na raiz do projeto (dois níveis acima deste ficheiro).
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidato = Path(base) / "icons"
        if candidato.exists():
            return candidato
    return Path(__file__).resolve().parents[2] / "icons"


_ICONES_DIR = Path(__file__).parent / "assets" / "icons"
_RAIZ_ICONS = _raiz_icons()


def icone(nome: str) -> QIcon:
    """QIcon from app/ui/assets/icons/<nome>.svg."""
    return QIcon(str(_ICONES_DIR / f"{nome}.svg"))


def icone_ficheiro(nome_ficheiro: str) -> QIcon:
    """QIcon a partir de <raiz>/icons/<nome_ficheiro> (ex.: 'icon_cleaner.ico')."""
    return QIcon(str(_RAIZ_ICONS / nome_ficheiro))
