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


def test_do_phc_so_vem_o_finalizado_e_o_arquivado(session, monkeypatch) -> None:
    """O Desenho e a Producao sao do utilizador: nao se copiam do PHC.

    Numa comparacao com dados reais, ler tambem o `2 - DESENHO` e o
    `4 - PRODUCAO` dava 52 sugestoes por cima do trabalho de quem esta' na
    obra. Os estados que o Martelo nao conhece (`3 - STANDBY`, `8 - SERVICOS`)
    tambem nao interessam ca'.
    """
    import app.services.producao_phc_sync_service as service_module

    session.add_all(
        [
            _processo(id=1, num_enc_phc="1001", estado="Desenho"),
            _processo(id=2, num_enc_phc="1002", estado="Desenho"),
            _processo(id=3, num_enc_phc="1003", estado="Desenho"),
            _processo(id=4, num_enc_phc="1004", estado="Producao"),
        ]
    )
    session.commit()
    chamadas = []

    def fake_query(session_arg, **kwargs):
        chamadas.append(kwargs)
        return [
            {"Ano": 2026, "Enc_No": "1001", "Estado_PHC": "4 - PRODU\u00c7\u00c3O"},
            {"Ano": 2026, "Enc_No": "1002", "Estado_PHC": "3 - STANDBY"},
            {"Ano": 2026, "Enc_No": "1003", "Estado_PHC": "2 - DESENHO"},
            {"Ano": 2026, "Enc_No": "1004", "Estado_PHC": "7 - ARQUIVADO"},
        ]

    monkeypatch.setattr(service_module, "query_phc_estado_debug_rows", fake_query)

    diffs = service_module.detetar_diferencas_estado_phc(session)

    assert chamadas == [{"ano": "2026", "max_rows": 0}]
    assert [(d["id"], d["estado_sugerido"]) for d in diffs] == [(4, "Arquivado")]
    assert diffs[0]["estado_phc_raw"] == "7 - ARQUIVADO"
    assert diffs[0]["fonte"] == "PHC"
    assert diffs[0]["responsavel"] == "Ana"


def test_uma_obra_nunca_recua_de_estado(session, monkeypatch) -> None:
    """Ja' se viu o PHC a querer por uma obra arquivada de volta em producao."""
    import app.services.producao_phc_sync_service as service_module

    session.add_all(
        [
            _processo(id=1, num_enc_phc="1001", estado="Arquivado"),
            _processo(id=2, num_enc_phc="1002", estado="Arquivado"),
        ]
    )
    session.commit()

    def fake_query(session_arg, **kwargs):
        return [
            {"Ano": 2026, "Enc_No": "1001", "Estado_PHC": "4 - PRODU\u00c7\u00c3O"},
            # Finalizado vem ANTES de arquivado: tambem seria recuar.
            {"Ano": 2026, "Enc_No": "1002", "Estado_PHC": "5 - FINALIZADO"},
        ]

    monkeypatch.setattr(service_module, "query_phc_estado_debug_rows", fake_query)

    assert service_module.detetar_diferencas_estado_phc(session) == []


