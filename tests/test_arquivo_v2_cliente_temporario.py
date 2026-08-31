"""Arquivo V2: o cliente temporário é o cliente, e não "CONSUMIDOR FINAL".

O V2 não tem coluna para clientes temporários. Quando o orçamento é para um
cliente que ainda não está no PHC, o ``client_id`` fica a apontar para o registo
genérico "CONSUMIDOR FINAL" (id 97 na base real) e o cliente verdadeiro vai para
o ``extras``, em JSON.

O Arquivo V2 do V3 lia só o ``client_id``, e por isso mostrava "CONSUMIDOR
FINAL" em 104 orçamentos — TODOS os que apareciam assim. Nenhum deles era mesmo
consumidor final. Apanhado pelo Paulo a comparar o V3 com o V2, 2026-08-31.
"""

from __future__ import annotations

import inspect

import pytest

from app.services.v2_arquivo_service import (
    V2ArquivoService,
    cliente_temporario_do_extras,
    escolher_nome_do_cliente,
)

#: Tal e qual como está na base do V2, no orçamento 260863.
EXTRAS_REAL = (
    '{"preco_manual": true, "temp_client_id": 20, '
    '"temp_client_nome": "DSTCARPINTARIA"}'
)


# ----- Ler o extras -----


def test_le_o_cliente_temporario_do_extras_a_serio() -> None:
    assert cliente_temporario_do_extras(EXTRAS_REAL) == (20, "DSTCARPINTARIA")


def test_aceita_o_extras_ja_em_dicionario() -> None:
    assert cliente_temporario_do_extras(
        {"temp_client_id": 84, "temp_client_nome": "FRANCISCO_CARRILHO"}
    ) == (84, "FRANCISCO_CARRILHO")


def test_aceita_o_extras_em_bytes() -> None:
    assert cliente_temporario_do_extras(EXTRAS_REAL.encode("utf-8")) == (
        20,
        "DSTCARPINTARIA",
    )


@pytest.mark.parametrize(
    "extras",
    [
        None,
        "",
        "isto nao e json",
        "[]",
        "null",
        '{"preco_manual": true}',      # extras sem cliente temporário nenhum
        '{"temp_client_id": "abc"}',   # id estragado
    ],
)
def test_extras_sem_cliente_temporario_nao_rebenta(extras) -> None:
    temp_id, nome = cliente_temporario_do_extras(extras)
    assert nome == ""
    assert temp_id is None or isinstance(temp_id, int)


def test_id_que_vem_como_texto_conta_na_mesma() -> None:
    assert cliente_temporario_do_extras('{"temp_client_id": "20"}')[0] == 20


# ----- Escolher o nome a mostrar -----


def test_o_temporario_ganha_ao_consumidor_final() -> None:
    nome, temporario = escolher_nome_do_cliente(
        nome_phc="CONSUMIDOR FINAL",
        temp_id=88,
        temp_nome="HELICA",
        temporarios={88: "HELICA GROUND SOLUTIONS LDA"},
    )

    # O nome por extenso da tabela, como acontece com os clientes do PHC.
    assert nome == "HELICA GROUND SOLUTIONS LDA"
    assert temporario is True


def test_sem_a_tabela_vale_o_nome_gravado_no_orcamento() -> None:
    """Salvaguarda: o cliente temporário pode ter sido apagado da tabela."""
    nome, temporario = escolher_nome_do_cliente(
        nome_phc="CONSUMIDOR FINAL",
        temp_id=999,
        temp_nome="DSTCARPINTARIA",
        temporarios={},
    )

    assert nome == "DSTCARPINTARIA"
    assert temporario is True


def test_cliente_do_phc_fica_como_esta() -> None:
    nome, temporario = escolher_nome_do_cliente(
        nome_phc="INNERE RUI VIEGAS - SISTEMAS DE DIVISÓRIAS, LDA",
        temp_id=None,
        temp_nome="",
        temporarios={20: "DSTCARPINTARIA"},
    )

    assert nome == "INNERE RUI VIEGAS - SISTEMAS DE DIVISÓRIAS, LDA"
    assert temporario is False


def test_sem_cliente_nenhum_nao_inventa() -> None:
    assert escolher_nome_do_cliente(
        nome_phc="", temp_id=None, temp_nome="", temporarios=None
    ) == ("", False)


# ----- Os casos verdadeiros do print do Paulo -----


@pytest.mark.parametrize(
    ("temp_id", "temp_nome", "esperado"),
    [
        (20, "DSTCARPINTARIA", "DSTCARPINTARIA"),
        (24, "DIOGO_CARVALHO", "DIOGO CARVALHO"),
        (84, "FRANCISCO_CARRILHO", "FRANCISCO CARRILHO"),
        (85, "NEXTPAL", "NEXTPAL"),
        (87, "DLF_CONSULTING", "DLF CONSULTING"),
        (88, "HELICA", "HELICA GROUND SOLUTIONS LDA"),
        (89, "DIAMETRO", "DIAMETRO"),
    ],
)
def test_os_orcamentos_do_print(temp_id: int, temp_nome: str, esperado: str) -> None:
    tabela = {
        20: "DSTCARPINTARIA",
        24: "DIOGO CARVALHO",
        84: "FRANCISCO CARRILHO",
        85: "NEXTPAL",
        87: "DLF CONSULTING",
        88: "HELICA GROUND SOLUTIONS LDA",
        89: "DIAMETRO",
    }

    nome, temporario = escolher_nome_do_cliente(
        nome_phc="CONSUMIDOR FINAL",
        temp_id=temp_id,
        temp_nome=temp_nome,
        temporarios=tabela,
    )

    assert nome == esperado
    assert temporario is True
    assert "CONSUMIDOR" not in nome


# ----- Ligação ao resto -----


def test_o_adaptador_usa_mesmo_o_cliente_temporario() -> None:
    fonte = inspect.getsource(V2ArquivoService._adaptar)
    assert "cliente_temporario_do_extras" in fonte
    assert "escolher_nome_do_cliente" in fonte


def test_a_tabela_dos_temporarios_e_lida_uma_vez_so() -> None:
    """Uma consulta por listagem, não uma por linha."""
    fonte = inspect.getsource(V2ArquivoService._clientes_temporarios)
    assert "clientes_temporarios" in fonte
    # Sem acesso à tabela, cai-se no nome gravado no orçamento em vez de rebentar.
    assert "return {}" in fonte


def test_a_pagina_avisa_que_o_cliente_e_temporario() -> None:
    from app.ui.pages.arquivo_v2_page import ArquivoV2Page

    fonte = inspect.getsource(ArquivoV2Page._render)
    assert "cliente_temporario" in fonte
    assert "TEMPOR" in fonte.upper()
