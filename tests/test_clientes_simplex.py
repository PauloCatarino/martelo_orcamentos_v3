"""Regras do nome abreviado do cliente (o "simplex")."""

from __future__ import annotations

from app.domain.clientes_simplex import (
    MAX_SIMPLEX,
    normalizar_simplex,
    simplex_demasiado_longo,
    validar_simplex,
)


def test_limite_vem_do_nome_da_encomenda_imos() -> None:
    # NNNN_VV_AA_<simplex> = 11 caracteres + simplex, e o iMos aceita 30.
    assert MAX_SIMPLEX == 19


def test_normalizar_poe_maiusculas_e_underscores() -> None:
    assert normalizar_simplex(" jf viva ") == "JF_VIVA"
    assert normalizar_simplex("ALEXANDRE PEREIRA ") == "ALEXANDRE_PEREIRA"


def test_normalizar_nao_inventa_a_partir_do_vazio() -> None:
    assert normalizar_simplex(None) is None
    assert normalizar_simplex("   ") is None
    assert normalizar_simplex("_-_") is None


def test_simplex_demasiado_longo() -> None:
    assert simplex_demasiado_longo("LINHAS_DIREITAS") is False
    assert simplex_demasiado_longo("A" * 19) is False
    assert simplex_demasiado_longo("A" * 20) is True


def test_validar_aceita_nome_curto() -> None:
    assert validar_simplex("WERNAGEN") is None
    assert validar_simplex("LINHAS_DIREITAS") is None


def test_validar_avisa_quando_vazio_e_diz_onde_corrigir() -> None:
    erro = validar_simplex("", nome_cliente="WERNAGEN - IMOBILIARIA LDA")
    assert erro is not None
    assert "WERNAGEN - IMOBILIARIA LDA" in erro
    assert "PHC" in erro

    erro_streamlit = validar_simplex(None, origem="Streamlit")
    assert erro_streamlit is not None and "Streamlit" in erro_streamlit


def test_validar_avisa_quando_passa_dos_19() -> None:
    erro = validar_simplex("WERNAGEN__IMOBILIARIA_LDA")
    assert erro is not None
    assert "25" in erro  # quantos tem
    assert "19" in erro  # quantos podia ter
