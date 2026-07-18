"""Tests for the CNC calculation-method constants and helpers."""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.metodo_calculo_types import (
    ESCALAO_AREA,
    FURACAO,
    METODO_CALCULO_LABELS,
    RASGO,
    REVESTIMENTO,
    TEMPO,
    get_metodo_calculo_label,
    get_metodo_calculo_options,
    inferir_metodo_calculo_legado,
    metodos_disponiveis_para_maquina,
    normalize_metodo_calculo,
)


def _maquina(tipo="CNC", escaloes=True, furacao=True, rasgos=True):
    return SimpleNamespace(
        tipo=tipo,
        permite_escaloes_area=escaloes,
        permite_furacao=furacao,
        permite_rasgos=rasgos,
    )


def test_normalize_conhecidos_e_desconhecidos() -> None:
    assert normalize_metodo_calculo(" tempo ") == TEMPO
    assert normalize_metodo_calculo("FURACAO") == FURACAO
    assert normalize_metodo_calculo(None) is None
    assert normalize_metodo_calculo("") is None
    assert normalize_metodo_calculo("XPTO") is None


def test_labels_e_opcoes() -> None:
    assert get_metodo_calculo_label(RASGO) == METODO_CALCULO_LABELS[RASGO]
    assert get_metodo_calculo_label(None) == ""
    codes = [code for code, _label in get_metodo_calculo_options()]
    assert codes == [ESCALAO_AREA, TEMPO, FURACAO, RASGO, REVESTIMENTO]


def test_metodos_maquina_cnc_completa() -> None:
    assert metodos_disponiveis_para_maquina(_maquina()) == (
        ESCALAO_AREA,
        TEMPO,
        FURACAO,
        RASGO,
    )


def test_metodos_maquina_abd_sem_rasgo() -> None:
    # ABD: only drilling besides tiers/time — no groove.
    assert metodos_disponiveis_para_maquina(_maquina(rasgos=False)) == (
        ESCALAO_AREA,
        TEMPO,
        FURACAO,
    )


def test_metodos_maquina_revestimento() -> None:
    assert metodos_disponiveis_para_maquina(_maquina(tipo="REVESTIMENTO")) == (
        REVESTIMENTO,
    )


def test_metodos_maquina_nao_cnc_vazio() -> None:
    assert metodos_disponiveis_para_maquina(_maquina(tipo="CORTE")) == ()
    assert metodos_disponiveis_para_maquina(None) == ()


def test_inferir_legado_rasgo_por_codigo_regra_ou_geometria() -> None:
    assert inferir_metodo_calculo_legado("CNC_RASGO", None, 0, 0, False) == RASGO
    assert inferir_metodo_calculo_legado("X", "RASGO_CNC", 0, 0, True) == RASGO
    assert inferir_metodo_calculo_legado("X", None, 1, 0, True) == RASGO
    assert inferir_metodo_calculo_legado("X", None, 0, 2, False) == RASGO


def test_inferir_legado_furacao_tempo_e_default() -> None:
    assert inferir_metodo_calculo_legado("X", "POR_FURACAO", 0, 0, True) == FURACAO
    assert inferir_metodo_calculo_legado("X", "FIXA", 0, 0, True) == TEMPO
    assert inferir_metodo_calculo_legado("X", None, None, None, False) == ESCALAO_AREA
