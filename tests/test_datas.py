"""Tests for date normalization helpers."""

from __future__ import annotations

from app.domain.datas import normalizar_data


def test_normalizar_data_formatos_suportados() -> None:
    assert normalizar_data("2026-01-08") == "08-01-2026"
    assert normalizar_data("16-03-2026") == "16-03-2026"
    assert normalizar_data("") == ""
    assert normalizar_data("2026/3/5") == "05-03-2026"
