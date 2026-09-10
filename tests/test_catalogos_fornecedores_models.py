"""Os catálogos de fornecedores vivem separados dos orçamentos.

O que estes testes guardam não é o feitio das tabelas — é a fronteira. Se um
dia alguém puser uma chave estrangeira a apontar de um catálogo para
``def_materias_primas``, ou registar um modelo de catálogo no ``metadata`` dos
orçamentos, a base dos catálogos deixa de poder ser reconstruída do zero sem
levar orçamentos atrás. É isso que aqui falha alto.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.catalogos import SCHEMA_CATALOGOS, catalogos_metadata
from app.models.catalogos import (
    FornArtigo,
    FornArtigoAlias,
    FornArtigoPreco,
    FornTabelaPreco,
)
import app.models  # noqa: F401  (regista os modelos dos orçamentos)


@pytest.fixture()
def session_catalogos():
    """Session sobre um SQLite em memória com a base dos catálogos anexada.

    No MySQL ``martelo_catalogos`` é outra base do mesmo servidor; no SQLite o
    equivalente é um ``ATTACH``. O nome tem de ser o mesmo em ambos, senão os
    modelos — que trazem o schema no ``__table_args__`` — não assentam.
    """
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _anexar(dbapi_connection, _record):  # noqa: ANN001
        dbapi_connection.execute(f"ATTACH DATABASE ':memory:' AS {SCHEMA_CATALOGOS}")

    catalogos_metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def _tabela_preco(**extra) -> FornTabelaPreco:
    dados = dict(
        fornecedor="Balbino & Faustino",
        fabricante="Innovus",
        nome="T-04 Innovus Brancos",
        referencia_tabela="T-04",
        unidade_preco="M2",
    )
    dados.update(extra)
    return FornTabelaPreco(**dados)


def _artigo(**extra) -> FornArtigo:
    dados = dict(
        fornecedor="Balbino & Faustino",
        fabricante="Innovus",
        chave_natural="B3822 MA|PB STD|19",
        referencia="B3822 MA",
        descricao="Innovus B3822 MA · White · Aglomerado de partículas standard",
        nome_design="White",
        unidade="M2",
        substrato="PB STD",
        espessura_mm=Decimal("19.00"),
        acabamento="MA",
    )
    dados.update(extra)
    return FornArtigo(**dados)


# --------------------------------------------------------------------------
# A fronteira
# --------------------------------------------------------------------------

def test_catalogos_nao_entram_no_metadata_dos_orcamentos() -> None:
    """Um ``create_all`` dos orçamentos nunca cria tabelas de catálogo."""
    nomes_orcamentos = set(Base.metadata.tables)
    nomes_catalogos = set(catalogos_metadata.tables)

    assert nomes_catalogos, "os modelos de catálogo não foram registados"
    assert not nomes_orcamentos & nomes_catalogos


def test_todas_as_tabelas_de_catalogo_ficam_na_base_dos_catalogos() -> None:
    for tabela in catalogos_metadata.tables.values():
        assert tabela.schema == SCHEMA_CATALOGOS, tabela.name


def test_nenhuma_chave_estrangeira_atravessa_a_fronteira() -> None:
    """As FK dos catálogos só apontam para dentro dos catálogos."""
    for tabela in catalogos_metadata.tables.values():
        for fk in tabela.foreign_keys:
            assert fk.column.table.schema == SCHEMA_CATALOGOS, (
                f"{tabela.name}.{fk.parent.name} aponta para fora dos catálogos "
                f"({fk.target_fullname})"
            )


def test_orcamentos_nao_apontam_para_os_catalogos() -> None:
    """E o contrário também não: nada em orçamentos referencia um catálogo."""
    for tabela in Base.metadata.tables.values():
        for fk in tabela.foreign_keys:
            assert fk.column.table.schema != SCHEMA_CATALOGOS, (
                f"{tabela.name}.{fk.parent.name} aponta para os catálogos"
            )


# --------------------------------------------------------------------------
# O básico funciona
# --------------------------------------------------------------------------

def test_grava_artigo_com_preco_e_alias(session_catalogos: Session) -> None:
    tabela = _tabela_preco(ficheiro_hash="a" * 64)
    artigo = _artigo()
    session_catalogos.add_all([tabela, artigo])
    session_catalogos.flush()

    session_catalogos.add_all(
        [
            FornArtigoPreco(
                artigo_id=artigo.id,
                tabela_preco_id=tabela.id,
                referencia=artigo.referencia,
                valor=Decimal("7.9400"),
                unidade="M2",
            ),
            FornArtigoAlias(artigo_id=artigo.id, tipo="EAN", valor="5601234567890"),
        ]
    )
    session_catalogos.commit()

    preco = session_catalogos.scalars(select(FornArtigoPreco)).one()
    assert preco.valor == Decimal("7.9400")
    assert preco.unidade == "M2"
    assert session_catalogos.scalars(select(FornArtigoAlias)).one().tipo == "EAN"


def test_a_mesma_chave_natural_nao_entra_duas_vezes(session_catalogos: Session) -> None:
    """É isto que faz a reimportação da mesma tabela não duplicar artigos."""
    session_catalogos.add(_artigo())
    session_catalogos.commit()

    session_catalogos.add(_artigo(descricao="descrição diferente, mesmo artigo"))
    with pytest.raises(IntegrityError):
        session_catalogos.commit()
    session_catalogos.rollback()


def test_espessuras_diferentes_sao_artigos_diferentes(session_catalogos: Session) -> None:
    """O desdobramento das placas: 19 mm e 8 mm têm preço próprio."""
    session_catalogos.add_all(
        [
            _artigo(),
            _artigo(chave_natural="B3822 MA|PB STD|8", espessura_mm=Decimal("8.00")),
        ]
    )
    session_catalogos.commit()

    assert len(session_catalogos.scalars(select(FornArtigo)).all()) == 2


def test_o_mesmo_ficheiro_nao_entra_duas_vezes(session_catalogos: Session) -> None:
    """O hash do ficheiro é o que torna a importação repetível sem estragos."""
    session_catalogos.add(_tabela_preco(ficheiro_hash="b" * 64))
    session_catalogos.commit()

    session_catalogos.add(_tabela_preco(ficheiro_hash="b" * 64, nome="outra vez"))
    with pytest.raises(IntegrityError):
        session_catalogos.commit()
    session_catalogos.rollback()


def test_apagar_o_artigo_leva_precos_e_aliases(session_catalogos: Session) -> None:
    tabela = _tabela_preco(ficheiro_hash="c" * 64)
    artigo = _artigo()
    session_catalogos.add_all([tabela, artigo])
    session_catalogos.flush()
    session_catalogos.add_all(
        [
            FornArtigoPreco(
                artigo_id=artigo.id, tabela_preco_id=tabela.id, valor=Decimal("1.0")
            ),
            FornArtigoAlias(artigo_id=artigo.id, tipo="EAN", valor="1"),
        ]
    )
    session_catalogos.commit()

    session_catalogos.execute(text("PRAGMA foreign_keys = ON"))
    session_catalogos.delete(artigo)
    session_catalogos.commit()

    assert session_catalogos.scalars(select(FornArtigoPreco)).all() == []
    assert session_catalogos.scalars(select(FornArtigoAlias)).all() == []
