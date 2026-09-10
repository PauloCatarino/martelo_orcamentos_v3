"""O adaptador de Innovus: substrato em coluna, e a célula vazia a querer dizer algo.

Ao contrário do EGGER, estes separadores não têm colunas «Esp NNmm»: é a célula
de preço vazia que diz que aquela espessura não existe naquele substrato. E a
mesma referência aparece repetida por doze substratos com preços diferentes —
se o substrato de origem sair da chave, onze delas desaparecem.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services.catalogos import innovus
from app.services.catalogos.base import FormatoInesperado

NOTAS = (
    "Tabela de Produtos INNOVUS BRANCOS (E05) — Balbino & Faustino · T-04 de 2026/08/03",
    "Painel decorativo revestido com superfície melamínica. Preços €/m², IVA não incluído.",
    "Uma linha por referência+acabamento e substrato.",
    "Agravamentos do PDF: outros acabamentos (MA, LP, TL) +0,66.",
    "PB IGN e MDF IGN CARB2 marcados (+) no PDF só existem em B4359.",
)
ESPESSURAS = ("3mm", "5mm", "6mm", "8mm", "10mm", "19mm")

CABECALHO_FIXO = [
    "id", "Referência", "Descrição", "Nome Design", "Ref. Base", "Acabamento",
    "Substrato", "Substrato Descrição", "Principal", "Grupo",
]
CABECALHO_FIM = [
    "Unidade", "Formatos", "Fornecedor", "Fabricante", "Família Produto",
    "Observações", "Tabela", "Ficheiro Origem",
]


def _escrever(
    caminho: Path,
    nome_folha: str = "BF_Innovus_Brancos_2026",
    *,
    notas: tuple[str, ...] = NOTAS,
    espessuras: tuple[str, ...] = ESPESSURAS,
    linhas: list[list[object]],
) -> Path:
    """Um separador com a forma dos dois de Innovus: notas, cabeçalho, dados.

    Cada linha vem como ``[ref, descricao, design, ref_base, acab, substrato,
    substrato_desc, principal, grupo, *precos, unidade, formatos, fornecedor,
    fabricante, familia, obs, tabela, ficheiro]``.
    """
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = nome_folha
    for nota in notas:
        worksheet.append([nota])
    worksheet.append([])

    cabecalho = (
        CABECALHO_FIXO
        + [f"Preço Tabela {e}" for e in espessuras]
        + CABECALHO_FIM
    )
    worksheet.append(cabecalho)
    for indice, linha in enumerate(linhas, start=1):
        worksheet.append([indice, *linha])
    workbook.save(caminho)
    return caminho


def _folha(nome: str = "BF_Innovus_Brancos_2026") -> innovus.FolhaInnovus:
    return innovus.FolhaInnovus(
        folha=nome,
        fornecedor="Balbino & Faustino",
        nome="Innovus Brancos E05 · Balbino & Faustino",
    )


def _linha(
    referencia: str = "B3822 MA",
    substrato: str = "PB STD",
    substrato_desc: str = "Aglomerado de partículas standard",
    precos: tuple[object, ...] = (None, None, 6.07, 6.27, 6.50, 7.94),
    **extra,
) -> list[object]:
    dados = {
        "descricao": f"Innovus {referencia} · White · {substrato_desc}",
        "design": "White",
        "ref_base": referencia.split()[0],
        "acabamento": referencia.split()[-1] if " " in referencia else None,
        "principal": "SIM",
        "grupo": None,
        "unidade": "M2",
        "formatos": "2800x2070 e 2750x1830",
        "fornecedor": "Balbino & Faustino",
        "fabricante": "Innovus",
        "familia": "Innovus Decorative Product — Brancos E05",
        "observacoes": None,
        "tabela": "T-04 · 2026/08/03",
        "ficheiro": "T04_Innovus_Brancos_2026_08_03.pdf",
    }
    dados.update(extra)
    return [
        referencia, dados["descricao"], dados["design"], dados["ref_base"],
        dados["acabamento"], substrato, substrato_desc, dados["principal"],
        dados["grupo"], *precos, dados["unidade"], dados["formatos"],
        dados["fornecedor"], dados["fabricante"], dados["familia"],
        dados["observacoes"], dados["tabela"], dados["ficheiro"],
    ]


# ---------------------------------------------------------------------------
# A célula vazia quer dizer «não existe»
# ---------------------------------------------------------------------------


def test_so_as_espessuras_com_preco_dao_artigo(tmp_path: Path) -> None:
    """Não há coluna «Esp NNmm»: é o preço em branco que diz que não existe."""
    caminho = _escrever(tmp_path / "t.xlsx", linhas=[_linha()])
    tabela = innovus.ler_folha(caminho, _folha())

    assert len(tabela.artigos) == 4
    assert tabela.com_preco == 4
    assert sorted(a.espessura_mm for a in tabela.artigos) == [
        Decimal("6"), Decimal("8"), Decimal("10"), Decimal("19")
    ]
    assert not tabela.avisos


def test_uma_linha_sem_preco_nenhum_avisa_e_nao_se_perde_a_tabela(
    tmp_path: Path,
) -> None:
    caminho = _escrever(
        tmp_path / "t.xlsx",
        linhas=[_linha(), _linha(referencia="B9999 MA", precos=(None,) * 6)],
    )
    tabela = innovus.ler_folha(caminho, _folha())

    assert len(tabela.artigos) == 4
    assert any("sem preço em espessura nenhuma" in a for a in tabela.avisos)


# ---------------------------------------------------------------------------
# O substrato de origem tem de entrar na chave
# ---------------------------------------------------------------------------


def test_a_mesma_referencia_em_dois_substratos_sao_artigos_diferentes(
    tmp_path: Path,
) -> None:
    """«PB STD» e «PB STD CARB2» têm preços diferentes e o mesmo canónico."""
    caminho = _escrever(
        tmp_path / "t.xlsx",
        linhas=[
            _linha(substrato="PB STD"),
            _linha(
                substrato="PB STD CARB2",
                substrato_desc="Aglomerado de partículas standard, baixo formaldeído (CARB2)",
                precos=(None, None, 6.50, 6.70, 6.93, 8.40),
            ),
        ],
    )
    tabela = innovus.ler_folha(caminho, _folha())

    chaves = {a.chave_natural for a in tabela.artigos}
    assert "B3822 MA|PB STD|19mm" in chaves
    assert "B3822 MA|PB STD CARB2|19mm" in chaves
    assert len(chaves) == 8

    # O canónico junta-os de propósito: é o eixo pelo qual se compara.
    assert {a.substrato for a in tabela.artigos} == {"PB STD"}
    origens = {(a.atributos or {})["substrato_origem"] for a in tabela.artigos}
    assert origens == {"PB STD", "PB STD CARB2"}


def test_um_substrato_desconhecido_avisa_e_o_artigo_fica(tmp_path: Path) -> None:
    caminho = _escrever(
        tmp_path / "t.xlsx",
        linhas=[_linha(substrato="XPTO 7", substrato_desc="Coisa nova")],
    )
    tabela = innovus.ler_folha(caminho, _folha())

    assert len(tabela.artigos) == 4
    assert {a.substrato for a in tabela.artigos} == {None}
    assert any("sem código canónico" in a for a in tabela.avisos)
    assert "B3822 MA|XPTO 7|19mm" in {a.chave_natural for a in tabela.artigos}


# ---------------------------------------------------------------------------
# O que se lê das colunas em vez de adivinhar
# ---------------------------------------------------------------------------


def test_a_data_e_o_codigo_saem_da_coluna_tabela(tmp_path: Path) -> None:
    """«T-04 · 2026/08/03» é dado; as notas do topo são prosa."""
    caminho = _escrever(tmp_path / "t.xlsx", linhas=[_linha()])
    tabela = innovus.ler_folha(caminho, _folha())

    assert tabela.referencia_tabela == "T-04"
    assert tabela.data_tabela == date(2026, 8, 3)
    # O nome não leva o ano: é ele que identifica a tabela entre versões.
    assert tabela.nome == "Innovus Brancos E05 · Balbino & Faustino"
    assert tabela.fabricante == "Innovus"
    assert "T04_Innovus_Brancos_2026_08_03.pdf" in tabela.ficheiro_origem


def test_unidade_formatos_e_familia_vem_das_colunas(tmp_path: Path) -> None:
    caminho = _escrever(tmp_path / "t.xlsx", linhas=[_linha()])
    artigo = innovus.ler_folha(caminho, _folha()).artigos[0]

    assert artigo.unidade == "M2"
    assert artigo.formatos == "2800x2070 e 2750x1830"
    assert artigo.familia == "Innovus Decorative Product — Brancos E05"
    assert artigo.nome_design == "White"
    assert artigo.acabamento == "MA"
    assert (artigo.atributos or {})["ref_base"] == "B3822"
    assert (artigo.atributos or {})["principal"] is True


def test_um_separador_com_duas_tabelas_diferentes_avisa(tmp_path: Path) -> None:
    """Duas versões de tabela no mesmo separador é engano de quem o montou."""
    caminho = _escrever(
        tmp_path / "t.xlsx",
        linhas=[
            _linha(),
            _linha(referencia="B4359 SC", tabela="T-09 · 2025/01/01"),
        ],
    )
    tabela = innovus.ler_folha(caminho, _folha())

    assert any("mistura tabelas diferentes" in a for a in tabela.avisos)


def test_a_coluna_fornecedor_que_nao_bate_avisa(tmp_path: Path) -> None:
    caminho = _escrever(
        tmp_path / "t.xlsx", linhas=[_linha(fornecedor="Outro Fornecedor")]
    )
    tabela = innovus.ler_folha(caminho, _folha())

    assert any("mas este separador é do" in a for a in tabela.avisos)


# ---------------------------------------------------------------------------
# O que rebenta
# ---------------------------------------------------------------------------


def test_sem_coluna_de_substrato_rebenta(tmp_path: Path) -> None:
    """Sem substrato a chave natural colapsa doze linhas numa — melhor parar."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "BF_Innovus_Brancos_2026"
    worksheet.append(["Tabela · T-04 de 2026/08/03"])
    worksheet.append(["id", "Referência", "Nome Design", "Preço Tabela 19mm", "Unidade"])
    worksheet.append([1, "B3822 MA", "White", 7.94, "M2"])
    caminho = tmp_path / "sem.xlsx"
    workbook.save(caminho)

    with pytest.raises(FormatoInesperado, match="substrato"):
        innovus.ler_folha(caminho, _folha())


def test_hash_estavel_e_diferente_por_separador(tmp_path: Path) -> None:
    a = _escrever(tmp_path / "a.xlsx", linhas=[_linha()])
    b = _escrever(tmp_path / "b.xlsx", linhas=[_linha()])
    c = _escrever(tmp_path / "c.xlsx", linhas=[_linha(referencia="B4359 SC")])

    hash_a = innovus.ler_folha(a, _folha()).ficheiro_hash
    assert hash_a == innovus.ler_folha(b, _folha()).ficheiro_hash
    assert hash_a != innovus.ler_folha(c, _folha()).ficheiro_hash
