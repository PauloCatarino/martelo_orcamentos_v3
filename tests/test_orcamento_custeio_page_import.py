"""Import checks for the Orcamento Custeio page."""

from __future__ import annotations

import inspect


def test_orcamento_custeio_page_imports() -> None:
    from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage

    assert OrcamentoCusteioPage is not None


def test_orcamento_custeio_page_accepts_versao_id() -> None:
    from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage

    signature = inspect.signature(OrcamentoCusteioPage)

    assert "orcamento_versao_id" in signature.parameters


def test_orcamento_custeio_page_headers() -> None:
    from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage

    assert OrcamentoCusteioPage.TABLE_HEADERS == [
        "Item",
        "Tipo",
        "Código",
        "Descrição",
        "Matéria-prima",
        "Unidade",
        "Quantidade",
        "Comp",
        "Larg",
        "Esp",
        "Área m²",
        "ML orla fina",
        "ML orla grossa",
        "Custo unitário",
        "Custo total",
        "Preço unitário",
        "Preço total",
        "Editado localmente",
        "Ativo",
    ]


def test_orcamento_custeio_page_loads_on_init() -> None:
    from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage

    source_names = OrcamentoCusteioPage.__init__.__code__.co_names

    assert "carregar" in source_names


def test_orcamento_custeio_page_uses_service() -> None:
    from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage

    source = inspect.getsource(OrcamentoCusteioPage.carregar)

    assert "OrcamentoItemCusteioLinhaService" in source
    assert "listar_linhas_da_versao" in source


def test_orcamento_custeio_page_formats_lines() -> None:
    from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage

    source = inspect.getsource(OrcamentoCusteioPage._preencher)

    assert "get_custeio_linha_type_label" in source
    assert "format_currency" in source


def test_orcamento_custeio_page_has_line_actions() -> None:
    from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage

    for method in (
        "abrir_nova_linha",
        "abrir_editar_linha",
        "alternar_linha_ativa",
        "_get_selected_linha",
    ):
        assert hasattr(OrcamentoCusteioPage, method)


def test_orcamento_custeio_page_line_actions_use_service_and_dialog() -> None:
    from app.ui.pages.orcamento_custeio_page import OrcamentoCusteioPage

    nova = inspect.getsource(OrcamentoCusteioPage.abrir_nova_linha)
    assert "CusteioLinhaManualDialog" in nova
    assert "criar_linha_manual" in nova
    assert "override_manual=True" in nova

    editar = inspect.getsource(OrcamentoCusteioPage.abrir_editar_linha)
    assert "editar_linha" in editar
    assert "editado_localmente=True" in editar

    toggle = inspect.getsource(OrcamentoCusteioPage.alternar_linha_ativa)
    assert "ativar_linha" in toggle
    assert "desativar_linha" in toggle
    assert "QMessageBox" in toggle
