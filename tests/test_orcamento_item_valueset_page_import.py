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
    ]


def test_page_has_actions() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    for method in ("criar_do_orcamento", "importar_modelo", "carregar"):
        assert hasattr(OrcamentoItemValuesetPage, method)


def test_page_uses_service() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    criar = inspect.getsource(OrcamentoItemValuesetPage.criar_do_orcamento)
    assert "criar_a_partir_do_orcamento" in criar

    carregar = inspect.getsource(OrcamentoItemValuesetPage.carregar)
    assert "OrcamentoItemValuesetLinhaService" in carregar
    assert "listar_linhas_ativas_do_item" in carregar


def test_page_import_modelo_uses_dialog_and_service() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    importar = inspect.getsource(OrcamentoItemValuesetPage.importar_modelo)
    assert "ImportarValuesetModeloDialog" in importar

    novo = inspect.getsource(OrcamentoItemValuesetPage._importar_modelo_novo)
    assert "importar_modelo_para_item" in novo
    assert "importado" in novo


def test_page_import_modelo_confirms_replace() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    importar = inspect.getsource(OrcamentoItemValuesetPage.importar_modelo)
    assert "listar_linhas_ativas_do_item" in importar
    assert "Substituir ValueSet do Item" in importar
    assert "QMessageBox" in importar

    substituir = inspect.getsource(OrcamentoItemValuesetPage._substituir_por_modelo)
    assert "substituir_por_modelo" in substituir
    assert "desativadas" in substituir


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

    toggle = inspect.getsource(OrcamentoItemValuesetPage.alternar_linha_ativa)
    assert "Linha ativada." in toggle
    assert "Linha desativada." in toggle


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
