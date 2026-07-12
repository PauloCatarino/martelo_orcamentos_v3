"""Behavior tests for the guided operation costing explanation (phase G1)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.operacao_guia import (
    CAMPO_QUANTIDADE_BASE,
    CAMPO_TEMPO_POR_UNIDADE,
    CAMPO_TEMPO_SETUP,
    CAMPO_UNIDADE_TEMPO,
    MODO_RASGO,
    MODO_SEM_CUSTEIO,
    MODO_TARIFA,
    MODO_TEMPO,
    construir_guia_operacao,
)


def _guia(**overrides):
    """Build a guide with neutral defaults, overridden per test."""
    params = {
        "tipo_operacao": None,
        "codigo": None,
        "regra_calculo": None,
        "unidade_tempo": None,
    }
    params.update(overrides)
    return construir_guia_operacao(**params)


# --- Panel tariff operations ---------------------------------------------------


def test_corte_em_peca_de_painel_usa_tarifa() -> None:
    guia = _guia(tipo_operacao="CORTE", codigo="CORTE_SECCIONADORA", natureza_peca="MATERIAL")

    assert guia.modo == MODO_TARIFA
    assert "corte" in guia.titulo
    assert any("perímetro" in linha for linha in guia.linhas)
    # Time fields stay editable (they feed the informative production times).
    assert guia.campos_inativos == {}
    assert any("NÃO alteram este custo" in linha for linha in guia.linhas)
    # Known panel context -> no dual hardware note.
    assert not any("FERRAGEM" in linha for linha in guia.linhas)


def test_orlagem_explica_lados_orlados() -> None:
    guia = _guia(tipo_operacao="ORLAGEM", codigo="ORLA_1", natureza_peca="MATERIAL")

    assert guia.modo == MODO_TARIFA
    assert any("dígito 1 ou 2" in linha for linha in guia.linhas)


def test_cnc_sem_contexto_mostra_nota_dupla() -> None:
    guia = _guia(tipo_operacao="CNC", codigo="CNC_STD")

    assert guia.modo == MODO_TARIFA
    assert any("escalão de área" in linha for linha in guia.linhas)
    # Unknown context (generic ValueSet line) -> explain the hardware case too.
    assert any("FERRAGEM" in linha for linha in guia.linhas)


def test_cnc_em_ferragem_conta_por_tempo() -> None:
    guia = _guia(
        tipo_operacao="CNC",
        codigo="CNC_FURACAO_FERRAGEM",
        unidade_tempo="FURO",
        quantidade_base=Decimal("5"),
        tempo_setup_minutos=Decimal("2"),
        tempo_por_unidade_minutos=Decimal("0.04"),
        custo_hora=Decimal("45"),
        natureza_peca="FERRAGEM",
    )

    assert guia.modo == MODO_TEMPO
    assert any("FERRAGEM" in linha for linha in guia.linhas)


# --- Time-based operations ------------------------------------------------------


def test_tempo_por_furo_tem_exemplo_numerico_do_motor() -> None:
    guia = _guia(
        tipo_operacao="MANUAL",
        codigo="FERRAGEM_APLICAR",
        unidade_tempo="FURO",
        quantidade_base=Decimal("5"),
        tempo_setup_minutos=Decimal("2"),
        tempo_por_unidade_minutos=Decimal("0.04"),
        custo_hora=Decimal("45"),
    )

    assert guia.modo == MODO_TEMPO
    # setup 2 + 5 furos × QT 10 × 0,04 = 2 -> total 4 min -> 4/60 × 45 = 3,00 €
    exemplo = next(linha for linha in guia.linhas if linha.startswith("Ex."))
    assert "QT 10" in exemplo
    assert "= 4 min" in exemplo
    assert "3,00 €" in exemplo


def test_tempo_sem_tempos_configurados_avisa() -> None:
    guia = _guia(tipo_operacao="MONTAGEM", codigo="MONTAGEM_STD", unidade_tempo="PECA")

    assert guia.modo == MODO_TEMPO
    assert any("ignorada sem aviso" in linha for linha in guia.linhas)


def test_unidade_m2_desativa_quantidade_base() -> None:
    guia = _guia(
        tipo_operacao="MANUAL",
        codigo="LIXAR",
        unidade_tempo="M2",
        tempo_por_unidade_minutos=Decimal("0.2"),
    )

    assert CAMPO_QUANTIDADE_BASE in guia.campos_inativos
    assert "área" in guia.campos_inativos[CAMPO_QUANTIDADE_BASE]
    assert CAMPO_TEMPO_POR_UNIDADE not in guia.campos_inativos


def test_unidade_hora_desativa_tempo_por_unidade() -> None:
    guia = _guia(
        tipo_operacao="MANUAL",
        codigo="ACABAMENTO",
        unidade_tempo="HORA",
        quantidade_base=Decimal("1.5"),
    )

    assert CAMPO_TEMPO_POR_UNIDADE in guia.campos_inativos
    assert CAMPO_QUANTIDADE_BASE not in guia.campos_inativos


def test_unidade_lote_nao_multiplica_pela_qt() -> None:
    guia = _guia(tipo_operacao="EMBALAMENTO", codigo="EMBALAR", unidade_tempo="LOTE")

    assert any("NÃO multiplica pela QT" in linha for linha in guia.linhas)


def test_setup_em_painel_tem_nota_de_tempos_informativos() -> None:
    guia = _guia(
        tipo_operacao="SETUP",
        codigo="SETUP_LINHA",
        unidade_tempo="OPERACAO",
        tempo_setup_minutos=Decimal("5"),
        natureza_peca="MATERIAL",
    )

    assert guia.modo == MODO_TEMPO
    assert any("tempos informativos" in linha for linha in guia.linhas)


# --- CNC groove (rasgo) ---------------------------------------------------------


def test_rasgo_por_codigo_desativa_campos_de_tempo() -> None:
    guia = _guia(
        tipo_operacao="CNC",
        codigo="CNC_RASGO",
        rasgo_qt_comp=1,
        rasgo_qt_larg=0,
        preco_rasgo_ml=Decimal("2"),
    )

    assert guia.modo == MODO_RASGO
    assert set(guia.campos_inativos) == {
        CAMPO_QUANTIDADE_BASE,
        CAMPO_TEMPO_SETUP,
        CAMPO_TEMPO_POR_UNIDADE,
        CAMPO_UNIDADE_TEMPO,
    }
    # 1 × 600 mm = 0,6 ML -> × QT 10 × 2 €/ML = 12,00 €
    exemplo = next(linha for linha in guia.linhas if linha.startswith("Ex."))
    assert "0,6 ML" in exemplo
    assert "12,00 €" in exemplo


def test_rasgo_por_regra_calculo_tambem_e_detetado() -> None:
    guia = _guia(tipo_operacao="CNC", codigo="CNC_STD", regra_calculo="RASGO_CNC")

    assert guia.modo == MODO_RASGO


def test_rasgo_sem_construcao_pede_comprimentos() -> None:
    guia = _guia(tipo_operacao="CNC", codigo="CNC_RASGO")

    assert any("pelo menos um comprimento" in linha for linha in guia.linhas)


def test_rasgo_sem_tarifa_avisa_maquina() -> None:
    guia = _guia(tipo_operacao="CNC", codigo="CNC_RASGO", rasgo_qt_comp=2)

    exemplo = next(linha for linha in guia.linhas if linha.startswith("Ex."))
    assert "sem €/ML de rasgo" in exemplo


# --- Operations outside the automatic costing -----------------------------------


def test_tipo_desconhecido_fica_fora_do_custeio() -> None:
    guia = _guia(tipo_operacao="OUTRO", codigo="XPTO")

    assert guia.modo == MODO_SEM_CUSTEIO
    assert any("não entra no custeio" in linha for linha in guia.linhas)
