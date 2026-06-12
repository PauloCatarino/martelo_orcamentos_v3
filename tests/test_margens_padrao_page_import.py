"""Import checks for the default margins settings page."""

from __future__ import annotations

import inspect


def test_margens_padrao_page_imports() -> None:
    from app.ui.pages.margens_padrao_page import MargensPadraoPage

    assert MargensPadraoPage is not None
    for method in (
        "carregar",
        "guardar_standard",
        "novo_registo",
        "editar_registo",
        "alternar_ativo",
    ):
        assert hasattr(MargensPadraoPage, method)


def test_margens_padrao_page_tem_tres_separadores() -> None:
    from app.ui.pages.margens_padrao_page import MargensPadraoPage

    source = inspect.getsource(MargensPadraoPage.__init__)
    assert '"Standard"' in source
    assert '"Por Cliente"' in source
    assert '"Por Utilizador"' in source


def test_margens_padrao_page_explica_valor_inicial() -> None:
    from app.ui.dialogs.margem_padrao_dialog import TOOLTIP_VALOR_INICIAL

    assert "VALOR INICIAL" in TOOLTIP_VALOR_INICIAL
    assert "altera livremente" in TOOLTIP_VALOR_INICIAL
