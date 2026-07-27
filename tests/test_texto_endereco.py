"""Tests for cleaning a pasted Teams address."""

from __future__ import annotations

import pytest

from app.domain.texto_endereco import endereco_suspeito, limpar_endereco
from app.services.teams_service import link_chat_teams, normalizar_destinos


LIMPO = "desenhos2@lancaencanto.pt"


@pytest.mark.parametrize(
    "sujo",
    [
        "desenhos2 @lancaencanto.pt",   # espaço-duro
        "desenhos2@lancaencanto.pt​",   # zero-width space
        "‎desenhos2@lancaencanto.pt",   # marca de direção
        "desenhos2@lancaencanto.pt﻿",   # BOM
        " desenhos2@lancaencanto.pt ",       # espaços normais
        "desenhos2 @ lancaencanto.pt",       # espaços pelo meio
    ],
)
def test_o_endereco_sai_limpo_seja_qual_for_o_lixo(sujo: str) -> None:
    """A olho nu parecem todos iguais; o Teams é que desiste sem dizer porquê."""
    assert limpar_endereco(sujo) == LIMPO


def test_endereco_ja_limpo_fica_intacto() -> None:
    assert limpar_endereco(LIMPO) == LIMPO
    assert endereco_suspeito(LIMPO) is False


def test_sabe_dizer_quando_o_endereco_tem_lixo() -> None:
    assert endereco_suspeito("desenhos2 @lancaencanto.pt") is True
    assert endereco_suspeito("  desenhos2@lancaencanto.pt  ") is False


def test_endereco_vazio_nao_e_suspeito() -> None:
    assert endereco_suspeito("") is False
    assert endereco_suspeito(None) is False
    assert limpar_endereco(None) == ""


def test_o_link_do_teams_leva_o_endereco_ja_limpo() -> None:
    """Rede de segurança para os endereços gravados antes desta limpeza."""
    url = link_chat_teams("desenhos2@lancaencanto.pt​", "Ola")

    assert "%E2%80%8B" not in url  # o zero-width não vai codificado no URL
    assert f"users={LIMPO}" in url


def test_lista_de_enderecos_tambem_e_limpa() -> None:
    assert normalizar_destinos(["a@x.pt​", " b@x.pt"]) == ["a@x.pt", "b@x.pt"]
