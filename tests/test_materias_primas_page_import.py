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

    cabecalhos = MateriasPrimasPage.TABLE_HEADERS

    # A tabela tem tudo o que o catálogo guarda; cada utilizador escolhe
    # depois o que quer ver no botão "Colunas...".
    assert cabecalhos[0] == "Ref LE"
    assert cabecalhos[1] == "Descrição"
    assert cabecalhos[-1] == "Ativo"
    for esperada in (
        "Tipo preço", "Preço tabela", "Desc %", "Mrg %", "Desp %",
        "Preço Líquido", "Último preço", "Stock", "Fornecedor",
        "Ref. fornecedor", "Fabricante", "Cor", "Ref. PHC", "Orla 0.4", "Orla 1.0",
        "Comp MP", "Larg MP", "Esp MP", "Observações", "Criado por",
        "Alterado por",
    ):
        assert esperada in cabecalhos

    assert len(cabecalhos) == len(set(cabecalhos))

    # As colunas dos avisos têm de continuar a apontar para as certas.
    assert cabecalhos[MateriasPrimasPage.COLUNA_PRECO_LIQUIDO] == "Preço Líquido"
    assert cabecalhos[MateriasPrimasPage.COLUNA_ULTIMO_PRECO] == "Último preço"

    # As escondidas por defeito existem mesmo, e as principais ficam à vista.
    assert set(MateriasPrimasPage.COLUNAS_OCULTAS_POR_DEFEITO).issubset(cabecalhos)
    for visivel in ("Ref LE", "Descrição", "Preço Líquido", "Ativo"):
        assert visivel not in MateriasPrimasPage.COLUNAS_OCULTAS_POR_DEFEITO


def test_materias_primas_page_tem_botao_de_colunas() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    init = inspect.getsource(MateriasPrimasPage.__init__)

    assert "Colunas" in init
    assert "ligar_menu_colunas" in init
    assert "COLUNAS_OCULTAS_POR_DEFEITO" in init


def test_uma_linha_tem_um_valor_por_coluna() -> None:
    """Se as duas listas saírem de sincronia, a tabela mostra valores trocados."""
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    fonte = inspect.getsource(MateriasPrimasPage._preencher_tabela)
    bloco = fonte[fonte.index("values = ["):fonte.index("]", fonte.index("values = ["))]

    assert bloco.count(",") == len(MateriasPrimasPage.TABLE_HEADERS)


def test_materias_primas_page_uses_service_and_currency_formatter() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    load_source = inspect.getsource(MateriasPrimasPage.carregar_materias_primas)
    table_source = inspect.getsource(MateriasPrimasPage._preencher_tabela)

    assert "DefMateriaPrimaService" in load_source
    assert "listar_materias_primas" in load_source
    assert "format_currency" in inspect.getsource(MateriasPrimasPage._texto_preco)
    # A coluna "Ativo" diz Sim/Não (sem depender de como o acento está escrito).
    assert '"Sim" if materia.ativo else' in table_source


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


def test_o_excel_deixou_de_ser_fonte_do_catalogo() -> None:
    """O V3 e o dono: importar do Excel escreveria por cima do que aqui se edita."""
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    for saiu in (
        "importar_do_excel",
        "verificar_excel",
        "abrir_excel",
        "_analisar_excel",
    ):
        assert not hasattr(MateriasPrimasPage, saiu)

    init = inspect.getsource(MateriasPrimasPage.__init__)
    assert "Importar" not in init
    assert "Verificar Excel" not in init


def test_pagina_exporta_para_excel() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    assert hasattr(MateriasPrimasPage, "exportar_excel")

    init = inspect.getsource(MateriasPrimasPage.__init__)
    assert "Exportar Excel" in init

    fonte = inspect.getsource(MateriasPrimasPage.exportar_excel)
    assert "getSaveFileName" in fonte
    assert "exportar_materias_primas" in fonte
    # A exportacao le a tabela; nunca escreve na base de dados.
    assert "SessionLocal" not in fonte


def test_colunas_podem_ser_arrastadas_e_a_ordem_fica_guardada() -> None:
    from app.ui.pages.materias_primas_page import MateriasPrimasPage

    init = inspect.getsource(MateriasPrimasPage.__init__)

    assert "guardar_ordem=True" in init
