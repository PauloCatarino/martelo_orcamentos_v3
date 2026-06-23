"""Tests for UI image helpers."""

from __future__ import annotations

from PySide6.QtCore import QSize

from app.ui.helpers.imagem import load_scaled_pixmap


def test_load_scaled_pixmap_empty_and_missing_path_returns_none() -> None:
    assert load_scaled_pixmap("", QSize(100, 100)) is None
    assert load_scaled_pixmap("C:/caminho/inexistente/imagem.png", QSize(100, 100)) is None
