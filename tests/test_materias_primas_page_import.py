"""Import checks for the MateriasPrimas page."""

from __future__ import annotations

import inspect


def test_materias_primas_page_imports() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    assert MateriasPrimasPage is not None


def test_materias_primas_page_loads_on_init() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    source_names = MateriasPrimasPage.__init__.__code__.co_names

    assert "carregar_materias_primas" in source_names


def test_materias_primas_page_table_headers() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    assert MateriasPrimasPage.TABLE_HEADERS == [
        "Ref LE",
        "Descri\u00e7\u00e3o",
        "Tipo Excel",
        "Fam\u00edlia Excel",
        "Unidade",
        "Pre\u00e7o L\u00edquido",
        "Ativo",
    ]


def test_materias_primas_page_uses_service_and_currency_formatter() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    load_source = inspect.getsource(MateriasPrimasPage.carregar_materias_primas)
    table_source = inspect.getsource(MateriasPrimasPage._preencher_tabela)

    assert "DefMateriaPrimaService" in load_source
    assert "listar_materias_primas" in load_source
    assert "format_currency" in table_source
    assert '"Sim" if materia.ativo else "N\\u00e3o"' in table_source
