"""Preparar a base de dados PARTILHADA do beta (martelo_v3_beta).

O que faz, contra a base beta (que ja' foi criada com criar_base_beta.sql):
  1. Cria o esquema completo (as 37 tabelas) correndo `alembic upgrade head`.
  2. Copia SO' a parametrizacao a partir da base de desenvolvimento:
     matterias-primas, pecas, operacoes, valuesets, modulos, maquinas,
     margens (so' as globais), regras, descricoes, system_settings e os
     utilizadores da app.
  3. NAO copia clientes, orcamentos nem producao -- ficam vazios de proposito,
     para os testadores criarem os seus. Ver a decisao do Paulo no historico.

Usa uma LISTA BRANCA (copiar estas) em vez de lista negra: se falhar em
identificar uma tabela, no pior caso ela fica vazia -- nunca expoe dados a
mais na base partilhada.

Seguro de repetir: recusa-se a correr se o beta ja' tiver dados de
parametrizacao, para nao duplicar.

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

# Lista branca: tabelas de PARAMETRIZACAO cujos dados sao copiados dev -> beta.
# Tudo o resto (clientes, orcamentos, producao, ...) fica vazio.
TABELAS_PARAMETRIZACAO = [
    "def_maquinas",
    "def_maquina_escaloes_area",
    "def_materias_primas",
    "def_modulos",
    "def_modulo_categorias",
    "def_modulo_linhas",
    "def_operacoes",
    "def_pecas",
    "def_peca_componentes",
    "def_peca_operacoes",
    "def_regras_quantidade",
    "def_valueset_modelos",
    "def_valueset_chaves",
    "def_valueset_modelo_linhas",
    "def_valueset_modelo_linha_operacoes",
    "descricoes_predefinidas",
    "system_settings",
    "users",
    "user_permissions",
]

# def_margens_padrao e' copiada a` parte: SO' as margens globais (sem cliente),
# porque as margens por cliente referem clientes que nao vamos trazer.
TABELA_MARGENS = "def_margens_padrao"


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
    print("      esquema criado (37 tabelas).")


def _copiar_parametrizacao(dry_run: bool) -> None:
    src = settings.db_name  # base de origem (dev)
    eng = sa.create_engine(_beta_url())
    with eng.begin() as con:
        # Salvaguarda: nao correr por cima de um beta ja' povoado.
        ja = con.execute(sa.text(f"SELECT COUNT(*) FROM `{src}`.def_materias_primas")).scalar()
        destino = con.execute(sa.text("SELECT COUNT(*) FROM def_materias_primas")).scalar()
        if destino:
            raise SystemExit(
                f"[ABORTADO] {BASE_BETA} ja' tem {destino} materias-primas. "
                "Se quer reconstruir do zero, esvazie o beta primeiro."
            )
        print(f"[2/3] copiar parametrizacao  {src} -> {BASE_BETA}  ({ja} materias-primas na origem)")

        if dry_run:
            print("      (dry-run: nada e' escrito)")
            return

        con.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0"))
        total = 0
        for tab in TABELAS_PARAMETRIZACAO:
            n = con.execute(sa.text(f"SELECT COUNT(*) FROM `{src}`.`{tab}`")).scalar()
            con.execute(sa.text(f"INSERT INTO `{tab}` SELECT * FROM `{src}`.`{tab}`"))
            print(f"      {tab:40} {n:>6} linhas")
            total += n

        # Margens: so' as globais (cliente_id IS NULL).
        cols = [r[0] for r in con.execute(sa.text(
            f"SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            f"WHERE TABLE_SCHEMA = '{src}' AND TABLE_NAME = '{TABELA_MARGENS}' "
            f"ORDER BY ORDINAL_POSITION"))]
        lista = ", ".join(f"`{c}`" for c in cols)
        nm = con.execute(sa.text(
            f"INSERT INTO `{TABELA_MARGENS}` ({lista}) "
            f"SELECT {lista} FROM `{src}`.`{TABELA_MARGENS}` WHERE cliente_id IS NULL"
        )).rowcount
        saltadas = con.execute(sa.text(
            f"SELECT COUNT(*) FROM `{src}`.`{TABELA_MARGENS}` WHERE cliente_id IS NOT NULL")).scalar()
        print(f"      {TABELA_MARGENS:40} {nm:>6} linhas  ({saltadas} por-cliente ignoradas)")
        total += nm

        con.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1"))
        print(f"      total copiado: {total} linhas")


def _verificar() -> None:
    print("[3/3] verificacao")
    eng = sa.create_engine(_beta_url())
    with eng.connect() as con:
        vazias = ["clientes", "orcamentos", "producao"]
        for t in vazias:
            n = con.execute(sa.text(f"SELECT COUNT(*) FROM `{t}`")).scalar()
            estado = "OK (vazia)" if n == 0 else f"!! TEM {n} LINHAS"
            print(f"      {t:20} {estado}")
        mp = con.execute(sa.text("SELECT COUNT(*) FROM def_materias_primas")).scalar()
        print(f"      def_materias_primas  {mp} linhas (deve ser > 0)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="mostra o que faria, sem escrever")
    args = ap.parse_args()

    print(f"Origem : {settings.db_name} @ {settings.db_host}")
    print(f"Destino: {BASE_BETA} @ {settings.db_host}")
    print()
    if not args.dry_run:
        _correr_alembic_no_beta()
    _copiar_parametrizacao(args.dry_run)
    if not args.dry_run:
        _verificar()
    print("\nConcluido." if not args.dry_run else "\nDry-run concluido.")


if __name__ == "__main__":
    main()
