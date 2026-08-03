"""Ver e arranjar as contas MySQL das pessoas (o login do Martelo).

Cada pessoa entra no Martelo com a **sua** conta do MySQL: quem valida o nome e
a password e' o servidor, nao a app. Quando alguem nao consegue entrar, a app so'
consegue dizer "username ou password invalidos" — o MySQL nao explica mais. Este
script explica.

Duas coisas, so':

    # o que e' que se passa com as contas?
    .venv\\Scripts\\python.exe scripts\\contas_mysql.py --verificar

    # dar uma password nova a alguem (escolhida por si, escrita no ecra' as
    # escuras e nunca gravada em ficheiro nenhum)
    .venv\\Scripts\\python.exe scripts\\contas_mysql.py --mudar Ana
    .venv\\Scripts\\python.exe scripts\\contas_mysql.py --mudar-todas

Por omissao trabalha na base do ``.env``; para a beta, ``--base martelo_v3_beta``.

O ``--verificar`` precisa de uma conta que possa ler as tabelas ``mysql.*`` (o
``root``). O ``--mudar`` chega-lhe a conta ``admin`` do Martelo.
"""

from __future__ import annotations

import argparse
import getpass
from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import bindparam, create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.services.mysql_contas_service import MINIMO_PASSWORD, PERFIS  # noqa: E402


#: As tres tabelas do ``mysql`` que respondem a`s tres perguntas do relatorio.
SQL_CONTAS = "SELECT user, host FROM mysql.user"
SQL_PERFIS = "SELECT from_user, to_user FROM mysql.role_edges"
SQL_PERFIS_ATIVOS = "SELECT user, default_role_user FROM mysql.default_roles"
#: Os GRANTs sao tabela a tabela (ver ``martelo_aplicar_grants``), por isso e'
#: aqui que se ve' se o perfil chega mesmo a esta base.
SQL_ACESSO_BASE = (
    "SELECT DISTINCT user FROM mysql.tables_priv WHERE db = :base AND user IN :perfis"
)


@dataclass(frozen=True)
class EstadoConta:
    """O que se sabe da conta de uma pessoa."""

    username: str
    existe: bool
    perfil: str
    perfil_ativo: bool

    @property
    def esta_bem(self) -> bool:
        return self.existe and bool(self.perfil) and self.perfil_ativo

    @property
    def problema(self) -> str:
        if not self.existe:
            return "nao tem conta no servidor"
        if not self.perfil:
            return "tem conta mas sem perfil do Martelo"
        if not self.perfil_ativo:
            return "tem perfil mas nao esta' ativo (falta o SET DEFAULT ROLE)"
        return ""


def pedir_credenciais(para_que: str) -> tuple[str, str]:
    """Credenciais de administrador, pedidas na hora e nunca gravadas."""
    print("")
    print(f"Credenciais de administrador ({para_que}):")
    utilizador = input("  utilizador [root]: ").strip() or "root"
    password = getpass.getpass("  password: ")
    return utilizador, password


def ligar_como(utilizador: str, password: str, base: str):
    """Engine para uma base, com estas credenciais."""
    url = settings.database_url_para(utilizador, password)
    url = url.replace(f"/{settings.DB_NAME}?", f"/{base}?")
    return create_engine(url)


def utilizadores_do_martelo(base: str) -> list[str]:
    """Os nomes da tabela ``users`` da base indicada."""
    if base != settings.DB_NAME:
        engine = ligar_como(settings.DB_USER, settings.DB_PASSWORD, base)
        SessionLocal.configure(bind=engine)

    with SessionLocal() as session:
        return [
            str(user.username)
            for user in session.execute(select(User).order_by(User.username)).scalars()
        ]


def recolher_estado(ligacao, nomes: list[str]) -> list[EstadoConta]:
    """Cruzar os utilizadores do Martelo com o que existe no servidor."""
    contas = {str(linha[0]) for linha in ligacao.execute(text(SQL_CONTAS))}
    perfis: dict[str, str] = {}
    for perfil, pessoa in ligacao.execute(text(SQL_PERFIS)):
        if str(perfil) in PERFIS:
            perfis[str(pessoa)] = str(perfil)
    ativos = {str(linha[0]) for linha in ligacao.execute(text(SQL_PERFIS_ATIVOS))}

    return [
        EstadoConta(
            username=nome,
            existe=nome in contas,
            perfil=perfis.get(nome, ""),
            perfil_ativo=nome in ativos,
        )
        for nome in nomes
    ]


def perfis_com_acesso(ligacao, base: str) -> set[str]:
    """Quais dos perfis do Martelo tem mesmo privilegios nesta base."""
    consulta = text(SQL_ACESSO_BASE).bindparams(
        bindparam("perfis", expanding=True)
    )
    linhas = ligacao.execute(consulta, {"base": base, "perfis": list(PERFIS)})
    return {str(linha[0]) for linha in linhas}


