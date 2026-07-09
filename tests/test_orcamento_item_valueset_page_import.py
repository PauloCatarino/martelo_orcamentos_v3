"""Import checks for the budget item ValueSet page."""

from __future__ import annotations

import inspect


def test_page_imports() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    assert OrcamentoItemValuesetPage is not None


def test_page_accepts_item_id() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    signature = inspect.signature(OrcamentoItemValuesetPage)

    assert "orcamento_item_id" in signature.parameters


def test_page_headers() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    assert OrcamentoItemValuesetPage.TABLE_HEADERS == [
        "Chave",
        "Opção",
        "Nome opção",
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
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Prioridade",
        "Ordem",
        "Origem",
        "Editado localmente",
        "Ativo",
        "Operações",
    ]


def test_page_has_actions() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    for method in ("criar_do_orcamento", "importar_modelo", "carregar"):
        assert hasattr(OrcamentoItemValuesetPage, method)


def test_page_uses_service() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    criar = inspect.getsource(OrcamentoItemValuesetPage.criar_do_orcamento)
    assert "criar_a_partir_do_orcamento" in criar
    assert "listar_linhas_do_item" in criar
    assert "_perguntar_modo_criar_do_orcamento" in criar
    assert "if linhas_existentes" in criar
    assert "substituir=substituir" in criar
    assert "_verificar_precos_apos_importacao(None" in criar

    carregar = inspect.getsource(OrcamentoItemValuesetPage.carregar)
    assert "OrcamentoItemValuesetLinhaService" in carregar
    assert "listar_linhas_ativas_do_item" in carregar


def test_page_import_modelo_uses_dialog_and_service() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    importar = inspect.getsource(OrcamentoItemValuesetPage.importar_modelo)
    assert "ImportarValuesetModeloDialog" in importar
    assert "_perguntar_modo_importacao_modelo" in importar

    importar_selecionado = inspect.getsource(
        OrcamentoItemValuesetPage._importar_modelo_selecionado
    )
    assert "importar_modelo_para_item" in importar_selecionado
    assert "substituir=substituir" in importar_selecionado
    assert "_verificar_precos_apos_importacao" in importar_selecionado
    assert "importado" in importar_selecionado


def test_page_import_modelo_pergunta_substituir_ou_atualizar() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    pergunta = inspect.getsource(OrcamentoItemValuesetPage._perguntar_modo_importacao_modelo)
    assert "Substituir tudo" in pergunta
    assert "Atualizar" in pergunta
    assert "Cancelar" in pergunta
    assert "DestructiveRole" in pergunta

    importar = inspect.getsource(OrcamentoItemValuesetPage.importar_modelo)
    assert "listar_linhas_ativas_do_item" not in importar


def test_page_criar_do_orcamento_pergunta_substituir_ou_atualizar() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    pergunta = inspect.getsource(
        OrcamentoItemValuesetPage._perguntar_modo_criar_do_orcamento
    )
    assert "Substituir tudo" in pergunta
    assert "Atualizar" in pergunta
    assert "Cancelar" in pergunta
    assert "DestructiveRole" in pergunta
    assert "incluindo as editadas localmente" in pergunta

    criar = inspect.getsource(OrcamentoItemValuesetPage.criar_do_orcamento)
    assert "if linhas_existentes" in criar
    assert "escolha = self._perguntar_modo_criar_do_orcamento()" in criar
    assert "return" in criar


def test_page_import_modelo_verifica_precos_e_pode_atualizar_custeio() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    verificar = inspect.getsource(
        OrcamentoItemValuesetPage._verificar_precos_apos_importacao
    )
    assert "AtualizarPrecosValuesetDialog" in verificar
    assert "detetar_divergencias_valueset" in verificar
    assert "atualizar_precos_linhas" in verificar
    assert "atualizar_modelo_origem_por_divergencias" in verificar
    assert "_perguntar_atualizar_custeio_apos_precos" in verificar
    assert "modelo_id: int | None" in verificar
    assert "mostrar_atualizar_modelo_origem=modelo_id is not None" in verificar
    assert "dialog.atualizar_modelo_origem and modelo_id is not None" in verificar

    custeio = inspect.getsource(OrcamentoItemValuesetPage._atualizar_custeio_para_linhas)
    assert "_propagar_para_custeio" in custeio


