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


def test_custeio_table_edicao_rapida() -> None:
    import inspect

    from app.ui.pages.orcamento_item_custeio_page import (
        CusteioEnterDelegate,
        CusteioLinhasTable,
        OrcamentoItemCusteioPage,
    )

    # Enter/Tab advance within a FIXED fast-edit flow, driven robustly by a
    # delegate (while editing) and keyPressEvent (when selected).
    for method in (
        "keyPressEvent",
        "avancar_celula_editavel",
        "_proxima_celula_editavel",
        "_colunas_fluxo_rapido",
    ):
        assert hasattr(CusteioLinhasTable, method)

    # The fast-flow set is exactly these columns (and excludes Fator série etc.).
    assert CusteioLinhasTable.FAST_FLOW_HEADERS == (
        "Descrição livre",
        "QT mod",
        "QT und",
        "Comp",
        "Larg",
        "Esp",
    )
    assert "Fator série" not in CusteioLinhasTable.FAST_FLOW_HEADERS

    # Both Enter and Tab are intercepted (no shift) for the forward move.
    delegate = inspect.getsource(CusteioEnterDelegate.eventFilter)
    for token in ("Key_Return", "Key_Enter", "Key_Tab", "avancar_celula_editavel"):
        assert token in delegate
    key_press = inspect.getsource(CusteioLinhasTable.keyPressEvent)
    for token in ("Key_Return", "Key_Enter", "Key_Tab"):
        assert token in key_press
    assert "event.accept()" in key_press  # consumes the event (no move down)

    # The next-cell search is restricted to the fast-flow columns.
    proxima = inspect.getsource(CusteioLinhasTable._proxima_celula_editavel)
    assert "_colunas_fluxo_rapido" in proxima
    assert "_celula_editavel" in proxima

    # The table installs the Enter/Tab delegate.
    init = inspect.getsource(CusteioLinhasTable.__init__)
    assert "setItemDelegate" in init
    assert "CusteioEnterDelegate" in init

    # Inline edit saves only this line (fast); the general recompute stays on
    # the Atualizar button.
    on_changed = inspect.getsource(OrcamentoItemCusteioPage._on_cell_changed)
    assert "propagar_item=False" in on_changed
    assert "_atualizar_linha_visivel" in on_changed

    # One-click / type-to-edit triggers.
    init = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    assert "CusteioLinhasTable" in init
    assert "CurrentChanged" in init
    assert "AnyKeyPressed" in init


def test_custeio_page_tooltips_formula_e_cabecalho() -> None:
    import inspect

    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert hasattr(OrcamentoItemCusteioPage, "_tooltip_formula")
    source = inspect.getsource(OrcamentoItemCusteioPage._tooltip_formula)
    for header in (
        "Custo MP",
        "Custo corte",
        "Custo orlagem",
        "Custo CNC",
        "Custo produção",
        "Custo total",
    ):
        assert header in source

    # New tooltip coverage: measures, area, perimeter, total parcels.
    for header in ("Área m²", "Perímetro ML", "Comp", "Larg"):
        assert header in source

    # Header tooltips for the new production columns.
    tooltips = OrcamentoItemCusteioPage.HEADER_TOOLTIPS
    for header in ("Custo corte", "Custo orlagem", "Custo CNC", "Custo produção"):
        assert header in tooltips

    # _preencher_linha applies the formula tooltip to cells.
    preencher = inspect.getsource(OrcamentoItemCusteioPage._preencher_linha)
    assert "_tooltip_formula" in preencher


def test_custeio_page_tooltips_tres_blocos() -> None:
    import inspect

    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    # Helper that joins the three blocks (rule, formula, substitution).
    assert hasattr(OrcamentoItemCusteioPage, "_tooltip_3")
    source = inspect.getsource(OrcamentoItemCusteioPage._tooltip_formula)
    # Each calculated column now uses the 3-block helper.
    assert source.count("self._tooltip_3(") >= 10

    # The manual-operation cost has its own rule/formula text.
    montagem = inspect.getsource(OrcamentoItemCusteioPage._tooltip_montagem_manual)
    assert "Trabalho avulso cobrado ao tempo na máquina" in montagem
    assert "minutos × QT / 60 × custo/hora" in montagem


