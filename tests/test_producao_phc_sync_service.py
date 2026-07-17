"""Tests for production state sync from PHC."""

from __future__ import annotations

import pytest

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models.producao import Producao


def _processo(
    *,
    id: int,
    num_enc_phc: str,
    estado: str,
    tipo_pasta: str = "Encomenda de Cliente",
    responsavel: str | None = "Ana",
    versao_obra: str = "01",
) -> Producao:
    return Producao(
        id=id,
        codigo_processo=f"26.{num_enc_phc}_{versao_obra}_01_CLIENTE",
        ano="2026",
        num_enc_phc=num_enc_phc,
        versao_obra=versao_obra,
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


@pytest.mark.parametrize(
    ("raw", "esperado"),
    [
        ("Arquivada", "Arquivado"),
        (7, "Arquivado"),
        ("7", "Arquivado"),
        ("Finalizada", "Finalizado"),
        (5, "Finalizado"),
        ("5", "Finalizado"),
        ("15", None),
        ("70", None),
    ],
)
def test_mapear_status_streamlit_tolerante(raw, esperado) -> None:
    import app.services.producao_phc_sync_service as service_module

    assert service_module._mapear_status_streamlit(raw) == esperado


def test_detetar_diferencas_estado_streamlit_status_e_ok(
    session,
    monkeypatch,
) -> None:
    import app.services.producao_phc_sync_service as service_module

    tipo_streamlit = "Encomenda de Cliente Final"
    session.add_all(
        [
            _processo(
                id=1,
                num_enc_phc="_001",
                estado="Desenho",
                tipo_pasta=tipo_streamlit,
            ),
            _processo(
                id=2,
                num_enc_phc="_002",
                estado="Desenho",
                tipo_pasta=tipo_streamlit,
            ),
            _processo(
                id=3,
                num_enc_phc="_003",
                estado="Desenho",
                tipo_pasta=tipo_streamlit,
            ),
            _processo(
                id=4,
                num_enc_phc="_004",
                estado="Producao",
                tipo_pasta=tipo_streamlit,
            ),
            _processo(
                id=5,
                num_enc_phc="_118",
                estado="Desenho",
                tipo_pasta=tipo_streamlit,
                versao_obra="01",
            ),
            _processo(
                id=6,
                num_enc_phc="_118",
                estado="Producao",
                tipo_pasta=tipo_streamlit,
                versao_obra="02",
            ),
            _processo(
                id=7,
                num_enc_phc="1005",
                estado="Desenho",
                tipo_pasta="Encomenda de Cliente",
            ),
        ]
    )
    session.commit()
    query_chamadas = []
    indice_chamadas = []

    def fake_encomendas(session_arg, *, ano_minimo, max_linhas=0):
        query_chamadas.append({"ano_minimo": ano_minimo, "max_linhas": max_linhas})
        return [
            {"Ano": 2026, "Numero": "_001", "Status": "Finalizada"},
            {"Ano": 2026, "Numero": "_002", "Status": "Arquivada"},
            {"Ano": 2026, "Numero": "_003", "Status": "A editar"},
            {"Ano": 2026, "Numero": "_004", "Status": "A editar"},
            {"Ano": 2026, "Numero": "_118", "Status": "Finalizada"},
            {"Ano": 2025, "Numero": "_099", "Status": "Finalizada"},
        ]

    def fake_carregar_indice(session_arg, *, anos_normais, anos_especiais):
        indice_chamadas.append((list(anos_normais), list(anos_especiais)))
        return {
            ("E", "2026", "_003"): [{"bd_orla_ok": "10"}],
            ("E", "2026", "_004"): [
                {"bd_corte_ok": "0", "bd_orla_ok": None, "bd_cnc_ok": "N"}
            ],
        }

    monkeypatch.setattr(
        service_module,
        "query_encomendas_cliente_final",
        fake_encomendas,
    )
    monkeypatch.setattr(service_module, "carregar_indice", fake_carregar_indice)

    diffs = service_module.detetar_diferencas_estado_streamlit(session)

    assert query_chamadas == [{"ano_minimo": 2026, "max_linhas": 0}]
    assert indice_chamadas == [([], ["2026"])]
    assert diffs == [
        {
            "id": 1,
            "codigo": "26._001_01_01_CLIENTE",
            "num_enc_phc": "_001",
            "cliente": "Cliente 1",
            "estado_martelo": "Desenho",
            "estado_sugerido": "Finalizado",
            "estado_phc_raw": "Finalizada",
            "fonte": "Streamlit",
        },
        {
            "id": 2,
            "codigo": "26._002_01_01_CLIENTE",
            "num_enc_phc": "_002",
            "cliente": "Cliente 2",
            "estado_martelo": "Desenho",
            "estado_sugerido": "Arquivado",
            "estado_phc_raw": "Arquivada",
            "fonte": "Streamlit",
        },
        {
            "id": 3,
            "codigo": "26._003_01_01_CLIENTE",
            "num_enc_phc": "_003",
            "cliente": "Cliente 3",
            "estado_martelo": "Desenho",
            "estado_sugerido": "Producao",
            "estado_phc_raw": "A editar",
            "fonte": "Streamlit",
        },
        {
            "id": 4,
            "codigo": "26._004_01_01_CLIENTE",
            "num_enc_phc": "_004",
            "cliente": "Cliente 4",
            "estado_martelo": "Producao",
            "estado_sugerido": "Desenho",
            "estado_phc_raw": "A editar",
            "fonte": "Streamlit",
        },
        {
            "id": 5,
            "codigo": "26._118_01_01_CLIENTE",
            "num_enc_phc": "_118",
            "cliente": "Cliente 5",
            "estado_martelo": "Desenho",
            "estado_sugerido": "Finalizado",
            "estado_phc_raw": "Finalizada",
            "fonte": "Streamlit",
        },
        {
            "id": 6,
            "codigo": "26._118_02_01_CLIENTE",
            "num_enc_phc": "_118",
            "cliente": "Cliente 6",
            "estado_martelo": "Producao",
            "estado_sugerido": "Finalizado",
            "estado_phc_raw": "Finalizada",
            "fonte": "Streamlit",
        },
    ]


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
