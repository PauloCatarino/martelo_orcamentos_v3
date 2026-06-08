"""Import checks for the Orcamento Item Custeio page."""

from __future__ import annotations

import inspect
from decimal import Decimal

from app.repositories.orcamento_item_repository import OrcamentoItemResumo


def test_orcamento_item_custeio_page_imports() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert OrcamentoItemCusteioPage is not None


def test_orcamento_item_custeio_page_accepts_expected_arguments() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    parameters = inspect.signature(OrcamentoItemCusteioPage).parameters

    assert "item" in parameters
    assert "orcamento_codigo" in parameters
    assert "orcamento_versao_id" in parameters
    assert "on_back" in parameters


def test_orcamento_item_custeio_page_headers() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    headers = OrcamentoItemCusteioPage.TABLE_HEADERS

    for column in (
        "Ordem",
        "Tipo linha",
        "C\u00f3digo",
        "Def. Pe\u00e7a",
        "Chave ValueSet",
        "Ref LE",
        "Descri\u00e7\u00e3o no or\u00e7amento",
        "\u00c1rea m\u00b2",
        "ML orla fina",
        "ML orla grossa",
        "Custo total",
        "Pre\u00e7o total",
        "Editado localmente",
        "Ativo",
    ):
        assert column in headers


def test_orcamento_item_custeio_page_uses_item_line_service() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage.carregar)

    assert "OrcamentoItemService" in source
    assert "get_item_by_id" in source
    assert "OrcamentoItemCusteioLinhaService" in source
    assert "listar_linhas_do_item" in source


def test_orcamento_item_custeio_page_formats_item_label() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    item = OrcamentoItemResumo(
        id=4,
        orcamento_versao_id=10,
        ordem=1,
        codigo="ITEM-TESTE-001",
        item="Roupeiro Teste",
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

    assert (
        OrcamentoItemCusteioPage._format_item_label(item)
        == "ITEM-TESTE-001 - Roupeiro Teste"
    )


def test_orcamento_item_custeio_page_has_future_layout_placeholders() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage.__init__)

    assert "Linhas de custeio do item" in source
    assert "Importar M" in source
    assert "Inserir Pe" in source
    assert "Inserir Opera" in source
    assert "Guardar Custeio" in source


def test_orcamento_item_custeio_page_has_valueset_tab() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage.__init__)

    assert "OrcamentoItemValuesetPage" in source
    assert '"ValueSet"' in source


def test_orcamento_item_custeio_page_has_parts_library_tree() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    for method in (
        "_create_library_panel",
        "_carregar_biblioteca",
        "_preencher_biblioteca",
        "adicionar_selecoes",
        "_atualizar_contador",
        "_peca_matches",
    ):
        assert hasattr(OrcamentoItemCusteioPage, method)

    panel = inspect.getsource(OrcamentoItemCusteioPage._create_library_panel)
    assert "Biblioteca de pe" in panel
    assert "QTreeWidget" in panel
    assert "tree_biblioteca_pecas" in panel
    assert "Pesquisar pe" in panel
    assert "Adicionar Sele" in panel
    assert "Selecionados: 0" in panel

    carregar = inspect.getsource(OrcamentoItemCusteioPage._carregar_biblioteca)
    assert "DefPecaService" in carregar
    assert "listar_ativas_para_biblioteca" in carregar


def test_orcamento_item_custeio_page_add_selections_inserts_pieces() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage.adicionar_selecoes)

    assert "Selecione pelo menos uma pe" in source
    assert "adicionar_pecas_da_biblioteca" in source
    assert "Peças adicionadas" in source
    assert "Componentes adicionados" in source
    assert "Ignoradas" in source


def test_orcamento_item_custeio_page_maps_hierarchy_columns() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage._linha_para_valores)

    assert '"Nível"' in source
    assert '"Linha pai"' in source


def test_orcamento_item_custeio_page_recalcular_medidas() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert hasattr(OrcamentoItemCusteioPage, "recalcular_medidas")

    init = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    assert "Recalcular Medidas" in init

    source = inspect.getsource(OrcamentoItemCusteioPage.recalcular_medidas)
    assert "recalcular_medidas_do_item" in source
    assert "Medidas recalculadas." in source

    valores = inspect.getsource(OrcamentoItemCusteioPage._linha_para_valores)
    assert '"Comp real"' in valores
    assert "comp_real" in valores
    assert '"Área m²"' in valores


def test_orcamento_item_custeio_page_editable_measure_columns() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert OrcamentoItemCusteioPage.EDITABLE_COLUMNS == {
        "QT mod": "qt_mod",
        "QT und": "qt_und",
        "Comp": "comp",
        "Larg": "larg",
        "Esp": "esp",
    }

    assert hasattr(OrcamentoItemCusteioPage, "_on_cell_changed")

    source = inspect.getsource(OrcamentoItemCusteioPage._on_cell_changed)
    assert "_carregando_tabela" in source
    assert "atualizar_medidas_linha" in source
    assert "Não foi possível atualizar a linha de custeio." in source


def test_orcamento_item_custeio_page_inserir_divisao() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert hasattr(OrcamentoItemCusteioPage, "inserir_divisao")
    assert hasattr(OrcamentoItemCusteioPage, "_coluna_editavel")

    init = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    assert "Inserir Divis" in init

    source = inspect.getsource(OrcamentoItemCusteioPage.inserir_divisao)
    assert "inserir_divisao_independente" in source

    editavel = inspect.getsource(OrcamentoItemCusteioPage._coluna_editavel)
    assert "Descri" in editavel and "livre" in editavel
    assert "DIVISAO_INDEPENDENTE" in editavel


def test_orcamento_item_custeio_page_material_menu() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    for method in (
        "_menu_contexto_material",
        "selecionar_materia_prima_linha",
        "editar_dados_material_linha",
        "limpar_dados_material_linha",
        "_linha_aceita_material",
    ):
        assert hasattr(OrcamentoItemCusteioPage, method)

    menu = inspect.getsource(OrcamentoItemCusteioPage._menu_contexto_material)
    assert "Selecionar Mat" in menu
    assert "Editar Dados do Material" in menu
    assert "Limpar Dados do Material" in menu

    selecionar = inspect.getsource(OrcamentoItemCusteioPage.selecionar_materia_prima_linha)
    assert "MateriaPrimaPickerDialog" in selecionar
    assert "aplicar_materia_prima_na_linha" in selecionar

    editar = inspect.getsource(OrcamentoItemCusteioPage.editar_dados_material_linha)
    assert "CusteioLinhaMaterialDialog" in editar
    assert "atualizar_material_local_linha" in editar

    limpar = inspect.getsource(OrcamentoItemCusteioPage.limpar_dados_material_linha)
    assert "limpar_material_linha" in limpar

    aceita = inspect.getsource(OrcamentoItemCusteioPage._linha_aceita_material)
    assert "DIVISAO_INDEPENDENTE" in aceita
    assert "PECA_COMPOSTA" in aceita
