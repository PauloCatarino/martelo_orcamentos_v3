"""Código da coluna «Colar» (PROCESSO_ESPECIAL) da Lista Material, em ensaio."""

from __future__ import annotations

import pytest

from app.domain import codigo_colar as cc


@pytest.mark.parametrize("texto", [
    "CNC_20+21x2+22x2_OC2+OL2_CNC",
    "CNC_20+21x2+22x2_O4L",
    "14+14_O4L_CNC",
    "14+16_OC2+OR",
    "14+16",
])
def test_exemplos_do_guia_leem_se_e_voltam_iguais(texto):
    assert cc.montar(cc.ler(texto)) == texto


def test_partes_do_codigo():
    codigo = cc.ler("CNC_20+21x2+22x2_OC2+OL2_CNC")
    assert codigo.pecas == ((20, 1), (21, 2), (22, 2))
    assert codigo.total_pecas == 5
    assert codigo.orlas == ("OC2", "OL2")
    assert codigo.cnc_inicio and codigo.cnc_fim


def test_duas_pecas_do_mesmo_id_escrevem_se_14_mais_14():
    assert cc.montar(cc.CodigoColar(((14, 2),))) == "14+14"
    assert cc.montar(cc.CodigoColar(((14, 1), (14, 1)))) == "14+14"
    assert cc.montar(cc.CodigoColar(((14, 3),))) == "14x3"
    assert cc.ler("14x2").pecas == ((14, 2),)
    assert cc.ler("14+14").pecas == ((14, 2),)


def test_orlas_a_partir_do_menu():
    assert cc.orlas_depois(2, 2) == ("O4L",)
    assert cc.orlas_depois(2, 2, raio=True) == ("O4L", "OR")
    assert cc.orlas_depois(2, 0) == ("OC2",)
    assert cc.orlas_depois(1, 1) == ("OC1", "OL1")
    assert cc.orlas_depois(0, 2, raio=True) == ("OL2", "OR")
    assert cc.orlas_depois(0, 0) == ()


def test_sem_pecas_nao_ha_codigo():
    assert cc.montar(cc.CodigoColar(())) == ""


@pytest.mark.parametrize("texto, motivo", [
    ("", "vazio"),
    ("14 + 14", "espaços"),
    ("14", "pelo menos 2 peças"),
    ("CNC", "falta o conjunto"),
    ("14+A", "não é um ID"),
    ("14+14_OX", "não é uma orla"),
    ("14+14_O4L+OC2", "O4L já são os 4 lados"),
    ("14+14_OC1+OC2", "só um OC"),
    ("14+14_OR+OR", "repetida"),
    ("14+14__O4L", "bloco vazio"),
    ("CNC_14+14_O4L_OR_CNC", "blocos a mais"),
])
def test_codigos_errados_dizem_porque(texto, motivo):
    with pytest.raises(ValueError, match=motivo):
        cc.ler(texto)


def test_listagem_certa_nao_tem_problemas():
    linhas = [(1, ""), (20, "CNC_20+21x2_O4L"), (21, "CNC_20+21x2_O4L"), (22, "")]
    assert cc.problemas_na_listagem(linhas) == []


def test_listagem_com_numeracao_mudada_e_conjunto_desencontrado():
    # Depois de inserir uma linha, os IDs andam um para a frente e o código fica para trás.
    linhas = [(20, ""), (21, "20+21_O4L"), (22, "20+21_O4L"), (23, "14+99")]
    problemas = cc.problemas_na_listagem(linhas)
    assert any("ID 22: o código «20+21_O4L» não inclui o ID 22" in p for p in problemas)
    assert any("a linha ID 20 tem outro código (vazio)" in p for p in problemas)
    assert any("o ID 99 não existe" in p for p in problemas)
    assert any("ID 23" in p and "não inclui o ID 23" in p for p in problemas)


def test_listagem_com_codigo_mal_escrito():
    problemas = cc.problemas_na_listagem([(5, "5 + 6"), (6, "5 + 6")])
    assert problemas[0].startswith("ID 5: o código «5 + 6» tem espaços")


def test_ids_com_casas_decimais_do_excel():
    assert cc.problemas_na_listagem([(14.0, "14+14"), ("x", "")]) == []
