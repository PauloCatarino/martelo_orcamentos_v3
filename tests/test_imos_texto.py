"""Caracteres que o iMos não aceita no texto livre da encomenda."""

from __future__ import annotations

from app.domain.imos_texto import limpar_texto_imos


def test_plica_passa_a_aspas() -> None:
    """O caso que o Paulo apanhou: PUXADOR 'J' H1030."""
    limpo = limpar_texto_imos("4 ROUPEIROS PUXADOR 'J' H1030")

    assert limpo.valor == '4 ROUPEIROS PUXADOR "J" H1030'
    assert limpo.substituidos == ("'",)
    assert limpo.suspeitos == ()
    assert "trocado" in limpo.aviso


def test_aspas_e_tracos_colados_do_word() -> None:
    limpo = limpar_texto_imos("PORTAS “ABRIR” – 2 GAVETAS …")

    assert limpo.valor == 'PORTAS "ABRIR" - 2 GAVETAS ...'
    assert set(limpo.substituidos) == {"“", "”", "–", "…"}


def test_texto_normal_nao_e_tocado() -> None:
    texto = "AGL_MLM_LINHO_CANCUN_10/16/19MM MDF_HID_BRANCO (B3002/MA_19MM) 50% + 2"

    limpo = limpar_texto_imos(texto)

    assert limpo.valor == texto
    assert limpo.mudou is False
    assert limpo.aviso == ""


def test_acentos_e_cedilha_nao_sao_suspeitos() -> None:
    """Português normal não pode encher o diálogo de avisos."""
    limpo = limpar_texto_imos("ARMÁRIO COM LACAGEM À COR, DIVISÓRIAS E PÉS")

    assert limpo.suspeitos == ()
    assert limpo.mudou is False


def test_caracteres_invulgares_sao_assinalados_mas_nao_apagados() -> None:
    """Não sabemos a lista do iMos: avisa-se, não se estraga o texto."""
    limpo = limpar_texto_imos("PORTAS <ABRIR> {2} ~ 90º")

    assert limpo.valor == "PORTAS <ABRIR> {2} ~ 90º"
    assert set(limpo.suspeitos) == {"<", ">", "{", "}", "~"}
    assert "invulgares" in limpo.aviso


def test_espaco_nao_separavel_do_excel_vira_espaco_normal() -> None:
    limpo = limpar_texto_imos("2 GAVETAS")

    assert limpo.valor == "2 GAVETAS"
    assert limpo.suspeitos == ()


def test_caracter_invisivel_aparece_com_nome_no_aviso() -> None:
    limpo = limpar_texto_imos("PORTAS​ABRIR")

    assert limpo.suspeitos and limpo.suspeitos[0].startswith("[")
    assert "WIDTH" in limpo.suspeitos[0]


def test_vazio_e_none_nao_rebentam() -> None:
    assert limpar_texto_imos(None).valor == ""
    assert limpar_texto_imos("").aviso == ""
