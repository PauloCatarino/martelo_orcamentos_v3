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
    ],
)
def test_assert_select_only_rejeita_nao_select(query: str) -> None:
    with pytest.raises(RuntimeError):
        assert_select_only(query)


def test_build_connection_string_sql_auth() -> None:
    conn = build_connection_string(_cfg())

    assert r"Server=Server_le\phc" in conn
    assert "Database=lancaencanto" in conn
    assert "User ID=adriano.silva" in conn
    assert "Password=segredo" in conn
    assert "TrustServerCertificate=True" in conn


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
