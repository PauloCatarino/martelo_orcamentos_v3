"""Testes da camada que fala com os procedimentos das contas MySQL.

Sem MySQL: a sessao e' de mentira e regista o que lhe foi pedido. O que se
verifica aqui e' que a app chama o procedimento certo, com os parametros
certos, e que nao monta SQL com a password la' dentro.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import OperationalError

from app.services import mysql_contas_service as servico
from app.services.mysql_contas_service import ContaMySQLError


class _SessaoFalsa:
    def __init__(self, *, tem_procedimentos: bool = True, erro=None) -> None:
        self.tem_procedimentos = tem_procedimentos
        self.erro = erro
        self.executados: list[tuple[str, dict]] = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, statement, parametros=None):
        sql = str(statement)
        self.executados.append((sql, parametros or {}))

        if "information_schema.routines" in sql:
            return _Escalar(1 if self.tem_procedimentos else 0)
        if self.erro is not None:
            raise self.erro
        return _Escalar(None)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _Escalar:
    def __init__(self, valor) -> None:
        self.valor = valor

    def scalar(self):
        return self.valor


def _erro(mensagem: str) -> OperationalError:
    return OperationalError("CALL ...", {}, Exception(1644, mensagem))


def test_contas_geridas_deteta_os_procedimentos() -> None:
    assert servico.contas_geridas(_SessaoFalsa(tem_procedimentos=True)) is True
    assert servico.contas_geridas(_SessaoFalsa(tem_procedimentos=False)) is False


def test_contas_geridas_e_falso_quando_nao_da_para_perguntar() -> None:
    """Em SQLite (testes) ou sem permissao, assume-se que nao ha procedimentos."""
    sessao = _SessaoFalsa()
    sessao.erro = _erro("no such table")

    def _rebenta(*_a, **_k):
        raise sessao.erro

    sessao.execute = _rebenta  # type: ignore[method-assign]
    assert servico.contas_geridas(sessao) is False


def test_criar_conta_chama_o_procedimento_com_parametros() -> None:
    sessao = _SessaoFalsa()

    servico.criar_conta(
        sessao, username="ana", password="password-comprida", admin=False
    )

    sql, parametros = sessao.executados[-1]
    assert "CALL martelo_criar_utilizador" in sql
    # A password viaja como parametro, nunca dentro do texto do SQL.
    assert "password-comprida" not in sql
    assert parametros == {
        "nome": "ana",
        "password": "password-comprida",
        "admin": False,
    }
    assert sessao.commits == 1


def test_mudar_a_minha_password_nao_aceita_nome_de_ninguem() -> None:
    """O procedimento usa USER(): a app nem sequer manda um nome."""
    sessao = _SessaoFalsa()

    servico.mudar_a_minha_password(sessao, password="password-comprida")

    sql, parametros = sessao.executados[-1]
    assert "CALL martelo_mudar_a_minha_password" in sql
    assert list(parametros) == ["password"]


@pytest.mark.parametrize(
    "chamada",
    [
        lambda s: servico.criar_conta(s, username="ana", password="curta", admin=False),
        lambda s: servico.repor_password(s, username="ana", password="curta"),
        lambda s: servico.mudar_a_minha_password(s, password="curta"),
    ],
)
def test_password_curta_nem_chega_ao_servidor(chamada) -> None:
    sessao = _SessaoFalsa()

    with pytest.raises(ContaMySQLError, match="12 caracteres"):
        chamada(sessao)

    assert sessao.executados == []


def test_erro_do_servidor_chega_ao_utilizador_em_portugues() -> None:
    sessao = _SessaoFalsa(erro=_erro("Nome de utilizador invalido: use 3 a 32 letras"))

    with pytest.raises(ContaMySQLError, match="Nome de utilizador invalido"):
        servico.criar_conta(sessao, username="a b", password="password-comprida", admin=False)

    assert sessao.rollbacks == 1
