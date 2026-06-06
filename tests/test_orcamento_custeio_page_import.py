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
