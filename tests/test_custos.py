"""Tests for the raw-material cost helpers (phase 8I)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.custos import (
    AVISO_FERRAGEM_DADOS_INCOMPLETOS,
    AVISO_FERRAGEM_UNIDADE_INVALIDA,
    AVISO_ML_DADOS_INCOMPLETOS,
    AVISO_MP_DADOS_INCOMPLETOS,
    AVISO_MP_UNIDADE_INVALIDA,
    AVISO_MP_UNIDADE_ML,
    AVISO_MP_UNIDADE_UND,
    calcular_custo_ferragem,
    calcular_custo_ml,
    calcular_custo_mp,
    desperdicio_para_fracao,
    fator_desperdicio,
)


def test_desperdicio_para_fracao_normaliza() -> None:
    assert desperdicio_para_fracao(None) == Decimal("0")
    assert desperdicio_para_fracao(Decimal("0.10")) == Decimal("0.10")
    assert desperdicio_para_fracao(Decimal("10")) == Decimal("0.10")
    assert desperdicio_para_fracao(Decimal("100")) == Decimal("1.00")


def test_fator_desperdicio_aceita_fracao_e_humano() -> None:
    assert fator_desperdicio(Decimal("0.20")) == Decimal("1.2")
    assert fator_desperdicio(Decimal("20")) == Decimal("1.2")
    assert fator_desperdicio(Decimal("0.10")) == Decimal("1.1")
    assert fator_desperdicio(Decimal("10")) == Decimal("1.1")
    assert fator_desperdicio(None) == Decimal("1")


def test_custo_mp_m2_com_desperdicio() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("6"), Decimal("10"), Decimal("0.20"), "M2"
    )
    assert custo == Decimal("36")
    assert aviso is None


def test_custo_mp_m2_sem_desperdicio() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("6"), Decimal("10"), None, "M2"
    )
    assert custo == Decimal("30")
    assert aviso is None


def test_custo_mp_qt_zero() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("0"), Decimal("10"), Decimal("0.20"), "M2"
    )
    assert custo == Decimal("0")
    assert aviso is None


def test_custo_mp_area_vazia() -> None:
    custo, aviso = calcular_custo_mp(None, Decimal("6"), Decimal("10"), None, "M2")
    assert custo is None
    assert aviso == AVISO_MP_DADOS_INCOMPLETOS


def test_custo_mp_preco_vazio() -> None:
    custo, aviso = calcular_custo_mp(Decimal("0.5"), Decimal("6"), None, None, "M2")
    assert custo is None
    assert aviso == AVISO_MP_DADOS_INCOMPLETOS


def test_custo_mp_unidade_ml() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("6"), Decimal("10"), None, "ML"
    )
    assert custo is None
    assert aviso == AVISO_MP_UNIDADE_ML


def test_custo_mp_unidade_und() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("6"), Decimal("10"), None, "UND"
    )
    assert custo is None
    assert aviso == AVISO_MP_UNIDADE_UND


def test_custo_mp_unidade_vazia() -> None:
    custo, aviso = calcular_custo_mp(
        Decimal("0.5"), Decimal("6"), Decimal("10"), None, ""
    )
    assert custo is None
    assert aviso == AVISO_MP_UNIDADE_INVALIDA


def test_custo_mp_unidade_m2_variacoes() -> None:
    for unidade in ("M2", "m2", "M²", "m²"):
        custo, aviso = calcular_custo_mp(
            Decimal("0.5"), Decimal("6"), Decimal("10"), None, unidade
        )
        assert custo == Decimal("30"), unidade
        assert aviso is None, unidade


def test_custo_ferragem_und_sem_desperdicio() -> None:
    custo, aviso = calcular_custo_ferragem(Decimal("5"), Decimal("2.53"), None, "UND")
    assert custo == Decimal("12.65")
    assert aviso is None


def test_custo_ferragem_und_desperdicio_fracao() -> None:
    custo, aviso = calcular_custo_ferragem(
        Decimal("5"), Decimal("2.53"), Decimal("0.02"), "UND"
    )
    assert custo == Decimal("12.903")
    assert aviso is None


def test_custo_ferragem_und_desperdicio_humano() -> None:
    custo, aviso = calcular_custo_ferragem(
        Decimal("5"), Decimal("2.53"), Decimal("2"), "UND"
    )
    assert custo == Decimal("12.903")
    assert aviso is None


def test_custo_ferragem_und_desperdicio_5() -> None:
    for desp in (Decimal("0.05"), Decimal("5")):
        custo, aviso = calcular_custo_ferragem(
            Decimal("10"), Decimal("1.50"), desp, "UND"
        )
        assert custo == Decimal("15.75"), desp
        assert aviso is None


def test_custo_ferragem_qt_vazia() -> None:
    custo, aviso = calcular_custo_ferragem(None, Decimal("2.53"), None, "UND")
    assert custo is None
    assert aviso == AVISO_FERRAGEM_DADOS_INCOMPLETOS


def test_custo_ferragem_preco_vazio() -> None:
    custo, aviso = calcular_custo_ferragem(Decimal("5"), None, None, "UND")
    assert custo is None
    assert aviso == AVISO_FERRAGEM_DADOS_INCOMPLETOS


def test_custo_ferragem_unidade_m2_nao_calcula() -> None:
    # M2 is handled by Custo MP -> no hardware cost and no warning.
    custo, aviso = calcular_custo_ferragem(Decimal("5"), Decimal("2.53"), None, "M2")
    assert custo is None
    assert aviso is None


def test_custo_ferragem_unidade_ml_deferido() -> None:
    # ML is now handled by calcular_custo_ml -> no cost and no warning here.
    custo, aviso = calcular_custo_ferragem(Decimal("5"), Decimal("2.53"), None, "ML")
    assert custo is None
    assert aviso is None


def test_custo_ferragem_unidade_desconhecida() -> None:
    custo, aviso = calcular_custo_ferragem(Decimal("5"), Decimal("2.53"), None, "")
    assert custo is None
    assert aviso == AVISO_FERRAGEM_UNIDADE_INVALIDA


def test_custo_ferragem_und_variacoes() -> None:
    for unidade in ("UND", "und", "un", "UN"):
        custo, aviso = calcular_custo_ferragem(
            Decimal("5"), Decimal("2.53"), None, unidade
        )
        assert custo == Decimal("12.65"), unidade
        assert aviso is None, unidade


def test_custo_ml_com_comp_real() -> None:
    eh_ml, cmu, total, custo, aviso = calcular_custo_ml(
        "ML", None, Decimal("800"), None, Decimal("2"), Decimal("1.32"), Decimal("10")
    )
    assert eh_ml is True
    assert cmu == Decimal("0.8")
    assert total == Decimal("1.6")
    assert custo == Decimal("2.3232")
    assert aviso is None


def test_custo_ml_fallback_larg_real() -> None:
    eh_ml, cmu, total, custo, aviso = calcular_custo_ml(
        "ML", None, None, Decimal("900"), Decimal("3"), Decimal("4.50"), Decimal("5")
    )
    assert cmu == Decimal("0.9")
    assert total == Decimal("2.7")
    assert custo == Decimal("12.7575")
    assert aviso is None


def test_custo_ml_consumo_manual() -> None:
    eh_ml, cmu, total, custo, aviso = calcular_custo_ml(
        "ML", Decimal("1.250"), None, None, Decimal("4"), Decimal("2.00"), None
    )
    assert cmu == Decimal("1.250")
    assert total == Decimal("5.000")
    assert custo == Decimal("10.00")
    assert aviso is None


def test_custo_ml_desperdicio_fracao_e_humano() -> None:
    _, _, _, custo_fracao, _ = calcular_custo_ml(
        "ML", None, Decimal("800"), None, Decimal("2"), Decimal("1.32"), Decimal("0.10")
    )
    _, _, _, custo_humano, _ = calcular_custo_ml(
        "ML", None, Decimal("800"), None, Decimal("2"), Decimal("1.32"), Decimal("10")
    )
    assert custo_fracao == Decimal("2.3232")
    assert custo_humano == Decimal("2.3232")


def test_custo_ml_sem_consumo_nem_medidas() -> None:
    eh_ml, cmu, total, custo, aviso = calcular_custo_ml(
        "ML", None, None, None, Decimal("2"), Decimal("1.32"), None
    )
    assert eh_ml is True
    assert custo is None
    assert aviso == AVISO_ML_DADOS_INCOMPLETOS


def test_custo_ml_nao_ml_e_ignorado() -> None:
    for unidade in ("M2", "UND", "", "ABC"):
        eh_ml, cmu, total, custo, aviso = calcular_custo_ml(
            unidade, None, Decimal("800"), None, Decimal("2"), Decimal("1.32"), None
        )
        assert eh_ml is False, unidade
        assert custo is None and aviso is None, unidade
