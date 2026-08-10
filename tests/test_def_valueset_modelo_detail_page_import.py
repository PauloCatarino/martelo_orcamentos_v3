"""Import checks for the ValueSet model detail page."""

from __future__ import annotations

import inspect


def test_page_imports() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    assert DefValuesetModeloDetailPage is not None


def test_page_accepts_modelo_and_on_back() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    signature = inspect.signature(DefValuesetModeloDetailPage)

    assert "modelo" in signature.parameters
    assert "on_back" in signature.parameters
    assert "on_modelo_duplicado" in signature.parameters


def test_cabecalho_do_modelo_compacta_metadados_na_horizontal() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    init = inspect.getsource(DefValuesetModeloDetailPage.__init__)
    assert "info_layout = QHBoxLayout()" in init
    assert "info_layout.addWidget(titulo)" in init
    assert "info_layout.addWidget(conteudo)" in init
    assert "conteudo.setToolTip(value)" in init
    assert "QFormLayout" not in init


def test_detalhe_do_modelo_tem_pesquisa_dinamica_de_linhas() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    init = inspect.getsource(DefValuesetModeloDetailPage.__init__)
    filtrar = inspect.getsource(DefValuesetModeloDetailPage._aplicar_filtro_linhas)
    assert "CampoPesquisa" in init
    assert "pesquisa_mudou.connect(self._aplicar_filtro_linhas)" in init
    assert "setToolTip" in init
    assert "filtrar_linhas_valueset_modelo" in filtrar
    assert "_operacoes_por_linha" in filtrar


def test_page_line_headers() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    assert DefValuesetModeloDetailPage.LINHA_HEADERS == [
        "Chave",
        "Opção",
        "Ref LE",
        "Descrição orçamento",
        "Unidade",
        "Preço tabela",
        "Margem %",
        "Desconto %",
        "Preço líquido",
        "Desp %",
        "Tipo",
        "Família",
        "Prioridade",
        "Ordem",
        "Editado localmente",
        "Ativo",
        "Operações",
    ]


def test_page_has_line_actions() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    for method in (
        "abrir_nova_linha",
        "abrir_editar_linha",
        "alternar_linha_ativa",
        "carregar_linhas",
        "verificar_precos",
        "gravar_modelo_como",
        "_get_selected_linha",
        "_abrir_dialog_criar_linha",
        "_criar_linha_from_form_data",
        "_criar_modelo_data_from_form_data",
        "_modelo_error_message",
        "copiar_dados",
        "colar_dados",
        "_abrir_menu_contexto",
        "_instalar_atalhos_clipboard",
        "propagar_operacoes",
    ):
        assert hasattr(DefValuesetModeloDetailPage, method)


def test_page_copia_conteudo_para_linha_existente_com_atalhos_e_menu() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    init = inspect.getsource(DefValuesetModeloDetailPage.__init__)
    assert "copy_button" in init
    assert "paste_button" in init
    assert "setToolTip" in init
    assert "CustomContextMenu" in init
    assert "_instalar_atalhos_clipboard" in init

    atalhos = inspect.getsource(DefValuesetModeloDetailPage._instalar_atalhos_clipboard)
    assert "QKeySequence.StandardKey.Copy" in atalhos
    assert "QKeySequence.StandardKey.Paste" in atalhos
    assert "WidgetShortcut" in atalhos

    copiar = inspect.getsource(DefValuesetModeloDetailPage.copiar_dados)
    assert "copiar_snapshot_linha" in copiar
    assert "listar_operacoes_da_linha" in copiar

    colar = inspect.getsource(DefValuesetModeloDetailPage.colar_dados)
    assert "aplicar_snapshot_linha" in colar
    assert "substituir_operacoes_de" in colar
    assert "commit=False" in colar
    assert "session.rollback()" in colar
    assert "session.commit()" in colar
    assert "identidade da linha de destino" in colar

    menu = inspect.getsource(DefValuesetModeloDetailPage._abrir_menu_contexto)
    assert "Copiar Dados (Ctrl+C)" in menu
    assert "Colar Dados (Ctrl+V)" in menu