def test_page_formats_percentages() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    source = inspect.getsource(OrcamentoItemValuesetPage._preencher)

    assert "formatar_percentagem" in source


def test_page_has_edit_and_snapshot_tools() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    for method in (
        "abrir_editar_linha",
        "copiar_dados",
        "colar_dados",
        "limpar_dados",
        "alternar_linha_ativa",
        "_abrir_menu_contexto",
        "_handle_double_click",
        "_get_selected_linha",
        "_get_selected_linhas",
    ):
        assert hasattr(OrcamentoItemValuesetPage, method)

    editar = inspect.getsource(OrcamentoItemValuesetPage.abrir_editar_linha)
    assert "OrcamentoItemValuesetLinhaDialog" in editar
    assert "editar_linha" in editar
    assert "Linha ValueSet atualizada." in editar

    copiar = inspect.getsource(OrcamentoItemValuesetPage.copiar_dados)
    assert "SNAPSHOT_FIELDS" in copiar
    assert "Dados da linha copiados." in copiar

    colar = inspect.getsource(OrcamentoItemValuesetPage.colar_dados)
    assert "aplicar_snapshot_linha" in colar
    assert "Não existem dados copiados." in colar

    limpar = inspect.getsource(OrcamentoItemValuesetPage.limpar_dados)
    assert "limpar_snapshot_linha" in limpar
    assert "Tem a certeza" in limpar
    assert "_get_selected_linhas" in limpar
    assert "commit=False" in limpar
    assert "Dados limpos em" in limpar

    toggle = inspect.getsource(OrcamentoItemValuesetPage.alternar_linha_ativa)
    assert "_get_selected_linhas" in toggle
    assert "commit=False" in toggle
    assert "Estado atualizado em" in toggle


def test_page_uses_multi_selection_for_batch_actions() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    init = inspect.getsource(OrcamentoItemValuesetPage.__init__)
    assert "ExtendedSelection" in init

    selected = inspect.getsource(OrcamentoItemValuesetPage._get_selected_linhas)
    assert "selectedRows()" in selected
    assert "seen_rows" in selected


def test_page_propaga_para_custeio() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    for method in (
        "atualizar_custeio_da_linha",
        "_propagar_para_custeio",
        "_perguntar_propagar_custeio",
    ):
        assert hasattr(OrcamentoItemValuesetPage, method)

    init = inspect.getsource(OrcamentoItemValuesetPage.__init__)
    assert "Atualizar Custeio" in init

    propagar = inspect.getsource(OrcamentoItemValuesetPage._propagar_para_custeio)
    assert "PropagarValuesetCusteioDialog" in propagar
    assert "listar_linhas_custeio_por_chave" in propagar
    assert "aplicar_valueset_item_em_linhas_custeio" in propagar
    assert "Não existem linhas de custeio associadas a esta chave ValueSet." in propagar
    assert "Linhas de custeio atualizadas:" in propagar


def test_page_carrega_coluna_operacoes() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    carregar = inspect.getsource(OrcamentoItemValuesetPage.carregar)
    assert "OrcamentoItemValuesetLinhaOperacaoService" in carregar
    assert "_operacoes_por_linha" in carregar

    preencher = inspect.getsource(OrcamentoItemValuesetPage._preencher)
    assert "_operacoes_por_linha" in preencher


def test_page_edit_lida_com_operacoes_alteradas() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    editar = inspect.getsource(OrcamentoItemValuesetPage.abrir_editar_linha)
    assert "dialog.operacoes_alteradas" in editar
    assert "Operações da linha atualizadas." in editar


def test_page_copiar_colar_com_operacoes_opt_in() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    copiar = inspect.getsource(OrcamentoItemValuesetPage.copiar_dados)
    assert "OrcamentoItemValuesetLinhaOperacaoService" in copiar
    assert "_copied_operacoes" in copiar

    colar = inspect.getsource(OrcamentoItemValuesetPage.colar_dados)
    assert "_copied_operacoes" in colar
    assert "copiar_operacoes_de" in colar
    assert "Colar também" in colar
    assert "Dados e operações colados" in colar
