"""Tests for the real production machine-tariffs seed."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import DefMaquina, DefOperacao
from scripts.create_default_operacoes import ensure_default_operacoes
from scripts.seed_tarifas_producao_reais import seed_tarifas_producao_reais


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            ensure_default_operacoes(session)
            yield session
    finally:
        engine.dispose()


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
        "CNC_SANDWICH",
        "CNC_5_EIXOS",
        "MANUAL",
        "MONTAGEM",
        "EMBALAMENTO",
    )
    campos = (
        "custo_hora",
        "custo_hora_serie",
        "preco_ml_std",
        "preco_ml_serie",
        "preco_lado_curto_std",
        "preco_lado_curto_serie",
        "preco_lado_longo_std",
        "preco_lado_longo_serie",
        "limite_lado_mm",
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
    orlagem = _maquina(session, "ORLAGEM")
    manual = _maquina(session, "MANUAL")
    montagem = _maquina(session, "MONTAGEM")
    embalamento = _maquina(session, "EMBALAMENTO")
    operacao_embalamento = _operacao(session, "EMBALAMENTO")

    assert primeira.embalamento_criada is True
    assert primeira.operacao_embalamento_reapontada is True
    assert primeira.maquinas_nao_encontradas == ()
    assert corte.preco_ml_std == Decimal("0.62")
    assert corte.preco_ml_serie == Decimal("0.41")
    assert corte.custo_setup_peca_std == Decimal("0.06")
    assert corte.custo_setup_peca_serie == Decimal("0.03")
    assert corte.custo_hora is None
    assert orlagem.preco_ml_std is None
    assert orlagem.preco_ml_serie is None
    assert orlagem.preco_lado_curto_std == Decimal("0.55")
    assert orlagem.preco_lado_curto_serie == Decimal("0.40")
    assert orlagem.preco_lado_longo_std == Decimal("1.10")
    assert orlagem.preco_lado_longo_serie == Decimal("0.80")
    assert orlagem.limite_lado_mm == Decimal("1500")
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
