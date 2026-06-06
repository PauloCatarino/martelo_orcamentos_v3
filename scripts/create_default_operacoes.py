"""Create default machine and operation definitions for Martelo V3."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domain.operacao_types import (  # noqa: E402
    CNC,
    COLAGEM,
    CORTE,
    EMBALAMENTO,
    FURACAO,
    MANUAL,
    MONTAGEM,
    ORLAGEM,
    RASGO,
    SETUP,
)
from app.models import DefMaquina, DefOperacao  # noqa: E402


@dataclass(frozen=True)
class DefMaquinaSeed:
    """Definition data for one default machine."""

    codigo: str
    nome: str
    tipo: str | None = None
    custo_hora: Decimal | None = None


@dataclass(frozen=True)
class DefOperacaoSeed:
    """Definition data for one default operation."""

    codigo: str
    nome: str
    tipo_operacao: str
    unidade_calculo: str | None = None
    maquina_codigo: str | None = None
    tempo_base: Decimal | None = None
    tempo_setup: Decimal | None = None
    custo_hora: Decimal | None = None
    custo_minimo: Decimal | None = None


@dataclass(frozen=True)
class EntityResult:
    """Result for one seeded entity."""

    status: str
    entity: object


@dataclass(frozen=True)
class DefaultOperacoesResult:
    """Summary of the default machine and operation seed."""

    maquinas_criadas: int
    maquinas_reutilizadas: int
    operacoes_criadas: int
    operacoes_reutilizadas: int


DEFAULT_MAQUINAS: tuple[DefMaquinaSeed, ...] = (
    DefMaquinaSeed(codigo="CORTE", nome="Corte", tipo=CORTE),
    DefMaquinaSeed(codigo="ORLAGEM", nome="Orlagem", tipo=ORLAGEM),
    DefMaquinaSeed(codigo="CNC", nome="CNC", tipo=CNC),
    DefMaquinaSeed(codigo="MONTAGEM", nome="Montagem", tipo=MONTAGEM),
    DefMaquinaSeed(codigo="MANUAL", nome="Manual", tipo=MANUAL),
)

DEFAULT_OPERACOES: tuple[DefOperacaoSeed, ...] = (
    DefOperacaoSeed(
        codigo="CORTE_PAINEL",
        nome="Corte de painel",
        tipo_operacao=CORTE,
        unidade_calculo="PECA",
        maquina_codigo="CORTE",
    ),
    DefOperacaoSeed(
        codigo="ORLAGEM_PECA",
        nome="Orlagem de peca",
        tipo_operacao=ORLAGEM,
        unidade_calculo="ML",
        maquina_codigo="ORLAGEM",
    ),
    DefOperacaoSeed(
        codigo="CNC_MECANIZACAO",
        nome="CNC / Mecanizacao",
        tipo_operacao=CNC,
        unidade_calculo="PECA",
        maquina_codigo="CNC",
    ),
    DefOperacaoSeed(
        codigo="FURACAO_MANUAL",
        nome="Furacao manual",
        tipo_operacao=FURACAO,
        unidade_calculo="PECA",
        maquina_codigo="MANUAL",
    ),
    DefOperacaoSeed(
        codigo="RASGO_MANUAL",
        nome="Rasgo manual",
        tipo_operacao=RASGO,
        unidade_calculo="PECA",
        maquina_codigo="MANUAL",
    ),
    DefOperacaoSeed(
        codigo="COLAGEM_MANUAL",
        nome="Colagem manual",
        tipo_operacao=COLAGEM,
        unidade_calculo="PECA",
        maquina_codigo="MANUAL",
    ),
    DefOperacaoSeed(
        codigo="MONTAGEM_GERAL",
        nome="Montagem geral",
        tipo_operacao=MONTAGEM,
        unidade_calculo="HORA",
        maquina_codigo="MONTAGEM",
    ),
    DefOperacaoSeed(
        codigo="EMBALAMENTO",
        nome="Embalamento",
        tipo_operacao=EMBALAMENTO,
        unidade_calculo="PECA",
        maquina_codigo="MANUAL",
    ),
    DefOperacaoSeed(
        codigo="SETUP_MAQUINA",
        nome="Setup de maquina",
        tipo_operacao=SETUP,
        unidade_calculo="SETUP",
        maquina_codigo="MANUAL",
    ),
    DefOperacaoSeed(
        codigo="OPERACAO_MANUAL",
        nome="Operacao manual",
        tipo_operacao=MANUAL,
        unidade_calculo="HORA",
        maquina_codigo="MANUAL",
    ),
)


def get_maquina_by_codigo(session: Session, codigo: str) -> DefMaquina | None:
    """Find one machine by code."""
    return session.execute(select(DefMaquina).where(DefMaquina.codigo == codigo)).scalar_one_or_none()


def get_operacao_by_codigo(session: Session, codigo: str) -> DefOperacao | None:
    """Find one operation by code."""
    return session.execute(select(DefOperacao).where(DefOperacao.codigo == codigo)).scalar_one_or_none()


def get_or_create_maquina(session: Session, seed: DefMaquinaSeed) -> EntityResult:
    """Create or reuse one default machine."""
    maquina = get_maquina_by_codigo(session, seed.codigo)

    if maquina is not None:
        maquina.nome = seed.nome
        maquina.tipo = seed.tipo
        maquina.custo_hora = seed.custo_hora
        maquina.ativo = True
        session.flush()
        return EntityResult(status="reutilizada", entity=maquina)

    maquina = DefMaquina(
        codigo=seed.codigo,
        nome=seed.nome,
        tipo=seed.tipo,
        custo_hora=seed.custo_hora,
        ativo=True,
    )
    session.add(maquina)
    session.flush()

    return EntityResult(status="criada", entity=maquina)


def get_or_create_operacao(session: Session, seed: DefOperacaoSeed) -> EntityResult:
    """Create or reuse one default operation."""
    operacao = get_operacao_by_codigo(session, seed.codigo)
    maquina = get_maquina_by_codigo(session, seed.maquina_codigo) if seed.maquina_codigo else None

    if operacao is not None:
        operacao.nome = seed.nome
        operacao.tipo_operacao = seed.tipo_operacao
        operacao.unidade_calculo = seed.unidade_calculo
        operacao.tempo_base = seed.tempo_base
        operacao.tempo_setup = seed.tempo_setup
        operacao.custo_hora = seed.custo_hora
        operacao.custo_minimo = seed.custo_minimo
        operacao.maquina_id = maquina.id if maquina is not None else None
        operacao.ativo = True
        session.flush()
        return EntityResult(status="reutilizada", entity=operacao)

    operacao = DefOperacao(
        codigo=seed.codigo,
        nome=seed.nome,
        tipo_operacao=seed.tipo_operacao,
        unidade_calculo=seed.unidade_calculo,
        tempo_base=seed.tempo_base,
        tempo_setup=seed.tempo_setup,
        custo_hora=seed.custo_hora,
        custo_minimo=seed.custo_minimo,
        maquina_id=maquina.id if maquina is not None else None,
        ativo=True,
    )
    session.add(operacao)
    session.flush()

    return EntityResult(status="criada", entity=operacao)


def ensure_default_operacoes(session: Session) -> DefaultOperacoesResult:
    """Create or reuse default machines and operations."""
    maquinas_criadas = 0
    maquinas_reutilizadas = 0
    operacoes_criadas = 0
    operacoes_reutilizadas = 0

    for seed in DEFAULT_MAQUINAS:
        result = get_or_create_maquina(session, seed)
        print(f"Maquina {seed.codigo} {result.status}")
        if result.status == "criada":
            maquinas_criadas += 1
        else:
            maquinas_reutilizadas += 1

    for seed in DEFAULT_OPERACOES:
        result = get_or_create_operacao(session, seed)
        print(f"Operacao {seed.codigo} {result.status}")
        if result.status == "criada":
            operacoes_criadas += 1
        else:
            operacoes_reutilizadas += 1

    session.commit()

    return DefaultOperacoesResult(
        maquinas_criadas=maquinas_criadas,
        maquinas_reutilizadas=maquinas_reutilizadas,
        operacoes_criadas=operacoes_criadas,
        operacoes_reutilizadas=operacoes_reutilizadas,
    )


def print_summary(result: DefaultOperacoesResult) -> None:
    """Print the final user-facing seed summary."""
    print("Resumo final")
    print(f"Maquinas criadas: {result.maquinas_criadas}")
    print(f"Maquinas reutilizadas: {result.maquinas_reutilizadas}")
    print(f"Operacoes criadas: {result.operacoes_criadas}")
    print(f"Operacoes reutilizadas: {result.operacoes_reutilizadas}")


def main() -> int:
    """Create or reuse default machines and operations in the configured database."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = ensure_default_operacoes(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