def test_page_propaga_operacoes_com_dialogo_e_servico_controlado() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    init = inspect.getsource(DefValuesetModeloDetailPage.__init__)
    assert "propagate_operations_button" in init
    assert "Propagar Operações" in init
    assert "setToolTip" in init

    propagar = inspect.getsource(DefValuesetModeloDetailPage.propagar_operacoes)
    assert "DefValuesetOperacaoPropagacaoService" in propagar
    assert "preparar_contexto" in propagar
    assert "PropagarOperacoesValuesetModeloDialog" in propagar
    assert "dialog.selected_ids" in propagar
    assert ".executar(" in propagar
    assert "Propagação cancelada" in propagar


def test_page_uses_line_service_and_dialog() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    criar_dialog = inspect.getsource(DefValuesetModeloDetailPage._abrir_dialog_criar_linha)
    criar_linha = inspect.getsource(DefValuesetModeloDetailPage._criar_linha_from_form_data)
    assert "DefValuesetModeloLinhaDialog" in criar_dialog
    assert "criar_linha" in criar_linha
    assert "editar_linha" not in criar_linha
    assert "prioridade=form_data.prioridade" in criar_linha

    carregar = inspect.getsource(DefValuesetModeloDetailPage.carregar_linhas)
    assert "DefValuesetModeloLinhaService" in carregar
    assert "listar_linhas_do_modelo" in carregar
    assert "DefValuesetModeloLinhaOperacaoService" in carregar
    assert "listar_operacoes_ativas_da_linha" in carregar
    assert "DefOperacaoService" in carregar

    verificar = inspect.getsource(DefValuesetModeloDetailPage.verificar_precos)
    assert "AtualizarPrecosValuesetDialog" in verificar
    assert "detetar_divergencias_valueset" in verificar
    assert "atualizar_precos_linhas" in verificar


def test_page_detail_nao_mostra_gravar_modelo_como_redundante() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    init = inspect.getsource(DefValuesetModeloDetailPage.__init__)
    assert "save_as_button" not in init

    source = inspect.getsource(DefValuesetModeloDetailPage.gravar_modelo_como)
    assert "DefValuesetModeloDialog" in source
    assert "on_save_as=handle_save_as" in source
    assert "duplicar_modelo" in source
    assert "_criar_modelo_data_from_form_data" in source
    assert "Já existe um modelo com esse código." in source
    assert "on_modelo_duplicado" in source
    assert "Modelo gravado como" in source


def test_page_edit_line_has_save_as_create_flow() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    source = inspect.getsource(DefValuesetModeloDetailPage.abrir_editar_linha)

    assert "on_save_as=handle_save_as" in source
    # A opção nova leva as operações da linha de onde foi copiada.
    assert "copiar_operacoes_de=linha.id" in source
    assert "Linha gravada como nova op" in source


def test_page_formats_percentages() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    source = inspect.getsource(DefValuesetModeloDetailPage._preencher)

    assert "formatar_percentagem" in source
    assert "_operacoes_por_linha" in source
    assert "preparar_linhas_valueset" in source
    assert "aplicar_estilo_item_valueset" in source
    assert "texto_chave_valueset" in source


def test_page_valueset_visual_helper_e_menu_colunas() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    init = inspect.getsource(DefValuesetModeloDetailPage.__init__)

    assert "setAlternatingRowColors(False)" in init
    assert "configurar_tabela_valueset" in init
    assert '"valueset_modelo"' in init


def test_page_colunas_redimensionaveis_com_seed() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    init = inspect.getsource(DefValuesetModeloDetailPage.__init__)
    assert "QHeaderView.ResizeMode.Interactive" in init
    assert "setStretchLastSection(False)" in init
    assert '"valueset_modelo"' in init

    preencher = inspect.getsource(DefValuesetModeloDetailPage._preencher)
    assert "resizeColumnsToContents" in preencher
    assert "_larguras_iniciais_aplicadas" in preencher
def test_linhas_modelo_ocultam_inativas_por_defeito() -> None:
    import inspect
    from app.ui.pages.def_valueset_modelo_detail_page import DefValuesetModeloDetailPage

    init = inspect.getsource(DefValuesetModeloDetailPage.__init__)
    filtrar = inspect.getsource(DefValuesetModeloDetailPage._aplicar_filtro_linhas)
    assert "mostrar_inativas_check" in init
    assert "if linha.ativo" in filtrar
