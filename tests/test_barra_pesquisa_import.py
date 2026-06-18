"""Import checks for the reusable search bar."""

from __future__ import annotations


def test_barra_pesquisa_imports() -> None:
    from app.ui import icones
    from app.ui.widgets.barra_pesquisa import CampoPesquisa

    assert CampoPesquisa is not None
    assert icones is not None
