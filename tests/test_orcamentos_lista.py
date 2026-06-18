"""Tests for pure budget-list helpers."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.domain.orcamento_estados import ESTADO_INICIAL
from app.domain.orcamentos_lista import filtrar_orcamentos, resumo_lista


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
