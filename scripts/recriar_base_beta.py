"""Recriar TODOS os dados da beta (martelo_v3_beta) a partir do dev (V3).

Substitui os dados da beta por uma copia EXATA do dev, mantendo o esquema.
Use-o quando a beta precisa de refletir tudo o que foi criado no V3 desde a
ultima copia: novas definicoes de pecas, orcamentos, obras da producao,
modelos ValueSet, clientes, etc. A beta e' de TESTES/descartavel.

Diferenca para os outros scripts:
  - ``atualizar_base_beta.py``  -> so' o ESQUEMA (alembic upgrade head).
  - ``preparar_base_beta.py``   -> primeira criacao (recusa se ja' tiver dados).
  - ``recriar_base_beta.py``    -> ESTE: refrescar os DADOS numa beta ja' povoada.

SEGURANCA (porque nao e' corrido pela IA):
  - A camada anti-eliminacao (hooks) impede a IA de apagar dados em massa;
    por isso este script e' para o PAULO correr no terminal.
  - Exige ``--confirmar`` (apaga os dados atuais da beta, incluindo o que os
    colegas tenham criado nos testes).
  - Recusa correr se o esquema dev != beta (corra antes as migracoes com
    ``scripts/atualizar_base_beta.py``).
  - FACA UM BACKUP ANTES:
      mysqldump -h 192.168.5.201 -u martelo_v3 -p ^
        --single-transaction --routines --triggers ^
        --databases martelo_v3_beta > backup_beta.sql

Uso:
    .venv\\Scripts\\python.exe scripts\\recriar_base_beta.py --dry-run
    .venv\\Scripts\\python.exe scripts\\recriar_base_beta.py --confirmar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sqlalchemy as sa

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from scripts.preparar_base_beta import BASE_BETA, NAO_COPIAR, _beta_url  # noqa: E402


def _tabelas(con, schema: str) -> list[str]:
    rows = con.execute(sa.text(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = :s AND TABLE_TYPE = 'BASE TABLE' "
        "ORDER BY TABLE_NAME"
    ), {"s": schema})
    return [r[0] for r in rows if r[0] not in NAO_COPIAR]


def _colunas(con, schema: str) -> set[tuple[str, str]]:
    rows = con.execute(sa.text(
        "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = :s"
    ), {"s": schema})
    return {(r[0], r[1]) for r in rows}


def _verificar_esquema(con, src: str) -> list[str]:
    """Aborta se o esquema dev != beta. Devolve as tabelas a copiar."""
    tab_src = set(_tabelas(con, src))
    tab_dst = set(_tabelas(con, BASE_BETA))
    if tab_src != tab_dst:
        so_dev = sorted(tab_src - tab_dst)
        so_beta = sorted(tab_dst - tab_src)
        raise SystemExit(
            "[ABORTADO] o esquema da beta nao bate certo com o dev.\n"
            f"       so' no dev : {so_dev or '-'}\n"
            f"       so' na beta: {so_beta or '-'}\n"
            "       Corra primeiro:  scripts\\atualizar_base_beta.py"
        )
    dif_col = _colunas(con, src) ^ _colunas(con, BASE_BETA)
    if dif_col:
        raise SystemExit(
            f"[ABORTADO] ha {len(dif_col)} colunas diferentes entre dev e beta.\n"
            "       Corra primeiro:  scripts\\atualizar_base_beta.py"
        )
    return sorted(tab_src)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="mostra o que faria, sem escrever")
    ap.add_argument("--confirmar", action="store_true",
                    help="APAGA os dados atuais da beta e copia do dev")
    args = ap.parse_args()

    src = settings.db_name  # base de origem (dev)

    # ------------------------------------------------------------------
    # A barreira que faltava, e que custou uma beta apagada.
    #
    # O `db_name` vem do .env -- MAS uma variavel de ambiente
    # (`$env:DB_NAME="martelo_v3_beta"`, escrita numa sessao anterior do
    # PowerShell para abrir a app contra a beta) manda mais que o .env e fica
    # ali colada ate' se fechar o terminal.
    #
    # Com origem == destino, o que este script faz e': apagar tudo, e depois
    # "copiar" de uma base que ele proprio acabou de esvaziar. Zero linhas
    # copiadas -- e a verificacao final ainda diz OK, porque compara zero com
    # zero. E' o pior tipo de falha: destroi e diz que correu bem.
    # ------------------------------------------------------------------
    if src == BASE_BETA:
        raise SystemExit(
            "[ABORTADO] a origem e o destino sao a mesma base "
            f"({BASE_BETA}).\n"
            "       Isto apagaria a beta e nao copiaria nada.\n\n"
            "       Quase de certeza tem DB_NAME definido no terminal:\n"
            "           $env:DB_NAME     (para ver)\n"
            "           Remove-Item Env:DB_NAME   (para limpar)\n"
            "       ...ou abra um terminal novo e volte a correr."
        )

    print(f"Origem : {src} @ {settings.db_host}")
    print(f"Destino: {BASE_BETA} @ {settings.db_host}  (dados vao ser SUBSTITUIDOS)")
    print()

    eng = sa.create_engine(_beta_url())
    with eng.connect() as con:
        tabelas = _verificar_esquema(con, src)
        print(f"esquema dev == beta  ({len(tabelas)} tabelas). OK.\n")
        # Pre-visualizacao das diferencas de contagem.
        print(f"{'tabela':42} {'dev':>8} {'beta':>8}")
        total_dev = 0
        for t in tabelas:
            a = con.execute(sa.text(f"SELECT COUNT(*) FROM `{src}`.`{t}`")).scalar()
            b = con.execute(sa.text(f"SELECT COUNT(*) FROM `{BASE_BETA}`.`{t}`")).scalar()
            marca = "  <-- dif" if a != b else ""
            print(f"{t:42} {a:>8} {b:>8}{marca}")
            total_dev += a

    if args.dry_run or not args.confirmar:
        print("\n(dry-run) Nada foi alterado.")
        if not args.confirmar:
            print("Para recriar mesmo, volte a correr com  --confirmar")
        return

    print("\na recriar os dados...")
    with eng.begin() as con:
        con.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0"))
        for t in tabelas:
            con.execute(sa.text(f"DELETE FROM `{BASE_BETA}`.`{t}`"))
        copiado = 0
        for t in tabelas:
            n = con.execute(sa.text(f"SELECT COUNT(*) FROM `{src}`.`{t}`")).scalar()
            if n:
                con.execute(sa.text(
                    f"INSERT INTO `{BASE_BETA}`.`{t}` SELECT * FROM `{src}`.`{t}`"
                ))
            copiado += n
        con.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1"))
    print(f"copiado: {copiado} linhas")

    # Copiar zero linhas de uma base com dados nao e' "nada a fazer" -- e' sinal
    # de que se apagou o destino e se leu de um sitio vazio. A verificacao la'
    # em baixo nao apanha isto, porque comparar zero com zero da' certo.
    if copiado == 0:
        raise SystemExit(
            "[ATENCAO] nao foi copiada uma unica linha, mas os dados da beta "
            "ja' foram apagados.\n"
            "       Restaure o backup ANTES de fazer mais alguma coisa:\n"
            '         & "C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\mysql.exe" '
            "-h 127.0.0.1 -u martelo_v3 -p -e \"source <backup>.sql\""
        )

    _desligar_o_que_nao_pode_vir_do_dev(eng)

    # Verificacao final.
    dif = 0
    with eng.connect() as con:
        for t in tabelas:
            a = con.execute(sa.text(f"SELECT COUNT(*) FROM `{src}`.`{t}`")).scalar()
            b = con.execute(sa.text(f"SELECT COUNT(*) FROM `{BASE_BETA}`.`{t}`")).scalar()
            if a != b:
                print(f"  !! {t}: dev={a} beta={b}")
                dif += 1
    print("VERIFICACAO:", "todas as tabelas batem certo. OK." if not dif
          else f"{dif} tabelas diferentes -- verificar!")
    print("\nConcluido. A beta reflete agora o V3 (dev).")


#: Definicoes que NAO podem vir do dev para a beta, com o valor seguro.
#:
#: A copia leva a `system_settings` inteira, e ha' definicoes em que o valor do
#: dev e' perigoso na beta -- desde logo o interruptor da escrita no iMos. Se
#: viesse ligado, um colega a experimentar a beta criava encomendas A SERIO no
#: iMos, a pensar que estava a brincar.
DEFINICOES_A_DESLIGAR = {
    "imos_escrita_ativa": "OFF",
}


def _desligar_o_que_nao_pode_vir_do_dev(eng) -> None:
    """Poe as definicoes perigosas no valor seguro, depois da copia."""
    with eng.begin() as con:
        for chave, seguro in DEFINICOES_A_DESLIGAR.items():
            atual = con.execute(
                sa.text(
                    f"SELECT valor FROM `{BASE_BETA}`.system_settings "
                    "WHERE chave = :chave"
                ),
                {"chave": chave},
            ).scalar()
            if atual is None or str(atual).strip().upper() == seguro:
                continue
            con.execute(
                sa.text(
                    f"UPDATE `{BASE_BETA}`.system_settings SET valor = :seguro "
                    "WHERE chave = :chave"
                ),
                {"seguro": seguro, "chave": chave},
            )
            print(f"  seguranca: {chave} = {seguro} (no dev estava {atual!r})")


if __name__ == "__main__":
    main()