def test_custeio_page_operacao_manual_so_edita_quantidade() -> None:
    import inspect

    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage._coluna_editavel)
    assert "OPERACAO_MANUAL" in source
    assert "QT mod" in source and "QT und" in source


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

    # The pipeline lives in a shared helper, reused by the Mat. default dropdown.
    assert "_recalcular_item_completo" in inspect.getsource(
        OrcamentoItemCusteioPage.atualizar_geral
    )
    source = inspect.getsource(OrcamentoItemCusteioPage._recalcular_item_completo)
    assert "recalcular_medidas_do_item" in source
    assert "recalcular_orlas_do_item" in source
    assert "recalcular_custo_materia_prima_do_item" in source
    assert "recalcular_custos_ferragens_do_item" in source
    assert "recalcular_custos_ml_do_item" in source
    assert "aplicar_acabamentos_do_item" in source
    assert "recalcular_areas_acabamento_do_item" in source
    assert "recalcular_custo_acabamento_do_item" in source
    assert "aplicar_operacoes_do_item" in source
    # Phase 8T.5.1: component quantity rules run after measures (which give the
    # parent's real dimensions) and before the cost steps that use qt_total.
    assert "aplicar_regras_quantidade_do_item" in source
    assert source.index("aplicar_regras_quantidade_do_item") > source.index(
        "recalcular_medidas_do_item"
    )
    assert source.index("aplicar_regras_quantidade_do_item") < source.index(
        "recalcular_custo_materia_prima_do_item"
    )
    assert "recalcular_custos_producao_do_item" in source
    # Phase 8R.1: informative production times are back in the pipeline, right
    # after the production cost (so they share the same time source).
    assert "recalcular_tempos_producao_do_item" in source
    assert source.index("recalcular_tempos_producao_do_item") > source.index(
        "recalcular_custos_producao_do_item"
    )
    assert "recalcular_custo_total_do_item" in source

    valores = inspect.getsource(OrcamentoItemCusteioPage._linha_para_valores)
    assert "acabamento_face_sup" in valores
    assert "area_acabamento_sup" in valores
    assert '"Área acab. sup"' in valores
    assert '"Custo acabamento"' in valores
    assert "custo_acabamento" in valores
    assert '"Operações"' in valores
    assert "linha.operacoes" in valores
    assert '"Máquina"' in valores
    assert '"Tempo corte"' in valores
    assert "linha.tempo_corte" in valores
    assert '"Tempo orlagem"' in valores
    assert '"Custo corte"' in valores
    assert "linha.custo_corte" in valores
    assert '"Custo CNC"' in valores
    assert "linha.custo_cnc" in valores
    assert '"Custo mont./manual"' in valores
    assert "linha.custo_montagem_manual" in valores
    assert '"Custo produção"' in valores
    assert "linha.custo_producao" in valores
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


def test_custeio_page_menu_operacao_manual() -> None:
    import inspect

    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    menu = inspect.getsource(OrcamentoItemCusteioPage._menu_contexto_material)
    assert "Inserir operação manual" in menu

    for method in (
        "inserir_operacao_manual_linha",
        "editar_operacao_manual_linha",
        "_maquinas_montagem_manual",
    ):
        assert hasattr(OrcamentoItemCusteioPage, method)

    inserir = inspect.getsource(OrcamentoItemCusteioPage.inserir_operacao_manual_linha)
    assert "OperacaoManualDialog" in inserir
    assert "inserir_operacao_manual" in inserir

    # the machine combo offers MANUAL, MONTAGEM and CNC machines
    maquinas = inspect.getsource(OrcamentoItemCusteioPage._maquinas_montagem_manual)
    assert '"MANUAL", "MONTAGEM", "CNC"' in maquinas


def test_orcamento_item_custeio_page_esp_edit_protection() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert hasattr(OrcamentoItemCusteioPage, "_confirmar_edicao_espessura")

    on_changed = inspect.getsource(OrcamentoItemCusteioPage._on_cell_changed)
    assert '"Esp"' in on_changed
    assert "_confirmar_edicao_espessura" in on_changed

    confirm = inspect.getsource(OrcamentoItemCusteioPage._confirmar_edicao_espessura)
    assert "vem normalmente da mat" in confirm  # "...da matéria-prima"
    assert "Sim, editar manualmente" in confirm


