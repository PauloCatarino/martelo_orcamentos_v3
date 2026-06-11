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
    assert hasattr(OrcamentoItemsPage, "abrir_custeio_item_selecionado")


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
    assert "on_open_item_custeio" in parameters


def test_orcamento_items_page_has_custeio_button_and_message() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    init_source = inspect.getsource(OrcamentoItemsPage.__init__)
    open_source = inspect.getsource(OrcamentoItemsPage.abrir_custeio_item_selecionado)

    assert "Custeio do Item" in init_source
    assert "Selecione um item para abrir o custeio." in open_source


def test_orcamento_items_page_seletor_producao_std_serie() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    assert "Produção" in OrcamentoItemsPage.TABLE_HEADERS

    init_source = inspect.getsource(OrcamentoItemsPage.__init__)
    assert "producao_std_button" in init_source
    assert "producao_serie_button" in init_source

    for method in (
        "_on_producao_default_clicked",
        "_on_producao_item_changed",
        "_recalcular_custeio_do_item",
        "_criar_combo_producao",
        "_atualizar_seletor_producao",
    ):
        assert hasattr(OrcamentoItemsPage, method)

    # The per-item combo offers Padrão (NULL) / STD / SERIE.
    combo_source = inspect.getsource(OrcamentoItemsPage._criar_combo_producao)
    assert "Padrão" in combo_source
    assert "None" in combo_source

    # Tooltips explain the default-for-all / per-item-exception rule.
    assert "exceção" in OrcamentoItemsPage.PRODUCAO_DEFAULT_TOOLTIP
    assert "exceção" in OrcamentoItemsPage.PRODUCAO_ITEM_TOOLTIP


def test_orcamento_items_page_recalcula_pipeline_do_custeio() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    source = inspect.getsource(OrcamentoItemsPage._recalcular_custeio_do_item)
    assert "recalcular_custos_producao_do_item" in source
    assert "recalcular_custo_total_do_item" in source

    default_source = inspect.getsource(OrcamentoItemsPage._on_producao_default_clicked)
    assert "definir_tipo_producao_default" in default_source
    assert "list_items_by_versao" in default_source

    item_source = inspect.getsource(OrcamentoItemsPage._on_producao_item_changed)
    assert "definir_tipo_producao_item" in item_source
