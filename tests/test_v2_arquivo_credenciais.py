"""O Arquivo V2 consultado com a conta de quem entra no Martelo.

Antes ia no ``.env`` de cada PC uma segunda conta -- e a que la' estava era a
``orc_user``, a conta com que o proprio Martelo V2 TRABALHA, com escrita em
tudo. Quem abrisse o ficheiro ficava com ela. Estes testes fixam o
comportamento novo: sem password em ficheiro nenhum, e uma mensagem que se
percebe quando falta o acesso do lado do servidor.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.db import session as db_session
from app.services import v2_arquivo_service
from app.services.v2_arquivo_service import (
    V2ArquivoConfigError,
    criar_engine_v2,
    explicar_erro_v2,
)

VARIAVEIS_V2 = (
    "V2_DATABASE_URL",
    "V2_DB_USER",
    "V2_DB_PASSWORD",
    "V2_DB_HOST",
    "V2_DB_PORT",
    "V2_DB_NAME",
)


@pytest.fixture()
def sem_env_v2(monkeypatch):
    """Um PC de colega: o .env que vem no instalador nao leva credenciais."""
    for chave in VARIAVEIS_V2:
        monkeypatch.delenv(chave, raising=False)
    return monkeypatch


class _LigacaoFalsa:
    """Faz de conta que alguem entrou no Martelo com esta conta."""

    def __init__(self, url: str) -> None:
        self.url = create_engine(url).url


# --------------------------------------------------------------------------
# credenciais_da_sessao
# --------------------------------------------------------------------------


def test_credenciais_da_sessao_sem_ninguem_ligado(monkeypatch) -> None:
    monkeypatch.setattr(db_session, "_engine_atual", None)
    assert db_session.credenciais_da_sessao() is None


def test_credenciais_da_sessao_devolve_a_conta_do_login(monkeypatch) -> None:
    monkeypatch.setattr(
        db_session,
        "_engine_atual",
        _LigacaoFalsa("mysql+pymysql://ana:segredo@192.168.5.201:3306/martelo_v3"),
    )
    atual = db_session.credenciais_da_sessao()
    assert atual is not None
    assert atual.utilizador == "ana"
    assert atual.password == "segredo"
    assert atual.host == "192.168.5.201"
    assert atual.porta == 3306


def test_credenciais_da_sessao_sem_password_nao_serve(monkeypatch) -> None:
    """Uma ligacao sem password (socket local, por ex.) nao da' para reutilizar."""
    monkeypatch.setattr(
        db_session,
        "_engine_atual",
        _LigacaoFalsa("mysql+pymysql://ana@192.168.5.201:3306/martelo_v3"),
    )
    assert db_session.credenciais_da_sessao() is None


# --------------------------------------------------------------------------
# criar_engine_v2
# --------------------------------------------------------------------------


def test_arquivo_v2_usa_a_conta_de_quem_entrou(sem_env_v2) -> None:
    sem_env_v2.setattr(
        v2_arquivo_service,
        "credenciais_da_sessao",
        lambda: db_session.LigacaoAtual("ana", "segredo", "192.168.5.201", 3306),
    )

    engine = criar_engine_v2()
    try:
        assert engine.url.username == "ana"
        assert engine.url.password == "segredo"
        # Mesmo servidor do Martelo, outra base: e' onde vive o arquivo.
        assert engine.url.host == "192.168.5.201"
        assert engine.url.database == "orcamentos_v2"
    finally:
        engine.dispose()


def test_arquivo_v2_segue_o_servidor_da_ligacao_em_curso(sem_env_v2) -> None:
    """No dia em que a base mudar de maquina, o arquivo vai atras dela."""
    sem_env_v2.setattr(
        v2_arquivo_service,
        "credenciais_da_sessao",
        lambda: db_session.LigacaoAtual("ana", "segredo", "servidor_novo", 3307),
    )

    engine = criar_engine_v2()
    try:
        assert engine.url.host == "servidor_novo"
        assert engine.url.port == 3307
    finally:
        engine.dispose()


def test_conta_do_env_continua_a_ganhar(sem_env_v2) -> None:
    """Na maquina de manutencao, o .env manda -- e nao a conta do login."""
    sem_env_v2.setenv("V2_DB_USER", "manutencao")
    sem_env_v2.setenv("V2_DB_PASSWORD", "outra")
    sem_env_v2.setattr(
        v2_arquivo_service,
        "credenciais_da_sessao",
        lambda: db_session.LigacaoAtual("ana", "segredo", "192.168.5.201", 3306),
    )

    engine = criar_engine_v2()
    try:
        assert engine.url.username == "manutencao"
    finally:
        engine.dispose()


def test_sem_conta_e_sem_login_explica_se(sem_env_v2) -> None:
    sem_env_v2.setattr(v2_arquivo_service, "credenciais_da_sessao", lambda: None)

    with pytest.raises(V2ArquivoConfigError) as erro:
        criar_engine_v2()
    assert "entrou no Martelo" in str(erro.value)


# --------------------------------------------------------------------------
# explicar_erro_v2
# --------------------------------------------------------------------------


def _erro_mysql(codigo: int) -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception(codigo, "denied"))


@pytest.mark.parametrize("codigo", [1044, 1045, 1142, 1143, 1698])
def test_falta_de_acesso_tem_nome(codigo: int) -> None:
    texto = explicar_erro_v2(_erro_mysql(codigo))
    assert "não tem acesso ao Arquivo V2" in texto
    assert "mysql_arquivo_v2.sql" in texto


def test_falta_de_acesso_tem_nome_tambem_ao_gravar() -> None:
    """Ao gravar, o motivo continua a ser o mesmo -- e deve dizer-se."""
    texto = explicar_erro_v2(_erro_mysql(1142), ao_gravar=True)
    assert "não tem acesso ao Arquivo V2" in texto


def test_servidor_em_baixo_nao_e_falta_de_acesso() -> None:
    texto = explicar_erro_v2(_erro_mysql(2003))
    assert "não tem acesso" not in texto
    assert "servidor" in texto


def test_erro_ao_gravar_sem_codigo_conhecido() -> None:
    texto = explicar_erro_v2(_erro_mysql(2003), ao_gravar=True)
    assert "gravar" in texto
