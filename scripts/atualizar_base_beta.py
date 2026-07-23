"""Aplicar as migracoes pendentes na base PARTILHADA do beta.

O `preparar_base_beta.py` cria o beta de raiz. Este script serve para o caso
normal do dia a dia: o beta ja' existe, com dados que o Paulo e os colegas
andaram a criar, e so' falta apanhar as migracoes novas que entretanto
entraram no dev.

Nao copia nem apaga dados nenhuns: corre apenas `alembic upgrade head`
contra a base do beta.

Uso:
    .venv\\Scripts\\python.exe scripts\\atualizar_base_beta.py --ver
    .venv\\Scripts\\python.exe scripts\\atualizar_base_beta.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import sqlalchemy as sa

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402

BASE_BETA = "martelo_v3_beta"


def _beta_url() -> str:
    return sa.engine.URL.create(
        "mysql+pymysql",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.db_host,
        port=int(settings.db_port),
        database=BASE_BETA,
        query={"charset": settings.db_charset or "utf8mb4"},
    ).render_as_string(hide_password=False)


def _correr_alembic(comando: list[str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["DATABASE_URL"] = _beta_url()
    return subprocess.run(
        [sys.executable, "-m", "alembic", *comando],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _versao_atual() -> str:
    res = _correr_alembic(["current"])
    return (res.stdout or "").strip() or "(desconhecida)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aplicar as migracoes pendentes na base do beta."
    )
    parser.add_argument(
        "--ver",
        action="store_true",
        help="So mostra em que migracao esta o beta, sem alterar nada.",
    )
    args = parser.parse_args()

    print(f"Base do beta: {BASE_BETA} em {settings.db_host}")
    print(f"Versao atual no beta: {_versao_atual()}")

    if args.ver:
        print("Nada foi alterado (--ver).")
        return 0

    print("A aplicar alembic upgrade head...")
    res = _correr_alembic(["upgrade", "head"])
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        print("[ERRO] A atualizacao falhou. O beta ficou como estava.")
        return 1

    print(res.stdout.strip())
    print(f"Versao depois da atualizacao: {_versao_atual()}")
    print("Beta atualizado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
