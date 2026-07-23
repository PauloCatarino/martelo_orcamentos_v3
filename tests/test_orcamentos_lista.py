"""Tests for pure budget-list helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from app.domain.orcamento_estados import ESTADO_INICIAL
from app.domain.orcamentos_lista import (
    filtrar_orcamentos,
    ordenar_orcamentos,
    resumo_lista,
    vocabulario_orcamentos,
)


def test_resumo_lista_conta_e_soma_precos_ignorando_none() -> None:
    orcamentos = [
        SimpleNamespace(preco_total=Decimal("10.50")),
        SimpleNamespace(preco_total=None),
        SimpleNamespace(preco_total=Decimal("2.25")),
    ]

    contagem, total = resumo_lista(orcamentos)

    assert contagem == 3
    assert total == Decimal("12.75")


def _orcamento(**overrides) -> SimpleNamespace:
    base = {
        "num_orcamento": "260001",
        "cliente_nome": "Cliente Alfa",
        "ref_cliente": "REF-A",
        "obra": "Cozinha Lisboa",
        "localizacao": "Lisboa",
        "descricao": "Moveis altos",
        "estado": ESTADO_INICIAL,
        "utilizador": "ana",
        "enc_phc": "1028",
        "info_1": "Entrega urgente",
        "info_2": "Sem observacoes",
        "preco_total": Decimal("10"),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_filtrar_orcamentos_pesquisa_multi_termo_case_insensitive() -> None:
    orcamentos = [
        _orcamento(cliente_nome="Cliente Alfa", obra="Cozinha Lisboa"),
        _orcamento(
            cliente_nome="Cliente Beta",
            obra="Roupeiro Porto",
            localizacao="Porto",
        ),
    ]

    resultado = filtrar_orcamentos(orcamentos, texto="cliente LISBOA")

    assert resultado == [orcamentos[0]]


def test_filtrar_orcamentos_separa_por_espaco_e_percentagem() -> None:
    orcamentos = [
        _orcamento(num_orcamento="260001", obra="Cozinha Lisboa"),
        _orcamento(num_orcamento="260002", obra="Cozinha Porto"),
    ]

    resultado = filtrar_orcamentos(orcamentos, texto="260001%lisboa")

    assert resultado == [orcamentos[0]]


def test_filtrar_orcamentos_casa_em_enc_phc_e_info_1() -> None:
    orcamentos = [
        _orcamento(enc_phc="PHC-999", info_1="Madeira especial"),
        _orcamento(enc_phc="PHC-100", info_1="Normal"),
    ]

    assert filtrar_orcamentos(orcamentos, texto="999 especial") == [orcamentos[0]]


def test_filtrar_orcamentos_filtra_por_estado_cliente_utilizador() -> None:
    orcamentos = [
        _orcamento(
            estado=ESTADO_INICIAL,
            cliente_nome="Cliente Alfa",
            utilizador="ana",
        ),
        _orcamento(
            estado="Enviado",
            cliente_nome="Cliente Alfa",
            utilizador="bruno",
        ),
        _orcamento(estado="Enviado", cliente_nome="Cliente Beta", utilizador="ana"),
    ]

    assert filtrar_orcamentos(orcamentos, estado="Enviado") == [
        orcamentos[1],
        orcamentos[2],
    ]
    assert filtrar_orcamentos(orcamentos, cliente="Cliente Alfa") == [
        orcamentos[0],
        orcamentos[1],
    ]
    assert filtrar_orcamentos(orcamentos, utilizador="ana") == [
        orcamentos[0],
        orcamentos[2],
    ]
    assert filtrar_orcamentos(
        orcamentos,
        estado="Enviado",
        cliente="Cliente Beta",
        utilizador="ana",
    ) == [orcamentos[2]]


def test_filtrar_orcamentos_todos_none_vazio_e_termos_vazios_nao_filtram() -> None:
    orcamentos = [
        _orcamento(num_orcamento="260001"),
        _orcamento(num_orcamento="260002"),
    ]

    assert filtrar_orcamentos(
        orcamentos,
        texto="  %% ",
        estado="Todos",
        cliente=None,
        utilizador="",
    ) == orcamentos


def test_filtrar_orcamentos_ignora_acentos_e_pontuacao() -> None:
    orcamentos = [
        _orcamento(obra="Instalação Eléctrica", cliente_nome="José"),
        _orcamento(obra="Cozinha", cliente_nome="Ana"),
    ]

    assert filtrar_orcamentos(orcamentos, texto="instalacao") == [orcamentos[0]]
    assert filtrar_orcamentos(orcamentos, texto="jose") == [orcamentos[0]]


def test_filtrar_orcamentos_encontra_plurais() -> None:
    orcamentos = [
        _orcamento(descricao="Roupeiro grande"),
        _orcamento(descricao="Cozinha pequena"),
    ]

    # «roupeiros» (plural escrito) encontra «Roupeiro» (singular na obra).
    assert filtrar_orcamentos(orcamentos, texto="roupeiros") == [orcamentos[0]]


def test_filtrar_orcamentos_usa_sinonimos_do_utilizador() -> None:
    orcamentos = [
        _orcamento(obra="Roupeiro Grande"),
        _orcamento(obra="Cozinha Lisboa"),
    ]
    sinonimos = {
        "armario": frozenset({"armario", "roupeiro"}),
        "roupeiro": frozenset({"armario", "roupeiro"}),
    }

    assert filtrar_orcamentos(
        orcamentos, texto="armario", sinonimos=sinonimos
    ) == [orcamentos[0]]


def test_filtrar_orcamentos_casa_em_ano_codigo_versao_e_preco() -> None:
    orcamentos = [
        _orcamento(ano=2026, codigo_versao="260001_02", preco_total=Decimal("1500")),
        _orcamento(ano=2025, codigo_versao="250009_01", preco_total=Decimal("30")),
    ]

    assert filtrar_orcamentos(orcamentos, texto="2026") == [orcamentos[0]]
    assert filtrar_orcamentos(orcamentos, texto="260001_02") == [orcamentos[0]]
    assert filtrar_orcamentos(orcamentos, texto="1500") == [orcamentos[0]]


def test_vocabulario_orcamentos_reune_raizes_para_quis_dizer() -> None:
    orcamentos = [_orcamento(obra="Roupeiro Grande", cliente_nome="José")]

    vocabulario = vocabulario_orcamentos(orcamentos)

    assert "roupeiro" in vocabulario
    assert "jose" in vocabulario


def _para_ordenar(**overrides) -> SimpleNamespace:
    base = {
        "ano": 2026,
        "num_orcamento": "260001",
        "numero_versao": 1,
        "cliente_nome": "Beta",
        "estado": ESTADO_INICIAL,
        "preco_total": Decimal("100"),
        "created_at": datetime(2026, 1, 1, 9, 0, 0),
        "orcamento_versao_id": 1,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_ordenar_sem_coluna_mantem_ordem_de_origem() -> None:
    orcamentos = [_para_ordenar(orcamento_versao_id=5), _para_ordenar(orcamento_versao_id=2)]

    assert ordenar_orcamentos(orcamentos) == orcamentos


def test_ordenar_por_preco_com_none_no_fim_ascendente() -> None:
    caro = _para_ordenar(preco_total=Decimal("900"))
    barato = _para_ordenar(preco_total=Decimal("10"))
    sem_preco = _para_ordenar(preco_total=None)

    ordenado = ordenar_orcamentos([caro, sem_preco, barato], "preco_total", True)

    assert ordenado == [sem_preco, barato, caro]


def test_ordenar_por_entrada_usa_data_e_depois_id() -> None:
    antigo = _para_ordenar(created_at=datetime(2026, 1, 1), orcamento_versao_id=7)
    mesmo_dia_a = _para_ordenar(created_at=datetime(2026, 5, 1), orcamento_versao_id=3)
    mesmo_dia_b = _para_ordenar(created_at=datetime(2026, 5, 1), orcamento_versao_id=9)

    ordenado = ordenar_orcamentos(
        [mesmo_dia_b, antigo, mesmo_dia_a], "entrada", True
    )

    assert ordenado == [antigo, mesmo_dia_a, mesmo_dia_b]


def test_ordenar_por_num_orcamento_e_numerico() -> None:
    n9 = _para_ordenar(num_orcamento="9")
    n10 = _para_ordenar(num_orcamento="10")

    assert ordenar_orcamentos([n10, n9], "num_orcamento", True) == [n9, n10]


def test_ordenar_descendente_e_estavel_nos_empates() -> None:
    primeiro = _para_ordenar(cliente_nome="Alfa", orcamento_versao_id=1)
    segundo = _para_ordenar(cliente_nome="Alfa", orcamento_versao_id=2)
    outro = _para_ordenar(cliente_nome="Beta", orcamento_versao_id=3)

    ordenado = ordenar_orcamentos([primeiro, segundo, outro], "cliente_nome", False)

    # Beta primeiro (desc); os dois "Alfa" mantêm a ordem de origem.
    assert ordenado == [outro, primeiro, segundo]
