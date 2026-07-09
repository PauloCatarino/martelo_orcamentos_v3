"""Import checks for the budget ValueSet page."""

from __future__ import annotations

import inspect


def test_page_imports() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    assert OrcamentoValuesetPage is not None


def test_page_accepts_versao_id() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    signature = inspect.signature(OrcamentoValuesetPage)

    assert "orcamento_versao_id" in signature.parameters


def test_page_headers() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    assert OrcamentoValuesetPage.TABLE_HEADERS == [
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
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    for method in (
        "importar_modelo",
        "abrir_editar_linha",
        "alternar_linha_ativa",
        "carregar",
        "_get_selected_linha",
        "_get_selected_linhas",
        "_handle_double_click",
    ):
        assert hasattr(OrcamentoValuesetPage, method)


def test_page_edit_uses_dialog_and_service() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    source = inspect.getsource(OrcamentoValuesetPage.abrir_editar_linha)

    assert "OrcamentoValuesetLinhaDialog" in source
    assert "editar_linha" in source
    assert "Linha ValueSet atualizada." in source


def test_page_uses_service_and_dialog() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    importar = inspect.getsource(OrcamentoValuesetPage.importar_modelo)
    assert "ImportarValuesetModeloDialog" in importar
    assert "_perguntar_modo_importacao_modelo" in importar
    assert "_verificar_precos_apos_importacao" in importar
    assert "importar_modelo_para_orcamento" in importar
    assert "substituir=substituir" in importar

    carregar = inspect.getsource(OrcamentoValuesetPage.carregar)
    assert "OrcamentoValuesetLinhaService" in carregar
    assert "listar_linhas_da_versao" in carregar


def test_page_import_modelo_pergunta_substituir_ou_atualizar() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    pergunta = inspect.getsource(OrcamentoValuesetPage._perguntar_modo_importacao_modelo)

    assert "Substituir tudo" in pergunta
    assert "Atualizar" in pergunta
    assert "Cancelar" in pergunta
    assert "DestructiveRole" in pergunta


def test_page_import_modelo_verifica_precos_explicitamente() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    verificar = inspect.getsource(OrcamentoValuesetPage._verificar_precos_apos_importacao)
    assert "AtualizarPrecosValuesetDialog" in verificar
    assert "detetar_divergencias_valueset" in verificar
    assert "atualizar_precos_linhas" in verificar
    assert "atualizar_modelo_origem_por_divergencias" in verificar


def test_page_formats_percentages() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    source = inspect.getsource(OrcamentoValuesetPage._preencher)

    assert "formatar_percentagem" in source


def test_page_has_snapshot_tools() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    for method in ("copiar_dados", "colar_dados", "limpar_dados", "_abrir_menu_contexto"):
        assert hasattr(OrcamentoValuesetPage, method)

    copiar = inspect.getsource(OrcamentoValuesetPage.copiar_dados)
    assert "SNAPSHOT_FIELDS" in copiar
    assert "Dados da linha copiados." in copiar

    colar = inspect.getsource(OrcamentoValuesetPage.colar_dados)
    assert "aplicar_snapshot_linha" in colar
    assert "Não existem dados copiados." in colar

    limpar = inspect.getsource(OrcamentoValuesetPage.limpar_dados)
    assert "limpar_snapshot_linha" in limpar
    assert "Tem a certeza" in limpar
    assert "_get_selected_linhas" in limpar
    assert "commit=False" in limpar
    assert "Dados limpos em" in limpar


def test_page_uses_multi_selection_for_batch_actions() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    init = inspect.getsource(OrcamentoValuesetPage.__init__)
    assert "ExtendedSelection" in init

    selected = inspect.getsource(OrcamentoValuesetPage._get_selected_linhas)
    assert "selectedRows()" in selected
    assert "seen_rows" in selected

    toggle = inspect.getsource(OrcamentoValuesetPage.alternar_linha_ativa)
    assert "_get_selected_linhas" in toggle
    assert "commit=False" in toggle
    assert "Estado atualizado em" in toggle


def test_page_carrega_coluna_operacoes() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    carregar = inspect.getsource(OrcamentoValuesetPage.carregar)
    assert "OrcamentoValuesetLinhaOperacaoService" in carregar
    assert "_operacoes_por_linha" in carregar

    preencher = inspect.getsource(OrcamentoValuesetPage._preencher)
    assert "_operacoes_por_linha" in preencher


def test_page_edit_lida_com_operacoes_alteradas() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    editar = inspect.getsource(OrcamentoValuesetPage.abrir_editar_linha)
    assert "dialog.operacoes_alteradas" in editar
    assert "Operações da linha atualizadas." in editar


def test_page_copiar_colar_com_operacoes_opt_in() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    copiar = inspect.getsource(OrcamentoValuesetPage.copiar_dados)
    assert "OrcamentoValuesetLinhaOperacaoService" in copiar
    assert "_copied_operacoes" in copiar

    colar = inspect.getsource(OrcamentoValuesetPage.colar_dados)
    assert "_copied_operacoes" in colar
    assert "copiar_operacoes_de" in colar
    assert "Colar também" in colar
    assert "Dados e operações colados" in colar
