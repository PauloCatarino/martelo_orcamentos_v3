"""Create the default (example) quantity rules (phase 8T.5.0).

Idempotent: creates a rule only when its code does not exist yet, and reuses
existing rules without modifying them. Nothing is deleted. Each expression is
validated against the sample context before being inserted.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domain.regras_quantidade_expr import (  # noqa: E402
    CONTEXTO_EXEMPLO,
    avaliar_regra_quantidade,
)
from app.models import DefRegraQuantidade  # noqa: E402


@dataclass(frozen=True)
class RegraSeed:
    """One default quantity rule."""

    codigo: str
    nome: str
    expressao: str
    descricao: str


# Default (example) quantity rules. All seeded active.
DEFAULT_REGRAS_QUANTIDADE: tuple[RegraSeed, ...] = (
    RegraSeed(
        codigo="DOBRADICA",
        nome="Dobradiças",
        expressao=(
            "(2 if COMP <= 850 else 3 if COMP <= 1600 else 4 if COMP <= 2000 "
            "else 5 if COMP <= 2600 else 6 + ((COMP - 2600) // 600)) "
            "+ (1 if LARG >= 605 else 0)"
        ),
        descricao="Dobradiças por altura(COMP) da porta + 1 se LARG>=605.",
    ),
    RegraSeed(
        codigo="PUXADOR",
        nome="Puxador",
        expressao="1",
        descricao="1 puxador por porta (por defeito).",
    ),
    RegraSeed(
        codigo="PES_NIVELADORES",
        nome="Pés niveladores",
        expressao=(
            "4 if COMP < 650 and LARG < 800 else "
            "6 if COMP >= 650 and LARG < 800 else 8"
        ),
        descricao="Pés por dimensão do fundo.",
    ),
    RegraSeed(
        codigo="SUPORTE_PRATELEIRA",
        nome="Suportes de prateleira",
        expressao=(
            "8 if COMP >= 1100 and LARG >= 800 else "
            "6 if (COMP >= 1100 or (LARG > 800 and COMP < 1100)) else 4"
        ),
        descricao="Suportes de prateleira por dimensão da prateleira.",
    ),
    RegraSeed(
        codigo="SUPORTE_TERMINAL_VARAO",
        nome="Terminais de varão",
        expressao="2",
        descricao="2 terminais por varão.",
    ),
    RegraSeed(
        codigo="SUPORTE_VARAO_CENTRAL",
        nome="Suporte central de varão",
        expressao="1 if COMP > 1100 else 0",
        descricao="Suporte central do varão só se COMP do varão > 1100mm.",
    ),
    RegraSeed(
        codigo="COSTA_NIVELADORES",
        nome="Niveladores de costa",
        expressao="2",
        descricao="2 niveladores/pendurais por costa de cozinha.",
    ),
    RegraSeed(
        codigo="RODAPE_GRAMPAS",
        nome="Grampas de rodapé",
        expressao="CEIL(COMP / 600)",
        descricao="1 grampa por cada 600mm de rodapé.",
    ),
    RegraSeed(
        codigo="VARAO_SPP",
        nome="Varão (SPP)",
        expressao="1",
        descricao="1 varão (COMP herdado para cálculo de ML).",
    ),
)


@dataclass(frozen=True)
class DefaultRegrasQuantidadeResult:
    """Summary of the quantity-rules seed."""

    criadas: int
    reutilizadas: int
    invalidas: int


def ensure_default_regras_quantidade(
    session: Session,
) -> DefaultRegrasQuantidadeResult:
    """Create or reuse the default quantity rules (idempotent)."""
    criadas = 0
    reutilizadas = 0
    invalidas = 0

    for seed in DEFAULT_REGRAS_QUANTIDADE:
        existing = session.execute(
            select(DefRegraQuantidade).where(
                DefRegraQuantidade.codigo == seed.codigo
            )
        ).scalar_one_or_none()

        if existing is not None:
            reutilizadas += 1
            print(f"Regra {seed.codigo} ja existe, mantida")
            continue

        _quantidade, motivo = avaliar_regra_quantidade(
            seed.expressao, CONTEXTO_EXEMPLO
        )
        if motivo is not None:
            invalidas += 1
            print(f"Regra {seed.codigo} IGNORADA (expressao invalida): {motivo}")
            continue

        regra = DefRegraQuantidade(
            codigo=seed.codigo,
            nome=seed.nome,
            expressao=seed.expressao,
            descricao=seed.descricao,
            ativo=True,
        )
        session.add(regra)
        session.flush()
        criadas += 1
        print(f"Regra {seed.codigo} criada")

    session.commit()

    return DefaultRegrasQuantidadeResult(
        criadas=criadas, reutilizadas=reutilizadas, invalidas=invalidas
    )


def print_summary(result: DefaultRegrasQuantidadeResult) -> None:
    """Print the final user-facing summary."""
    print("Resumo final")
    print(f"Regras criadas: {result.criadas}")
    print(f"Regras mantidas (ja existiam): {result.reutilizadas}")
    if result.invalidas:
        print(f"Regras ignoradas (invalidas): {result.invalidas}")


def main() -> int:
    """Create or reuse the default quantity rules in the configured database."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = ensure_default_regras_quantidade(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
