"""O adaptador da FINSA: o separador maior, e a referência que não é única.

Duas coisas que só se descobrem olhando para os dados: o ``SUPERPAN`` não é
aglomerado nem MDF, e a referência ``688B`` com acabamento ``YOKU`` aparece
duas vezes em cada substrato, com dois decorativos e dois preços. Estes testes
guardam as duas.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services.catalogos import finsa
from app.services.catalogos.base import FormatoInesperado

NOTAS = (
    "Tabela de Produtos FINSA Balbino & Faustino - 2026",
    "Base criada a partir do PDF FI-03 Finsa Superfícies Decorativas 2026/04/06.",
    "Lógica aplicada: uma linha por Referência + Acabamento + Tipo/Substrato.",
)
ESPESSURAS = ("8mm", "10mm", "16mm", "19mm", "30mm")


def _escrever(
    caminho: Path,
    nome_folha: str = "Stock_B&F_Finsa",
    *,
    notas: tuple[str, ...] = NOTAS,
    espessuras: tuple[str, ...] = ESPESSURAS,
    linhas: list[list[object]],
) -> Path:
    """Um separador com a forma do da Finsa: pares Esp/Preço por espessura.

    Cada linha vem como ``[ref, acab, design, grupo, familia, tabela_familia,
    substrato, *(esp, preço) por espessura, fornecedor, obs]``.
    """
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = nome_folha
    for nota in notas:
        worksheet.append([nota])

    cabecalho = [
        "id", "Referência", "Acab.", "Nome Design", "Grupo",
        "Família Produto", "Tabela Família", "Tipo/Substrato",
    ]
    for espessura in espessuras:
        cabecalho += [f"Esp {espessura}", f"Preço Tabela {espessura}"]
    cabecalho += ["Fornecedor", "Observações"]
    worksheet.append(cabecalho)

    for indice, linha in enumerate(linhas, start=1):
        worksheet.append([indice, *linha])
    workbook.save(caminho)
    return caminho


def _folha() -> finsa.FolhaFinsa:
    return finsa.FolhaFinsa(
        folha="Stock_B&F_Finsa",
        fornecedor="Balbino & Faustino",
        nome="FINSA Balbino & Faustino",
    )


def _linha(
    referencia: str = "25D",
    acabamento: str = "MESURA",
    design: str = "ACACIA CHOCO",
    substrato: str = "AGL STD",
    *,
    grupo: str = "2",
    tabela_familia: str = "DUO GRUPO 2",
    precos: tuple[object, ...] = (10.68, 10.78, 11.86, 13.20, 18.72),
    fornecedor: str = "Balbino & Faustino",
) -> list[object]:
    pares: list[object] = []
    for preco in precos:
        pares += (["SIM", preco] if preco is not None else [None, None])
    return [
        referencia, acabamento, design, grupo, "DUO", tabela_familia, substrato,
        *pares, fornecedor, "Tabela FI-03 2026/04/06",
    ]


# ---------------------------------------------------------------------------
# A referência que não é única
# ---------------------------------------------------------------------------


def test_o_design_entra_na_chave_e_nada_se_perde(tmp_path: Path) -> None:
    """688B YOKU é CARYA WOOD **e** TIVOLI ASH, com preços diferentes."""
    caminho = _escrever(
        tmp_path / "t.xlsx",
        linhas=[
            _linha("688B", "YOKU", "CARYA WOOD", "AGL STD",
                   grupo="3", tabela_familia="DUO GRUPO 3",
                   precos=(11.41, 11.49, 12.57, 13.94, 19.52)),
            _linha("688B", "YOKU", "TIVOLI ASH", "AGL STD",
                   precos=(10.68, 10.78, 11.86, 13.20, 18.72)),
        ],
    )
    tabela = finsa.ler_folha(caminho, _folha())

    assert len(tabela.artigos) == 10
    chaves = {a.chave_natural for a in tabela.artigos}
    assert "688B|CARYA WOOD|YOKU|AGL STD|19mm" in chaves
    assert "688B|TIVOLI ASH|YOKU|AGL STD|19mm" in chaves

    precos = {
        a.nome_design: a.preco
        for a in tabela.artigos
        if a.espessura_mm == Decimal("19")
    }
    assert precos == {"CARYA WOOD": Decimal("13.94"), "TIVOLI ASH": Decimal("13.2")}


def test_a_referencia_ambigua_da_um_aviso(tmp_path: Path) -> None:
    """Tem todo o ar de gralha na tabela de origem — alguém tem de perguntar."""
    caminho = _escrever(
        tmp_path / "t.xlsx",
        linhas=[
            _linha("688B", "YOKU", "CARYA WOOD"),
            _linha("688B", "YOKU", "TIVOLI ASH"),
        ],
    )
    tabela = finsa.ler_folha(caminho, _folha())

    aviso = next(a for a in tabela.avisos if "nome de decorativo" in a)
    assert "688B" in aviso
    assert "CARYA WOOD" in aviso and "TIVOLI ASH" in aviso


def test_sem_ambiguidade_nao_ha_aviso(tmp_path: Path) -> None:
    caminho = _escrever(
        tmp_path / "t.xlsx",
        linhas=[_linha(), _linha(substrato="AGL HID")],
    )
    assert not finsa.ler_folha(caminho, _folha()).avisos


# ---------------------------------------------------------------------------
# Os substratos da Finsa
# ---------------------------------------------------------------------------


def test_o_substrato_de_origem_distingue_o_que_o_canonico_junta(
    tmp_path: Path,
) -> None:
    """«AGL STD» e «AGL STD EZ» são preços diferentes do mesmo ``PB STD``."""
    caminho = _escrever(
        tmp_path / "t.xlsx",
        linhas=[
            _linha(substrato="AGL STD"),
            _linha(substrato="AGL STD EZ", precos=(11.00, 11.11, 12.21, 13.60, 19.29)),
        ],
    )
    tabela = finsa.ler_folha(caminho, _folha())

    assert {a.substrato for a in tabela.artigos} == {"PB STD"}
    assert len({a.chave_natural for a in tabela.artigos}) == 10
    assert "25D|ACACIA CHOCO|MESURA|AGL STD EZ|19mm" in {
        a.chave_natural for a in tabela.artigos
    }


def test_o_superpan_nao_vira_aglomerado(tmp_path: Path) -> None:
    caminho = _escrever(
        tmp_path / "t.xlsx",
        linhas=[
            _linha(substrato="SUPERPAN STD"),
            _linha(substrato="SUPERPAN STAR", precos=(None, None, None, None, 29.92)),
        ],
    )
    tabela = finsa.ler_folha(caminho, _folha())

    assert {a.substrato for a in tabela.artigos} == {"SUPERPAN STD", "SUPERPAN STAR"}


# ---------------------------------------------------------------------------
# O resto
# ---------------------------------------------------------------------------


def test_espessura_sem_marca_nem_preco_fica_de_fora(tmp_path: Path) -> None:
    """Na Finsa a maioria das células está vazia: 15 colunas, poucas cheias."""
    caminho = _escrever(
        tmp_path / "t.xlsx",
        linhas=[_linha(precos=(None, 13.36, 15.06, 16.63, None))],
    )
    tabela = finsa.ler_folha(caminho, _folha())

    assert sorted(a.espessura_mm for a in tabela.artigos) == [
        Decimal("10"), Decimal("16"), Decimal("19")
    ]
    assert not tabela.avisos


def test_o_grupo_e_a_tabela_familia_e_nao_o_numero_solto(tmp_path: Path) -> None:
    """«DUO GRUPO 2» diz de que tabela do PDF saiu a linha; «2» não diz nada."""
    caminho = _escrever(tmp_path / "t.xlsx", linhas=[_linha()])
    artigo = finsa.ler_folha(caminho, _folha()).artigos[0]

    assert artigo.grupo == "DUO GRUPO 2"
    assert artigo.familia == "DUO"
    assert artigo.acabamento == "MESURA"
    assert (artigo.atributos or {})["substrato_origem"] == "AGL STD"


def test_a_data_e_o_codigo_saem_das_notas(tmp_path: Path) -> None:
    caminho = _escrever(tmp_path / "t.xlsx", linhas=[_linha()])
    tabela = finsa.ler_folha(caminho, _folha())

    assert tabela.referencia_tabela == "FI-03"
    assert tabela.data_tabela == date(2026, 4, 6)
    assert tabela.nome == "FINSA Balbino & Faustino"
    assert tabela.fabricante == "FINSA"
    assert tabela.unidade_preco == "M2"


def test_a_coluna_fornecedor_que_nao_bate_avisa(tmp_path: Path) -> None:
    caminho = _escrever(
        tmp_path / "t.xlsx", linhas=[_linha(fornecedor="Outro Fornecedor")]
    )
    assert any(
        "mas este separador é do" in a
        for a in finsa.ler_folha(caminho, _folha()).avisos
    )


def test_sem_coluna_de_substrato_rebenta(tmp_path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Stock_B&F_Finsa"
    worksheet.append(["Tabela FINSA FI-03 2026/04/06"])
    worksheet.append(["id", "Referência", "Acab.", "Nome Design", "Esp 19mm", "Preço Tabela 19mm"])
    worksheet.append([1, "25D", "MESURA", "ACACIA CHOCO", "SIM", 13.20])
    caminho = tmp_path / "sem.xlsx"
    workbook.save(caminho)

    with pytest.raises(FormatoInesperado, match="substrato"):
        finsa.ler_folha(caminho, _folha())