def verificar(base: str) -> int:
    """Relatorio do estado das contas desta base."""
    nomes = utilizadores_do_martelo(base)
    if not nomes:
        print(f"A tabela `users` da base {base} esta' vazia. Nada a verificar.")
        return 1

    utilizador, password = pedir_credenciais("para ler as contas do servidor")
    engine = ligar_como(utilizador, password, base)
    try:
        with engine.connect() as ligacao:
            estados = recolher_estado(ligacao, nomes)
            acesso = perfis_com_acesso(ligacao, base)
    except SQLAlchemyError as exc:
        print("")
        print(f"[ERRO] {_mensagem(exc)}")
        print("")
        print("Se o erro fala em 'command denied ... mysql.user', a conta que")
        print("usou nao chega: para este relatorio e' preciso o root.")
        return 1
    finally:
        engine.dispose()

    print("")
    print(f"Base: {base}    Servidor: {settings.DB_HOST}:{settings.DB_PORT}")
    print("")
    largura = max(len(nome) for nome in nomes)
    print(f"  {'utilizador'.ljust(largura)}  conta   perfil          ativo")
    for estado in estados:
        print(
            f"  {estado.username.ljust(largura)}  "
            f"{'sim' if estado.existe else 'NAO':6}  "
            f"{(estado.perfil or '—'):14}  "
            f"{'sim' if estado.perfil_ativo else 'NAO'}"
        )

    print("")
    for perfil in PERFIS:
        tem = perfil in acesso
        print(f"  perfil {perfil}: {'chega' if tem else 'NAO CHEGA'} a` base {base}")

    problemas = [estado for estado in estados if not estado.esta_bem]
    sem_acesso = [perfil for perfil in PERFIS if perfil not in acesso]
    print("")
    if not problemas and not sem_acesso:
        print("Contas todas em ordem.")
        print("")
        print("Se mesmo assim alguem nao entra, e' a password que nao e' a que")
        print("pensa — o servidor nao guarda a password a` vista, nem para o")
        print("root. Nesse caso: --mudar <nome> e escolha uma nova.")
        print("")
        print("Nota: no MySQL o nome da conta distingue maiusculas de")
        print("minusculas. 'ana' nao entra na conta 'Ana'.")
        return 0

    for estado in problemas:
        print(f"  ! {estado.username}: {estado.problema}")
    for perfil in sem_acesso:
        print(f"  ! o perfil {perfil} nao tem privilegios em {base}")

    print("")
    print("Como resolver:")
    if any(not estado.existe for estado in problemas):
        print("  - contas em falta: correr deploy/contas_martelo.sql (as chamadas")
        print("    a martelo_criar_utilizador) ou gerar_contas_mysql.py --aplicar")
    if any(estado.existe and not estado.perfil_ativo for estado in problemas):
        print("  - perfil por ativar: SET DEFAULT ROLE ALL TO '<nome>'@'%';")
    if sem_acesso:
        print(f"  - privilegios em falta: USE {base}; CALL martelo_aplicar_grants();")
    return 1


def mudar_password(base: str, nomes: list[str]) -> int:
    """Dar uma password nova a uma ou a varias pessoas."""
    if not nomes:
        print("Nenhum utilizador indicado.")
        return 1

    escolhidas: list[tuple[str, str]] = []
    print("")
    print("Escreva a password nova de cada pessoa (nao aparece no ecra).")
    print("Enter vazio salta essa pessoa.")
    for nome in nomes:
        print("")
        nova = getpass.getpass(f"  {nome}: ")
        if not nova:
            print("    (saltado)")
            continue
        if len(nova) < MINIMO_PASSWORD:
            print(f"    (ignorado: minimo {MINIMO_PASSWORD} caracteres)")
            continue
        if getpass.getpass("    repita: ") != nova:
            print("    (ignorado: as duas nao coincidem)")
            continue
        escolhidas.append((nome, nova))

    if not escolhidas:
        print("")
        print("Nada a fazer.")
        return 1

    utilizador, password = pedir_credenciais("a conta 'admin' do Martelo, ou o root")
    engine = ligar_como(utilizador, password, base)
    feitas = 0
    try:
        with engine.begin() as ligacao:
            for nome, nova in escolhidas:
                ligacao.execute(
                    text("CALL martelo_repor_password(:nome, :password)"),
                    {"nome": nome, "password": nova},
                )
                feitas += 1
                print(f"  {nome}: password mudada")
    except SQLAlchemyError as exc:
        print("")
        print(f"[ERRO] {_mensagem(exc)}")
        return 1
    finally:
        engine.dispose()

    print("")
    print(f"{feitas} password(s) mudadas em {settings.DB_HOST}.")
    print("As contas do MySQL sao do servidor inteiro: servem a dev e a beta.")
    print("Nenhuma password foi gravada em ficheiro — diga-as a cada pessoa.")
    return 0


def _mensagem(exc: SQLAlchemyError) -> str:
    original = getattr(exc, "orig", None)
    for arg in getattr(original, "args", ()) or ():
        if isinstance(arg, str) and arg.strip():
            return arg.strip()
    return str(original or exc).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default="",
        help="base de dados a usar (por omissao, a do .env)",
    )
    parser.add_argument(
        "--verificar",
        action="store_true",
        help="relatorio do estado das contas (precisa do root)",
    )
    parser.add_argument(
        "--mudar",
        default="",
        help="nome de quem leva password nova (varios separados por virgula)",
    )
    parser.add_argument(
        "--mudar-todas",
        action="store_true",
        help="percorrer todos os utilizadores, um a um",
    )
    args = parser.parse_args()

    base = args.base or settings.DB_NAME

    if args.verificar:
        return verificar(base)

    if args.mudar_todas:
        return mudar_password(base, utilizadores_do_martelo(base))

    if args.mudar:
        nomes = [nome.strip() for nome in args.mudar.split(",") if nome.strip()]
        return mudar_password(base, nomes)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
