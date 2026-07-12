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
    descricao: str | None = None
    permite_rasgos: bool = False
    preco_rasgo_ml_std: Decimal | None = None
    preco_rasgo_ml_serie: Decimal | None = None


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
        descricao="Pecas pequenas e trabalhos simples, por exemplo caixas de gavetas.",
    ),
    DefMaquinaSeed(
        codigo="CNC_VERTICAL",
        nome="CNC Vertical",
        tipo=CNC,
        descricao=(
            "Versatil para mobiliario geral, roupeiros e cozinhas; boa para pequenas "
            "quantidades e pecas sem grande complexidade; furacao, cavilhas, rasgos com "
            "disco/fresa e algumas operacoes de milling."
        ),
        permite_rasgos=True,
        preco_rasgo_ml_std=Decimal("0.40"),
        preco_rasgo_ml_serie=Decimal("0.40"),
    ),
    DefMaquinaSeed(
        codigo="CNC_HORIZONTAL",
        nome="CNC Horizontal",
        tipo=CNC,
        descricao=(
            "Pecas em serie ou maior quantidade, sem grande complexidade; furacao, "
            "cavilhas, rasgos com disco e fresagens limitadas."
        ),
        permite_rasgos=True,
        preco_rasgo_ml_std=Decimal("0.40"),
        preco_rasgo_ml_serie=Decimal("0.40"),
    ),
    DefMaquinaSeed(
        codigo="CNC_5_EIXOS_ORLAGEM",
        nome="CNC 5 Eixos / Orlagem",
        tipo=CNC,
        descricao=(
            "Maquina complexa/multitarefas para pecas 2D/3D, formas especiais, tampos "
            "redondos, recortes e orlagem de formas nao retangulares; custo mais elevado "
            "e menos orientada para producao em serie."
        ),
        permite_rasgos=True,
        preco_rasgo_ml_std=Decimal("0.40"),
        preco_rasgo_ml_serie=Decimal("0.40"),
    ),
    DefMaquinaSeed(codigo="MONTAGEM", nome="Montagem", tipo=MONTAGEM),
    DefMaquinaSeed(codigo="MANUAL", nome="Manual", tipo=MANUAL),
)

# Machine codes that existed in earlier seeds and are now replaced. They are
# deactivated (not deleted) when the seed runs again.
OBSOLETE_MAQUINA_CODIGOS: tuple[str, ...] = ("CNC",)

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
        maquina_codigo="CNC_VERTICAL",
    ),
    DefOperacaoSeed(
        codigo="CNC_RASGO",
        nome="Rasgo CNC",
        tipo_operacao=CNC,
        unidade_calculo="ML",
        maquina_codigo="CNC_VERTICAL",
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
