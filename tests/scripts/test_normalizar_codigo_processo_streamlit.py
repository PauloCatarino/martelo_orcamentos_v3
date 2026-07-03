"""Tests for the Streamlit codigo_processo backfill script."""

from __future__ import annotations

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models.producao import Producao
from scripts.normalizar_codigo_processo_streamlit import normalizar_codigo_processo


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _processo(
    *,
    id: int,
    codigo_processo: str,
    num_enc_phc: str,
    versao_obra: str = "01",
    versao_plano: str = "01",
) -> Producao:
    return Producao(
        id=id,
        codigo_processo=codigo_processo,
        ano="2026",
        num_enc_phc=num_enc_phc,
        versao_obra=versao_obra,
        versao_plano=versao_plano,
        estado="Producao",
        tipo_pasta="Encomenda de Cliente Final",
        nome_cliente="Tiago Lopes",
        nome_cliente_simplex="TIAGO_LOPES",
    )


def test_normaliza_apenas_linhas_streamlit_com_prefixo_antigo(session) -> None:
    session.add_all(
        [
            _processo(
                id=1,
                codigo_processo="26._118_01_01_TIAGO_LOPES",
                num_enc_phc="_118",
                versao_plano="01",
            ),
            _processo(
                id=2,
                codigo_processo="26.0118_01_02_TIAGO_LOPES",
                num_enc_phc="_118",
                versao_plano="02",
            ),
            _processo(
                id=3,
                codigo_processo="26.0118_01_03_TIAGO_LOPES",
                num_enc_phc="_118",
                versao_plano="03",
            ),
            _processo(
                id=4,
                codigo_processo="26.0475_01_01_JF_VIVA",
                num_enc_phc="475",
            ),
        ]
    )
    session.commit()

    summary = normalizar_codigo_processo(session, dry_run=False)

    assert summary.total == 4
    assert sorted(summary.ids_atualizados) == [2, 3]
    assert summary.ids_colisao == []

    assert session.get(Producao, 1).codigo_processo == "26._118_01_01_TIAGO_LOPES"
    assert session.get(Producao, 2).codigo_processo == "26._118_01_02_TIAGO_LOPES"
    assert session.get(Producao, 3).codigo_processo == "26._118_01_03_TIAGO_LOPES"
    assert session.get(Producao, 4).codigo_processo == "26.0475_01_01_JF_VIVA"


def test_dry_run_nao_grava_alteracoes(session) -> None:
    session.add(
        _processo(
            id=1,
            codigo_processo="26.0118_01_02_TIAGO_LOPES",
            num_enc_phc="_118",
            versao_plano="02",
        )
    )
    session.commit()

    summary = normalizar_codigo_processo(session, dry_run=True)

    assert summary.linhas_atualizadas == 1
    assert session.get(Producao, 1).codigo_processo == "26.0118_01_02_TIAGO_LOPES"


def test_ignora_colisao_com_codigo_processo_existente(session) -> None:
    # id=1 e id=2 tem chaves (num_enc_phc/versao_plano) distintas -- respeita a
    # unique constraint da BD -- mas id=1 ja tem gravado, por inconsistencia de
    # dados legada, exatamente o codigo_processo que id=2 passaria a ter depois
    # da correcao. O backfill deve detetar a colisao e nao tocar em nenhum dos dois.
    session.add_all(
        [
            _processo(
                id=1,
                codigo_processo="26._118_01_02_TIAGO_LOPES",
                num_enc_phc="_118",
                versao_plano="99",
            ),
            _processo(
                id=2,
                codigo_processo="26.0118_01_02_TIAGO_LOPES",
                num_enc_phc="_118",
                versao_plano="02",
            ),
        ]
    )
    session.commit()

    summary = normalizar_codigo_processo(session, dry_run=False)

    assert summary.ids_colisao == [2]
    assert summary.linhas_atualizadas == 0
    assert session.get(Producao, 1).codigo_processo == "26._118_01_02_TIAGO_LOPES"
    assert session.get(Producao, 2).codigo_processo == "26.0118_01_02_TIAGO_LOPES"
