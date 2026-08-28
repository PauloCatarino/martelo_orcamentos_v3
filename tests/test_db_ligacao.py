"""Testes da ligacao a` base com as credenciais de cada pessoa.

Nao tocam em MySQL nenhum: o ``criar_engine`` e' trocado por um que devolve
SQLite em memoria, ou que rebenta como o PyMySQL rebentaria.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.db import session as db_session


@pytest.fixture(autouse=True)
def _sem_ligacao_pendurada():
    """Cada teste comeca e acaba sem ligacao aberta."""
    db_session.desligar()
    yield
    db_session.desligar()


def _engine_falso(*_args, **_kwargs):
    return create_engine("sqlite:///:memory:")


def _erro_pymysql(codigo: int, mensagem: str) -> OperationalError:
    """Imita o que o SQLAlchemy levanta por cima de um erro do PyMySQL."""
    return OperationalError("SELECT 1", {}, Exception(codigo, mensagem))


def _engine_que_recusa(erro: OperationalError):
    """Um engine como o real: cria-se sem falhar, rebenta ao ligar.

    E' este o caminho verdadeiro — o ``create_engine`` nunca fala com o
    servidor, so' o ``connect`` e' que la' vai bater.
    """

    class _EngineFalso:
        def __init__(self) -> None:
            self.disposed = False

        def connect(self):
            raise erro

        def dispose(self) -> None:
            self.disposed = True

    def _criar(*_args, **_kwargs):
        return _EngineFalso()

    return _criar


def test_ligar_configura_o_sessionmaker(monkeypatch) -> None:
    monkeypatch.setattr(db_session, "criar_engine", _engine_falso)

    db_session.ligar("paulo", "segredo")

    assert db_session.esta_ligado() is True
    with db_session.SessionLocal() as sessao:
        assert sessao.execute(text("SELECT 1")).scalar() == 1


def test_sem_ligar_nao_ha_sessao_nenhuma() -> None:
    """Antes de alguem entrar nao existe ligacao — e falha de forma ruidosa."""
    assert db_session.esta_ligado() is False
    with pytest.raises(Exception):
        with db_session.SessionLocal() as sessao:
            sessao.execute(text("SELECT 1"))


def test_desligar_larga_a_ligacao(monkeypatch) -> None:
    monkeypatch.setattr(db_session, "criar_engine", _engine_falso)
    db_session.ligar("paulo", "segredo")

    db_session.desligar()

    assert db_session.esta_ligado() is False


def test_mudar_de_utilizador_troca_a_ligacao(monkeypatch) -> None:
    criados = []

    def _criar(user, _password):
        criados.append(user)
        return create_engine("sqlite:///:memory:")

    monkeypatch.setattr(db_session, "criar_engine", _criar)

    db_session.ligar("paulo", "x")
    primeiro = db_session._engine_atual
    db_session.ligar("ana", "y")

    assert criados == ["paulo", "ana"]
    assert db_session._engine_atual is not primeiro


@pytest.mark.parametrize("codigo", [1045, 1044, 1698])
def test_password_errada_da_erro_de_credenciais(monkeypatch, codigo: int) -> None:
    erro = _erro_pymysql(codigo, "Access denied for user 'paulo'@'pc'")
    monkeypatch.setattr(db_session, "criar_engine", _engine_que_recusa(erro))

    with pytest.raises(db_session.CredenciaisInvalidas):
        db_session.ligar("paulo", "errada")


def test_access_denied_sem_codigo_tambem_conta(monkeypatch) -> None:
    erro = OperationalError("SELECT 1", {}, Exception("Access denied for user"))
    monkeypatch.setattr(db_session, "criar_engine", _engine_que_recusa(erro))

    with pytest.raises(db_session.CredenciaisInvalidas):
        db_session.ligar("paulo", "errada")


def test_servidor_em_baixo_nao_e_password_errada(monkeypatch) -> None:
    """Distinguir os dois casos evita mandar a pessoa mudar a password em vao."""
    erro = _erro_pymysql(2003, "Can't connect to MySQL server on '192.168.5.201'")
    monkeypatch.setattr(db_session, "criar_engine", _engine_que_recusa(erro))

    with pytest.raises(db_session.BaseIndisponivel):
        db_session.ligar("paulo", "segredo")


def test_url_invalido_tambem_e_tratado(monkeypatch) -> None:
    """Se o proprio ``create_engine`` rebentar, nao sai um traceback cru."""

    def _rebenta(*_args, **_kwargs):
        raise _erro_pymysql(2003, "servidor desconhecido")

    monkeypatch.setattr(db_session, "criar_engine", _rebenta)

    with pytest.raises(db_session.BaseIndisponivel):
        db_session.ligar("paulo", "segredo")


def test_ligacao_falhada_nao_deixa_a_anterior_pendurada(monkeypatch) -> None:
    monkeypatch.setattr(db_session, "criar_engine", _engine_falso)
    db_session.ligar("paulo", "segredo")

    erro = _erro_pymysql(1045, "Access denied")
    monkeypatch.setattr(db_session, "criar_engine", _engine_que_recusa(erro))
    with pytest.raises(db_session.CredenciaisInvalidas):
        db_session.ligar("ana", "errada")

    # A do Paulo continua de pe': uma tentativa falhada nao o deve expulsar.
    assert db_session.esta_ligado() is True
    with db_session.SessionLocal() as sessao:
        assert sessao.execute(text("SELECT 1")).scalar() == 1


# ---------------------------------------------------------------------------
# A mensagem de "servidor nao responde"
# ---------------------------------------------------------------------------
#
# A base do Martelo vive num PC da empresa. Quando esse PC esta' desligado --
# ou, um dia, muda de endereco -- toda a gente deixa de entrar ao mesmo tempo,
# e o que chega ao Paulo e' "o Martelo nao abre". A mensagem tem de dizer QUAL
# o computador que nao respondeu, para a chamada durar dez segundos em vez de
# uma tarde.

def test_mensagem_diz_a_que_servidor_e_base_tentou_chegar(monkeypatch) -> None:
    from app.config.settings import settings

    monkeypatch.setattr(settings, "DB_HOST", "192.168.5.201", raising=False)
    monkeypatch.setattr(settings, "DB_PORT", 3306, raising=False)
    monkeypatch.setattr(settings, "DB_NAME", "martelo_v3", raising=False)

    mensagem = db_session.mensagem_base_indisponivel()

    assert "192.168.5.201" in mensagem
    assert "3306" in mensagem
    assert "martelo_v3" in mensagem


def test_mensagem_nao_leva_credenciais(monkeypatch) -> None:
    """O ecra do login e' publico: o endereco pode aparecer, a password nunca."""
    from app.config.settings import settings

    monkeypatch.setattr(settings, "DB_USER", "conta_secreta", raising=False)
    monkeypatch.setattr(settings, "DB_PASSWORD", "password_secreta", raising=False)

    mensagem = db_session.mensagem_base_indisponivel()

    assert "conta_secreta" not in mensagem
    assert "password_secreta" not in mensagem


def test_servidor_em_baixo_traz_a_mensagem_com_o_endereco(monkeypatch) -> None:
    """O caminho todo: o MySQL nao responde -> a pessoa ve' o endereco."""
    from app.config.settings import settings

    monkeypatch.setattr(settings, "DB_HOST", "192.168.5.201", raising=False)

    def _rebenta(*_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("(2003, \"Can't connect\")"))

    monkeypatch.setattr(db_session, "criar_engine", _rebenta)

    with pytest.raises(db_session.BaseIndisponivel) as erro:
        db_session.ligar("paulo", "seja-o-que-for")

    assert "192.168.5.201" in str(erro.value)
