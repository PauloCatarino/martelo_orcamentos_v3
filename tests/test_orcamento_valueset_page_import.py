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
        "Padrão",
        "Ordem",
        "Origem",
        "Editado localmente",
        "Ativo",
    ]


def test_page_has_actions() -> None:
    from app.ui.pages.orcamento_valueset_page import OrcamentoValuesetPage

    for method in (
        "importar_modelo",
        "abrir_editar_linha",
        "alternar_linha_ativa",
        "carregar",
        "_get_selected_linha",
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
    assert "importar_modelo_para_orcamento" in importar

    carregar = inspect.getsource(OrcamentoValuesetPage.carregar)
    assert "OrcamentoValuesetLinhaService" in carregar
    assert "listar_linhas_da_versao" in carregar


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
