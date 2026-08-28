"""Criar a base de dados OFICIAL do Martelo V3, a partir da de desenvolvimento.

O QUE ISTO FAZ
--------------
Cria uma base nova (por omissao `martelo_v3`) com:

  - a estrutura TODA da dev (as 59 tabelas, os indices, os procedimentos)
  - os DADOS de tudo o que e' trabalho a serio: clientes, materias-primas,
    definicoes de pecas, modelos, maquinas, utilizadores, configuracoes, obras
  - SEM os orcamentos: esses foram de teste e o programa comeca do zero

E aplica os privilegios, para as contas dos colegas entrarem no primeiro dia.

O QUE ISTO **NAO** FAZ
----------------------
Nao apaga nada, em lado nenhum. A base de desenvolvimento fica exatamente como
esta'. Os orcamentos de teste nao sao apagados -- simplesmente nao sao copiados.
Se algo correr mal, a saida e' apagar a base nova e voltar a comecar.

PRECISA DA CONTA root
---------------------
Criar bases, copiar procedimentos e distribuir privilegios sao coisas que a
conta de manutencao (martelo_v3) nao pode fazer.

COMO SE USA
-----------
    .venv\\Scripts\\python.exe scripts\\criar_base_producao.py --ver
    .venv\\Scripts\\python.exe scripts\\criar_base_producao.py --root root
"""

from __future__ import annotations

import argparse
import getpass
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.domain.orcamento_numeracao import (  # noqa: E402
    chave_numero_minimo,
    primeiro_numero_do_ano,
)

#: Ano em que o V3 entra ao servico -- o unico que herda numeros do V2.
ANO_ARRANQUE = 2026


def _do_backup(nome: str):
    """Reaproveita uma funcao do backup_martelo.py (a pasta scripts nao e' pacote)."""
    caminho = Path(__file__).resolve().parent / "backup_martelo.py"
    spec = importlib.util.spec_from_file_location("backup_martelo", caminho)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return getattr(modulo, nome)

ORIGEM = "martelo_v3_dev"
DESTINO = "martelo_v3"

#: Tabelas cujos DADOS ficam para tras.
#:
#: Sao os orcamentos e tudo o que pende deles. Foram feitos para experimentar o
#: programa e nao fazem parte do trabalho da empresa; o Martelo comeca do zero.
#: A ESTRUTURA vem toda na mesma -- o que fica de fora sao so' as linhas.
SEM_DADOS = (
    "orcamentos",
    "orcamento_versoes",
    "orcamento_items",
    "orcamento_item_modulos",
    "orcamento_item_variaveis",
    "orcamento_item_custeio_linhas",
    "orcamento_item_custeio_linha_operacoes",
    "orcamento_item_valueset_linhas",
    "orcamento_item_valueset_linha_operacoes",
    "orcamento_valueset_linhas",
    "orcamento_valueset_linha_operacoes",
    "orcamento_versao_eventos",
    "orcamento_versao_encomendas_phc",
    "orcamento_versao_placa_nao_stock",
    "orcamento_tempo_atividade",
)

#: O que vem com dados, agrupado para o resumo fazer sentido a quem le.
FAMILIAS = {
    "Catalogo e definicoes": ("def_",),
    "Assistente da Lista de Material": ("lm_",),
    "Clientes": ("clientes",),
    "Producao": ("producao",),
    "Utilizadores e configuracao": ("users", "user_", "system_settings", "equipa_"),
}


def _ligar(utilizador: str, password: str, base: str | None = None):
    import pymysql

    return pymysql.connect(
        host=settings.DB_HOST,
        port=int(settings.DB_PORT),
        user=utilizador,
        password=password,
        database=base,
        connect_timeout=8,
    )


def _tabelas(ligacao, base: str) -> list[str]:
    with ligacao.cursor() as cursor:
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
            (base,),
        )
        return [linha[0] for linha in cursor.fetchall()]


def _linhas(ligacao, base: str, tabela: str) -> int:
    with ligacao.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM `{base}`.`{tabela}`")
        return int(cursor.fetchone()[0])


def _familia(tabela: str) -> str:
    for nome, prefixos in FAMILIAS.items():
        if any(tabela.startswith(prefixo) for prefixo in prefixos):
            return nome
    return "Outras"


