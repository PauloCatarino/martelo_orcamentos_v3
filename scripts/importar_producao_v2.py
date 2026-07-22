"""Synchronise production processes from Martelo V2 into Martelo V3.

This upsert overwrites V3 production fields from V2. Run it only when V2 should
remain the source of truth, or review the merge policy before syncing over V3
manual edits.

Usage:
    python -m scripts.importar_producao_v2 --dry-run
    python -m scripts.importar_producao_v2
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.engine import Engine, URL  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app.services.producao_v2_sync_service import (  # noqa: E402
    CAMPOS_DIRETOS_V2_V3,
    mapear_estado,
    mapear_linha,
)


V2_DEFAULT_HOST = "192.168.5.201"
V2_DEFAULT_PORT = "3306"
V2_DEFAULT_DB_NAME = "orcamentos_v2"

__all__ = [
    "CAMPOS_DIRETOS_V2_V3",
    "mapear_estado",
    "mapear_linha",
    "main",
]


class ConfigError(RuntimeError):
    """Raised when the V2 connection environment is incomplete or invalid."""


@dataclass
class ImportSummary:
    """Counters for one production sync run."""

    total_v2: int = 0
    criados: int = 0
    atualizados: int = 0
    sem_cliente_associado: int = 0
    sem_orcamento_associado: int = 0
    erros: int = 0
    avisos: list[str] = field(default_factory=list)


def criar_engine_v2() -> Engine:
    """Create the read-only V2 engine from env vars."""
    return create_engine(_v2_database_url(), pool_pre_ping=True, future=True)


def ler_linhas_v2(engine: Engine) -> list[Mapping[str, Any]]:
    """Read all V2 production rows. This function only executes SELECT."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM producao"))
        return list(result.mappings())


def sincronizar_linhas(
    session,
    linhas_v2: Sequence[Mapping[str, Any]],
    *,
    dry_run: bool,
) -> ImportSummary:
    """Create or update V3 production rows from V2 rows."""
    from app.models.producao import Producao

    summary = ImportSummary(total_v2=len(linhas_v2))

    for v2_row in linhas_v2:
        try:
            valores = mapear_linha(v2_row)
            codigo_processo = _texto_obrigatorio(valores.get("codigo_processo"))

            cliente_id = _resolver_cliente_id(session, valores.get("num_cliente_phc"))
            orcamento_id = _resolver_orcamento_id(
                session,
                valores.get("ano"),
                valores.get("num_orcamento"),
            )
            if cliente_id is None:
                summary.sem_cliente_associado += 1
            if orcamento_id is None:
                summary.sem_orcamento_associado += 1

            existing = session.scalar(
                select(Producao).where(Producao.codigo_processo == codigo_processo)
            )

            if dry_run:
                if existing is None:
                    summary.criados += 1
                else:
                    summary.atualizados += 1
                continue

            if existing is None:
                processo = Producao()
                _aplicar_valores(processo, valores, cliente_id, orcamento_id)
                session.add(processo)
                session.flush()
                session.commit()
                summary.criados += 1
            else:
                _aplicar_valores(existing, valores, cliente_id, orcamento_id)
                session.flush()
                session.commit()
                summary.atualizados += 1
        except (ValueError, SQLAlchemyError) as error:
            summary.erros += 1
            codigo = _row_get(v2_row, "codigo_processo") or "<sem codigo_processo>"
            summary.avisos.append(f"{codigo}: {error}")
            session.rollback()

    if dry_run:
        session.rollback()

    return summary


def print_summary(summary: ImportSummary, *, dry_run: bool) -> None:
    """Print the final user-facing sync summary."""
    modo = "DRY-RUN (sem gravar no V3)" if dry_run else "IMPORTACAO REAL"
    print(f"Modo: {modo}")
    print(f"total_v2: {summary.total_v2}")
    print(f"criados: {summary.criados}")
    print(f"atualizados: {summary.atualizados}")
    print(f"sem_cliente_associado: {summary.sem_cliente_associado}")
    print(f"sem_orcamento_associado: {summary.sem_orcamento_associado}")
    print(f"erros: {summary.erros}")
    for aviso in summary.avisos[:20]:
        print(f"  - {aviso}")
    if len(summary.avisos) > 20:
        print(f"  ... e mais {len(summary.avisos) - 20} erros/avisos")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Sincronizar obras de producao do Martelo V2 para o V3.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Le e mapeia sem gravar alteracoes no V3.",
    )
    return parser.parse_args(sys.argv[1:] if argv is None else argv)


