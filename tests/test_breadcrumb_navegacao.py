"""Tests for the clickable breadcrumb (phase P4)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.widgets.breadcrumb import Breadcrumb, BreadcrumbItem

_app = QApplication.instance() or QApplication([])


def test_segmento_clicavel_chama_callback() -> None:
    chamado: list[str] = []
    bc = Breadcrumb(
        [
            BreadcrumbItem("Orçamento 260001_01", lambda: chamado.append("orc")),
            BreadcrumbItem("Item: X", lambda: chamado.append("item")),
            BreadcrumbItem("Custeio"),
        ]
    )
    bc._on_link("1")
    assert chamado == ["item"]
    assert bc.text() == "Orçamento 260001_01 > Item: X > Custeio"


def test_strings_continuam_compativeis() -> None:
    bc = Breadcrumb(["Orçamento 260001_01"])
    assert bc.text() == "Orçamento 260001_01"
    bc._on_link("0")  # sem callback associado -> não rebenta
