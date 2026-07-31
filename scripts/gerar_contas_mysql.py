"""Gera as contas MySQL das pessoas que ja' existem na tabela ``users``.

Corre uma vez, na passagem para o login por utilizador. Le' os utilizadores do
Martelo e escreve dois ficheiros:

  * ``contas_martelo.sql``  -- o SQL a correr no servidor (CREATE USER + perfil)
  * ``contas_martelo.txt``  -- a lista de passwords, para distribuir e apagar

Nao toca na base de dados: so' le'. O SQL fica para si rever antes de correr.

    .venv\\Scripts\\python.exe scripts\\gerar_contas_mysql.py
    .venv\\Scripts\\python.exe scripts\\gerar_contas_mysql.py --pasta C:\\temp

Depois:

    mysql -u root -p martelo_v3_beta < deploy\\mysql_contas_beta.sql
    mysql -u root -p martelo_v3_beta < contas_martelo.sql
"""

from __future__ import annotations

import argparse
import re
import secrets
import string
from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


#: O mesmo limite que o procedimento ``martelo_criar_utilizador`` impoe.
NOME_VALIDO = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")

#: Comprimento da password gerada. Longa porque ninguem a decora: escreve-se
#: uma vez e muda-se logo a seguir, na propria app.
TAMANHO_PASSWORD = 16

#: Sem caracteres que se confundam a ler em voz alta ou num papel (l/1/I, O/0).
ALFABETO = (
    "".join(c for c in string.ascii_letters + string.digits if c not in "lIO01")
    + "!#%+=?"
)


@dataclass(frozen=True)
class ContaGerada:
    username: str
    nome: str
    password: str
    admin: bool


def criar_engine_para_base(nome_base: str):
    """Engine para outra base, com as credenciais do ``.env``.

    O servidor e as credenciais sao os mesmos (a conta de manutencao chega a`
    dev e a` beta); so' muda o nome da base.
    """
    from sqlalchemy import create_engine

    from app.config.settings import settings

    url = settings.database_url_para(settings.DB_USER, settings.DB_PASSWORD)
    return create_engine(url.replace(f"/{settings.DB_NAME}?", f"/{nome_base}?"))


def gerar_password(tamanho: int = TAMANHO_PASSWORD) -> str:
    """Password aleatoria — uma por pessoa, nunca repetida."""
    return "".join(secrets.choice(ALFABETO) for _ in range(tamanho))


def contas_para(utilizadores) -> list[ContaGerada]:
    """Transforma os utilizadores do Martelo em contas a criar.

    Quem tiver um username que o MySQL nao aceita fica de fora, com aviso: e'
    preciso corrigir o username na app antes de lhe criar a conta.
    """
    contas: list[ContaGerada] = []
    for user in utilizadores:
        username = str(getattr(user, "username", "") or "").strip()
        if not NOME_VALIDO.match(username):
            print(
                f"  ! IGNORADO: '{username}' nao serve como conta MySQL "
                "(3 a 32 letras, algarismos, _ . -). Corrija o username na app."
            )
            continue

        contas.append(
            ContaGerada(
                username=username,
                nome=str(getattr(user, "nome", "") or "").strip(),
                password=gerar_password(),
                admin=str(getattr(user, "role", "") or "").strip().lower() == "admin",
            )
        )
    return contas


def _sql_escape(valor: str) -> str:
    """Escapa uma plica para o literal do SQL."""
    return valor.replace("\\", "\\\\").replace("'", "''")


def montar_sql(contas: list[ContaGerada], *, repor: bool = False) -> str:
    """SQL das chamadas ao procedimento, uma por pessoa.

    ``repor=True`` troca as passwords de contas que ja' existem, em vez de as
    criar -- as contas do MySQL sao globais e criam-se uma vez so'.
    """
    procedimento = "martelo_repor_password" if repor else "martelo_criar_utilizador"
    linhas = [
        "-- Contas do Martelo, geradas por scripts/gerar_contas_mysql.py",
        (
            "-- REPOSICAO de passwords (as contas ja' existem)."
            if repor
            else "-- Correr DEPOIS de deploy/mysql_contas_beta.sql."
        ),
        "--",
        "-- As passwords estao em contas_martelo.txt: distribua-as e apague o",
        "-- ficheiro. Cada pessoa muda a sua na app, em Utilizadores.",
        "",
    ]
    for conta in contas:
        perfil = "administrador" if conta.admin else "normal"
        linhas.append(f"-- {conta.nome or conta.username} ({perfil})")
        if repor:
            linhas.append(
                f"CALL {procedimento}("
                f"'{_sql_escape(conta.username)}', "
                f"'{_sql_escape(conta.password)}');"
            )
        else:
            linhas.append(
                f"CALL {procedimento}("
                f"'{_sql_escape(conta.username)}', "
                f"'{_sql_escape(conta.password)}', "
                f"{'TRUE' if conta.admin else 'FALSE'});"
            )
        linhas.append("")
    return "\n".join(linhas)


