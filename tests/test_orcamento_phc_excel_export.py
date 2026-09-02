"""O Excel do orçamento no formato que o PHC importa.

Duas coisas que o PHC exige e que aqui se garantem: o ficheiro é mesmo um
``.xls`` (não um ``.xlsx`` com outro nome), e nenhuma linha da designação passa
dos 55 caracteres — o que passa disso o PHC corta em silêncio.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.domain.texto_phc import MAX_CARACTERES_LINHA
from app.services.orcamento_phc_excel_export import (
    gerar_excel_phc,
    linhas_do_item,
)

#: Os primeiros bytes de um ficheiro OLE (o formato do .xls). Um .xlsx começa
#: por "PK" — é assim que se distingue um dos outros sem abrir o Excel.
ASSINATURA_XLS = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

COL_REF, COL_REFERENCIA, COL_DESIGNACAO = 0, 1, 2
COL_ALTURA, COL_LARGURA, COL_PROF, COL_QTD, COL_UND, COL_VENDA = 3, 4, 5, 6, 7, 8


def _items() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            codigo="RP_01(A)",
            # Título + linha "- " + linha "* " (linha vazia ignorada).
            descricao=(
                "Movel de cozinha em termolaminado\n"
                "- Puxador TIC-TAC\n"
                "\n"
                "* Montado em obra"
            ),
            altura=Decimal("720"),
            largura=Decimal("600"),
            profundidade=Decimal("560"),
            quantidade=Decimal("2"),
            unidade="und",
            preco_unitario=Decimal("1191.62"),
        ),
        SimpleNamespace(
            codigo="RP_02",
            descricao=None,
            altura=None,
            largura=Decimal("800"),
            profundidade=None,
            quantidade=Decimal("1"),
            unidade="",
            preco_unitario=Decimal("50"),
        ),
    ]


def test_o_ficheiro_e_mesmo_um_xls(tmp_path) -> None:
    """Um .xlsx renomeado para .xls é recusado pelo PHC."""
    output = tmp_path / "260001_01_PHC.xls"
    orcamento = SimpleNamespace(num_orcamento="260001", numero_versao=1)

    resultado = gerar_excel_phc(output, orcamento=orcamento, items=_items())

    assert resultado == output
    assert output.exists()
    assert output.read_bytes()[:8] == ASSINATURA_XLS


def test_linha_principal_leva_o_item_todo() -> None:
    linhas = linhas_do_item(_items()[0])
    principal = linhas[0]

    assert principal[COL_REF] == "RP_01(A)"
    assert principal[COL_REFERENCIA] == "MOB"
    assert principal[COL_DESIGNACAO].startswith("COMP. MOB. - ")
    assert "MOVEL DE COZINHA EM TERMOLAMINADO" in principal[COL_DESIGNACAO]
    assert principal[COL_ALTURA] == 720
    assert principal[COL_LARGURA] == 600
    assert principal[COL_PROF] == 560
    assert principal[COL_QTD] == 2
    # "und" -> "un".
    assert principal[COL_UND] == "un"
    # Venda como TEXTO com vírgula decimal, para o PHC ler tal e qual.
    assert principal[COL_VENDA] == "1191,62"
    assert isinstance(principal[COL_VENDA], str)


def test_as_linhas_da_descricao_so_levam_a_designacao() -> None:
    linhas = linhas_do_item(_items()[0])
    extras = linhas[1:]

    assert [linha[COL_DESIGNACAO] for linha in extras] == [
        "- Puxador TIC-TAC",
        "* Montado em obra",
    ]
    for linha in extras:
        assert linha[COL_REF] == ""
        assert linha[COL_VENDA] is None
    # A linha vazia da descrição não gera linha nenhuma.
    assert len(linhas) == 3


def test_item_sem_descricao_e_sem_unidade() -> None:
    linhas = linhas_do_item(_items()[1])

    assert len(linhas) == 1
    assert linhas[0][COL_DESIGNACAO] == "COMP. MOB. -"
    assert linhas[0][COL_UND] == "un"
    assert linhas[0][COL_ALTURA] is None
    assert linhas[0][COL_LARGURA] == 800
    assert linhas[0][COL_VENDA] == "50,00"


def test_nenhuma_linha_passa_dos_55_caracteres() -> None:
    """O que passa de 55 o PHC corta — e ninguém dá por isso."""
    item = SimpleNamespace(
        codigo="RP_01",
        descricao=(
            "ROUPEIRO PORTAS ABRIR C/ INTERIOR EM AGL MLM B3822 ASM "
            "19/16/8MM E FRENTES EM AGL MLM BRANCO B3768 MA 19MM\n"
            "- 1 BLOCO DE 3 GAVETAS C/ CORREDIÇA EXTRAÇÃO TOTAL E TRAVÃO "
            "AMORTECIDO NAS DUAS PONTAS"
        ),
        altura=Decimal("2540"),
        largura=Decimal("900"),
        profundidade=Decimal("550"),
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("428.83"),
    )

    linhas = linhas_do_item(item)
    designacoes = [linha[COL_DESIGNACAO] for linha in linhas]

    assert all(len(texto) <= MAX_CARACTERES_LINHA for texto in designacoes)
    # Partiu-se mesmo: o título sozinho já não cabia numa linha.
    assert len(linhas) > 2
    # E não se perdeu nada pelo caminho.
    assert "B3768 MA 19MM" in " ".join(designacoes)
    assert "AMORTECIDO NAS DUAS PONTAS" in " ".join(designacoes)
    # As continuações continuam a ser linhas só de designação.
    for linha in linhas[1:]:
        assert linha[COL_REF] == ""
        assert linha[COL_QTD] is None
