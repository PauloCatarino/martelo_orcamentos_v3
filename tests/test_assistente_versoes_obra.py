"""Tests for asking the assistant about one specific version of an obra."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domain.assistente_obra import (
    DossierObra,
    VersaoObra,
    aviso_outras_versoes,
    extrair_versoes,
    identificar_pedido,
)
from app.services.assistente_producao_service import AssistenteProducaoService


def _processo(versao_obra: str, versao_plano: str, enc: str = "_111"):
    return SimpleNamespace(
        id=int(f"{versao_obra}{versao_plano}"),
        num_enc_phc=enc,
        ano="2026",
        versao_obra=versao_obra,
        versao_plano=versao_plano,
        codigo_processo=f"26.{enc}_{versao_obra}_{versao_plano}_TIAGO_LOPES",
    )


_TRES_VERSOES = [
    _processo("01", "01"),
    _processo("02", "01"),
    _processo("03", "01"),
]


# ---- ler a versão da pergunta -------------------------------------------
@pytest.mark.parametrize(
    ("pergunta", "obra", "plano"),
    [
        ("ponto situacao da enc phc _111_03_01", "03", "01"),
        ("ponto situacao da enc phc _111_03", "03", ""),
        ("estado da obra 111/03/01", "03", "01"),
        ("estado da obra 111-03-01", "03", "01"),
        ("estado da obra _111_3_1", "03", "01"),
    ],
)
def test_a_versao_e_lida_do_numero_completo(pergunta, obra, plano) -> None:
    pedido = identificar_pedido(pergunta)

    assert (pedido.versao_obra, pedido.versao_plano) == (obra, plano)


@pytest.mark.parametrize(
    "pergunta",
    [
        "mostra como esta ponto situacao da enc phc _111",
        "estado da obra 111",
        "estado da obra 111 03",  # números soltos não são uma versão
    ],
)
def test_sem_numero_completo_nao_ha_versao_pedida(pergunta) -> None:
    pedido = identificar_pedido(pergunta)

    assert (pedido.versao_obra, pedido.versao_plano) == ("", "")


def test_a_versao_e_lida_do_texto_em_bruto() -> None:
    """O normalizar transforma «_» em espaço; a versão tem de vir do original."""
    assert extrair_versoes("enc phc _111_03_01", "111") == ("03", "01")
    assert extrair_versoes("enc phc _111_03_01", "222") == ("", "")
    assert extrair_versoes("", "111") == ("", "")
    assert extrair_versoes("enc phc _111", "") == ("", "")


# ---- filtrar as obras ----------------------------------------------------
def test_sem_versao_devolve_as_tres() -> None:
    encontradas = AssistenteProducaoService._encontrar_obras(_TRES_VERSOES, "111")

    assert len(encontradas) == 3
    assert encontradas[-1].versao_obra == "03"  # a mais recente fica no fim


def test_com_versao_de_obra_devolve_so_essa() -> None:
    encontradas = AssistenteProducaoService._encontrar_obras(
        _TRES_VERSOES, "111", versao_obra="02"
    )

    assert [p.versao_obra for p in encontradas] == ["02"]


def test_a_versao_compara_se_por_numero_e_nao_por_texto() -> None:
    """«3», «03» e «_03» são a mesma versão."""
    encontradas = AssistenteProducaoService._encontrar_obras(
        _TRES_VERSOES, "111", versao_obra="3"
    )

    assert [p.versao_obra for p in encontradas] == ["03"]


def test_versao_do_plano_de_corte_tambem_filtra() -> None:
    processos = [_processo("01", "01"), _processo("01", "02")]

    encontradas = AssistenteProducaoService._encontrar_obras(
        processos, "111", versao_obra="01", versao_plano="02"
    )

    assert [p.versao_plano for p in encontradas] == ["02"]


def test_versao_que_nao_existe_nao_devolve_nada() -> None:
    assert (
        AssistenteProducaoService._encontrar_obras(
            _TRES_VERSOES, "111", versao_obra="09"
        )
        == []
    )


# ---- o aviso -------------------------------------------------------------
def _dossier(*pares, enc: str = "_111") -> DossierObra:
    return DossierObra(
        enc=enc,
        versoes=tuple(VersaoObra(versao_obra=o, versao_plano=p) for o, p in pares),
    )


def test_o_aviso_diz_quantas_versoes_ha_e_como_pedir_outra() -> None:
    aviso = aviso_outras_versoes(_dossier(("01", "01"), ("02", "01"), ("03", "01")))

    assert "3 versões" in aviso
    assert "_111_03_01" in aviso   # a que foi mostrada
    assert "_111_01_01" in aviso   # as outras
    assert "_111_02_01" in aviso


def test_o_underscore_do_numero_da_encomenda_e_mantido() -> None:
    """«_111» escreve-se com o underscore; é assim que a pessoa o escreve."""
    aviso = aviso_outras_versoes(_dossier(("01", "01"), ("02", "01")))

    assert "_111_01_01" in aviso
    assert "111_01_01." not in aviso.replace("_111_01_01", "")


def test_encomenda_sem_underscore_nao_ganha_um() -> None:
    aviso = aviso_outras_versoes(_dossier(("01", "01"), ("01", "02"), enc="1134"))

    assert "1134_01_01" in aviso
    assert "_1134" not in aviso


def test_uma_so_versao_nao_gera_aviso() -> None:
    assert aviso_outras_versoes(_dossier(("01", "01"))) == ""
    assert aviso_outras_versoes(_dossier()) == ""


def test_quem_ja_pediu_uma_versao_nao_leva_o_aviso() -> None:
    dossier = _dossier(("01", "01"), ("02", "01"))

    assert aviso_outras_versoes(dossier, pediu_versao=True) == ""