def test_custeio_page_etiqueta_producao() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    init = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    assert "producao_label" in init

    assert hasattr(OrcamentoItemCusteioPage, "_atualizar_producao_label")
    label = inspect.getsource(OrcamentoItemCusteioPage._atualizar_producao_label)
    assert "padrão" in label
    assert "exceção" in label
    assert "tipo_producao_efetivo" in label


def test_custeio_page_fator_serie_editavel() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    editavel = inspect.getsource(OrcamentoItemCusteioPage._coluna_editavel)
    assert '"Fator série"' in editavel

    on_changed = inspect.getsource(OrcamentoItemCusteioPage._on_cell_changed)
    assert "_on_fator_serie_changed" in on_changed

    handler = inspect.getsource(OrcamentoItemCusteioPage._on_fator_serie_changed)
    assert "atualizar_fator_serie_linha" in handler

    assert "Tipo produção" in OrcamentoItemCusteioPage.HEADER_TOOLTIPS
    assert "Fator série" in OrcamentoItemCusteioPage.HEADER_TOOLTIPS


def test_custeio_page_tooltips_tarifa_std_serie() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    for method in (
        "_descrever_tarifa",
        "_tarifa_ml_tooltip",
        "_tarifa_cnc_tooltip",
        "_tarifa_hora_tooltip",
        "_carregar_tarifas_maquinas",
    ):
        assert hasattr(OrcamentoItemCusteioPage, method)

    descrever = inspect.getsource(OrcamentoItemCusteioPage._descrever_tarifa)
    assert "SERIE não definida — fallback" in descrever

    # The production-cost tooltip includes the fator série in the substitution.
    formula = inspect.getsource(OrcamentoItemCusteioPage._tooltip_formula)
    assert "fator" in formula
    assert "_tarifa_ml_tooltip" in formula
    assert "_tarifa_cnc_tooltip" in formula


def test_custeio_page_caixa_preco_item() -> None:
    """The page shows a read-only reference-price box updated on load."""
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    for method in ("_atualizar_caixa_preco", "_tooltip_preco_item"):
        assert hasattr(OrcamentoItemCusteioPage, method)

    init_source = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    assert "preco_item_label" in init_source

    # The box reads its values from the service's recalcular_preco_item.
    caixa = inspect.getsource(OrcamentoItemCusteioPage._atualizar_caixa_preco)
    assert "recalcular_preco_item" in caixa
    assert "Custo produzido" in caixa
    assert "Preço unitário" in caixa
    assert "Preço total" in caixa

    # The box is refreshed whenever the page loads (and thus after Atualizar).
    carregar = inspect.getsource(OrcamentoItemCusteioPage.carregar)
    assert "_atualizar_caixa_preco" in carregar


def test_custeio_page_biblioteca_tooltip_nas_folhas() -> None:
    """Each library leaf carries a multiline detail tooltip on column 0."""
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert hasattr(OrcamentoItemCusteioPage, "_biblioteca_tooltip")

    preencher = inspect.getsource(OrcamentoItemCusteioPage._preencher_biblioteca)
    assert "setToolTip(0" in preencher

    tooltip = inspect.getsource(OrcamentoItemCusteioPage._biblioteca_tooltip)
    for campo in ("Código:", "Nome:", "Tipo:", "Grupo:", "Código de orlas:", "Chave ValueSet:"):
        assert campo in tooltip
    assert "Peça de serviço (sem material)" in tooltip


def test_custeio_page_qt_total_antes_de_comp_real() -> None:
    """Phase: QT total moves to just before Comp real (after Esp)."""
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    headers = OrcamentoItemCusteioPage.TABLE_HEADERS
    i_esp = headers.index("Esp")
    i_qt_total = headers.index("QT total")
    i_comp_real = headers.index("Comp real")

    assert i_qt_total == i_esp + 1
    assert i_comp_real == i_qt_total + 1
    # The editable quantity/measure inputs stay grouped and in order.
    assert headers.index("QT mod") < headers.index("QT und") < headers.index("Comp")
    assert headers.index("Comp") < headers.index("Larg") < headers.index("Esp")
    # Phase 8T.5: the standalone "Qtds" column is gone (the chain is in QT mod).
    assert "Qtds" not in headers


