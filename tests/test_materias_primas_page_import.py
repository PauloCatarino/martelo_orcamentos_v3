"""Import checks for the MateriasPrimas page."""

from __future__ import annotations

import inspect
from decimal import Decimal


def test_materias_primas_page_imports() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    assert MateriasPrimasPage is not None


def test_materias_primas_page_loads_on_init() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    source_names = MateriasPrimasPage.__init__.__code__.co_names
    init_source = inspect.getsource(MateriasPrimasPage.__init__)

    assert "carregar_materias_primas" in source_names
    assert "CampoPesquisa" in source_names
    assert "QLineEdit" not in source_names
    assert "QHeaderView.ResizeMode.Interactive" in init_source
    assert "ligar_persistencia_larguras" in init_source


def test_materias_primas_page_tem_zebra_por_celula() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    source = inspect.getsource(MateriasPrimasPage._preencher_tabela)

    assert "tema.cor_zebra(row_index)" in source
    assert "QColor" in source
    assert "resizeColumnsToContents" in source


def test_materias_primas_page_table_headers() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    assert MateriasPrimasPage.TABLE_HEADERS == [
        "Ref LE",
        "Descri\u00e7\u00e3o",
        "Tipo Excel",
        "Fam\u00edlia Excel",
        "Unidade",
        "Desp %",
        "Pre\u00e7o L\u00edquido",
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
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


def test_materias_primas_page_has_excel_import() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    assert hasattr(MateriasPrimasPage, "importar_do_excel")

    init = inspect.getsource(MateriasPrimasPage.__init__)
    assert "Atualizar P" in init  # "Atualizar Página"
    assert "Importar/Atualizar Excel" in init

    source = inspect.getsource(MateriasPrimasPage.importar_do_excel)
    assert "QMessageBox" in source
    assert "Deseja continuar?" in source
    assert "importar_materias_primas" in source
    assert "carregar_materias_primas" in source
    assert "atualizadas" in source


def test_materias_primas_page_reapplies_search_on_refresh() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    source = inspect.getsource(MateriasPrimasPage.carregar_materias_primas)

    assert "self._materias_primas = materias_primas" in source
    assert "self.aplicar_pesquisa()" in source


def test_normalize_search_text_ignores_case_and_accents() -> None:
    from app.ui.pages.materias_primas_page import normalize_search_text

    assert normalize_search_text(" DOBRADI\u00c7A Blum ") == "dobradica blum"
    assert normalize_search_text("Fam\u00edlia Excel") == "familia excel"


def test_materia_matches_search_checks_multiple_columns_and_tokens() -> None:
    from app.repositories.def_materia_prima_repository import DefMateriaPrimaResumo
    from app.ui.pages.materias_primas_page import materia_matches_search

    materia = DefMateriaPrimaResumo(
        id=1,
        ref_le="DOB0001",
        referencia_fornecedor=None,
        descricao="Dobradi\u00e7a curva",
        tipo_original_excel="FERRAGENS",
        familia_original_excel="FERRAGENS",
        tipo_martelo=None,
        familia_martelo=None,
        unidade="UND",
        preco_tabela=None,
        desconto=None,
        margem=None,
        preco_liquido=Decimal("12.34"),
        comprimento=None,
        largura=None,
        espessura=None,
        fornecedor="Blum Portugal",
        origem_dados="EXCEL",
        ativo=True,
        observacoes=None,
    )

    assert materia_matches_search(materia, "dobradica blum") is True
    assert materia_matches_search(materia, "ferragens und") is True
    assert materia_matches_search(materia, "corredica blum") is False
    assert materia_matches_search(materia, "") is True