def main(argv: list[str] | None = None) -> int:
    """Run the V2 -> V3 production sync."""
    args = parse_args(argv)

    try:
        engine_v2 = criar_engine_v2()
    except ConfigError as error:
        print(str(error))
        return 2

    try:
        linhas_v2 = ler_linhas_v2(engine_v2)
    except SQLAlchemyError as error:
        print("Nao foi possivel ligar/ler a base de dados V2.")
        print(f"Detalhe: {error}")
        return 1

    from app.db.session import SessionLocal

    try:
        with SessionLocal() as session:
            summary = sincronizar_linhas(session, linhas_v2, dry_run=args.dry_run)
    except SQLAlchemyError as error:
        print("Nao foi possivel escrever/consultar a base de dados V3.")
        print(f"Detalhe: {error}")
        return 1

    print_summary(summary, dry_run=args.dry_run)
    return 0 if summary.erros == 0 else 1


def _v2_database_url() -> str | URL:
    url = os.environ.get("V2_DATABASE_URL")
    if url:
        return url

    user = os.environ.get("V2_DB_USER")
    password = os.environ.get("V2_DB_PASSWORD")
    if not user or not password:
        raise ConfigError(
            "Faltam credenciais do V2. Defina V2_DB_USER e V2_DB_PASSWORD, "
            "ou V2_DATABASE_URL completo."
        )

    port_text = os.environ.get("V2_DB_PORT", V2_DEFAULT_PORT)
    try:
        port = int(port_text)
    except ValueError as error:
        raise ConfigError(f"V2_DB_PORT invalido: {port_text!r}") from error

    return URL.create(
        "mysql+pymysql",
        username=user,
        password=password,
        host=os.environ.get("V2_DB_HOST", V2_DEFAULT_HOST),
        port=port,
        database=os.environ.get("V2_DB_NAME", V2_DEFAULT_DB_NAME),
        query={"charset": "utf8mb4"},
    )


def _resolver_cliente_id(session, num_cliente_phc: object) -> int | None:
    from app.models.cliente import Cliente

    numero = _texto_opcional(num_cliente_phc)
    if numero is None:
        return None

    return session.scalar(
        select(Cliente.id).where(Cliente.num_cliente_phc == numero).limit(1)
    )


def _resolver_orcamento_id(
    session,
    ano: object,
    num_orcamento: object,
) -> int | None:
    from app.models.orcamento import Orcamento

    numero = _texto_opcional(num_orcamento)
    if numero is None:
        return None

    try:
        ano_int = int(str(ano).strip())
    except (TypeError, ValueError):
        return None

    return session.scalar(
        select(Orcamento.id)
        .where(Orcamento.ano == ano_int, Orcamento.num_orcamento == numero)
        .limit(1)
    )


def _aplicar_valores(
    processo,
    valores: Mapping[str, Any],
    cliente_id: int | None,
    orcamento_id: int | None,
) -> None:
    for campo, valor in valores.items():
        if campo in {"created_at", "updated_at"} and valor is None:
            continue
        setattr(processo, campo, valor)

    processo.cliente_id = cliente_id
    processo.orcamento_id = orcamento_id
    processo.created_by_id = None
    processo.updated_by_id = None


def _texto_obrigatorio(valor: object) -> str:
    texto = _texto_opcional(valor)
    if texto is None:
        raise ValueError("codigo_processo vazio")
    return texto


def _texto_opcional(valor: object) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _row_get(row: Mapping[str, Any], key: str) -> Any:
    return row.get(key)


if __name__ == "__main__":
    raise SystemExit(main())
