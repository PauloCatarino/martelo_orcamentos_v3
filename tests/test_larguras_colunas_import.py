"""Import check for the column-width persistence helper."""

from __future__ import annotations


def test_helper_importa() -> None:
    from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras

    assert callable(ligar_persistencia_larguras)
