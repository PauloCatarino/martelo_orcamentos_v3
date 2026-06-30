"""Tests for production state sync from PHC."""

from __future__ import annotations

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models.producao import Producao


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _processo(
    *,
    id: int,
    num_enc_phc: str,
    estado: str,
    tipo_pasta: str = "Encomenda de Cliente",
    responsavel: str | None = "Ana",
) -> Producao:
    return Producao(
        id=id,
        codigo_processo=f"26.{num_enc_phc}_01_01_CLIENTE",
        ano="2026",
        num_enc_phc=num_enc_phc,
        versao_obra="01",
        versao_plano="01",
        estado=estado,
        responsavel=responsavel,
        tipo_pasta=tipo_pasta,
        nome_cliente=f"Cliente {id}",
        nome_cliente_simplex=f"CLIENTE_{id}",
    )


def test_detetar_diferencas_estado_phc_filtra_e_mapeia(session, monkeypatch) -> None:
    import app.services.producao_phc_sync_service as service_module

    session.add_all(
        [
            _processo(id=1, num_enc_phc="1001", estado="Desenho"),
            _processo(id=2, num_enc_phc="1002", estado="Finalizado"),
            _processo(
                id=3,
                num_enc_phc="_007",
                estado="Desenho",
                tipo_pasta="Encomenda de Cliente Final",
            ),
            _processo(id=4, num_enc_phc="1003", estado="Desenho"),
        ]
    )
    session.commit()
    chamadas = []

    def fake_query(session_arg, **kwargs):
        chamadas.append(kwargs)
        return [
            {"Ano": 2026, "Enc_No": "1001", "Estado_PHC": "Em Produ\u00e7\u00e3o"},
            {"Ano": 2026, "Enc_No": "1002", "Estado_PHC": "Finalizado"},
            {"Ano": 2026, "Enc_No": "_007", "Estado_PHC": "Arquivado"},
            {"Ano": 2026, "Enc_No": "1003", "Estado_PHC": "Sem Estado"},
        ]

    monkeypatch.setattr(service_module, "query_phc_estado_debug_rows", fake_query)

    diffs = service_module.detetar_diferencas_estado_phc(session)

    assert chamadas == [{"ano": "2026", "max_rows": 0}]
    assert diffs == [
        {
            "id": 1,
            "codigo": "26.1001_01_01_CLIENTE",
            "num_enc_phc": "1001",
            "cliente": "Cliente 1",
            "estado_martelo": "Desenho",
            "estado_sugerido": "Producao",
            "estado_phc_raw": "Em Produ\u00e7\u00e3o",
        }
    ]


def test_detetar_diferencas_estado_phc_filtra_responsavel(
    session,
    monkeypatch,
) -> None:
    import app.services.producao_phc_sync_service as service_module

    session.add_all(
        [
            _processo(
                id=1,
                num_enc_phc="1001",
                estado="Desenho",
                responsavel="Ana",
            ),
            _processo(
                id=2,
                num_enc_phc="1002",
                estado="Desenho",
                responsavel="Paulo",
            ),
        ]
    )
    session.commit()

    def fake_query(session_arg, **kwargs):
        return [
            {"Ano": 2026, "Enc_No": "1001", "Estado_PHC": "Em Produ\u00e7\u00e3o"},
            {"Ano": 2026, "Enc_No": "1002", "Estado_PHC": "Arquivado"},
        ]

    monkeypatch.setattr(service_module, "query_phc_estado_debug_rows", fake_query)

    diffs = service_module.detetar_diferencas_estado_phc(
        session,
        responsavel="paulo",
    )

    assert [diff["id"] for diff in diffs] == [2]
    assert diffs[0]["num_enc_phc"] == "1002"


def test_aplicar_estados_atualiza_selecionados(session) -> None:
    from app.services.producao_phc_sync_service import aplicar_estados

    session.add_all(
        [
            _processo(id=1, num_enc_phc="1001", estado="Desenho"),
            _processo(id=2, num_enc_phc="1002", estado="Desenho"),
        ]
    )
    session.commit()

    atualizadas = aplicar_estados(
        session,
        [(1, "Producao"), (999, "Arquivado")],
        current_user_id=7,
    )

    assert atualizadas == 1
    assert session.get(Producao, 1).estado == "Producao"
    assert session.get(Producao, 1).updated_by_id == 7
    assert session.get(Producao, 2).estado == "Desenho"