def test_custeio_page_colunas_redimensionaveis_e_splitter() -> None:
    """Interactive (resizable) columns and a resizable library/table splitter."""
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    init_source = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    assert "QHeaderView.ResizeMode.Interactive" in init_source
    assert "setStretchLastSection(False)" in init_source
    assert "QSplitter" in init_source
    assert "workspace_splitter" in init_source

    preencher = inspect.getsource(OrcamentoItemCusteioPage._preencher_tabela)
    assert "resizeColumnsToContents" in preencher


def test_custeio_page_navegacao_enter_horizontal() -> None:
    """Enter commits and moves to the next editable cell to the right."""
    from app.ui.pages.orcamento_item_custeio_page import CusteioLinhasTable

    for method in (
        "keyPressEvent",
        "avancar_celula_editavel",
        "_proxima_celula_editavel",
        "_editar_celula",
    ):
        assert hasattr(CusteioLinhasTable, method)

    proxima = inspect.getsource(CusteioLinhasTable._proxima_celula_editavel)
    # Walks the fast-flow columns to the right, then wraps to the next rows.
    assert "_colunas_fluxo_rapido" in proxima
    assert "for c in fluxo" in proxima
    assert "range(row + 1, self.rowCount())" in proxima


def test_custeio_page_normaliza_variaveis_e_tooltips() -> None:
    """Comp/Larg/Esp normalise variables to uppercase and expose formula tooltips."""
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    # Save path uppercases the variables before storing.
    on_changed = inspect.getsource(OrcamentoItemCusteioPage._on_cell_changed)
    assert "normalizar_variaveis_medida" in on_changed

    # Display path uppercases too.
    fmt = inspect.getsource(OrcamentoItemCusteioPage._format_medida_var)
    assert "normalizar_variaveis_medida" in fmt

    for method in (
        "_tooltip_quantidade",
        "_tooltip_medida",
        "_tooltip_medida_real",
        "_substituir_variaveis_medida",
    ):
        assert hasattr(OrcamentoItemCusteioPage, method)

    tooltip_formula = inspect.getsource(OrcamentoItemCusteioPage._tooltip_formula)
    for header in ("QT mod", "QT und", "QT total", "Comp real", "Larg real", "Esp real"):
        assert header in tooltip_formula

    qt_tooltip = inspect.getsource(OrcamentoItemCusteioPage._tooltip_quantidade)
    assert "QT total = qt_mod efetivo × qt_und" in qt_tooltip


def test_custeio_page_cadeia_no_qt_mod() -> None:
    """Phase 8T.5: the chain shows in QT mod (no standalone column)."""
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    for method in (
        "_cadeia_quantidade",
        "_calcular_quantidades_das_linhas",
        "_valor_qt_mod",
        "_valor_qt_und",
    ):
        assert hasattr(OrcamentoItemCusteioPage, method)

    valores = inspect.getsource(OrcamentoItemCusteioPage._linha_para_valores)
    assert '"QT mod": self._valor_qt_mod(linha)' in valores
    assert '"QT und": self._valor_qt_und(linha)' in valores
    assert "Qtds" not in valores

    # QT mod shows the chain on pieces (a plain number on manual lines).
    qt_mod_src = inspect.getsource(OrcamentoItemCusteioPage._valor_qt_mod)
    assert "_cadeia_quantidade" in qt_mod_src
    # QT und is blank on a division line.
    qt_und_src = inspect.getsource(OrcamentoItemCusteioPage._valor_qt_und)
    assert "DIVISAO_INDEPENDENTE" in qt_und_src


