"""Tests for the pure parts of the PHC proposal-automation service.

The pywinauto execution can only run with the real PHC window open, so these
tests cover the deterministic keystroke *plan* and the designation helper.
"""

from __future__ import annotations

import pytest

from app.services.phc_automation_service import (
    TABS_CLIENTE_ATE_REF,
    TABS_REF_ATE_DESIGNACAO,
    TECLA_NOVA_PROPOSTA,
    PassoPausa,
    PassoTeclas,
    PassoTexto,
    _escape_literal,
    construir_designacao,
    construir_plano,
    descrever_plano,
    formatar_num_cliente_phc,
)


def test_formatar_num_cliente_phc_preenche_ate_3_digitos():
    assert formatar_num_cliente_phc("35") == "035"
    assert formatar_num_cliente_phc("7") == "007"
    assert formatar_num_cliente_phc("035") == "035"
    assert formatar_num_cliente_phc("1234") == "1234"


def test_formatar_num_cliente_phc_ignora_nao_numericos_e_vazios():
    assert formatar_num_cliente_phc("") == ""
    assert formatar_num_cliente_phc(None) == ""
    assert formatar_num_cliente_phc(" 35 ") == "035"
    assert formatar_num_cliente_phc("AB12") == "AB12"


def test_plano_escreve_num_cliente_com_3_digitos():
    plano = construir_plano(
        num_cliente_phc="35", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    textos = [p.texto for p in plano if isinstance(p, PassoTexto)]
    assert textos[0] == "035"


def test_construir_designacao_com_ref():
    assert construir_designacao("2510008") == "Obra: 2510008"


def test_construir_designacao_sem_ref():
    assert construir_designacao("") == "Obra:"
    assert construir_designacao(None) == "Obra:"
    assert construir_designacao("  ") == "Obra:"


def _textos(plano):
    return [p.texto for p in plano if isinstance(p, PassoTexto)]


def _teclas(plano):
    return [p.keys for p in plano if isinstance(p, PassoTeclas)]


def test_plano_comeca_com_nova_proposta():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    assert isinstance(plano[0], PassoTeclas)
    assert plano[0].keys == TECLA_NOVA_PROPOSTA


def test_plano_escreve_cliente_ref_e_designacao_por_ordem():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    assert _textos(plano) == ["035", "2510008", "Obra: 2510008"]


def test_plano_confirma_cliente_com_enter():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    assert "{ENTER}" in _teclas(plano)


def test_plano_usa_contagem_de_tabs_configurada():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    teclas = _teclas(plano)
    assert f"{{TAB {TABS_CLIENTE_ATE_REF}}}" in teclas
    assert f"{{TAB {TABS_REF_ATE_DESIGNACAO}}}" in teclas


def test_plano_sem_ref_nao_escreve_ref_mas_mantem_tabs():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="", designacao="Obra:"
    )
    assert _textos(plano) == ["035", "Obra:"]
    teclas = _teclas(plano)
    assert f"{{TAB {TABS_REF_ATE_DESIGNACAO}}}" in teclas


def test_plano_exige_numero_cliente():
    with pytest.raises(ValueError):
        construir_plano(num_cliente_phc="  ", ref_cliente="x", designacao="Obra:")


def test_plano_tem_pausa_apos_nova_proposta():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    # O passo logo a seguir ao ALT+N é uma pausa.
    assert isinstance(plano[1], PassoPausa)


def test_escape_literal_protege_caracteres_especiais():
    assert _escape_literal("a+b(c)") == "a{+}b{(}c{)}"
    assert _escape_literal("Obra: 2510008") == "Obra: 2510008"


def test_plano_pausa_depois_de_cada_escrita_e_tabs():
    """Cada escrita/TAB é seguida de pausa — o PHC precisa de acompanhar."""
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    for indice, passo in enumerate(plano[:-1]):
        if isinstance(passo, (PassoTexto, PassoTeclas)):
            seguinte = plano[indice + 1]
            assert isinstance(seguinte, PassoPausa), (
                f"passo {indice} ({passo}) não é seguido de pausa"
            )


def test_plano_pausa_antes_de_gravar_no_fim():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    assert isinstance(plano[-1], PassoPausa)


def test_gravar_usa_ctrl_g():
    from app.services.phc_automation_service import TECLA_GRAVAR

    assert TECLA_GRAVAR == "^g"


def test_descrever_plano_menciona_textos():
    plano = construir_plano(
        num_cliente_phc="035", ref_cliente="2510008", designacao="Obra: 2510008"
    )
    descricao = descrever_plano(plano)
    assert "035" in descricao
    assert "Obra: 2510008" in descricao
