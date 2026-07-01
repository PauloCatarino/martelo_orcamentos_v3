"""Tests for the real production machine-tariffs seed."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import DefMaquina, DefOperacao
from scripts.create_default_operacoes import ensure_default_operacoes
from scripts.seed_tarifas_producao_reais import seed_tarifas_producao_reais


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        ensure_default_operacoes(session)
        yield session


def _maquina(session: Session, codigo: str) -> DefMaquina:
    return session.execute(
        select(DefMaquina).where(DefMaquina.codigo == codigo)
    ).scalar_one()


def _operacao(session: Session, codigo: str) -> DefOperacao:
    return session.execute(
        select(DefOperacao).where(DefOperacao.codigo == codigo)
    ).scalar_one()


def _snapshot(session: Session) -> dict[str, object]:
    codigos = (
        "CORTE",
        "ORLAGEM",
        "CNC_ABD",
        "CNC_VERTICAL",
        "CNC_HORIZONTAL",
        "CNC_5_EIXOS_ORLAGEM",
        "MANUAL",
        "MONTAGEM",
        "EMBALAMENTO",
    )
    campos = (
        "custo_hora",
        "custo_hora_serie",
        "preco_ml_std",
        "preco_ml_serie",
        "custo_setup_peca_std",
        "custo_setup_peca_serie",
    )
    maquinas = {}
    for codigo in codigos:
        maquina = _maquina(session, codigo)
        maquinas[codigo] = tuple(getattr(maquina, campo) for campo in campos)

    return {
        "maquinas": maquinas,
        "embalamento_maquina_id": _maquina(session, "EMBALAMENTO").id,
        "embalamento_operacao_maquina_id": _operacao(
            session, "EMBALAMENTO"
        ).maquina_id,
    }


def test_seed_tarifas_reais_e_idempotente(session) -> None:
    _maquina(session, "CORTE").preco_ml_std = Decimal("9.99")
    _maquina(session, "CORTE").custo_hora = Decimal("99")
    _maquina(session, "MANUAL").custo_hora = Decimal("12")
    _maquina(session, "MONTAGEM").custo_hora = Decimal("15")
    _maquina(session, "MONTAGEM").preco_ml_std = Decimal("1.23")
    session.commit()

    primeira = seed_tarifas_producao_reais(session)

    corte = _maquina(session, "CORTE")
    manual = _maquina(session, "MANUAL")
    montagem = _maquina(session, "MONTAGEM")
    embalamento = _maquina(session, "EMBALAMENTO")
    operacao_embalamento = _operacao(session, "EMBALAMENTO")

    assert primeira.embalamento_criada is True
    assert primeira.operacao_embalamento_reapontada is True
    assert primeira.maquinas_nao_encontradas == ()
    assert corte.preco_ml_std == Decimal("0.8235")
    assert corte.custo_hora is None
    assert manual.custo_hora == Decimal("20")
    assert montagem.custo_hora == Decimal("60")
    assert montagem.preco_ml_std is None
    assert embalamento.custo_hora == Decimal("30")
    assert embalamento.nome == "Embalamento"
    assert embalamento.tipo == "MONTAGEM"
    assert embalamento.ativo is True
    assert operacao_embalamento.maquina_id == embalamento.id

    antes = _snapshot(session)
    segunda = seed_tarifas_producao_reais(session)
    depois = _snapshot(session)

    assert segunda.embalamento_criada is False
    assert segunda.maquinas_nao_encontradas == ()
    assert depois == antes