def montar_lista(contas: list[ContaGerada]) -> str:
    """A folha de passwords para distribuir."""
    largura = max((len(c.username) for c in contas), default=10)
    linhas = [
        "PASSWORDS INICIAIS DO MARTELO",
        "",
        "Entregue a cada pessoa apenas a linha dela e apague este ficheiro.",
        "Cada um deve mudar a sua no Martelo, em Utilizadores.",
        "",
    ]
    for conta in contas:
        perfil = "  (administrador)" if conta.admin else ""
        linhas.append(
            f"  {conta.username.ljust(largura)}  {conta.password}"
            f"{perfil}   {conta.nome}"
        )
    linhas.append("")
    return "\n".join(linhas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pasta",
        default=str(PROJECT_ROOT / "deploy"),
        # Ao lado do mysql_contas_beta.sql e companhia: e' onde se vai procurar
        # quando se abre o ficheiro no Workbench.
        help="onde gravar os dois ficheiros (por omissao, a pasta deploy)",
    )
    parser.add_argument(
        "--base",
        default="",
        # O .env aponta para a base de desenvolvimento; para gerar as contas da
        # BETA sem lhe andar a mexer, indica-se aqui o nome da base.
        help="base de dados a ler (por omissao, a do .env)",
    )
    parser.add_argument(
        "--repor",
        action="store_true",
        # As contas do MySQL sao globais: uma vez criadas servem todas as bases.
        # O que se precisa a seguir nao e' cria-las outra vez -- e' dar-lhes
        # passwords novas, por exemplo quando as antigas andaram a` vista.
        help="gerar reposicoes de password em vez de contas novas",
    )
    parser.add_argument(
        "--excepto",
        default="",
        help="nomes a deixar de fora, separados por virgula (ex.: paulo,admin)",
    )
    args = parser.parse_args()

    if args.base:
        engine = criar_engine_para_base(args.base)
        SessionLocal.configure(bind=engine)
        print(f"a ler a base: {args.base}")

    with SessionLocal() as session:  # type: Session
        utilizadores = list(
            session.execute(select(User).order_by(User.username)).scalars()
        )

    if not utilizadores:
        print("Nao ha utilizadores na tabela `users`. Nada a fazer.")
        return 1

    print(f"{len(utilizadores)} utilizador(es) na tabela `users`.")
    contas = contas_para(utilizadores)

    fora = {n.strip().casefold() for n in args.excepto.split(",") if n.strip()}
    if fora:
        antes = len(contas)
        contas = [c for c in contas if c.username.casefold() not in fora]
        print(f"  deixados de fora: {antes - len(contas)} ({args.excepto})")
    if not contas:
        print("Nenhum username servia como conta MySQL. Nada gerado.")
        return 1

    pasta = Path(args.pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho_sql = pasta / "contas_martelo.sql"
    caminho_txt = pasta / "contas_martelo.txt"

    caminho_sql.write_text(montar_sql(contas, repor=args.repor), encoding="utf-8")
    caminho_txt.write_text(montar_lista(contas), encoding="utf-8")

    admins = sum(1 for c in contas if c.admin)
    print(f"{len(contas)} conta(s) geradas ({admins} administrador(es)).")
    print(f"  SQL       -> {caminho_sql}")
    print(f"  passwords -> {caminho_txt}")
    print()
    print("ATENCAO: estes dois ficheiros levam as passwords de toda a gente em")
    print("texto simples. O .gitignore ja' os travava, mas confirme que nao vao")
    print("para o repositorio e apague-os assim que distribuir.")
    _avisar_se_o_git_os_ve(caminho_sql, caminho_txt)
    print()
    print("A seguir:")
    print("  1. correr deploy/mysql_contas_beta.sql   (uma vez, por base)")
    print(f"  2. correr {caminho_sql.name}")
    print(f"  3. distribuir as passwords e APAGAR o {caminho_txt.name}")
    return 0


def _avisar_se_o_git_os_ve(*caminhos: Path) -> None:
    """Grita se algum dos ficheiros nao estiver a ser ignorado pelo git.

    Um `git add -A` distraido mandava as passwords todas para o repositorio, e
    dali nao saem mais -- ficam no historico. Mais vale um aviso a mais.
    """
    import subprocess

    for caminho in caminhos:
        # Fora do repositorio o git nao tem opiniao nenhuma -- e nao ha' risco
        # de um "git add" distraido os apanhar.
        try:
            caminho.resolve().relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            continue
        try:
            resultado = subprocess.run(
                ["git", "check-ignore", "-q", str(caminho)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                check=False,
            )
        except (OSError, ValueError):
            return  # sem git a` mao: nada a dizer
        if resultado.returncode != 0:
            print()
            print(f"  !!! {caminho.name} NAO esta a ser ignorado pelo git !!!")
            print("      Acrescente-o ao .gitignore ANTES de fazer commit.")


if __name__ == "__main__":
    raise SystemExit(main())
