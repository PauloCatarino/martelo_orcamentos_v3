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
    REVESTIMENTO,
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
    descricao: str | None = None
    permite_rasgos: bool = False
    preco_rasgo_ml_std: Decimal | None = None
    preco_rasgo_ml_serie: Decimal | None = None
    permite_furacao: bool = False
    permite_pocket: bool = False
    permite_escaloes_area: bool = False
    preco_furo_std: Decimal | None = None
    preco_furo_serie: Decimal | None = None
    preco_m2_face_std: Decimal | None = None
    preco_m2_face_serie: Decimal | None = None


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
    maquinas_desativadas: int
    operacoes_criadas: int
    operacoes_reutilizadas: int


DEFAULT_MAQUINAS: tuple[DefMaquinaSeed, ...] = (
    DefMaquinaSeed(codigo="CORTE", nome="Corte", tipo=CORTE),
    DefMaquinaSeed(codigo="ORLAGEM", nome="Orlagem", tipo=ORLAGEM),
    DefMaquinaSeed(
        codigo="CNC_ABD",
        nome="CNC ABD",
        tipo=CNC,
        descricao=(
            "So faz furacao; usada em pecas mais simples, por exemplo caixas de "
            "gavetas. Metodos: escaloes de area, tempo ou n.o de furos."
        ),
        permite_furacao=True,
        permite_escaloes_area=True,
        preco_furo_std=Decimal("0.10"),
        preco_furo_serie=Decimal("0.07"),
    ),
    DefMaquinaSeed(
        codigo="CNC_VERTICAL",
        nome="CNC Vertical",
        tipo=CNC,
        descricao=(
            "Pratica de operar; usada para mecanizar a maioria das pecas. "
            "Metodos: escaloes de area, tempo, n.o de furos, rasgo e pocket."
        ),
        permite_rasgos=True,
        preco_rasgo_ml_std=Decimal("0.40"),
        preco_rasgo_ml_serie=Decimal("0.40"),
        permite_furacao=True,
        permite_pocket=True,
        permite_escaloes_area=True,
        preco_furo_std=Decimal("0.12"),
        preco_furo_serie=Decimal("0.09"),
    ),
    DefMaquinaSeed(
        codigo="CNC_SANDWICH",
        nome="CNC Sandwich",
        tipo=CNC,
        descricao=(
            "Muito eficiente para todo o tipo de furacoes e muito rapida em "
            "quantidades de pecas. Metodos: escaloes de area, tempo, n.o de "
            "furos e rasgo (sem pocket)."
        ),
        permite_rasgos=True,
        preco_rasgo_ml_std=Decimal("0.40"),
        preco_rasgo_ml_serie=Decimal("0.40"),
        permite_furacao=True,
        permite_escaloes_area=True,
        preco_furo_std=Decimal("0.10"),
        preco_furo_serie=Decimal("0.06"),
    ),
    DefMaquinaSeed(
        codigo="CNC_5_EIXOS",
        nome="CNC 5 Eixos / Orlagem",
        tipo=CNC,
        descricao=(
            "A maquina mais polivalente, faz 'tudo': pecas 2D/3D, formas "
            "especiais, recortes e orlagem de formas nao retangulares. "
            "Metodos: escaloes de area, tempo, n.o de furos, rasgo e pocket."
        ),
        permite_rasgos=True,
        preco_rasgo_ml_std=Decimal("0.40"),
        preco_rasgo_ml_serie=Decimal("0.40"),
        permite_furacao=True,
        permite_pocket=True,
        permite_escaloes_area=True,
        preco_furo_std=Decimal("0.15"),
        preco_furo_serie=Decimal("0.11"),
    ),
    DefMaquinaSeed(
        codigo="REVESTIMENTO_SANDWICH",
        nome="Revestimento Sandwich",
        tipo=REVESTIMENTO,
        descricao=(
            "Reveste paineis sandwich em 1 ou 2 faces; tarifa por m2 e por "
            "face revestida."
        ),
        preco_m2_face_std=Decimal("3.25"),
        preco_m2_face_serie=Decimal("3.25"),
    ),
    DefMaquinaSeed(codigo="MONTAGEM", nome="Montagem", tipo=MONTAGEM),
    DefMaquinaSeed(codigo="MANUAL", nome="Manual", tipo=MANUAL),
)

# Machine codes that existed in earlier seeds and are now replaced. They are
# deactivated (not deleted) when the seed runs again. CNC_HORIZONTAL and
# CNC_5_EIXOS_ORLAGEM are renamed by migration 20260805_75; the codes only
# still exist on databases that never ran it.
OBSOLETE_MAQUINA_CODIGOS: tuple[str, ...] = (
    "CNC",
    "CNC_HORIZONTAL",
    "CNC_5_EIXOS_ORLAGEM",
)