def mostrar_plano(ligacao, origem: str) -> tuple[list[str], list[str]]:
    """Diz, tabela a tabela, o que vem e o que fica. Devolve (com dados, sem)."""
    tabelas = _tabelas(ligacao, origem)
    desconhecidas = [t for t in SEM_DADOS if t not in tabelas]
    if desconhecidas:
        raise SystemExit(
            "[ERRO] estas tabelas estao na lista de 'sem dados' mas nao existem "
            f"na {origem}: {', '.join(desconhecidas)}.\n"
            "       A lista ficou desatualizada; corrija-a antes de continuar."
        )

    com_dados = [t for t in tabelas if t not in SEM_DADOS]
    sem_dados = [t for t in tabelas if t in SEM_DADOS]

    print(f"\nDE  {origem}   ->   PARA  {DESTINO}\n")

    print("VEM COM OS DADOS (o trabalho a serio):")
    por_familia: dict[str, list[tuple[str, int]]] = {}
    for tabela in com_dados:
        por_familia.setdefault(_familia(tabela), []).append(
            (tabela, _linhas(ligacao, origem, tabela))
        )
    for familia in sorted(por_familia):
        linhas = sum(n for _, n in por_familia[familia])
        tabelas_familia = len(por_familia[familia])
        print(f"   {familia:32} {tabelas_familia:3} tabelas   {linhas:6} linhas")

    print("\nVEM SO' A ESTRUTURA, SEM AS LINHAS (os orcamentos de teste):")
    total_deixado = 0
    for tabela in sem_dados:
        quantas = _linhas(ligacao, origem, tabela)
        total_deixado += quantas
        if quantas:
            print(f"   {tabela:44} {quantas:6} linhas ficam para tras")
    print(f"\n   {total_deixado} linhas de orcamentos de teste NAO sao copiadas.")
    print(f"   (Continuam na {origem}, intactas. Nada e' apagado.)")

    return com_dados, sem_dados


def _correr_mysql(mysql: Path, opcoes: Path, base: str | None, sql_stdin) -> None:
    comando = [str(mysql), f"--defaults-file={opcoes}"]
    if base:
        comando.append(base)
    processo = subprocess.run(comando, stdin=sql_stdin, capture_output=True)
    if processo.returncode != 0:
        texto = processo.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"[ERRO] o mysql falhou:\n{texto}")


def _opcoes_root(pasta: Path, utilizador: str, password: str) -> Path:
    """Ficheiro de opcoes, para a password nao ir na linha de comandos."""
    caminho = pasta / "my.cnf"
    caminho.write_text(
        "[client]\n"
        f"user={utilizador}\n"
        f"password={password}\n"
        f"host={settings.DB_HOST}\n"
        f"port={settings.DB_PORT}\n",
        encoding="utf-8",
    )
    return caminho


