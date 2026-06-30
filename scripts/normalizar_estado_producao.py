"""Normalize the production state to the canonical 'Producao' (no accent).

Idempotente: muda as obras cujo ``estado`` está na forma acentuada 'Produção'
para 'Producao'. Útil para PCs/BDs com dados antigos; numa BD já limpa devolve 0.

Uso:
    python -m scripts.normalizar_estado_producao --dry-run
    python -m scripts.normalizar_estado_producao
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select, update  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.producao import Producao  # noqa: E402

ESTADO_CANONICO = "Producao"
# Variante acentuada a normalizar ("Produção"); ç=U+00E7, ã=U+00E3.
ESTADO_ACENTUADO = "Produção"


def normalizar_estado(session, *, dry_run: bool) -> int:
    """Põe estado='Producao' nas linhas com 'Produção'. Devolve quantas afeta.

    A comparação é feita em Python (exata, sensível a acentos) e a atualização
    por ``id``: a collation do MySQL costuma ser insensível a acentos, pelo que um
    ``WHERE estado = 'Produção'`` apanharia também as linhas 'Producao' já corretas.
    """
    linhas = session.execute(select(Producao.id, Producao.estado)).all()
    ids = [pid for pid, estado in linhas if estado == ESTADO_ACENTUADO]
    afetadas = len(ids)

    if not dry_run and ids:
        session.execute(
            update(Producao)
            .where(Producao.id.in_(ids))
            .values(estado=ESTADO_CANONICO)
        )
        session.commit()
    else:
        session.rollback()

    return afetadas


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Normalizar o estado de producao para 'Producao' (sem acento).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Conta as linhas a alterar sem gravar na base de dados.",
    )
    return parser.parse_args(sys.argv[1:] if argv is None else argv)


def main(argv: list[str] | None = None) -> int:
    """Run the production state normalization script."""
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            afetadas = normalizar_estado(session, dry_run=args.dry_run)
    except SQLAlchemyError as error:
        print("Nao foi possivel normalizar o estado de producao.")
        print(f"Detalhe: {error}")
        return 1

    modo = "DRY-RUN (sem gravar)" if args.dry_run else "NORMALIZACAO REAL"
    print(f"Modo: {modo}")
    print(f"linhas_afetadas: {afetadas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
