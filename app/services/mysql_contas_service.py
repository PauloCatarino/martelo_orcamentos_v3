"""Contas MySQL das pessoas — a camada da app sobre os procedimentos do servidor.

Cada utilizador do Martelo tem a sua conta na base de dados: e' ela que decide
o que ele pode fazer, em vez de a interface esconder botoes sobre uma ligacao
partilhada. Criar contas exige o privilegio ``CREATE USER``, que no MySQL e'
global; para nao o dar a` app, o trabalho e' feito por procedimentos
``SQL SECURITY DEFINER`` instalados uma vez (``deploy/mysql_contas_beta.sql``) —
a app so' tem ``EXECUTE`` sobre eles.

**A base pode ainda nao os ter.** Estamos a aplicar isto primeiro na beta, por
isso tudo aqui verifica primeiro se os procedimentos existem: onde nao existirem
(a base principal, para ja'), a app continua a trabalhar como antes.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

PROC_CRIAR = "martelo_criar_utilizador"
PROC_REPOR = "martelo_repor_password"
PROC_APAGAR = "martelo_apagar_utilizador"
PROC_MUDAR_A_MINHA = "martelo_mudar_a_minha_password"

#: O mesmo minimo que os procedimentos impoem, para o aviso sair antes da
#: viagem ao servidor. Seis e' pouco para uma password na Internet, mas isto e'
#: uma rede fechada e as pessoas ja' tinham este habito do V2 -- obrigar a doze
#: so' faria com que as apontassem num papel colado ao monitor.
MINIMO_PASSWORD = 6


class ContaMySQLError(Exception):
    """O servidor recusou a operacao sobre a conta."""


#: Perfis criados pelo ``deploy/mysql_contas_beta.sql``.
PERFIS = ("martelo_normal", "martelo_admin")


def contas_geridas(session: Session) -> bool:
    """Indica se quem esta' ligado entrou com uma conta por utilizador.

    Pergunta-se pelo **perfil ativo** e nao pelos procedimentos: um
    ``GRANT EXECUTE`` numa rotina deixa chama-la, mas nao a mostra no
    ``information_schema.routines`` -- para isso era preciso privilegio ao
    nivel da base, que ninguem tem. Perguntar por ai' dava sempre "nao", mesmo
    com tudo bem instalado, e a app ficava a mexer no hash antigo em silencio.

    ``CURRENT_ROLE()`` toda a gente pode correr, e responde a` pergunta certa:
    esta ligacao e' de uma pessoa, com perfil, ou e' a conta partilhada antiga?
    """
    try:
        perfil = session.execute(text("SELECT CURRENT_ROLE()")).scalar()
    except SQLAlchemyError:
        # SQLite nos testes, ou MySQL sem roles: comporta-se como antes.
        return False

    texto = str(perfil or "")
    return any(nome in texto for nome in PERFIS)


def sou_admin_na_base(session: Session) -> bool:
    """Indica se o perfil ativo e' o de administrador da base de dados.

    Serve para a UI so' oferecer o que a base deixa mesmo fazer, em vez de
    mostrar um botao que rebenta com erro de permissao.
    """
    try:
        perfil = session.execute(text("SELECT CURRENT_ROLE()")).scalar()
    except SQLAlchemyError:
        return False
    return "martelo_admin" in str(perfil or "")


def criar_conta(session: Session, *, username: str, password: str, admin: bool) -> None:
    """Cria a conta MySQL desta pessoa, com o perfil normal ou de admin."""
    _validar_password(password)
    _chamar(
        session,
        f"CALL {PROC_CRIAR}(:nome, :password, :admin)",
        {"nome": username, "password": password, "admin": bool(admin)},
        falhou="Nao foi possivel criar a conta na base de dados",
    )


def repor_password(session: Session, *, username: str, password: str) -> None:
    """Repoe a palavra-passe de outra pessoa (so' o administrador)."""
    _validar_password(password)
    _chamar(
        session,
        f"CALL {PROC_REPOR}(:nome, :password)",
        {"nome": username, "password": password},
        falhou="Nao foi possivel repor a palavra-passe",
    )


def apagar_conta(session: Session, *, username: str) -> None:
    """Apaga a conta MySQL — usado para desfazer uma criacao a meio."""
    _chamar(
        session,
        f"CALL {PROC_APAGAR}(:nome)",
        {"nome": username},
        falhou="Nao foi possivel apagar a conta",
    )


def mudar_a_minha_password(session: Session, *, password: str) -> None:
    """Muda a palavra-passe de quem esta' ligado.

    O procedimento usa ``USER()``, por isso ninguem consegue por aqui mexer na
    password de outra pessoa — nem sequer indicando outro nome.
    """
    _validar_password(password)
    _chamar(
        session,
        f"CALL {PROC_MUDAR_A_MINHA}(:password)",
        {"password": password},
        falhou="Nao foi possivel mudar a palavra-passe",
    )


def _validar_password(password: str) -> None:
    if len(str(password or "")) < MINIMO_PASSWORD:
        raise ContaMySQLError(
            f"A palavra-passe tem de ter pelo menos {MINIMO_PASSWORD} caracteres."
        )


def _chamar(session: Session, sql: str, parametros: dict, *, falhou: str) -> None:
    """Corre um procedimento e traduz o erro do servidor para portugues.

    Os procedimentos recusam com ``SIGNAL`` e uma mensagem ja' escrita para
    quem esta' a` frente do ecra; e' essa que se mostra, quando existe.
    """
    try:
        session.execute(text(sql), parametros)
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise ContaMySQLError(f"{falhou}: {_mensagem(exc)}") from exc


def _mensagem(exc: SQLAlchemyError) -> str:
    original = getattr(exc, "orig", None)
    args = getattr(original, "args", ()) or ()
    for arg in args:
        if isinstance(arg, str) and arg.strip():
            return arg.strip()
    return str(original or exc).strip()
