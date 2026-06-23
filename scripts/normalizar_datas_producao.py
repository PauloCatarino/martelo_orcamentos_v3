"""Normalize V3 production date strings to dd-mm-aaaa.

Usage:
    python -m scripts.normalizar_datas_producao --dry-run
    python -m scripts.normalizar_datas_producao
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.domain.datas import normalizar_data  # noqa: E402
from app.models.producao import Producao  # noqa: E402


@dataclass
class NormalizarDatasSummary:
    """Counters for one production date normalization run."""

    total: int = 0
    linhas_atualizadas: int = 0


def normalizar_datas(session, *, dry_run: bool) -> NormalizarDatasSummary:
    """Normalize data_inicio/data_entrega on all production rows."""
    processos = list(session.scalars(select(Producao).order_by(Producao.id.asc())).all())
    summary = NormalizarDatasSummary(total=len(processos))

    for processo in processos:
        data_inicio = normalizar_data(processo.data_inicio)
        data_entrega = normalizar_data(processo.data_entrega)
        if data_inicio == (processo.data_inicio or "") and data_entrega == (
            processo.data_entrega or ""
        ):
            continue

        summary.linhas_atualizadas += 1
        if dry_run:
            continue

        processo.data_inicio = data_inicio
        processo.data_entrega = data_entrega

    if dry_run:
        session.rollback()
    else:
        session.commit()

    return summary


def print_summary(summary: NormalizarDatasSummary, *, dry_run: bool) -> None:
    """Print the final user-facing summary."""
    modo = "DRY-RUN (sem gravar)" if dry_run else "NORMALIZACAO REAL"
    print(f"Modo: {modo}")
    print(f"total: {summary.total}")
    print(f"linhas_atualizadas: {summary.linhas_atualizadas}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Normalizar datas de producao no V3 para dd-mm-aaaa.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calcula as alterações sem gravar na base de dados.",
    )
    return parser.parse_args(sys.argv[1:] if argv is None else argv)


def main(argv: list[str] | None = None) -> int:
    """Run the production date normalization script."""
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            summary = normalizar_datas(session, dry_run=args.dry_run)
    except SQLAlchemyError as error:
        print("Nao foi possivel normalizar as datas de producao.")
        print(f"Detalhe: {error}")
        return 1

    print_summary(summary, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