def criar(
    utilizador: str, password: str, origem: str, destino: str, com_dados: list[str]
) -> None:
    """Cria a base nova: estrutura toda + dados so' das tabelas escolhidas."""
    mysqldump = _do_backup("encontrar_mysqldump")()
    mysql = mysqldump.parent / "mysql.exe"
    if not mysql.exists():
        raise SystemExit(f"[ERRO] nao encontrei o mysql.exe ao lado de {mysqldump}")

    with tempfile.TemporaryDirectory(prefix="martelo_prod_") as temporaria:
        pasta = Path(temporaria)
        opcoes = _opcoes_root(pasta, utilizador, password)

        print(f"\n[1/5] criar a base {destino}")
        ligacao = _ligar(utilizador, password)
        with ligacao.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s",
                (destino,),
            )
            if int(cursor.fetchone()[0]):
                raise SystemExit(
                    f"[ERRO] a base `{destino}` ja' existe.\n"
                    "       Este script nunca escreve por cima de uma base que ja'\n"
                    "       exista. Escolha outro nome com --destino, ou apague essa\n"
                    "       base a` mao no Workbench se tiver a certeza."
                )
            cursor.execute(
                f"CREATE DATABASE `{destino}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        ligacao.commit()
        print("      OK")

        # 2. Estrutura de tudo + procedimentos.
        print("[2/5] copiar a estrutura e os procedimentos")
        estrutura = pasta / "estrutura.sql"
        with estrutura.open("wb") as saida:
            resultado = subprocess.run(
                [
                    str(mysqldump), f"--defaults-file={opcoes}",
                    "--no-data", "--routines", "--triggers", "--events",
                    "--no-tablespaces", "--default-character-set=utf8mb4",
                    origem,
                ],
                stdout=saida, stderr=subprocess.PIPE,
            )
        if resultado.returncode != 0:
            raise SystemExit(
                "[ERRO] nao consegui copiar a estrutura:\n"
                + resultado.stderr.decode("utf-8", errors="replace")
            )
        with estrutura.open("rb") as entrada:
            _correr_mysql(mysql, opcoes, destino, entrada)
        print(f"      OK ({estrutura.stat().st_size/1024:.0f} KB)")

        # 3. Dados, so' das tabelas que vem.
        print(f"[3/5] copiar os dados ({len(com_dados)} tabelas)")
        dados = pasta / "dados.sql"
        with dados.open("wb") as saida:
            resultado = subprocess.run(
                [
                    str(mysqldump), f"--defaults-file={opcoes}",
                    "--no-create-info", "--single-transaction", "--no-tablespaces",
                    "--default-character-set=utf8mb4", "--hex-blob",
                    origem, *com_dados,
                ],
                stdout=saida, stderr=subprocess.PIPE,
            )
        if resultado.returncode != 0:
            raise SystemExit(
                "[ERRO] nao consegui copiar os dados:\n"
                + resultado.stderr.decode("utf-8", errors="replace")
            )
        with dados.open("rb") as entrada:
            _correr_mysql(mysql, opcoes, destino, entrada)
        print(f"      OK ({dados.stat().st_size/1024/1024:.1f} MB)")

        # 4. Privilegios.
        print("[4/5] dar acesso as contas dos colegas")
        ligacao_destino = _ligar(utilizador, password, destino)
        with ligacao_destino.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.routines "
                "WHERE routine_schema = DATABASE() "
                "AND routine_name = 'martelo_aplicar_grants'"
            )
            if int(cursor.fetchone()[0]):
                cursor.execute("CALL martelo_aplicar_grants()")
                print("      OK (martelo_aplicar_grants)")
            else:
                print("      AVISO: o procedimento martelo_aplicar_grants nao veio.")
                print("             Corra o deploy\\mysql_contas_beta.sql nesta base.")
        ligacao_destino.commit()
        ligacao_destino.close()

        # 5. Conferir.
        print("[5/5] conferir")
        with ligacao.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE'", (destino,)
            )
            tabelas = int(cursor.fetchone()[0])
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = %s",
                (destino,),
            )
            rotinas = int(cursor.fetchone()[0])
            cursor.execute(f"SELECT version_num FROM `{destino}`.alembic_version")
            migracao = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM `{destino}`.orcamentos")
            orcamentos = int(cursor.fetchone()[0])
            cursor.execute(f"SELECT COUNT(*) FROM `{destino}`.clientes")
            clientes = int(cursor.fetchone()[0])
            cursor.execute(f"SELECT COUNT(*) FROM `{destino}`.users")
            utilizadores = int(cursor.fetchone()[0])
            # O piso da numeracao: sem ele o primeiro orcamento a serio ia
            # escrever dentro da pasta de um cliente do Martelo V2.
            cursor.execute(
                f"SELECT valor FROM `{destino}`.system_settings "
                "WHERE chave = %s AND ativo = 1",
                (chave_numero_minimo(ANO_ARRANQUE),),
            )
            linha = cursor.fetchone()
            piso = str(linha[0]).strip() if linha and linha[0] else ""
        ligacao.close()

        print(f"      {tabelas} tabelas, {rotinas} procedimentos, migracao {migracao}")
        print(f"      {clientes} clientes, {utilizadores} utilizadores, "
              f"{orcamentos} orcamentos (zero, como devia ser)")

        if orcamentos:
            raise SystemExit(
                f"[ERRO] a base nova ficou com {orcamentos} orcamentos e devia ter 0."
            )

        if piso.isdigit():
            print(f"      o primeiro orcamento de {ANO_ARRANQUE} vai ser o {piso}")
        else:
            raise SystemExit(
                f"[ERRO] falta o piso da numeracao de {ANO_ARRANQUE} nesta base.\n"
                f"       Sem ele o Martelo comeca no "
                f"{primeiro_numero_do_ano(ANO_ARRANQUE)} e escreve por cima das\n"
                "       pastas dos orcamentos do Martelo V2, uma a uma.\n"
                f"       A base de origem ({origem}) tem de estar na migracao\n"
                "       20260828_97 ou mais recente:\n"
                "           .venv\\Scripts\\alembic.exe upgrade head"
            )


def main() -> int:
    ap = argparse.ArgumentParser(description="Criar a base oficial do Martelo V3")
    ap.add_argument("--origem", default=ORIGEM)
    ap.add_argument("--destino", default=DESTINO)
    ap.add_argument("--root", default="root", help="conta com poder de criar bases")
    ap.add_argument("--ver", action="store_true",
                    help="so' mostrar o que ia acontecer, sem criar nada")
    args = ap.parse_args()

    print("Martelo V3 - criar a base de dados oficial")

    password = getpass.getpass(f"Password de '{args.root}': ")
    try:
        ligacao = _ligar(args.root, password)
    except Exception as erro:  # noqa: BLE001
        raise SystemExit(f"[ERRO] nao consegui entrar como '{args.root}': {erro}")

    com_dados, _ = mostrar_plano(ligacao, args.origem)
    ligacao.close()

    if args.ver:
        print("\n(--ver: nao criei nada.)")
        return 0

    print(f"\nIsto cria a base `{args.destino}`. Nao apaga nada em lado nenhum.")
    if input("Continuar? (escreva SIM) ").strip() != "SIM":
        print("Cancelado.")
        return 0

    criar(args.root, password, args.origem, args.destino, com_dados)

    print(f"""
Feito. A base `{args.destino}` esta' pronta.

Falta:
  1. Fazer-lhe uma copia de seguranca ANTES de a por a trabalhar:
       .venv\\Scripts\\python.exe scripts\\backup_martelo.py --base {args.destino}
  2. Apontar o .env da versao oficial para ela (DB_NAME={args.destino},
     APP_ENV=production).
  3. Confirmar que os numeros dos orcamentos comecam onde deve: o primeiro
     orcamento de 2026 vai ser o 260001. Se as pastas 260001..260006 dos testes
     ainda estiverem no servidor, trate delas primeiro.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
