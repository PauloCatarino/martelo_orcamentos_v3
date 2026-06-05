"""Import checks for the Orcamento items page."""

from __future__ import annotations

import inspect
from decimal import Decimal

from app.repositories.orcamento_item_repository import OrcamentoItemResumo


def test_orcamento_items_page_imports() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    assert OrcamentoItemsPage is not None
    assert "M\u00f3dulos" in OrcamentoItemsPage.TABLE_HEADERS
    assert hasattr(OrcamentoItemsPage, "abrir_modulos_item_selecionado")


def test_orcamento_items_page_formats_item_label() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    item = OrcamentoItemResumo(
        id=4,
        orcamento_versao_id=10,
        ordem=1,
        codigo="RP_01",
        item="4 PORTAS",
        descricao=None,
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("0"),
        preco_total=Decimal("0"),
        tipo_item="ROUPEIRO_ABRIR",
    )

    assert OrcamentoItemsPage._format_item_label(item) == "4 PORTAS - RP_01"


def test_orcamento_items_page_formats_modulos_count() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    assert OrcamentoItemsPage._format_modulos_count(0) == "0 m\u00f3dulos"
    assert OrcamentoItemsPage._format_modulos_count(1) == "1 m\u00f3dulo"
    assert OrcamentoItemsPage._format_modulos_count(2) == "2 m\u00f3dulos"


def test_orcamento_items_page_accepts_orcamento_codigo() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    parameters = inspect.signature(OrcamentoItemsPage).parameters

    assert "orcamento_codigo" in parameters
