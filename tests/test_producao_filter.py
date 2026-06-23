"""Tests for production-process filtering."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.producao_service import filtrar_processos


def _processo(**overrides) -> SimpleNamespace:
    base = {
        "codigo_processo": "26.1028_01_01",
        "num_enc_phc": "1028",
        "nome_cliente": "Cliente Alfa",
        "nome_cliente_simplex": "cliente alfa",
        "ref_cliente": "REF-A",
        "obra": "Cozinha Lisboa",
        "localizacao": "Lisboa",
        "num_orcamento": "260001",
        "responsavel": "ana",
        "descricao_producao": "Moveis lacados",
        "estado": "Desenho",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_filtrar_processos_pesquisa_multi_termo() -> None:
    processos = [
        _processo(nome_cliente="Cliente Alfa", obra="Cozinha Lisboa"),
        _processo(
            nome_cliente="Cliente Beta",
            obra="Roupeiro Porto",
            localizacao="Porto",
        ),
    ]

    assert filtrar_processos(processos, texto="cliente LISBOA") == [processos[0]]
    assert filtrar_processos(processos, texto="1028%lacados") == processos


def test_filtrar_processos_filtra_por_estado_cliente_responsavel() -> None:
    processos = [
        _processo(estado="Desenho", nome_cliente="Cliente Alfa", responsavel="ana"),
        _processo(estado="Produção", nome_cliente="Cliente Alfa", responsavel="bruno"),
        _processo(estado="Produção", nome_cliente="Cliente Beta", responsavel="ana"),
    ]

    assert filtrar_processos(processos, estado="Produção") == [
        processos[1],
        processos[2],
    ]
    assert filtrar_processos(processos, cliente="Cliente Alfa") == [
        processos[0],
        processos[1],
    ]
    assert filtrar_processos(processos, responsavel="ana") == [
        processos[0],
        processos[2],
    ]
    assert filtrar_processos(
        processos,
        estado="Produção",
        cliente="Cliente Beta",
        responsavel="ana",
    ) == [processos[2]]


def test_filtrar_processos_todos_none_vazio_e_sem_match() -> None:
    processos = [
        _processo(codigo_processo="26.1028_01_01"),
        _processo(codigo_processo="26.1029_01_01"),
    ]

    assert filtrar_processos(
        processos,
        texto="  %% ",
        estado="Todos",
        cliente=None,
        responsavel="",
    ) == processos
    assert filtrar_processos(processos, texto="inexistente") == []
