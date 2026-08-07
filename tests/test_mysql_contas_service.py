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
    def __init__(
        self, *, tem_procedimentos: bool = True, erro=None, perfil: str | None = None
    ) -> None:
        self.tem_procedimentos = tem_procedimentos
        self.erro = erro
        self.perfil = perfil
        self.executados: list[tuple[str, dict]] = []
        self.commits = 0
        self.rollbacks = 0

    def __post_init__(self) -> None:  # pragma: no cover - compatibilidade
        pass

    def execute(self, statement, parametros=None):
        sql = str(statement)
        self.executados.append((sql, parametros or {}))

        if "CURRENT_ROLE" in sql:
            return _Escalar(
                getattr(self, "perfil", None)
                or ("`martelo_normal`@`%`" if self.tem_procedimentos else "NONE")
            )
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


def test_contas_geridas_olha_para_o_perfil_ativo() -> None:
    assert servico.contas_geridas(_SessaoFalsa(perfil="`martelo_normal`@`%`")) is True
    assert servico.contas_geridas(_SessaoFalsa(perfil="`martelo_admin`@`%`")) is True


def test_contas_geridas_e_falso_com_a_conta_partilhada_antiga() -> None:
    """O martelo_v3 nao tem perfil nenhum: a app trabalha como dantes."""
    assert servico.contas_geridas(_SessaoFalsa(perfil="NONE")) is False
    assert servico.contas_geridas(_SessaoFalsa(perfil=None, tem_procedimentos=False)) is False


def test_contas_geridas_nao_pergunta_pelo_information_schema() -> None:
    """Regressao: um GRANT EXECUTE numa rotina nao a mostra no
    information_schema.routines -- perguntar por ai' dava sempre "nao", mesmo
    com tudo instalado, e a app mexia no hash antigo em silencio."""
    sessao = _SessaoFalsa(perfil="`martelo_normal`@`%`")

    servico.contas_geridas(sessao)

    sql = " ".join(s for s, _ in sessao.executados)
    assert "information_schema" not in sql
    assert "CURRENT_ROLE" in sql


def test_sou_admin_na_base_distingue_os_perfis() -> None:
    assert servico.sou_admin_na_base(_SessaoFalsa(perfil="`martelo_admin`@`%`")) is True
    assert servico.sou_admin_na_base(_SessaoFalsa(perfil="`martelo_normal`@`%`")) is False
    assert servico.sou_admin_na_base(_SessaoFalsa(perfil="NONE")) is False


def test_contas_geridas_e_falso_quando_nao_da_para_perguntar() -> None:
    """Em SQLite (testes) ou sem roles, assume-se o comportamento antigo."""
    sessao = _SessaoFalsa()

    def _rebenta(*_a, **_k):
        raise _erro("no such function: CURRENT_ROLE")

    sessao.execute = _rebenta  # type: ignore[method-assign]
    assert servico.contas_geridas(sessao) is False
    assert servico.sou_admin_na_base(sessao) is False


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


def test_sincronizar_permissoes_chama_procedimento_e_confirma() -> None:
    sessao = _SessaoFalsa()

    servico.sincronizar_permissoes(sessao)

    sql, parametros = sessao.executados[-1]
    assert sql == "CALL martelo_aplicar_grants()"
    assert parametros == {}
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

    with pytest.raises(ContaMySQLError, match="6 caracteres"):
        chamada(sessao)

    assert sessao.executados == []


def test_erro_do_servidor_chega_ao_utilizador_em_portugues() -> None:
    sessao = _SessaoFalsa(erro=_erro("Nome de utilizador invalido: use 3 a 32 letras"))

    with pytest.raises(ContaMySQLError, match="Nome de utilizador invalido"):
        servico.criar_conta(sessao, username="a b", password="password-comprida", admin=False)

    assert sessao.rollbacks == 1
