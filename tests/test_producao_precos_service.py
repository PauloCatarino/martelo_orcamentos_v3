"""Tests for production price validation against PHC/Streamlit."""

from __future__ import annotations

from decimal import Decimal

import pytest

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models.producao import Producao


def _processo(
    *,
    id: int,
    num_enc_phc: str,
    tipo_pasta: str,
    preco_total=None,
    responsavel: str | None = "Ana",
) -> Producao:
    return Producao(
        id=id,
        codigo_processo=f"26.{num_enc_phc}_01_01_CLIENTE",
        ano="2026",
        num_enc_phc=num_enc_phc,
        versao_obra="01",
        versao_plano="01",
        estado="Desenho",
        responsavel=responsavel,
        tipo_pasta=tipo_pasta,
        nome_cliente=f"Cliente {id}",
        nome_cliente_simplex=f"CLIENTE_{id}",
        preco_total=preco_total,
    )


def test_detetar_diferencas_preco_phc_streamlit_e_responsavel(
    session,
    monkeypatch,
) -> None:
    import app.services.producao_precos_service as service_module

    session.add_all(
        [
            _processo(
                id=1,
                num_enc_phc="1001",
                tipo_pasta="Encomenda de Cliente",
                preco_total=None,
                responsavel="Ana",
            ),
            _processo(
                id=2,
                num_enc_phc="1002",
                tipo_pasta="Encomenda de Cliente",
                preco_total=Decimal("250.00"),
                responsavel="Paulo",
            ),
            _processo(
                id=3,
                num_enc_phc="_007",
                tipo_pasta="Encomenda de Cliente Final",
                preco_total=Decimal("50.00"),
                responsavel="Ana",
            ),
            _processo(
                id=4,
                num_enc_phc="1004",
                tipo_pasta="Encomenda de Cliente",
                preco_total=Decimal("101.20"),
                responsavel="Ana",
            ),
        ]
    )
    session.commit()
    phc_queries = []

    monkeypatch.setattr(service_module.phc_sql, "load_phc_config", lambda s: {})
    monkeypatch.setattr(
        service_module.phc_sql,
        "build_connection_string",
        lambda cfg: "phc-conn",
    )
    monkeypatch.setattr(service_module.st, "load_streamlit_config", lambda s: {})
    monkeypatch.setattr(
        service_module.st,
        "build_connection_string",
        lambda cfg: "st-conn",
    )

    def fake_run(conn, query):
        if conn == "phc-conn":
            phc_queries.append(query)
            return [
                {"enc": "1001", "total": 123.45},
                {"enc": "1002", "total": 300.00},
                {"enc": "1004", "total": 101.60},
            ]
        if conn == "st-conn":
            return [{"numero": "_007", "total": 75.50}]
        raise AssertionError(conn)

    monkeypatch.setattr(service_module.phc_sql, "run_select", fake_run)

    diffs = service_module.detetar_diferencas_preco(session, responsavel="ana")

    assert len(phc_queries) == 1
    assert "BO.DATAOBRA >= '2026-01-01'" in phc_queries[0]
    assert "BO.DATAOBRA < '2027-01-01'" in phc_queries[0]
    assert diffs == [
        {
            "id": 1,
            "codigo": "26.1001_01_01_CLIENTE",
            "num_enc": "1001",
            "cliente": "Cliente 1",
            "fonte": "PHC",
            "preco_martelo": None,
            "preco_externo": 123.45,
            "default_check": True,
        },
        {
            "id": 3,
            "codigo": "26._007_01_01_CLIENTE",
            "num_enc": "_007",
            "cliente": "Cliente 3",
            "fonte": "Streamlit",
            "preco_martelo": 50.0,
            "preco_externo": 75.5,
            "default_check": False,
        },
    ]


def test_aplicar_precos_atualiza_selecionados(session) -> None:
    from app.services.producao_precos_service import aplicar_precos

    session.add_all(
        [
            _processo(
                id=1,
                num_enc_phc="1001",
                tipo_pasta="Encomenda de Cliente",
                preco_total=None,
            ),
            _processo(
                id=2,
                num_enc_phc="_007",
                tipo_pasta="Encomenda de Cliente Final",
                preco_total=Decimal("10.00"),
            ),
        ]
    )
    session.commit()

    atualizadas = aplicar_precos(
        session,
        [(1, 123.45), (999, 1), (2, "invalido")],
        current_user_id=7,
    )

    assert atualizadas == 1
    assert session.get(Producao, 1).preco_total == Decimal("123.45")
    assert session.get(Producao, 1).updated_by_id == 7
    assert session.get(Producao, 2).preco_total == Decimal("10.00")
