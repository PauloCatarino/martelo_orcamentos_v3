"""Tests for PHC material/article read service."""

from __future__ import annotations

from app.services import phc_materiais_service as service_module


def test_query_phc_materiais_usa_st_e_familias_de_material(monkeypatch) -> None:
    capturado: dict[str, object] = {}

    def _fake_load(session):
        capturado["session"] = session
        return {"cfg": "ok"}

    def _fake_build(cfg):
        capturado["cfg"] = cfg
        return "conn"

    def _fake_run(conn_str, query):
        capturado["conn_str"] = conn_str
        capturado["query"] = query
        return [{"Ref": "X"}]

    monkeypatch.setattr(service_module, "load_phc_config", _fake_load)
    monkeypatch.setattr(service_module, "build_connection_string", _fake_build)
    monkeypatch.setattr(service_module, "run_select", _fake_run)

    session = object()
    result = service_module.query_phc_materiais(session)

    assert result == [{"Ref": "X"}]
    assert capturado["session"] is session
    assert capturado["conn_str"] == "conn"
    query = str(capturado["query"])
    assert "FROM ST WITH (NOLOCK)" in query
    assert "inactivo = 0" in query
    assert "'FF00000'" in query
    assert "'FM00000'" in query
    assert "'FO00000'" in query
    assert "epv1 AS Preco_Venda" in query
    assert "epcusto AS Preco_Custo" in query
