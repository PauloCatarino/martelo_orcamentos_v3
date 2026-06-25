"""Tests for the Streamlit (Cliente Final) read-only SQL service."""

from __future__ import annotations

import pytest

from app.services import streamlit_sql_service as service_module
from app.services.phc_sql import assert_select_only
from app.services.streamlit_sql_service import build_connection_string


def _cfg(**overrides):
    base = {
        "server": "DESKTOP-PTJ4TE6,1433",
        "database": "Lanca_Encanto2026",
        "user": "Lanca_Encanto_ReadOnly",
        "password": "segredo",
        "trusted": False,
        "trust_server_certificate": True,
    }
    base.update(overrides)
    return base


def _patch(monkeypatch, capturado) -> None:
    def _fake_load(session):
        capturado["session"] = session
        return {"cfg": "ok"}

    def _fake_build(cfg):
        capturado["cfg"] = cfg
        return "conn"

    def _fake_run(conn_str, query):
        capturado["conn_str"] = conn_str
        capturado["query"] = query
        return [{"Id": 1}]

    monkeypatch.setattr(service_module, "load_streamlit_config", _fake_load)
    monkeypatch.setattr(service_module, "build_connection_string", _fake_build)
    monkeypatch.setattr(service_module, "run_select", _fake_run)


def test_build_connection_string_inclui_encrypt_e_trust() -> None:
    conn = build_connection_string(_cfg())

    assert "Server=DESKTOP-PTJ4TE6,1433" in conn
    assert "Database=Lanca_Encanto2026" in conn
    assert "Encrypt=False" in conn
    assert "Connection Timeout=60" in conn
    assert "User ID=Lanca_Encanto_ReadOnly" in conn
    assert "Password=segredo" in conn
    assert "TrustServerCertificate=True" in conn


def test_build_connection_string_trusted_sem_user() -> None:
    conn = build_connection_string(_cfg(trusted=True))

    assert "Integrated Security=True" in conn
    assert "User ID=" not in conn
    assert "Encrypt=False" in conn


def test_build_connection_string_exige_server_e_db() -> None:
    with pytest.raises(ValueError):
        build_connection_string(_cfg(server=""))


def test_build_connection_string_exige_password_em_sql_auth() -> None:
    with pytest.raises(ValueError):
        build_connection_string(_cfg(password=""))


def test_query_encomendas_cliente_final(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    _patch(monkeypatch, capturado)

    session = object()
    result = service_module.query_encomendas_cliente_final(session, ano_minimo=2026)

    assert result == [{"Id": 1}]
    assert capturado["session"] is session
    assert capturado["conn_str"] == "conn"

    query = str(capturado["query"])
    assert_select_only(query)
    assert "dbo.Encomendas" in query
    assert "Ano >= 2026" in query
    assert "TOP" not in query


def test_query_encomendas_cliente_final_aplica_top(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    _patch(monkeypatch, capturado)

    service_module.query_encomendas_cliente_final(
        object(), ano_minimo=2024, max_linhas=5000
    )

    query = str(capturado["query"])
    assert_select_only(query)
    assert "TOP" in query
    assert "5000" in query
    assert "2024" in query


def test_query_itens_encomenda(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    _patch(monkeypatch, capturado)

    result = service_module.query_itens_encomenda(object(), encomenda_id=42)

    assert result == [{"Id": 1}]
    query = str(capturado["query"])
    assert_select_only(query)
    assert "dbo.ItensEncomenda" in query
    assert "EncomendaId = 42" in query
    assert "TOP" not in query


def test_query_itens_encomenda_aplica_top(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    _patch(monkeypatch, capturado)

    service_module.query_itens_encomenda(object(), encomenda_id=7, max_itens=20000)

    query = str(capturado["query"])
    assert_select_only(query)
    assert "TOP" in query
    assert "20000" in query
    assert "EncomendaId = 7" in query
