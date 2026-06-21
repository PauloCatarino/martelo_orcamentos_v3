"""Import check for the formatted-description table delegate (phase P9)."""

from __future__ import annotations


def test_descricao_delegate_imports() -> None:
    from app.ui.widgets.descricao_delegate import DescricaoItemDelegate

    assert DescricaoItemDelegate is not None
