"""Tests for the PHC orders (Encomendas) read service."""

from __future__ import annotations

from app.services import encomendas_phc_service as service_module
from app.services.phc_sql import assert_select_only


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
        return [{"Cliente": "X"}]

    monkeypatch.setattr(service_module, "load_phc_config", _fake_load)
    monkeypatch.setattr(service_module, "build_connection_string", _fake_build)
    monkeypatch.setattr(service_module, "run_select", _fake_run)


def test_query_encomendas_phc_constroi_select_valido(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    _patch(monkeypatch, capturado)

    session = object()
    result = service_module.query_encomendas_phc(session, ano_minimo=2026)

    assert result == [{"Cliente": "X"}]
    assert capturado["session"] is session
    assert capturado["conn_str"] == "conn"

    query = str(capturado["query"])
    assert_select_only(query)  # passa o guarda so-leitura
    assert "FROM BI" in query
    assert "BO2.ANULADO = 0" in query
    assert "2026" in query
    assert "TOP" not in query  # max_linhas=0 (default) => sem limite


def test_query_encomendas_phc_aplica_top_quando_max_linhas(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    _patch(monkeypatch, capturado)

    service_module.query_encomendas_phc(
        object(), ano_minimo=2024, max_linhas=5000
    )

    query = str(capturado["query"])
    assert_select_only(query)
    assert "TOP" in query
    assert "5000" in query
    assert "2024" in query
