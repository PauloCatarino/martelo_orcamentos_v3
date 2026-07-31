"""Tests for the PHC read-only SQL helpers."""

from __future__ import annotations

import pytest

from app.services.phc_sql import (
    PHCConfig,
    _parse_bool,
    assert_select_only,
    build_connection_string,
)


def _cfg(**overrides) -> PHCConfig:
    base = {
        "server": r"Server_le\phc",
        "database": "lancaencanto",
        "user": "adriano.silva",
        "password": "segredo",
        "trusted": False,
        "trust_server_certificate": True,
    }
    base.update(overrides)
    return base  # type: ignore[return-value]


def test_assert_select_only_aceita_select() -> None:
    assert_select_only("SELECT NOME FROM dbo.CL WITH (NOLOCK)")
    assert_select_only("select 1")


@pytest.mark.parametrize(
    "query",
    [
        "",
        "UPDATE CL SET NOME='x'",
        "DELETE FROM CL",
        "DROP TABLE CL",
        "EXEC sp_who",
        "SELECT 1; DROP TABLE CL",
        "SELECT NOME INTO dbo.COPIA FROM dbo.CL",
    ],
)
def test_assert_select_only_rejeita_nao_select(query: str) -> None:
    with pytest.raises(RuntimeError):
        assert_select_only(query)


def test_build_connection_string_sql_auth() -> None:
    conn = build_connection_string(_cfg())

    assert r'Server="Server_le\phc"' in conn
    assert 'Database="lancaencanto"' in conn
    assert 'User ID="adriano.silva"' in conn
    assert 'Password="segredo"' in conn
    assert "TrustServerCertificate=True" in conn


def test_build_connection_string_escapa_ponto_e_virgula() -> None:
    """Uma password com ``;`` nao pode partir a ligacao em dois."""
    conn = build_connection_string(_cfg(password="segredo;com;ponto"))

    assert 'Password="segredo;com;ponto"' in conn
    # Os ';' ficam DENTRO das aspas: a ligacao continua com os mesmos
    # atributos, apenas com os dois ';' extra da propria password.
    assert conn.count(";") == build_connection_string(_cfg()).count(";") + 2


def test_build_connection_string_escapa_aspas() -> None:
    conn = build_connection_string(_cfg(password='as"pas'))

    assert 'Password="as""pas"' in conn


def test_build_connection_string_nao_deixa_injetar_atributos() -> None:
    """Uma password nao pode acrescentar atributos a` ligacao."""
    conn = build_connection_string(
        _cfg(password="x;TrustServerCertificate=False;Initial Catalog=outra")
    )

    assert 'Password="x;TrustServerCertificate=False;Initial Catalog=outra"' in conn
    assert "TrustServerCertificate=True;" in conn


@pytest.mark.parametrize("mau", ["quebra\nlinha", "retorno\rcarro", "nulo\x00byte"])
def test_build_connection_string_recusa_caracteres_impossiveis(mau: str) -> None:
    with pytest.raises(ValueError, match="PHC"):
        build_connection_string(_cfg(password=mau))


def test_build_connection_string_trusted_sem_user() -> None:
    conn = build_connection_string(_cfg(trusted=True))

    assert "Integrated Security=True" in conn
    assert "User ID=" not in conn


def test_build_connection_string_exige_server_e_db() -> None:
    with pytest.raises(ValueError):
        build_connection_string(_cfg(server=""))


def test_build_connection_string_exige_password_em_sql_auth() -> None:
    with pytest.raises(ValueError):
        build_connection_string(_cfg(password=""))


def test_parse_bool() -> None:
    assert _parse_bool("ON") is True
    assert _parse_bool("1") is True
    assert _parse_bool("sim") is True
    assert _parse_bool("OFF") is False
    assert _parse_bool("", default=True) is True
    assert _parse_bool(None, default=False) is False
