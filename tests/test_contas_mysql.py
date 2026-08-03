"""O relatorio das contas MySQL diz onde e' que o login se parte."""

from __future__ import annotations

import pytest

from scripts.contas_mysql import (
    EstadoConta,
    perfis_com_acesso,
    recolher_estado,
)


class _LigacaoFalsa:
    """Responde a`s consultas do relatorio com o estado que o teste montar."""

    def __init__(self, *, contas, perfis, ativos, acesso) -> None:
        self.contas = contas
        self.perfis = perfis
        self.ativos = ativos
        self.acesso = acesso

    def execute(self, statement, parametros=None):
        sql = str(statement)
        if "mysql.user" in sql:
            return [(nome, "%") for nome in self.contas]
        if "role_edges" in sql:
            return [(perfil, nome) for nome, perfil in self.perfis.items()]
        if "default_roles" in sql:
            return [(nome, "martelo_normal") for nome in self.ativos]
        if "tables_priv" in sql:
            return [(perfil,) for perfil in self.acesso]
        raise AssertionError(f"consulta inesperada: {sql}")


@pytest.fixture()
def ligacao():
    return _LigacaoFalsa(
        contas=["paulo", "admin", "Ana", "Bruno"],
        perfis={
            "paulo": "martelo_normal",
            "admin": "martelo_admin",
            "Ana": "martelo_normal",
            "Bruno": "martelo_normal",
        },
        ativos=["paulo", "admin", "Ana"],
        acesso=["martelo_normal", "martelo_admin"],
    )


def test_conta_em_falta_e_apanhada(ligacao) -> None:
    estados = recolher_estado(ligacao, ["Ana", "Marcia"])

    ana, marcia = estados
    assert ana.esta_bem is True
    assert marcia.existe is False
    assert marcia.problema == "nao tem conta no servidor"


def test_perfil_por_ativar_e_apanhado(ligacao) -> None:
    # O engano classico dos roles: a conta existe, o perfil foi dado, mas
    # falta o SET DEFAULT ROLE — e o MySQL recusa a base como se fosse a
    # password errada.
    (bruno,) = recolher_estado(ligacao, ["Bruno"])

    assert bruno.existe is True
    assert bruno.perfil == "martelo_normal"
    assert bruno.perfil_ativo is False
    assert bruno.esta_bem is False
    assert "SET DEFAULT ROLE" in bruno.problema


def test_conta_sem_perfil_do_martelo(ligacao) -> None:
    ligacao.contas.append("Pedro")
    ligacao.ativos.append("Pedro")

    (pedro,) = recolher_estado(ligacao, ["Pedro"])

    assert pedro.existe is True
    assert pedro.perfil == ""
    assert pedro.problema == "tem conta mas sem perfil do Martelo"


def test_o_nome_distingue_maiusculas(ligacao) -> None:
    # No MySQL 'ana' e 'Ana' sao contas diferentes: e' uma das causas de
    # "password invalida" que nao tem nada a ver com a password.
    (minuscula,) = recolher_estado(ligacao, ["ana"])

    assert minuscula.existe is False


def test_perfis_sem_privilegios_na_base(ligacao) -> None:
    assert perfis_com_acesso(ligacao, "martelo_v3_dev") == {
        "martelo_normal",
        "martelo_admin",
    }

    ligacao.acesso = []
    assert perfis_com_acesso(ligacao, "martelo_v3_dev") == set()


def test_conta_certa_nao_tem_problema_nenhum() -> None:
    boa = EstadoConta(
        username="Ana", existe=True, perfil="martelo_normal", perfil_ativo=True
    )

    assert boa.esta_bem is True
    assert boa.problema == ""
