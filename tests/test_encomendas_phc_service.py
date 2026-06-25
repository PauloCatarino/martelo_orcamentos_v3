"""Tests for the PHC orders (Encomendas) read service."""

from __future__ import annotations

import pytest

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


def test_build_phc_estado_debug_query_defaults_select_valido() -> None:
    query = service_module._build_phc_estado_debug_query(min_year=2026)

    assert_select_only(query)
    assert query.startswith("SELECT DISTINCT TOP (2000)")
    assert not query.endswith(";")
    assert "BI.NDOS = 1" in query
    assert "LTRIM(RTRIM(BI.NMDOS)) = 'Encomenda de Cliente'" in query
    assert "BI.DATAOBRA >= '2026-01-01'" in query
    assert "BI.OBRANO =" not in query
    assert "BI.FDATA AS FDataRaw" in query
    assert "BI_DataObraRaw" not in query
    assert "ORDER BY FDataRaw DESC, Enc_No DESC, BI_Bostamp DESC" in query


def test_build_phc_estado_debug_query_filtra_numero_e_ano() -> None:
    query = service_module._build_phc_estado_debug_query(
        num_enc_phc="402",
        ano=2025,
        min_year=2020,
        max_rows=50,
    )

    assert_select_only(query)
    assert "SELECT DISTINCT TOP (50)" in query
    assert "BI.OBRANO = 402" in query
    assert "BI.DATAOBRA >= '2025-01-01'" in query
    assert "BI.DATAOBRA < '2026-01-01'" in query
    assert "BI.DATAOBRA >= '2020-01-01'" not in query


def test_query_phc_estado_debug_rows_executa_select_read_only(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    _patch(monkeypatch, capturado)

    result = service_module.query_phc_estado_debug_rows(
        object(),
        num_enc_phc="402",
        min_year=2026,
        max_rows=2000,
    )

    assert result == [{"Cliente": "X"}]
    assert capturado["conn_str"] == "conn"
    query = str(capturado["query"])
    assert_select_only(query)
    assert "FROM BI WITH (NOLOCK)" in query
    assert "BI.OBRANO = 402" in query
    assert "TOP (2000)" in query


def test_query_phc_encomenda_itens_constroi_select_read_only(monkeypatch) -> None:
    capturado: dict[str, object] = {}
    _patch(monkeypatch, capturado)

    result = service_module.query_phc_encomenda_itens(
        object(),
        num_enc_phc="ENC 402",
        ano=2026,
    )

    assert result == [{"Cliente": "X"}]
    assert capturado["conn_str"] == "conn"
    query = str(capturado["query"])
    assert_select_only(query)
    assert "FROM BI WITH (NOLOCK)" in query
    assert "INNER JOIN BO2 WITH (NOLOCK)" in query
    assert "BO2.ANULADO = 0" in query
    assert "BI.OBRANO = 402" in query
    assert "BI.DATAOBRA >= '2026-01-01'" in query
    assert "BI.DATAOBRA < '2027-01-01'" in query
    assert "ORDER BY BI.LORDEM ASC" in query


def test_query_phc_encomenda_itens_valida_numero() -> None:
    with pytest.raises(ValueError, match="Num Enc PHC"):
        service_module.query_phc_encomenda_itens(object(), num_enc_phc="")