def test_uma_obra_sem_estado_aceita_o_que_vier(session, monkeypatch) -> None:
    import app.services.producao_phc_sync_service as service_module

    session.add(_processo(id=1, num_enc_phc="1001", estado=""))
    session.commit()

    def fake_query(session_arg, **kwargs):
        return [{"Ano": 2026, "Enc_No": "1001", "Estado_PHC": "5 - FINALIZADO"}]

    monkeypatch.setattr(service_module, "query_phc_estado_debug_rows", fake_query)

    diffs = service_module.detetar_diferencas_estado_phc(session)

    assert [(d["estado_martelo"], d["estado_sugerido"]) for d in diffs] == [
        ("(sem estado)", "Finalizado")
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


def test_detetar_diferencas_estado_streamlit_so_estados_de_fora(
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

    def fake_encomendas(session_arg, *, ano_minimo, max_linhas=0):
        query_chamadas.append({"ano_minimo": ano_minimo, "max_linhas": max_linhas})
        return [
            {"Ano": 2026, "Numero": "_001", "Status": "Finalizada"},
            {"Ano": 2026, "Numero": "_002", "Status": "Arquivada"},
            # "A editar" nao e' um estado de fora: quem manda no Desenho e na
            # Producao e' o utilizador, no Martelo.
            {"Ano": 2026, "Numero": "_003", "Status": "A editar"},
            {"Ano": 2026, "Numero": "_004", "Status": "A editar"},
            {"Ano": 2026, "Numero": "_118", "Status": "Finalizada"},
            {"Ano": 2025, "Numero": "_099", "Status": "Finalizada"},
        ]

    monkeypatch.setattr(
        service_module,
        "query_encomendas_cliente_final",
        fake_encomendas,
    )

    diffs = service_module.detetar_diferencas_estado_streamlit(session)

    assert query_chamadas == [{"ano_minimo": 2026, "max_linhas": 0}]
    # _003 e _004 ficam de fora (Status que nao e' terminal); a encomenda PHC
    # 1005 tambem, porque esta funcao so' olha para as de cliente final.
    assert [(d["id"], d["estado_sugerido"]) for d in diffs] == [
        (1, "Finalizado"),
        (2, "Arquivado"),
        (5, "Finalizado"),
        (6, "Finalizado"),
    ]
    assert all(diff["fonte"] == "Streamlit" for diff in diffs)
    assert diffs[0]["estado_phc_raw"] == "Finalizada"


def test_levantar_junta_as_duas_fontes_e_ordena(session, monkeypatch) -> None:
    import app.services.producao_phc_sync_service as service_module

    monkeypatch.setattr(
        service_module,
        "detetar_diferencas_estado_phc",
        lambda s, **k: [{"codigo": "26.2000_01_01_B", "id": 2}],
    )
    monkeypatch.setattr(
        service_module,
        "detetar_diferencas_estado_streamlit",
        lambda s, **k: [{"codigo": "26.1000_01_01_A", "id": 1}],
    )

    levantamento = service_module.levantar_estados_de_fora(lambda: session)

    # Misturadas e por código: quem lê a lista não quer o PHC todo primeiro.
    assert [d["id"] for d in levantamento.diferencas] == [1, 2]
    assert bool(levantamento) is True
    assert levantamento.falharam_as_duas is False


def test_uma_fonte_em_baixo_nao_estraga_a_outra(session, monkeypatch) -> None:
    """PHC e Streamlit são servidores diferentes: um pode faltar sozinho."""
    import app.services.producao_phc_sync_service as service_module

    def rebenta(_session, **_kwargs):
        raise RuntimeError("sem rede")

    monkeypatch.setattr(service_module, "detetar_diferencas_estado_phc", rebenta)
    monkeypatch.setattr(
        service_module,
        "detetar_diferencas_estado_streamlit",
        lambda s, **k: [{"codigo": "26.1000_01_01_A", "id": 1}],
    )

    levantamento = service_module.levantar_estados_de_fora(lambda: session)

    assert [d["id"] for d in levantamento.diferencas] == [1]
    assert levantamento.erro_phc == "sem rede"
    assert levantamento.erro_streamlit == ""
    assert levantamento.falharam_as_duas is False


def test_as_duas_em_baixo_dizem_se(session, monkeypatch) -> None:
    import app.services.producao_phc_sync_service as service_module

    def rebenta(_session, **_kwargs):
        raise RuntimeError("sem rede")

    monkeypatch.setattr(service_module, "detetar_diferencas_estado_phc", rebenta)
    monkeypatch.setattr(
        service_module, "detetar_diferencas_estado_streamlit", rebenta
    )

    levantamento = service_module.levantar_estados_de_fora(lambda: session)

    assert levantamento.falharam_as_duas is True
    assert bool(levantamento) is False


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
