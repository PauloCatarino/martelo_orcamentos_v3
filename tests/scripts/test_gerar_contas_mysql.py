"""Testes do gerador de contas MySQL."""

from __future__ import annotations

from types import SimpleNamespace

from scripts.gerar_contas_mysql import (
    ContaGerada,
    contas_para,
    gerar_password,
    montar_lista,
    montar_sql,
)


def _user(username: str, role: str = "user", nome: str = "") -> SimpleNamespace:
    return SimpleNamespace(username=username, role=role, nome=nome or username)


def test_gera_uma_conta_por_utilizador() -> None:
    contas = contas_para([_user("paulo"), _user("ana"), _user("admin", role="admin")])

    assert [c.username for c in contas] == ["paulo", "ana", "admin"]


def test_admin_fica_marcado_como_admin() -> None:
    contas = contas_para([_user("paulo"), _user("admin", role="admin")])

    assert [c.admin for c in contas] == [False, True]


def test_passwords_sao_todas_diferentes() -> None:
    contas = contas_para([_user(f"user{n}") for n in range(20)])

    assert len({c.password for c in contas}) == 20


def test_password_e_longa_o_suficiente_para_o_procedimento() -> None:
    """O procedimento do MySQL recusa passwords com menos de 12 caracteres."""
    assert len(gerar_password()) >= 12


def test_password_nao_leva_caracteres_que_se_confundem() -> None:
    juntas = "".join(gerar_password() for _ in range(50))

    for confuso in "lIO01":
        assert confuso not in juntas


def test_username_invalido_fica_de_fora(capsys) -> None:
    """Um username que o MySQL nao aceita nao pode gerar SQL torto."""
    contas = contas_para([_user("paulo"), _user("nome com espacos"), _user("ab")])

    assert [c.username for c in contas] == ["paulo"]
    assert "IGNORADO" in capsys.readouterr().out


def test_sql_chama_o_procedimento_uma_vez_por_conta() -> None:
    sql = montar_sql(
        [
            ContaGerada("paulo", "Paulo", "segredo-do-paulo", admin=False),
            ContaGerada("admin", "Admin", "segredo-do-admin", admin=True),
        ]
    )

    assert sql.count("CALL martelo_criar_utilizador(") == 2
    assert "'paulo', 'segredo-do-paulo', FALSE" in sql
    assert "'admin', 'segredo-do-admin', TRUE" in sql


def test_sql_escapa_plicas() -> None:
    """Uma plica na password nao pode fechar o literal do SQL."""
    sql = montar_sql([ContaGerada("ana", "Ana", "com'plica", admin=False)])

    assert "'com''plica'" in sql


def test_lista_mostra_cada_pessoa_e_marca_os_admins() -> None:
    lista = montar_lista(
        [
            ContaGerada("paulo", "Paulo Catarino", "abc123456789", admin=False),
            ContaGerada("admin", "Administrador", "xyz987654321", admin=True),
        ]
    )

    assert "paulo" in lista and "abc123456789" in lista
    assert "Paulo Catarino" in lista
    assert "(administrador)" in lista
    assert lista.count("(administrador)") == 1
