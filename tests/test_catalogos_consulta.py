"""A leitura dos catálogos da base, para a Pesquisa IA.

O que estes testes guardam é o caminho de volta da Fase 2: os adaptadores
desdobraram cada referência numa linha por espessura, e aqui volta-se a
dobrá-las. Um redobramento mal feito não rebenta — perde um preço e cala-se,
que é o pior que podia acontecer a uma tabela de preços.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.catalogos import SCHEMA_CATALOGOS, catalogos_metadata
from app.models.catalogos import FornTabelaPreco
from app.services.catalogos.base import ArtigoCatalogo, TabelaCatalogo
from app.services.catalogos.consulta import (
    CHAVE_PRECO_UNITARIO,
    assinatura_catalogos,
    esta_vazia,
    listar_artigos,
    listar_referencias,
)
from app.services.catalogos.importador import importar


@pytest.fixture()
def session():
    """SQLite em memória com a base dos catálogos anexada (ver a Fase 1)."""
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _anexar(dbapi_connection, _record):  # noqa: ANN001
        dbapi_connection.execute(f"ATTACH DATABASE ':memory:' AS {SCHEMA_CATALOGOS}")

    catalogos_metadata.create_all(engine)
    try:
        with Session(engine) as db:
            yield db
    finally:
        engine.dispose()


def _placa(espessura: str, preco: str, **extra) -> ArtigoCatalogo:
    dados = dict(
        chave_natural=f"F037|ST76|PB STD|{espessura}",
        referencia="F037",
        descricao=f"EGGER F037 ST76 · Travertino Taormina · {espessura}",
        unidade="M2",
        nome_design="Travertino Taormina",
        familia="Eurodekor",
        seccao="Eurodekor Aglomerado revestido",
        grupo="Grupo 8",
        fabricante="EGGER",
        substrato="PB STD",
        espessura_mm=Decimal(espessura.replace("mm", "")),
        acabamento="ST76",
        preco=Decimal(preco),
        atributos={
            "folha": "Stock_B&F_Egger",
            "espessura": espessura,
            "tipo_produto": "Eurodekor Aglomerado revestido",
            "st": "ST76",
        },
    )
    dados.update(extra)
    return ArtigoCatalogo(**dados)


def _ferragem(**extra) -> ArtigoCatalogo:
    dados = dict(
        chave_natural="22.8000|Kit capas Cinza|Preço un.",
        referencia="22.8000",
        descricao="BLUM · Kit capas Cinza",
        unidade="UN",
        familia="DOBRADIÇAS E COMPLEMENTOS",
        seccao="BL.1.1.",
        grupo="Preço un.",
        fabricante="BLUM",
        preco=Decimal("9.02"),
        atributos={"folha": "Somapil_BLUM"},
    )
    dados.update(extra)
    return ArtigoCatalogo(**dados)


def _tabela(*artigos, **extra) -> TabelaCatalogo:
    dados = dict(
        fornecedor="Balbino & Faustino",
        fabricante="EGGER",
        nome="EGGER Balbino & Faustino",
        data_tabela=date(2026, 4, 20),
        ficheiro_origem="12_Placas_Referencias_COMPLETO.xlsx#Stock_B&F_Egger",
        ficheiro_hash="a" * 64,
        unidade_preco="M2",
        artigos=artigos,
    )
    dados.update(extra)
    return TabelaCatalogo(**dados)


# ---------------------------------------------------------------------------
# Um artigo por linha
# ---------------------------------------------------------------------------


def test_a_base_vazia_diz_que_esta_vazia(session: Session) -> None:
    assert esta_vazia(session) is True
    assert listar_artigos(session) == []
    assert listar_referencias(session) == []


def test_listar_artigos_traz_o_preco_da_tabela(session: Session) -> None:
    importar(session, _tabela(_placa("8mm", "17.98"), _placa("19mm", "21.02")))
    session.commit()

    artigos = listar_artigos(session)
    assert [artigo.espessura for artigo in artigos] == ["8mm", "19mm"]
    assert [artigo.preco for artigo in artigos] == [
        Decimal("17.98"),
        Decimal("21.02"),
    ]
    assert {artigo.unidade for artigo in artigos} == {"M2"}
    assert {artigo.folha for artigo in artigos} == {"Stock_B&F_Egger"}
    assert {artigo.tabela for artigo in artigos} == {"EGGER Balbino & Faustino"}
    assert {artigo.data_tabela for artigo in artigos} == {date(2026, 4, 20)}


def test_o_tipo_do_egger_e_o_texto_inteiro_e_nao_a_primeira_palavra(
    session: Session,
) -> None:
    """A ``familia`` do Egger é «Eurodekor»; a coluna do Excel dizia mais."""
    importar(session, _tabela(_placa("19mm", "21.02")))
    session.commit()

    assert listar_artigos(session)[0].tipo == "Eurodekor Aglomerado revestido"


def test_uma_tabela_desativada_deixa_de_ser_lida(session: Session) -> None:
    importar(session, _tabela(_placa("19mm", "21.02")))
    session.commit()
    tabela = session.scalars(select(FornTabelaPreco)).one()
    tabela.ativa = False
    session.commit()

    assert listar_artigos(session) == []
    assert esta_vazia(session) is True


# ---------------------------------------------------------------------------
# O redobramento das espessuras
# ---------------------------------------------------------------------------


def test_as_espessuras_da_mesma_referencia_voltam_a_uma_linha(
    session: Session,
) -> None:
    importar(
        session,
        _tabela(
            _placa("8mm", "17.98"), _placa("19mm", "21.02"), _placa("25mm", "30.50")
        ),
    )
    session.commit()

    linhas = listar_referencias(session)
    assert len(linhas) == 1
    linha = linhas[0]
    assert linha.folha == "Stock_B&F_Egger"
    assert linha.referencia == "F037"
    assert linha.st_acab == "ST76"
    assert linha.nome_design == "Travertino Taormina"
    assert linha.grupo == "Grupo 8"
    assert linha.tipo == "Eurodekor Aglomerado revestido"
    assert linha.fornecedor == "Balbino & Faustino"
    assert linha.precos == {
        "8mm": "17,98 €",
        "19mm": "21,02 €",
        "25mm": "30,50 €",
    }


def test_o_substrato_de_origem_separa_linhas_da_mesma_referencia(
    session: Session,
) -> None:
    """``AGL STD`` e ``AGL STD EZ`` são preços diferentes do mesmo desenho."""
    normal = _placa(
        "19mm",
        "21.02",
        chave_natural="008|MESURA|AGL STD|19mm",
        atributos={
            "folha": "Stock_B&F_Finsa",
            "espessura": "19mm",
            "substrato_origem": "AGL STD",
        },
    )
    hidrofugo = _placa(
        "19mm",
        "27.40",
        chave_natural="008|MESURA|AGL STD EZ|19mm",
        atributos={
            "folha": "Stock_B&F_Finsa",
            "espessura": "19mm",
            "substrato_origem": "AGL STD EZ",
        },
    )
    importar(session, _tabela(normal, hidrofugo))
    session.commit()

    linhas = listar_referencias(session)
    assert len(linhas) == 2
    assert sorted(linha.precos["19mm"] for linha in linhas) == [
        "21,02 €",
        "27,40 €",
    ]


def test_a_juncao_e_pela_chave_natural_e_nao_pelo_que_se_ve(
    session: Session,
) -> None:
    """O BLUM distingue artigos por coisas que a tabela não mostra.

    A mesma referência, a mesma descrição e o mesmo preço-base, em secções
    diferentes do PDF, são artigos diferentes com preços diferentes. Juntar
    pelos campos visíveis fazia desaparecer um dos dois.
    """
    barato = _ferragem(
        chave_natural="70T3550|Dobradiça|Preço un.|BL.2.1.|70T3550 CLIP",
        preco=Decimal("2.51"),
    )
    caro = _ferragem(
        chave_natural="70T3550|Dobradiça|Preço un.|BL.9.4.|70T3550 CLIP",
        preco=Decimal("1.00"),
    )
    importar(
        session,
        _tabela(barato, caro, fornecedor="Somapil", fabricante="BLUM", nome="BLUM"),
    )
    session.commit()

    linhas = listar_referencias(session)
    assert len(linhas) == 2
    assert sorted(linha.precos[CHAVE_PRECO_UNITARIO] for linha in linhas) == [
        "1,00 €",
        "2,51 €",
    ]


def test_uma_ferragem_tem_preco_na_coluna_do_preco_unitario(
    session: Session,
) -> None:
    importar(
        session,
        _tabela(_ferragem(), fornecedor="Somapil", fabricante="BLUM", nome="BLUM"),
    )
    session.commit()

    linha = listar_referencias(session)[0]
    assert linha.precos == {CHAVE_PRECO_UNITARIO: "9,02 €"}
    assert linha.st_acab == ""
    # Sem ``nome_design``, a descrição é o que resta para se ler.
    assert linha.nome_design == "BLUM · Kit capas Cinza"
    assert linha.tipo == "DOBRADIÇAS E COMPLEMENTOS"
    assert linha.grupo == "Preço un."


def test_um_artigo_sem_preco_aparece_na_mesma(session: Session) -> None:
    """Sob consulta é uma resposta; desaparecer da tabela não é."""
    importar(
        session,
        _tabela(
            _ferragem(preco=None),
            fornecedor="Somapil",
            fabricante="BLUM",
            nome="BLUM",
        ),
    )
    session.commit()

    linha = listar_referencias(session)[0]
    assert linha.referencia == "22.8000"
    assert linha.precos == {}


def test_a_espessura_sai_do_espessura_mm_quando_os_atributos_nao_a_tem(
    session: Session,
) -> None:
    """Atributos escritos por uma versão antiga não podem calar o preço."""
    importar(
        session,
        _tabela(
            _placa(
                "19mm",
                "21.02",
                chave_natural="F037|ST76|PB STD",
                atributos={"folha": "Stock_B&F_Egger"},
            )
        ),
    )
    session.commit()

    linha = listar_referencias(session)[0]
    assert linha.precos == {"19mm": "21,02 €"}


# ---------------------------------------------------------------------------
# A cache de quem mostra isto
# ---------------------------------------------------------------------------


def test_a_assinatura_muda_quando_entra_uma_tabela(session: Session) -> None:
    antes = assinatura_catalogos(session)
    importar(session, _tabela(_placa("19mm", "21.02")))
    session.commit()

    assert assinatura_catalogos(session) != antes
    assert esta_vazia(session) is False


# ---------------------------------------------------------------------------
# Dois preços para a mesma coisa
# ---------------------------------------------------------------------------


def test_dois_precos_para_a_mesma_medida_valem_o_mais_caro(session: Session) -> None:
    """A decisão do Paulo: não conseguindo validar, orçamenta-se pelo caro.

    A Finsa dá à referência 688B/YOKU dois designs com preços diferentes no
    mesmo substrato e na mesma espessura. Os dois ficam na base; o que esta
    marca resolve é qual deles a resposta IA cita.
    """
    def finsa(design: str, grupo: str, preco: str) -> ArtigoCatalogo:
        return _placa(
            "19mm",
            preco,
            chave_natural=f"688B|{design}|YOKU|AGL HID|19mm",
            referencia="688B",
            nome_design=design,
            acabamento="YOKU",
            grupo=grupo,
            atributos={
                "folha": "Stock_B&F_Finsa",
                "espessura": "19mm",
                "substrato_origem": "AGL HID",
            },
        )

    importar(session, _tabela(finsa("CARYA WOOD", "DUO GRUPO 3", "17.36"),
                              finsa("TIVOLI ASH", "DUO GRUPO 2", "16.63")))
    session.commit()

    artigos = {artigo.nome_design: artigo for artigo in listar_artigos(session)}
    assert artigos["CARYA WOOD"].preco_a_considerar is True
    assert artigos["TIVOLI ASH"].preco_a_considerar is False
    assert artigos["CARYA WOOD"].precos_da_medida == (
        Decimal("16.63"),
        Decimal("17.36"),
    )
    # Nenhum dos dois desaparece da tabela.
    assert len(listar_referencias(session)) == 2


def test_espessuras_diferentes_nao_sao_a_mesma_medida(session: Session) -> None:
    """Preços diferentes em espessuras diferentes são o normal, não ambiguidade."""
    importar(session, _tabela(_placa("8mm", "17.98"), _placa("19mm", "21.02")))
    session.commit()

    for artigo in listar_artigos(session):
        assert artigo.precos_da_medida == ()
        assert artigo.preco_a_considerar is True
