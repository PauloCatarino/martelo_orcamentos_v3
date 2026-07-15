"""Import checks for the Orcamento items page."""

from __future__ import annotations

import inspect
from decimal import Decimal

from app.repositories.orcamento_item_repository import OrcamentoItemResumo


def test_orcamento_items_page_imports() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    assert OrcamentoItemsPage is not None
    assert hasattr(OrcamentoItemsPage, "abrir_custeio_item_selecionado")


def test_orcamento_items_page_ordem_e_nomes_das_colunas() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    assert OrcamentoItemsPage.TABLE_HEADERS == [
        "Ordem",
        "C\u00f3digo",
        "Tipo",
        "Item",
        "Descri\u00e7\u00e3o",
        "Altura",
        "Largura",
        "Prof",
        "Qtd",
        "Und",
        "Pre\u00e7o Unit\u00e1rio",
        "Pre\u00e7o Total",
        "Ajuste",
        "Custo Produzido",
        "Custo MP",
        "Custo Produ\u00e7\u00e3o",
        "Custo Acabamentos",
        "Margem Lucro Efetiva",
        "Custeio",
        "Produ\u00e7\u00e3o",
    ]

    # Abbreviated headers keep the full name in the header tooltip.
    tooltips = OrcamentoItemsPage.HEADER_TOOLTIPS
    assert "Profundidade" in tooltips["Prof"]
    assert "Quantidade" in tooltips["Qtd"]
    assert "Unidade" in tooltips["Und"]


def test_orcamento_items_page_sem_navegacao_de_modulos() -> None:
    """Modules moved out of the items page (future costing module library)."""
    import app.ui.pages.orcamento_items_page as page_module
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    assert "M\u00f3dulos" not in OrcamentoItemsPage.TABLE_HEADERS
    for method in (
        "abrir_modulos_item_selecionado",
        "_show_modulos_page",
        "_voltar_aos_items",
        "_format_modulos_count",
    ):
        assert not hasattr(OrcamentoItemsPage, method)

    source = inspect.getsource(page_module)
    assert "OrcamentoItemModulosPage" not in source
    assert "OrcamentoItemModuloService" not in source
    assert "modules_button" not in source


def test_orcamento_items_page_tooltips_de_formula() -> None:
    """The price cells expose 3-block tooltips with the real parcels."""
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    source = inspect.getsource(OrcamentoItemsPage._tooltip_formula)
    assert "\u03a3 custo MP + \u03a3 custo orlas + \u03a3 custo ferragem" in source
    assert "\u03a3 corte + \u03a3 orlagem + \u03a3 CNC" in source
    assert "Custo Produzido = Custo MP + Custo Produ\u00e7\u00e3o + Custo Acabamentos" in source
    assert "parcela_mp" in source
    assert "parcela_corte" in source
    assert "Pre\u00e7o manual: item sem linhas de custeio." in source

    for header in (
        "Custo Produzido",
        "Custo MP",
        "Custo Produ\u00e7\u00e3o",
        "Custo Acabamentos",
        "Ajuste",
        "Margem Lucro Efetiva",
        "Pre\u00e7o Unit\u00e1rio",
        "Pre\u00e7o Total",
    ):
        assert f'header == "{header}"' in source


def test_orcamento_items_page_repor_padrao() -> None:
    """Repor Padrão re-applies the default margin set with confirmation."""
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    assert hasattr(OrcamentoItemsPage, "repor_margens_padrao")

    source = inspect.getsource(OrcamentoItemsPage.repor_margens_padrao)
    assert "QMessageBox.question" in source  # confirmation before replacing
    assert "resolver_margens_perfil" in source
    assert "definir_margens_versao" in source  # re-applies prices

    init_source = inspect.getsource(OrcamentoItemsPage._criar_painel_margens)
    assert "Repor Padrão" in init_source


def test_orcamento_items_page_formata_percentagem_e_euros() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    formatar = OrcamentoItemsPage._format_percentagem
    assert formatar(None) == ""
    assert formatar(Decimal("25.26")) == "25,3%"
    # Rounding artifacts close to zero must never show "-0%".
    assert formatar(Decimal("-0.004")) == "0,0%"
    assert formatar(Decimal("0")) == "0,0%"

    fmt_eur = OrcamentoItemsPage._fmt_eur
    assert fmt_eur(Decimal("1846.05")) == "1.846,05"
    assert fmt_eur(Decimal("28.808")) == "28,81"
    assert fmt_eur(None) == "0,00"

    fmt_pct = OrcamentoItemsPage._fmt_pct
    assert fmt_pct(Decimal("15")) == "15%"
    assert fmt_pct(Decimal("2.5")) == "2,5%"
    assert fmt_pct(None) == "0%"


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


def test_orcamento_items_page_sincroniza_precos_ao_carregar() -> None:
    """Loading the list re-applies prices from the stored costing (no button)."""
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    source = inspect.getsource(OrcamentoItemsPage.carregar_items)
    # Lightweight sync: re-applies the formula from the stored line costs.
    assert "aplicar_precos_da_versao" in source


def test_orcamento_items_page_recalcula_pipeline_do_custeio() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    source = inspect.getsource(OrcamentoItemsPage._recalcular_custeio_do_item)
    assert "recalcular_item_completo" in source

    default_source = inspect.getsource(OrcamentoItemsPage._on_producao_default_clicked)
    assert "definir_tipo_producao_default" in default_source
    assert "list_items_by_versao" in default_source

    item_source = inspect.getsource(OrcamentoItemsPage._on_producao_item_changed)
    assert "definir_tipo_producao_item" in item_source


def test_orcamento_items_page_seletor_custeio_simplificado() -> None:
    from app.ui.pages.orcamento_items_page import OrcamentoItemsPage

    assert "Custeio" in OrcamentoItemsPage.TABLE_HEADERS
    assert hasattr(OrcamentoItemsPage, "_criar_combo_custeio")
    assert hasattr(OrcamentoItemsPage, "_on_custeio_item_changed")
    assert "definir_modalidade_custeio_item" in inspect.getsource(
        OrcamentoItemsPage._on_custeio_item_changed
    )
