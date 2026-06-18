"""Tests for customer list filters."""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.clientes_lista import filtrar_clientes


def _cliente(**overrides) -> SimpleNamespace:
    base = {
        "nome": "Cliente Alfa",
        "nome_simplex": "ALFA",
        "morada": "Rua Norte",
        "email": "alfa@example.test",
        "pagina_web": "https://alfa.test",
        "telefone": "210000000",
        "telemovel": "910000000",
        "num_cliente_phc": "PHC-001",
        "info_1": "Entrega urgente",
        "info_2": "Sem observacoes",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_filtrar_clientes_multi_termo_case_insensitive() -> None:
    clientes = [
        _cliente(nome="Cliente Alfa", morada="Lisboa"),
        _cliente(nome="Cliente Beta", morada="Porto"),
    ]

    assert filtrar_clientes(clientes, texto="cliente LISBOA") == [clientes[0]]


def test_filtrar_clientes_separa_por_espaco_e_percentagem() -> None:
    clientes = [
        _cliente(nome="Cliente Alfa", pagina_web="https://alfa.test"),
        _cliente(
            nome="Cliente Beta",
            nome_simplex="BETA",
            email="beta@example.test",
            pagina_web="https://beta.test",
        ),
    ]

    assert filtrar_clientes(clientes, texto="cliente%alfa") == [clientes[0]]


def test_filtrar_clientes_casa_em_info_e_num_phc() -> None:
    clientes = [
        _cliente(num_cliente_phc="PHC-999", info_1="Madeira especial"),
        _cliente(num_cliente_phc="PHC-100", info_1="Normal"),
    ]

    assert filtrar_clientes(clientes, texto="999 especial") == [clientes[0]]


def test_filtrar_clientes_texto_vazio_devolve_todos() -> None:
    clientes = [_cliente(nome="A"), _cliente(nome="B")]

    assert filtrar_clientes(clientes, texto="  %% ") == clientes
    assert filtrar_clientes(clientes, texto=None) == clientes
