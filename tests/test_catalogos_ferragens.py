"""O adaptador das ferragens: quatro fornecedores lidos por configuração.

Aqui não há unpivot — uma linha é um artigo. O que muda de fornecedor para
fornecedor são os nomes das colunas e o que é preciso para identificar um
artigo, e isso está escrito como dados no ``FOLHAS``. Estes testes guardam as
três decisões que os dados obrigaram a tomar: a chave que não é só a
referência (BLUM), as repetições de propósito (Casa Trend) e os aliases.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services.catalogos import ferragens
from app.services.catalogos.base import ALIAS_EAN, ALIAS_FABRICANTE, FormatoInesperado


def _escrever(
    caminho: Path,
    nome_folha: str,
    cabecalho: list[str],
    linhas: list[list[object]],
    notas: tuple[str, ...] = (),
) -> Path:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = nome_folha
    for nota in notas:
        worksheet.append([nota])
    worksheet.append(cabecalho)
    for indice, linha in enumerate(linhas, start=1):
        worksheet.append([indice, *linha])
    workbook.save(caminho)
    return caminho


def _folha(nome: str) -> ferragens.FolhaFerragens:
    return next(f for f in ferragens.FOLHAS if f.folha == nome)


# ---------------------------------------------------------------------------
# Emuca — o caso simples, com código de barras
# ---------------------------------------------------------------------------

CAB_EMUCA = [
    "id", "Referência", "Codigo Barras", "customer code",
    "Designação ES", "Descrição PT", "und", "box", "Preço Tabela",
]


def test_emuca_le_uma_linha_por_artigo(tmp_path: Path) -> None:
    caminho = _escrever(
        tmp_path / "t.xlsx", "Emuca_2026", CAB_EMUCA,
        [
            ["1000107", "8432393100012", None, "BIS SECRETER REG D35 NI",
             "DOBRADIÇA SECRETÁRIA REG. D35 NI", "UN", 25, 1.52],
            ["1000225", "8432393100029", None, "PISTON ABATIBLE 12Kg",
             "PISTÃO ABATÍVEL 12KG 100MM GR", "UN", 20, 2.58],
        ],
        notas=("Tabela de Produtos EMUCA 2026",),
    )
    tabela = ferragens.ler_folha(caminho, _folha("Emuca_2026"))

    assert len(tabela.artigos) == 2
    artigo = tabela.artigos[0]
    assert artigo.chave_natural == "1000107"
    assert artigo.preco == Decimal("1.52")
    assert artigo.unidade == "UN"
    assert "DOBRADIÇA SECRETÁRIA" in artigo.descricao
    # A descrição leva o fabricante à frente, para a pesquisa o encontrar.
    assert artigo.descricao.startswith("Emuca · ")
    assert (artigo.atributos or {})["box"] == "25"
    assert (artigo.atributos or {})["designacao es"] == "BIS SECRETER REG D35 NI"


def test_o_codigo_de_barras_vira_alias(tmp_path: Path) -> None:
    """Sem isto a pesquisa falha para quem tem o código à frente."""
    caminho = _escrever(
        tmp_path / "t.xlsx", "Emuca_2026", CAB_EMUCA,
        [["1000107", "8432393100012", None, "BIS", "DOBRADIÇA", "UN", 25, 1.52]],
    )
    tabela = ferragens.ler_folha(caminho, _folha("Emuca_2026"))

    assert tabela.artigos[0].aliases == ((ALIAS_EAN, "8432393100012"),)


def test_uma_celula_com_dois_codigos_da_dois_aliases(tmp_path: Path) -> None:
    """O BLUM escreve «06303402 | 06303582» numa célula só."""
    assert ferragens._separar_aliases("06303402 | 06303582") == [
        "06303402", "06303582"
    ]
    assert ferragens._separar_aliases("8432393100012") == ["8432393100012"]
    assert ferragens._separar_aliases(None) == []
    assert ferragens._separar_aliases("   ") == []


# ---------------------------------------------------------------------------
# BLUM — a referência que não chega
# ---------------------------------------------------------------------------

CAB_BLUM = [
    "id", "Referência Artigo", "Código BLUM", "Descrição",
    "Preço Tabela EUR sem IVA", "Base do preço", "Família",
    "Designação BLUM completa", "Embalagem no PDF", "Componentes do conjunto",
    "Aplicação / exemplo no PDF", "Fornecedor", "Fabricante", "Tabela",
    "Página PDF", "Secção PDF", "Observações", "Ficheiro fonte",
]


def _linha_blum(descricao: str, preco: float, designacao: str, **extra) -> list[object]:
    dados = {
        "codigo": "01783069",
        "base": "Preço un.",
        "familia": "AVENTOS",
        "embalagem": None,
        "componentes": None,
        "aplicacao": None,
        "pagina": "5 | 7",
        "seccao": "BL.1.1. | BL.1.3.",
    }
    dados.update(extra)
    return [
        "22.8000", dados["codigo"], descricao, preco, dados["base"],
        dados["familia"], designacao, dados["embalagem"], dados["componentes"],
        dados["aplicacao"], "Somapil", "BLUM", "Maio 2025", dados["pagina"],
        dados["seccao"], "IVA não incluído.", "11_Tabela Blum.pdf",
    ]


def test_a_mesma_referencia_com_precos_diferentes_nao_se_perde(tmp_path: Path) -> None:
    """A 22.8000 é «Kit capas Cinza» a 9,02 e «Kit capas Branco» a 9,84."""
    caminho = _escrever(
        tmp_path / "t.xlsx", "Somapil_BLUM", CAB_BLUM,
        [
            _linha_blum("Kit capas Cinza", 9.02, "22.8000 ABD R+L V1HGIG"),
            _linha_blum("Kit capas Branco", 9.84, "22.8000 ABD R+L V1SWIG"),
        ],
        notas=("Tabela de produtos BLUM - Somapil - Maio 2025",),
    )
    tabela = ferragens.ler_folha(caminho, _folha("Somapil_BLUM"))

    assert len(tabela.artigos) == 2
    assert {a.referencia for a in tabela.artigos} == {"22.8000"}
    assert sorted(a.preco for a in tabela.artigos) == [
        Decimal("9.02"), Decimal("9.84")
    ]
    assert len({a.chave_natural for a in tabela.artigos}) == 2
    assert not tabela.avisos


def test_o_mesmo_artigo_em_seccoes_diferentes_tambem_nao_se_perde(
    tmp_path: Path,
) -> None:
    """O PDF lista a mesma dobradiça a 2,51 numa secção e a 1,00 noutra."""
    caminho = _escrever(
        tmp_path / "t.xlsx", "Somapil_BLUM", CAB_BLUM,
        [
            _linha_blum("BLUMOTION 170°", 2.51, "973A6000", seccao="BL.2.10."),
            _linha_blum("BLUMOTION 170°", 1.00, "973A6000", seccao="BL.2.23."),
        ],
    )
    tabela = ferragens.ler_folha(caminho, _folha("Somapil_BLUM"))

    assert len(tabela.artigos) == 2
    assert sorted(a.preco for a in tabela.artigos) == [Decimal("1"), Decimal("2.51")]


def test_a_pagina_do_blum_fica_nos_atributos_e_nao_na_coluna(tmp_path: Path) -> None:
    """São até dezoito páginas por artigo; a coluna ``pagina`` tem 20 caracteres."""
    paginas = "5 | 6 | 12 | 13 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 24"
    caminho = _escrever(
        tmp_path / "t.xlsx", "Somapil_BLUM", CAB_BLUM,
        [_linha_blum("Calço CLIP", 1.5, "CLIP calco", pagina=paginas)],
    )
    artigo = ferragens.ler_folha(caminho, _folha("Somapil_BLUM")).artigos[0]

    assert artigo.pagina is None
    assert (artigo.atributos or {})["pagina pdf"] == paginas


def test_o_codigo_blum_vira_alias_de_fabricante(tmp_path: Path) -> None:
    caminho = _escrever(
        tmp_path / "t.xlsx", "Somapil_BLUM", CAB_BLUM,
        [_linha_blum("Kit capas", 9.02, "ABD", codigo="06303402 | 06303582")],
    )
    artigo = ferragens.ler_folha(caminho, _folha("Somapil_BLUM")).artigos[0]

    assert artigo.aliases == (
        (ALIAS_FABRICANTE, "06303402"),
        (ALIAS_FABRICANTE, "06303582"),
    )


def test_blum_sem_preco_e_sob_consulta(tmp_path: Path) -> None:
    caminho = _escrever(
        tmp_path / "t.xlsx", "Somapil_BLUM", CAB_BLUM,
        [_linha_blum("Kit sob consulta", None, "SC")],
    )
    tabela = ferragens.ler_folha(caminho, _folha("Somapil_BLUM"))

    assert tabela.artigos[0].preco is None
    assert any("sem preço" in a for a in tabela.avisos)


def test_a_data_sai_de_um_mes_por_extenso(tmp_path: Path) -> None:
    """A Somapil e a FIWARE datam as tabelas por mês, sem dia."""
    caminho = _escrever(
        tmp_path / "t.xlsx", "Somapil_BLUM", CAB_BLUM,
        [_linha_blum("Kit", 9.02, "ABD")],
        notas=("Tabela de produtos BLUM - Somapil - Maio 2025",),
    )
    tabela = ferragens.ler_folha(caminho, _folha("Somapil_BLUM"))

    assert tabela.data_tabela == date(2025, 5, 1)


# ---------------------------------------------------------------------------
# Casa Trend — as repetições de propósito
# ---------------------------------------------------------------------------

CAB_CASATREND = [
    "id", "Referência Artigo", "Descrição", "Unidade", "Preço Tabela", "Stock",
    "Cód. Catálogo", "Família Produto", "Grupo/Secção", "Pág.", "Atributos",
    "Fornecedor", "Ficheiro Origem", "Tabela",
]


def _linha_ct(referencia: str, familia: str, preco: float = 7.21) -> list[object]:
    return [
        referencia, "Porta talheres", "UN", preco, "Stock", "01.01.01",
        familia, "Interior", "12", "Emb.: 1", "Casa Trend", "x.csv",
        "extraído 09/09/2026",
    ]


def test_a_mesma_referencia_em_varias_familias_fica_num_artigo_so(
    tmp_path: Path,
) -> None:
    """A folha diz que acontece e que o preço é coincidente."""
    caminho = _escrever(
        tmp_path / "t.xlsx", "CasaTrend_2026", CAB_CASATREND,
        [
            _linha_ct("BN520.001.001", "Cozinha Acessórios Decorativos Diversos"),
            _linha_ct("BN520.001.001", "Cozinha Acessórios Decorativos Porta Talheres"),
            _linha_ct("H.3271351", "Roupeiro Acessórios Interior Diversos"),
        ],
        notas=("Tabela CASA TREND", "Exportada de casatrend.pt (10/09/2026)."),
    )
    tabela = ferragens.ler_folha(caminho, _folha("CasaTrend_2026"))

    assert len(tabela.artigos) == 2
    juntado = next(a for a in tabela.artigos if a.referencia == "BN520.001.001")
    assert (juntado.atributos or {})["familias"] == [
        "Cozinha Acessórios Decorativos Diversos",
        "Cozinha Acessórios Decorativos Porta Talheres",
    ]
    assert any("mais do que uma família" in a for a in tabela.avisos)


def test_a_data_do_casa_trend_sai_no_formato_portugues(tmp_path: Path) -> None:
    """«10/09/2026» é dia/mês/ano, ao contrário do «2026/04/20» do EGGER."""
    caminho = _escrever(
        tmp_path / "t.xlsx", "CasaTrend_2026", CAB_CASATREND,
        [_linha_ct("BN520.001.001", "Cozinha")],
        notas=("Tabela CASA TREND", "Exportada de casatrend.pt (10/09/2026)."),
    )
    tabela = ferragens.ler_folha(caminho, _folha("CasaTrend_2026"))

    assert tabela.data_tabela == date(2026, 9, 10)


# ---------------------------------------------------------------------------
# FIWARE — a unidade que não é unidade
# ---------------------------------------------------------------------------

CAB_FIWARE = ["id", "Referência Artigo", "Descrição", "un", "Preço PVP1", "TAB"]


def test_fiware_normaliza_a_unidade_e_avisa_da_que_nao_presta(
    tmp_path: Path,
) -> None:
    """Doze linhas trazem «%» na coluna da unidade. É gralha, não um artigo."""
    caminho = _escrever(
        tmp_path / "t.xlsx", "Fiware_2026", CAB_FIWARE,
        [
            ["7225829100", "VB_JINO", "UN", 210, "1001"],
            ["7225829111", "PERFIL", "MT", 12.5, "1002"],
            ["7993810001", "SUPORTES DE PRATELEIRA", "%", 5.5, None],
        ],
        notas=("Tabela de Produtos FIWARE - Abril 2026",),
    )
    tabela = ferragens.ler_folha(caminho, _folha("Fiware_2026"))

    unidades = {a.referencia: a.unidade for a in tabela.artigos}
    assert unidades["7225829100"] == "UN"
    assert unidades["7225829111"] == "ML"   # MT é metro
    assert unidades["7993810001"] == "UN"   # o «%» não se aproveita
    assert any("unidade que não é unidade" in a for a in tabela.avisos)
    assert tabela.data_tabela == date(2026, 4, 1)


# ---------------------------------------------------------------------------
# O que rebenta
# ---------------------------------------------------------------------------


def test_sem_coluna_de_preco_rebenta(tmp_path: Path) -> None:
    caminho = _escrever(
        tmp_path / "t.xlsx", "Fiware_2026",
        ["id", "Referência Artigo", "Descrição", "un", "Custo"],
        [["7225829100", "VB_JINO", "UN", 210]],
    )
    with pytest.raises(FormatoInesperado, match="preço"):
        ferragens.ler_folha(caminho, _folha("Fiware_2026"))


def test_uma_coluna_da_chave_em_falta_rebenta(tmp_path: Path) -> None:
    """Sem a «Base do preço» o BLUM colapsava 103 linhas de preços."""
    cabecalho = [c for c in CAB_BLUM if c != "Base do preço"]
    linha = _linha_blum("Kit capas", 9.02, "ABD")
    del linha[4]  # tira a base do preço
    caminho = _escrever(tmp_path / "t.xlsx", "Somapil_BLUM", cabecalho, [linha])

    with pytest.raises(FormatoInesperado, match="chave natural"):
        ferragens.ler_folha(caminho, _folha("Somapil_BLUM"))


def test_todas_as_folhas_configuradas_tem_o_essencial() -> None:
    """Um fornecedor novo é uma entrada no ``FOLHAS`` — mas não uma vazia."""
    assert len(ferragens.FOLHAS) == 4
    for folha in ferragens.FOLHAS:
        assert folha.folha and folha.fornecedor and folha.nome
        assert folha.referencia and folha.preco
    assert len({f.folha for f in ferragens.FOLHAS}) == 4