# Operation codes replaced by the per-machine CNC operations (deactivated when
# still present; migration 20260805_75 deletes them after repointing links).
OBSOLETE_OPERACAO_CODIGOS: tuple[str, ...] = ("CNC_MECANIZACAO", "CNC_RASGO")

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
    # One CNC operation per machine: the user picks the MACHINE here and the
    # calculation METHOD on the piece/ValueSet/costing link.
    DefOperacaoSeed(
        codigo="CNC_ABD",
        nome="CNC ABD",
        tipo_operacao=CNC,
        unidade_calculo="PECA",
        maquina_codigo="CNC_ABD",
    ),
    DefOperacaoSeed(
        codigo="CNC_VERTICAL",
        nome="CNC Vertical",
        tipo_operacao=CNC,
        unidade_calculo="PECA",
        maquina_codigo="CNC_VERTICAL",
    ),
    DefOperacaoSeed(
        codigo="CNC_SANDWICH",
        nome="CNC Sandwich",
        tipo_operacao=CNC,
        unidade_calculo="PECA",
        maquina_codigo="CNC_SANDWICH",
    ),
    DefOperacaoSeed(
        codigo="CNC_5_EIXOS",
        nome="CNC 5 Eixos",
        tipo_operacao=CNC,
        unidade_calculo="PECA",
        maquina_codigo="CNC_5_EIXOS",
    ),
    DefOperacaoSeed(
        codigo="REVESTIMENTO_SANDWICH",
        nome="Revestimento Sandwich",
        tipo_operacao=REVESTIMENTO,
        unidade_calculo="M2",
        maquina_codigo="REVESTIMENTO_SANDWICH",
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
        maquina.descricao = seed.descricao
        maquina.custo_hora = seed.custo_hora
        maquina.permite_rasgos = seed.permite_rasgos
        maquina.preco_rasgo_ml_std = seed.preco_rasgo_ml_std
        maquina.preco_rasgo_ml_serie = seed.preco_rasgo_ml_serie
        maquina.permite_furacao = seed.permite_furacao
        maquina.permite_pocket = seed.permite_pocket
        maquina.permite_escaloes_area = seed.permite_escaloes_area
        maquina.preco_furo_std = seed.preco_furo_std
        maquina.preco_furo_serie = seed.preco_furo_serie
        maquina.preco_m2_face_std = seed.preco_m2_face_std
        maquina.preco_m2_face_serie = seed.preco_m2_face_serie
        maquina.ativo = True
        session.flush()
        return EntityResult(status="reutilizada", entity=maquina)

    maquina = DefMaquina(
        codigo=seed.codigo,
        nome=seed.nome,
        tipo=seed.tipo,
        descricao=seed.descricao,
        custo_hora=seed.custo_hora,
        permite_rasgos=seed.permite_rasgos,
        preco_rasgo_ml_std=seed.preco_rasgo_ml_std,
        preco_rasgo_ml_serie=seed.preco_rasgo_ml_serie,
        permite_furacao=seed.permite_furacao,
        permite_pocket=seed.permite_pocket,
        permite_escaloes_area=seed.permite_escaloes_area,
        preco_furo_std=seed.preco_furo_std,
        preco_furo_serie=seed.preco_furo_serie,
        preco_m2_face_std=seed.preco_m2_face_std,
        preco_m2_face_serie=seed.preco_m2_face_serie,
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


def deactivate_obsolete_maquinas(session: Session) -> int:
    """Deactivate machines that were replaced and are no longer default."""
    desativadas = 0

    for codigo in OBSOLETE_MAQUINA_CODIGOS:
        maquina = get_maquina_by_codigo(session, codigo)
        if maquina is not None and maquina.ativo:
            maquina.ativo = False
            session.flush()
            desativadas += 1
            print(f"Maquina {codigo} desativada (obsoleta)")

    return desativadas


def deactivate_obsolete_operacoes(session: Session) -> int:
    """Deactivate catalog operations replaced by the per-machine CNC set."""
    desativadas = 0

    for codigo in OBSOLETE_OPERACAO_CODIGOS:
        operacao = get_operacao_by_codigo(session, codigo)
        if operacao is not None and operacao.ativo:
            operacao.ativo = False
            session.flush()
            desativadas += 1
            print(f"Operacao {codigo} desativada (obsoleta)")

    return desativadas


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

    maquinas_desativadas = deactivate_obsolete_maquinas(session)

    for seed in DEFAULT_OPERACOES:
        result = get_or_create_operacao(session, seed)
        print(f"Operacao {seed.codigo} {result.status}")
        if result.status == "criada":
            operacoes_criadas += 1
        else:
            operacoes_reutilizadas += 1

    deactivate_obsolete_operacoes(session)

    session.commit()

    return DefaultOperacoesResult(
        maquinas_criadas=maquinas_criadas,
        maquinas_reutilizadas=maquinas_reutilizadas,
        maquinas_desativadas=maquinas_desativadas,
        operacoes_criadas=operacoes_criadas,
        operacoes_reutilizadas=operacoes_reutilizadas,
    )


def print_summary(result: DefaultOperacoesResult) -> None:
    """Print the final user-facing seed summary."""
    print("Resumo final")
    print(f"Maquinas criadas: {result.maquinas_criadas}")
    print(f"Maquinas reutilizadas: {result.maquinas_reutilizadas}")
    print(f"Maquinas desativadas: {result.maquinas_desativadas}")
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
