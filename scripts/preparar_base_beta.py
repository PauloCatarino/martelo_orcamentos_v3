"""Preparar a base de dados PARTILHADA do beta (martelo_v3_beta).

Faz uma COPIA COMPLETA da base de desenvolvimento para o beta:
  1. Cria o esquema completo (as 37 tabelas) correndo `alembic upgrade head`.
  2. Copia os dados de TODAS as tabelas dev -> beta.

Porque copia tudo (incluindo clientes): o id da tabela `clientes` e'
auto-incremento LOCAL, nao vem do PHC. Se o beta arrancasse sem clientes,
os orcamentos copiados (que apontam para cliente_id do dev) ficariam com
os links partidos, e re-mapear o PHC nao os restauraria (o PHC entraria com
ids novos). Copiando `clientes` com os seus ids, os orcamentos ligam-se de
imediato; o sync do PHC no beta depois so' ATUALIZA esses clientes (casa
pelo num_cliente_phc), sem partir nada.

Contexto: base de TESTES, dados descartaveis. No fim, a base de producao
sera' criada de novo e limpa. Ver historico da decisao do Paulo.

Seguro de repetir: recusa correr se o beta ja' tiver dados, para nao duplicar.

Pre-requisito (uma linha corrida pelo Paulo no Workbench, como root):
    GRANT ALL PRIVILEGES ON martelo_v3_beta.* TO 'martelo_v3'@'localhost';
    FLUSH PRIVILEGES;

Uso:
    .venv\\Scripts\\python.exe scripts\\preparar_base_beta.py
    .venv\\Scripts\\python.exe scripts\\preparar_base_beta.py --dry-run
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

# O alembic define a sua propria linha; nao copiar (evita conflito de versao).
NAO_COPIAR = {"alembic_version"}


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


def _correr_alembic_no_beta() -> None:
    print(f"[1/3] alembic upgrade head  ->  {BASE_BETA}")
    env = dict(os.environ)
    env["DATABASE_URL"] = _beta_url()
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(PROJECT_ROOT), env=env,
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        raise SystemExit("[ERRO] alembic upgrade head falhou. Nada foi copiado.")
    print("      esquema criado.")


def _copiar_tudo(dry_run: bool) -> None:
    src = settings.db_name  # base de origem (dev)
    eng = sa.create_engine(_beta_url())
    with eng.begin() as con:
        tabelas = [r[0] for r in con.execute(sa.text(
            f"SELECT TABLE_NAME FROM information_schema.TABLES "
            f"WHERE TABLE_SCHEMA = '{src}' AND TABLE_TYPE = 'BASE TABLE' "
            f"ORDER BY TABLE_NAME"))]
        tabelas = [t for t in tabelas if t not in NAO_COPIAR]

        # Salvaguarda: nao correr por cima de um beta ja' povoado.
        destino = con.execute(sa.text("SELECT COUNT(*) FROM def_materias_primas")).scalar()
        if destino:
            raise SystemExit(
                f"[ABORTADO] {BASE_BETA} ja' tem {destino} materias-primas. "
                "Se quer reconstruir do zero, esvazie o beta primeiro."
            )

        print(f"[2/3] copiar {len(tabelas)} tabelas  {src} -> {BASE_BETA}")
        if dry_run:
            for t in tabelas:
                n = con.execute(sa.text(f"SELECT COUNT(*) FROM `{src}`.`{t}`")).scalar()
                print(f"      {t:42} {n:>7} linhas (dry-run)")
            return

        con.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0"))
        total = 0
        for t in tabelas:
            n = con.execute(sa.text(f"SELECT COUNT(*) FROM `{src}`.`{t}`")).scalar()
            if n:
                con.execute(sa.text(f"INSERT INTO `{t}` SELECT * FROM `{src}`.`{t}`"))
            print(f"      {t:42} {n:>7} linhas")
            total += n
        con.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1"))
        print(f"      total copiado: {total} linhas")


def _verificar() -> None:
    print("[3/3] verificacao (dev vs beta, deve bater certo)")
    src = settings.db_name
    eng = sa.create_engine(_beta_url())
    diferencas = 0
    with eng.connect() as con:
        tabelas = [r[0] for r in con.execute(sa.text(
            f"SELECT TABLE_NAME FROM information_schema.TABLES "
            f"WHERE TABLE_SCHEMA = '{src}' AND TABLE_TYPE = 'BASE TABLE'"))]
        for t in tabelas:
            if t in NAO_COPIAR:
                continue
            a = con.execute(sa.text(f"SELECT COUNT(*) FROM `{src}`.`{t}`")).scalar()
            b = con.execute(sa.text(f"SELECT COUNT(*) FROM `{t}`")).scalar()
            if a != b:
                print(f"      !! {t}: dev={a} beta={b}")
                diferencas += 1
    if diferencas:
        print(f"      {diferencas} tabelas com contagem diferente -- verificar!")
    else:
        print("      todas as tabelas com a mesma contagem. OK.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="mostra o que faria, sem escrever")
    args = ap.parse_args()

    print(f"Origem : {settings.db_name} @ {settings.db_host}")
    print(f"Destino: {BASE_BETA} @ {settings.db_host}")
    print()
    if not args.dry_run:
        _correr_alembic_no_beta()
    _copiar_tudo(args.dry_run)
    if not args.dry_run:
        _verificar()
    print("\nConcluido." if not args.dry_run else "\nDry-run concluido.")


if __name__ == "__main__":
    main()
