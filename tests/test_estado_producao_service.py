"""Testes do serviço SQL do estado de produção (PD2).

Sem tocar na BD real: a lógica de junção/normalização é testada com ``run_select``
mockado (monkeypatch) e uma sessão SQLite em memória para as obras (``producao``).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (regista todos os modelos em Base.metadata)
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
    tipo_pasta: str,
    preco_total=None,
    responsavel: str | None = "Ana",
    ref_cliente: str | None = None,
) -> Producao:
    return Producao(
        id=id,
        codigo_processo=f"26.{num_enc_phc}_01_01_CLIENTE",
        ano="2026",
        num_enc_phc=num_enc_phc,
        versao_obra="01",
        versao_plano="01",
        estado="Produção",
        responsavel=responsavel,
        tipo_pasta=tipo_pasta,
        nome_cliente=f"Cliente {id}",
        ref_cliente=ref_cliente,
        preco_total=preco_total,
    )


def _linha_st(bd_ano: str, bd_n_encomenda: str, **overrides) -> dict:
    """Uma linha (bd_key) do Streamlit, com tudo "vazio" por defeito."""
    base = {
        "bd_key": f"{bd_ano}_{bd_n_encomenda}_01_01",
        "bd_ano": bd_ano,
        "bd_n_encomenda": bd_n_encomenda,
        "bd_modelo": "01",
        "bd_versao": "01",
        "bd_cliente": "X",
        "bd_existe_montagem": "0",
        "bd_stock_ok": None,
        "bd_preparacao_placas_ok": None,
        "bd_corte_ok": None,
        "bd_orla_ok": None,
        "bd_cnc_ok": None,
        "bd_montagem_ok": None,
        "bd_embalagem_ok": None,
        "bd_expedicao_ok": None,
        "bd_operacoes_corte_quantidade": 0,
        "bd_operacoes_orla_quantidade": 0,
        "bd_operacoes_cnc_quantidade": 0,
        "bd_tempo_embalamento_minutos": 0,
    }
    base.update(overrides)
    return base


def _patch_streamlit(monkeypatch, svc, fake_run) -> None:
    monkeypatch.setattr(svc.st, "load_streamlit_config", lambda s: {})
    monkeypatch.setattr(svc.st, "build_connection_string", lambda cfg: "st-conn")
    monkeypatch.setattr(svc, "run_select", fake_run)


def test_encomenda_normal_duas_linhas_media_agregada(session, monkeypatch) -> None:
    import app.services.estado_producao_service as svc

    session.add(
        _processo(
            id=1,
            num_enc_phc="1001",
            tipo_pasta="Encomenda de Cliente",
            ref_cliente="REF-A",
        )
    )
    session.commit()

    def fake_run(conn, query):
        assert conn == "st-conn"
        if "dbo.CadernoEncargos_" in query:
            return []  # universo especial vazio
        # Duas bd_key da mesma encomenda: Preparação 100 e 0 -> média 50.
        return [
            _linha_st("2026", "1001", bd_preparacao_placas_ok="100"),
            _linha_st("2026", "1001", bd_preparacao_placas_ok="0"),
        ]

    _patch_streamlit(monkeypatch, svc, fake_run)

    resultados = svc.estado_producao_por_processo(session)

    assert len(resultados) == 1
    obra = resultados[0]
    assert obra.encontrado is True
    assert obra.fonte == "Streamlit"
    # Obra PHC: enc_phc preenchido, enc_streamlit vazio; ref_cliente propagado.
    assert obra.enc_phc == "1001"
    assert obra.enc_streamlit == ""
    assert obra.ref_cliente == "REF-A"
    setores = {s.nome: s.media_pct for s in obra.estado.setores}
    assert setores == {"Preparação": 50.0}


def test_encomenda_especial_liga_obra_streamlit(session, monkeypatch) -> None:
    import app.services.estado_producao_service as svc

    # Obra Streamlit "_58" deve ligar à linha especial "_058" (normalização).
    session.add(
        _processo(id=3, num_enc_phc="_58", tipo_pasta="Encomenda de Cliente Final")
    )
    session.commit()

    def fake_run(conn, query):
        if "dbo.CadernoEncargos_" in query:
            return [_linha_st("2026", "_058", bd_stock_ok="100")]
        return []

    _patch_streamlit(monkeypatch, svc, fake_run)

    resultados = svc.estado_producao_por_processo(session)

    assert len(resultados) == 1
    obra = resultados[0]
    assert obra.fonte == "Streamlit _"
    assert obra.encontrado is True
    # Obra Streamlit: enc_streamlit preenchido com o num_enc_phc; enc_phc vazio.
    assert obra.enc_streamlit == "_58"
    assert obra.enc_phc == ""
    assert {s.nome for s in obra.estado.setores} == {"Stock"}
    assert obra.estado.setores[0].media_pct == 100.0


def test_obra_sem_linhas_no_streamlit(session, monkeypatch) -> None:
    import app.services.estado_producao_service as svc

    session.add(
        _processo(id=1, num_enc_phc="1001", tipo_pasta="Encomenda de Cliente")
    )
    session.commit()

    _patch_streamlit(monkeypatch, svc, lambda conn, query: [])

    resultados = svc.estado_producao_por_processo(session)

    assert len(resultados) == 1
    obra = resultados[0]
    assert obra.encontrado is False
    assert obra.estado.total_setores == 0
    assert obra.estado.etiqueta == "—"
    assert obra.concluido_sem_preco is False


def test_concluido_sem_preco(session, monkeypatch) -> None:
    import app.services.estado_producao_service as svc

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
                num_enc_phc="1002",
                tipo_pasta="Encomenda de Cliente",
                preco_total=Decimal("250.00"),
            ),
        ]
    )
    session.commit()

    def fake_run(conn, query):
        if "dbo.CadernoEncargos_" in query:
            return []
        return [
            _linha_st("2026", "1001", bd_preparacao_placas_ok="100"),
            _linha_st("2026", "1002", bd_preparacao_placas_ok="100"),
        ]

    _patch_streamlit(monkeypatch, svc, fake_run)

    por_id = {r.id: r for r in svc.estado_producao_por_processo(session)}

    # Ambas 100%; só a sem preço é "concluído sem preço".
    assert por_id[1].estado.global_pct == 100.0
    assert por_id[1].concluido_sem_preco is True
    assert por_id[2].estado.global_pct == 100.0
    assert por_id[2].concluido_sem_preco is False


def test_filtro_por_responsavel(session, monkeypatch) -> None:
    import app.services.estado_producao_service as svc

    session.add_all(
        [
            _processo(
                id=1,
                num_enc_phc="1001",
                tipo_pasta="Encomenda de Cliente",
                responsavel="Ana",
            ),
            _processo(
                id=2,
                num_enc_phc="1002",
                tipo_pasta="Encomenda de Cliente",
                responsavel="Paulo",
            ),
        ]
    )
    session.commit()

    _patch_streamlit(monkeypatch, svc, lambda conn, query: [])

    resultados = svc.estado_producao_por_processo(session, responsavel="ana")

    assert [r.id for r in resultados] == [1]
