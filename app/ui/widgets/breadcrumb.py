"""Breadcrumb widget with optional clickable segments."""

from __future__ import annotations

import html
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.ui import tema


@dataclass(frozen=True)
class BreadcrumbItem:
    """Um segmento do breadcrumb; clicável quando tem ``ao_clicar``."""

    texto: str
    ao_clicar: Callable[[], None] | None = None


def _texto_item(item) -> str:
    return item.texto if isinstance(item, BreadcrumbItem) else str(item)


def format_breadcrumb(items: Sequence) -> str:
    """Junta os segmentos (texto puro) com ' > '."""
    normalizados = [
        _texto_item(item).strip() for item in items if _texto_item(item).strip()
    ]
    return " > ".join(normalizados)


class Breadcrumb(QWidget):
    """Breadcrumb destacado, com segmentos opcionalmente clicáveis."""

    def __init__(self, items: Sequence | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("breadcrumb")
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._texto_simples = ""

        self.label = QLabel("")
        self.label.setObjectName("breadcrumbLabel")
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setStyleSheet(
            "#breadcrumbLabel {"
            f" background-color: {tema.BEGE_AREIA};"
            f" color: {tema.CASTANHO_ESCURO};"
            " font-weight: bold; padding: 4px 8px; border-radius: 4px; }"
            "#breadcrumbLabel a {"
            f" color: {tema.CASTANHO_ESCURO};"
            " }"
        )
        self.label.linkActivated.connect(self._on_link)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.set_items(items or [])

    def set_items(self, items: Sequence) -> None:
        """Atualiza os segmentos. ``str`` (ou item sem callback) = não clicável."""
        self._callbacks = {}
        partes: list[str] = []
        for indice, item in enumerate(items):
            texto = _texto_item(item).strip()
            if not texto:
                continue
            escapado = html.escape(texto)
            callback = item.ao_clicar if isinstance(item, BreadcrumbItem) else None
            if callback is not None:
                self._callbacks[indice] = callback
                partes.append(f'<a href="{indice}">{escapado}</a>')
            else:
                partes.append(escapado)
        self.label.setText(" &gt; ".join(partes))
        self._texto_simples = format_breadcrumb(items)

    def text(self) -> str:
        """Texto simples atual (sem markup), para retrocompatibilidade."""
        return self._texto_simples

    def _on_link(self, href: str) -> None:
        try:
            indice = int(href)
        except (TypeError, ValueError):
            return
        callback = self._callbacks.get(indice)
        if callback is not None:
            callback()
