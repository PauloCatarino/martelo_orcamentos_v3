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
        # Exclusion headers renamed from "Inclui X" -> "Excluir X".
        "Excluir MP",
        "Excluir Orla",
        "Excluir Ferragem",
        "Excluir Produ\u00e7\u00e3o",
        "Excluir Acabamento",
        "Excluir MO",
    ):
        assert column in headers

    # The old "Inclui X" headers must be gone.
    for antigo in ("Inclui MP", "Inclui Orla", "Inclui Ferragem"):
        assert antigo not in headers


def test_orcamento_item_custeio_page_exclusao_checkboxes() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert OrcamentoItemCusteioPage.EXCLUSAO_COLUMNS == {
        "Excluir MP": "excluir_mp",
        "Excluir Orla": "excluir_orla",
        "Excluir Ferragem": "excluir_ferragem",
        "Excluir Produ\u00e7\u00e3o": "excluir_producao",
        "Excluir Acabamento": "excluir_acabamento",
        "Excluir MO": "excluir_mo",
    }

    for method in ("_criar_item_exclusao", "_on_exclusao_changed", "_linha_calcula_total"):
        assert hasattr(OrcamentoItemCusteioPage, method)

    criar = inspect.getsource(OrcamentoItemCusteioPage._criar_item_exclusao)
    assert "ItemIsUserCheckable" in criar
    assert "setCheckState" in criar

    handler = inspect.getsource(OrcamentoItemCusteioPage._on_exclusao_changed)
    assert "atualizar_exclusao_linha" in handler
    assert "checkState" in handler

    on_changed = inspect.getsource(OrcamentoItemCusteioPage._on_cell_changed)
    assert "EXCLUSAO_COLUMNS" in on_changed


def test_orcamento_item_custeio_page_menu_exclusoes_em_lote() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    for method in ("_preencher_menu_exclusoes", "_aplicar_exclusao_em_lote"):
        assert hasattr(OrcamentoItemCusteioPage, method)

    menu = inspect.getsource(OrcamentoItemCusteioPage._menu_contexto_material)
    assert "Exclusões" in menu

    submenu = inspect.getsource(OrcamentoItemCusteioPage._preencher_menu_exclusoes)
    assert "Marcar todos" in submenu
    assert "Desmarcar todos" in submenu
    assert "EXCLUSAO_COLUMNS" in submenu

    aplicar = inspect.getsource(OrcamentoItemCusteioPage._aplicar_exclusao_em_lote)
    assert "atualizar_exclusao_em_lote" in aplicar
    assert "carregar" in aplicar


def test_orcamento_item_custeio_page_picker_pre_filtra_tipo_familia() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(
        OrcamentoItemCusteioPage.selecionar_materia_prima_linha
    )
    assert "MateriaPrimaPickerDialog" in source
    assert "initial_tipo=linha.tipo_materia_prima" in source
    assert "initial_familia=linha.familia_materia_prima" in source


def test_orcamento_item_custeio_page_menu_acabamento() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    menu = inspect.getsource(OrcamentoItemCusteioPage._menu_contexto_material)
    assert "Editar Dados do Acabamento" in menu

    assert hasattr(OrcamentoItemCusteioPage, "editar_dados_acabamento_linha")
    handler = inspect.getsource(
        OrcamentoItemCusteioPage.editar_dados_acabamento_linha
    )
    assert "atualizar_acabamento_local_linha" in handler
    assert "suporta acabamento" in handler  # message for unsupported lines
    assert "CusteioLinhaAcabamentoDialog" in handler


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


def test_orcamento_item_custeio_page_eliminar_linhas() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert hasattr(OrcamentoItemCusteioPage, "eliminar_linhas_selecionadas")

    menu = inspect.getsource(OrcamentoItemCusteioPage._menu_contexto_material)
    assert "Eliminar linha(s)" in menu

    source = inspect.getsource(OrcamentoItemCusteioPage.eliminar_linhas_selecionadas)
    assert "selectedRows" in source
    assert "eliminar_linhas" in source
    assert "definitivamente" in source
    assert "carregar" in source


def test_orcamento_item_custeio_page_atualizar_geral() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert hasattr(OrcamentoItemCusteioPage, "atualizar_geral")

    init = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    assert "self.atualizar_geral" in init

    source = inspect.getsource(OrcamentoItemCusteioPage.atualizar_geral)
    assert "recalcular_medidas_do_item" in source
    assert "recalcular_orlas_do_item" in source
    assert "recalcular_custo_materia_prima_do_item" in source
    assert "recalcular_custos_ferragens_do_item" in source
    assert "recalcular_custos_ml_do_item" in source
    assert "aplicar_acabamentos_do_item" in source
    assert "recalcular_areas_acabamento_do_item" in source
    assert "recalcular_custo_acabamento_do_item" in source
    assert "recalcular_custo_total_do_item" in source

    valores = inspect.getsource(OrcamentoItemCusteioPage._linha_para_valores)
    assert "acabamento_face_sup" in valores
    assert "area_acabamento_sup" in valores
    assert '"Área acab. sup"' in valores
    assert '"Custo acabamento"' in valores
    assert "custo_acabamento" in valores
    assert '"Custo orlas"' in valores
    assert "custo_orlas" in valores
    assert "ml_orla_fina" in valores
    assert '"Custo MP"' in valores
    assert "custo_mp" in valores
    assert '"Custo ferragem"' in valores
    assert "custo_ferragem" in valores
    assert '"SPP ML und"' in valores
    assert "consumo_ml_unitario" in valores
    assert '"SPP ML total"' in valores
    assert "consumo_ml_total" in valores


def test_orcamento_item_custeio_page_esp_edit_protection() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert hasattr(OrcamentoItemCusteioPage, "_confirmar_edicao_espessura")

    on_changed = inspect.getsource(OrcamentoItemCusteioPage._on_cell_changed)
    assert '"Esp"' in on_changed
    assert "_confirmar_edicao_espessura" in on_changed

    confirm = inspect.getsource(OrcamentoItemCusteioPage._confirmar_edicao_espessura)
    assert "vem normalmente da mat" in confirm  # "...da matéria-prima"
    assert "Sim, editar manualmente" in confirm
