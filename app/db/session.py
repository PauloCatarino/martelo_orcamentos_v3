"""Database session helpers.

Na **aplicacao** quem manda na ligacao e' o login: cada pessoa tem a sua conta
MySQL e o ``ligar()`` troca o ``bind`` do ``SessionLocal`` com essas
credenciais. Como o ``SessionLocal`` e' um ``sessionmaker``, os sitios que fazem
``with SessionLocal() as session`` continuam todos iguais.

Nos **scripts de seed e no alembic** nao ha' login nenhum: correm na maquina de
quem faz a manutencao, com as credenciais do ``.env``. Por isso, e so' se essas
credenciais existirem mesmo, o ``SessionLocal`` ja' nasce ligado — e os scripts
continuam a funcionar sem alteracoes.

Nos PCs dos colegas o ``.env`` nao leva credenciais nenhumas: ali o
``SessionLocal`` nasce sem ligacao e rebenta se alguem o usar antes do login,
que e' exatamente o que se quer. E o arranque da app chama ``desligar()`` de
qualquer maneira, para nunca trabalhar com uma conta vinda de ficheiro.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.db.database import criar_engine, get_engine


def _bind_inicial() -> Engine | None:
    """Ligacao do ``.env``, so' para a maquina de manutencao (ver docstring)."""
    if settings.DATABASE_URL:
        return get_engine()
    if settings.DB_USER and settings.DB_PASSWORD:
        return get_engine()
    return None


#: Engine da sessao em curso; ``None`` quando nao ha' ligacao aberta.
_engine_atual: Engine | None = _bind_inicial()

SessionLocal = sessionmaker(
    bind=_engine_atual,
    autocommit=False,
    autoflush=False,
    future=True,
)


class CredenciaisInvalidas(Exception):
    """A base de dados recusou o utilizador ou a password."""


class BaseIndisponivel(Exception):
    """A base de dados nao respondeu (rede, servidor em baixo, nome errado)."""


#: Codigos do MySQL que sao mesmo "utilizador ou password errados".
#: 1045 = access denied; 1044 = sem acesso a esta base; 1698 = auth plugin.
_ERROS_DE_CREDENCIAIS = (1045, 1044, 1698)


def mensagem_base_indisponivel() -> str:
    """Diz QUAL o computador que nao respondeu, e nao so' que algo falhou.

    A base do Martelo vive num PC da empresa, e o endereco dele esta' escrito
    no ficheiro de configuracao de cada maquina. Basta esse PC estar desligado
    -- ou, um dia, mudar de endereco -- para toda a gente deixar de entrar ao
    mesmo tempo. Sem o nome do computador na mensagem, ninguem consegue
    adivinhar o que se passa, e a chamada que chega e' "o Martelo nao abre".

    Com o endereco a` frente, quem esta' do outro lado consegue dizer logo se
    o computador esta' desligado ou se o endereco deixou de ser aquele.
    """
    return (
        "Nao foi possivel ligar a base de dados do Martelo.\n\n"
        f"O Martelo tentou chegar a '{settings.DB_NAME}' em "
        f"{settings.DB_HOST}:{settings.DB_PORT} e nao houve resposta.\n\n"
        "Normalmente e' o computador onde a base vive que esta' desligado ou "
        "fora da rede. Se ele estiver ligado e o problema continuar, mostre "
        "esta mensagem ao responsavel: o endereco pode ter mudado."
    )


def ligar(user: str, password: str) -> Engine:
    """Liga a base com estas credenciais e passa a ser a ligacao da app.

    Levanta ``CredenciaisInvalidas`` se o MySQL recusar a conta e
    ``BaseIndisponivel`` se o problema for outro (servidor em baixo, rede).
    """
    global _engine_atual

    engine: Engine | None = None
    try:
        # O ``create_engine`` nao liga a nada; quem fala com o servidor — e
        # portanto quem recusa a password — e' o ``connect``. Ambos ficam
        # dentro do mesmo try porque um URL invalido rebenta logo no primeiro.
        engine = criar_engine(user, password)
        with engine.connect() as ligacao:
            ligacao.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        if engine is not None:
            engine.dispose()
        if _e_erro_de_credenciais(exc):
            raise CredenciaisInvalidas(
                "Utilizador ou palavra-passe invalidos."
            ) from exc
        raise BaseIndisponivel(mensagem_base_indisponivel()) from exc

    desligar()
    SessionLocal.configure(bind=engine)
    _engine_atual = engine
    return engine


def desligar() -> None:
    """Fecha a ligacao em curso (mudanca de utilizador ou fim da app)."""
    global _engine_atual

    if _engine_atual is None:
        return

    SessionLocal.configure(bind=None)
    try:
        _engine_atual.dispose()
    finally:
        _engine_atual = None


def esta_ligado() -> bool:
    """Indica se ja' ha' uma ligacao aberta (ou seja, se alguem entrou)."""
    return _engine_atual is not None


def _e_erro_de_credenciais(exc: SQLAlchemyError) -> bool:
    """Distingue "password errada" de "o servidor nao responde".

    O numero do erro vem do driver (PyMySQL), por baixo da excecao do
    SQLAlchemy; quando nao vier, olha-se para o texto.
    """
    original = getattr(exc, "orig", None)
    args = getattr(original, "args", ()) or ()
    if args and isinstance(args[0], int) and args[0] in _ERROS_DE_CREDENCIAIS:
        return True

    texto = str(original or exc).lower()
    return "access denied" in texto


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and close it afterwards."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
