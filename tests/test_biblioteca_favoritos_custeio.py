"""Checks for the Favoritos group in the costing piece library tree."""

from __future__ import annotations

import inspect


def test_preencher_biblioteca_cria_grupo_favoritos() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage._preencher_biblioteca)

    assert "FAVORITOS" in source
    assert "favoritas" in source
    assert "_criar_folha_biblioteca" in source


def test_folhas_registadas_por_peca() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage._criar_folha_biblioteca)

    assert "_biblioteca_folhas_por_peca" in source
    assert "setCheckState" in source


def test_item_changed_sincroniza_folhas_gemeas() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage._on_biblioteca_item_changed)

    assert "_biblioteca_folhas_por_peca" in source
    assert "blockSignals" in source


def test_adicionar_selecoes_usa_conjunto_de_ids() -> None:
    """Twin leaves must not double-add pieces: selection is an id set."""
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage.adicionar_selecoes)

    assert "self._selecionados" in source
    assert "list(self._selecionados)" in source
