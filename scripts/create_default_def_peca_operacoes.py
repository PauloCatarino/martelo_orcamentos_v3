"""Associate default production operations to existing piece definitions.

This seed is idempotent: it creates a link in def_peca_operacoes only when it
does not exist yet, and reuses existing links without modifying them. Missing
pieces or operations are reported and skipped, nothing is deleted.
"""

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
from app.domain.regra_operacao_types import (  # noqa: E402
    POR_FURACAO,
    POR_ORLAS,
    POR_PECA,
)
from app.models import DefOperacao, DefPeca, DefPecaOperacao  # noqa: E402


@dataclass(frozen=True)
class PecaOperacaoSeed:
    """One default operation link for a piece definition."""

    operacao_codigo: str
    ordem: int
    regra_calculo: str
    obrigatorio: bool = True
    ativo: bool = True
    quantidade_base: Decimal | None = None


@dataclass(frozen=True)
class DefaultPecaOperacoesResult:
    """Summary of the default piece-operation seed."""

    ligacoes_criadas: int
    ligacoes_reutilizadas: int
    pecas_nao_encontradas: int
    operacoes_nao_encontradas: int
    ligacoes_inativas: int


# Shared operation sets reused across several piece definitions.
CORTE_ORLAGEM_CNC_OPERACOES: tuple[PecaOperacaoSeed, ...] = (
    PecaOperacaoSeed("CORTE_PAINEL", 1, POR_PECA),
    PecaOperacaoSeed("ORLAGEM_PECA", 2, POR_ORLAS),
    PecaOperacaoSeed("CNC_MECANIZACAO", 3, POR_FURACAO),
)

CORTE_ORLAGEM_OPERACOES: tuple[PecaOperacaoSeed, ...] = (
    PecaOperacaoSeed("CORTE_PAINEL", 1, POR_PECA),
    PecaOperacaoSeed("ORLAGEM_PECA", 2, POR_ORLAS),
)

CORTE_OPERACOES: tuple[PecaOperacaoSeed, ...] = (
    PecaOperacaoSeed("CORTE_PAINEL", 1, POR_PECA),
)

GAVETA_OPERACOES: tuple[PecaOperacaoSeed, ...] = (
    PecaOperacaoSeed("MONTAGEM_GERAL", 10, POR_PECA),
)


# Piece code -> default operation links. Pieces that do not exist are skipped.
DEFAULT_PECA_OPERACOES: tuple[tuple[str, tuple[PecaOperacaoSeed, ...]], ...] = (
    ("PORTA", CORTE_ORLAGEM_CNC_OPERACOES),
    ("PORTA_SIMPLES", CORTE_ORLAGEM_CNC_OPERACOES),
    ("PRATELEIRA", CORTE_ORLAGEM_OPERACOES),
    ("PRATELEIRA_AMOVIVEL", CORTE_ORLAGEM_OPERACOES),
    ("LATERAL", CORTE_ORLAGEM_CNC_OPERACOES),
    ("TAMPO", CORTE_ORLAGEM_OPERACOES),
    ("FUNDO", CORTE_ORLAGEM_OPERACOES),
    ("COSTA", CORTE_OPERACOES),
    ("LADO_GAVETA", CORTE_ORLAGEM_OPERACOES),
    ("FUNDO_GAVETA", CORTE_OPERACOES),
    ("TRASEIRA_GAVETA", CORTE_OPERACOES),
    ("FRENTE_GAVETA", CORTE_ORLAGEM_CNC_OPERACOES),
    ("GAVETA", GAVETA_OPERACOES),
)


def get_peca_by_codigo(session: Session, codigo: str) -> DefPeca | None:
    """Find one piece definition by code."""
    return session.execute(select(DefPeca).where(DefPeca.codigo == codigo)).scalar_one_or_none()


def get_operacao_by_codigo(session: Session, codigo: str) -> DefOperacao | None:
    """Find one operation by code."""
    return session.execute(
        select(DefOperacao).where(DefOperacao.codigo == codigo)
    ).scalar_one_or_none()


def get_ligacao(
    session: Session, def_peca_id: int, def_operacao_id: int
) -> DefPecaOperacao | None:
    """Find one existing piece-operation link."""
    return session.execute(
        select(DefPecaOperacao).where(
            DefPecaOperacao.def_peca_id == def_peca_id,
            DefPecaOperacao.def_operacao_id == def_operacao_id,
        )
    ).scalar_one_or_none()


def ensure_default_def_peca_operacoes(session: Session) -> DefaultPecaOperacoesResult:
    """Create or reuse the default operation links for existing pieces."""
    ligacoes_criadas = 0
    ligacoes_reutilizadas = 0
    pecas_nao_encontradas = 0
    operacoes_nao_encontradas = 0
    ligacoes_inativas = 0

    operacao_cache: dict[str, DefOperacao | None] = {}

    for peca_codigo, seeds in DEFAULT_PECA_OPERACOES:
        peca = get_peca_by_codigo(session, peca_codigo)
        if peca is None:
            print(f"Peca {peca_codigo} nao encontrada, ignorada")
            pecas_nao_encontradas += 1
            continue

        for seed in seeds:
            if seed.operacao_codigo not in operacao_cache:
                operacao_cache[seed.operacao_codigo] = get_operacao_by_codigo(
                    session, seed.operacao_codigo
                )
            operacao = operacao_cache[seed.operacao_codigo]

            if operacao is None:
                print(
                    f"Operacao {seed.operacao_codigo} nao encontrada "
                    f"(peca {peca_codigo}), ignorada"
                )
                operacoes_nao_encontradas += 1
                continue

            ligacao = get_ligacao(session, peca.id, operacao.id)
            if ligacao is not None:
                ligacoes_reutilizadas += 1
                if ligacao.ativo:
                    print(f"Ligacao {peca_codigo} -> {seed.operacao_codigo} reutilizada")
                else:
                    ligacoes_inativas += 1
                    print(
                        f"Ligacao {peca_codigo} -> {seed.operacao_codigo} "
                        f"reutilizada (inativa, mantida como esta)"
                    )
                continue

            ligacao = DefPecaOperacao(
                def_peca_id=peca.id,
                def_operacao_id=operacao.id,
                ordem=seed.ordem,
                regra_calculo=seed.regra_calculo,
                quantidade_base=seed.quantidade_base,
                obrigatorio=seed.obrigatorio,
                ativo=seed.ativo,
            )
            session.add(ligacao)
            session.flush()
            ligacoes_criadas += 1
            print(f"Ligacao {peca_codigo} -> {seed.operacao_codigo} criada")

    session.commit()

    return DefaultPecaOperacoesResult(
        ligacoes_criadas=ligacoes_criadas,
        ligacoes_reutilizadas=ligacoes_reutilizadas,
        pecas_nao_encontradas=pecas_nao_encontradas,
        operacoes_nao_encontradas=operacoes_nao_encontradas,
        ligacoes_inativas=ligacoes_inativas,
    )


def print_summary(result: DefaultPecaOperacoesResult) -> None:
    """Print the final user-facing seed summary."""
    print("Resumo final")
    print(f"Ligacoes criadas: {result.ligacoes_criadas}")
    print(f"Ligacoes reutilizadas: {result.ligacoes_reutilizadas}")
    print(f"Pecas nao encontradas: {result.pecas_nao_encontradas}")
    print(f"Operacoes nao encontradas: {result.operacoes_nao_encontradas}")
    print(f"Ligacoes inativas mantidas: {result.ligacoes_inativas}")


def main() -> int:
    """Create or reuse default piece-operation links in the configured database."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = ensure_default_def_peca_operacoes(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