def test_custeio_page_regras_de_edicao_qt() -> None:
    """QT mod editable only on the division; QT und editable only on pieces."""
    from types import SimpleNamespace

    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    editavel = OrcamentoItemCusteioPage._coluna_editavel

    def _linha(tipo):
        return SimpleNamespace(tipo_linha=tipo)

    page = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)

    divisao = _linha("DIVISAO_INDEPENDENTE")
    peca = _linha("PECA")
    componente = _linha("FERRAGEM")

    # Division: QT mod editable, QT und NOT editable.
    assert editavel(page, "QT mod", divisao) is True
    assert editavel(page, "QT und", divisao) is False
    # Pieces/components: QT mod read-only, QT und editable.
    assert editavel(page, "QT mod", peca) is False
    assert editavel(page, "QT und", peca) is True
    assert editavel(page, "QT mod", componente) is False
    assert editavel(page, "QT und", componente) is True
    # Measures stay editable on every line.
    assert editavel(page, "Comp", peca) is True
    assert editavel(page, "Comp", divisao) is True


def test_custeio_page_propaga_quantidades_da_divisao() -> None:
    """Editing QT mod/und reloads; a division edit shows the block message."""
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    on_changed = inspect.getsource(OrcamentoItemCusteioPage._on_cell_changed)
    assert 'header in ("QT mod", "QT und")' in on_changed
    assert "Quantidades do bloco atualizadas." in on_changed
    assert "DIVISAO_INDEPENDENTE" in on_changed

    tooltip = inspect.getsource(OrcamentoItemCusteioPage._tooltip_quantidade)
    assert "qt_mod efetivo" in tooltip


def test_custeio_page_mat_default_dropdown() -> None:
    """Phase 8G.x: 'Mat. default' is a per-line ValueSet-options dropdown."""
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    for method in (
        "_montar_combo_material",
        "_criar_combo_material",
        "_label_opcao_material",
        "_opcao_atual_id",
        "_on_material_combo_changed",
        "_tooltip_mat_default",
        "_linha_aceita_dropdown_material",
    ):
        assert hasattr(OrcamentoItemCusteioPage, method)

    # The fill loop special-cases the Mat. default column with the combo.
    preencher = inspect.getsource(OrcamentoItemCusteioPage._preencher_linha)
    assert '"Mat. default"' in preencher
    assert "_montar_combo_material" in preencher

    # Eligibility: PECA/FERRAGEM lines that carry material (not service pieces).
    aceita = inspect.getsource(OrcamentoItemCusteioPage._linha_aceita_dropdown_material)
    assert "PECA" in aceita
    assert "FERRAGEM" in aceita
    assert "sem_material" in aceita

    # Selecting an option applies it and recomputes via the shared pipeline.
    handler = inspect.getsource(OrcamentoItemCusteioPage._on_material_combo_changed)
    assert "aplicar_opcao_valueset_na_linha" in handler
    assert "_recalcular_item_completo" in handler

    # The combo uses the IMOS compatibility filter.
    combo = inspect.getsource(OrcamentoItemCusteioPage._montar_combo_material)
    assert "opcoes_valueset_compativeis" in combo


def test_custeio_page_miniatura_modulo() -> None:
    """Phase 8U.4: the 'Módulo' column shows a thumbnail + zoom tooltip."""
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert "Módulo" in OrcamentoItemCusteioPage.TABLE_HEADERS
    assert hasattr(OrcamentoItemCusteioPage, "_criar_item_modulo")

    # The fill loop special-cases the Módulo column with the thumbnail cell.
    preencher = inspect.getsource(OrcamentoItemCusteioPage._preencher_linha)
    assert '"Módulo"' in preencher
    assert "_criar_item_modulo" in preencher

    # The cell uses the line's modulo_imagem_path, a scaled icon and the HTML
    # zoom tooltip, with a discreet placeholder when the image cannot open.
    criar = inspect.getsource(OrcamentoItemCusteioPage._criar_item_modulo)
    assert "modulo_imagem_path" in criar
    assert "setIcon" in criar
    assert "tooltip_imagem_html" in criar
    assert "(sem img)" in criar

    # Saving a module copies the chosen image to the configured folder.
    assert hasattr(OrcamentoItemCusteioPage, "_copiar_imagem_modulo")
    copiar = inspect.getsource(OrcamentoItemCusteioPage._copiar_imagem_modulo)
    assert "pasta_imagens_modulos" in copiar
    assert "copiar_imagem_para_pasta" in copiar
