"""Tests for the edge banding (orlas) helpers."""

from __future__ import annotations

from decimal import Decimal

from app.domain.orlas import (
    AVISO_ESPESSURA_ORLA,
    AVISO_UNIDADE_ORLA,
    MARGEM_ORLADORA_POR_LADO_MM,
    calcular_custo_orla,
    calcular_orlas_detalhe,
    calcular_orlas_linha,
    preco_ml_orla,
    selecionar_largura_orla_mm,
    somar_custo_orlas,
)


def test_margem_orladora_constante() -> None:
    assert MARGEM_ORLADORA_POR_LADO_MM == Decimal("100")


def test_codigo_0000_gera_zero() -> None:
    fina, grossa = calcular_orlas_linha(
        "0000", Decimal("2500"), Decimal("600"), Decimal("1")
    )
    assert fina == Decimal("0")
    assert grossa == Decimal("0")


def test_codigo_2222_grossa() -> None:
    # Each of the 4 banded sides adds a 100 mm edge-bander margin.
    fina, grossa = calcular_orlas_linha(
        "2222", Decimal("2500"), Decimal("600"), Decimal("1")
    )
    assert fina == Decimal("0")
    assert grossa == Decimal("6.6")


def test_codigo_1111_fina() -> None:
    fina, grossa = calcular_orlas_linha(
        "1111", Decimal("2500"), Decimal("600"), Decimal("1")
    )
    assert fina == Decimal("6.6")
    assert grossa == Decimal("0")


def test_codigo_2111_separa_grossa_e_fina() -> None:
    fina, grossa = calcular_orlas_linha(
        "2111", Decimal("800"), Decimal("600"), Decimal("18")
    )
    # grossa = (800+100) * 18 / 1000 ; fina = (900 + 700 + 700) * 18 / 1000
    assert grossa == Decimal("16.2")
    assert fina == Decimal("41.4")


def test_qt_total_multiplica() -> None:
    _, grossa_1 = calcular_orlas_linha(
        "2222", Decimal("1000"), Decimal("500"), Decimal("1")
    )
    _, grossa_10 = calcular_orlas_linha(
        "2222", Decimal("1000"), Decimal("500"), Decimal("10")
    )
    assert grossa_10 == grossa_1 * Decimal("10")


def test_qt_total_none_assume_um() -> None:
    # (1100 + 1100 + 600 + 600) / 1000 with qt assumed 1.
    _, grossa = calcular_orlas_linha("2222", Decimal("1000"), Decimal("500"), None)
    assert grossa == Decimal("3.4")


def test_medidas_incompletas_nao_rebenta() -> None:
    fina, grossa = calcular_orlas_linha("2222", None, Decimal("600"), Decimal("1"))
    assert fina is None
    assert grossa is None


def test_codigo_invalido_nao_rebenta() -> None:
    assert calcular_orlas_linha("abc", Decimal("2500"), Decimal("600"), Decimal("1")) == (
        Decimal("0"),
        Decimal("0"),
    )
    assert calcular_orlas_linha(None, Decimal("2500"), Decimal("600"), Decimal("1")) == (
        Decimal("0"),
        Decimal("0"),
    )
    assert calcular_orlas_linha("22", Decimal("2500"), Decimal("600"), Decimal("1")) == (
        Decimal("0"),
        Decimal("0"),
    )


def test_codigo_com_parenteses() -> None:
    _, grossa = calcular_orlas_linha(
        "[2222]", Decimal("2500"), Decimal("600"), Decimal("1")
    )
    assert grossa == Decimal("6.6")


def test_selecionar_largura_orla_mm() -> None:
    assert selecionar_largura_orla_mm(Decimal("8")) == Decimal("19")
    assert selecionar_largura_orla_mm(Decimal("10")) == Decimal("19")
    assert selecionar_largura_orla_mm(Decimal("12")) == Decimal("19")
    assert selecionar_largura_orla_mm(Decimal("16")) == Decimal("19")
    assert selecionar_largura_orla_mm(Decimal("19")) == Decimal("22")
    assert selecionar_largura_orla_mm(Decimal("20")) == Decimal("25")
    assert selecionar_largura_orla_mm(Decimal("25")) == Decimal("28")
    assert selecionar_largura_orla_mm(Decimal("30")) == Decimal("33")
    # Colado 19+19 -> esp_real 38 -> 38+3 = 41 -> próxima standard >= 41 = 43.
    assert selecionar_largura_orla_mm(Decimal("38")) == Decimal("43")
    assert selecionar_largura_orla_mm(Decimal("61")) == Decimal("71")
    assert selecionar_largura_orla_mm(None) is None


def test_preco_ml_orla_converte_m2() -> None:
    preco_ml, aviso = preco_ml_orla(Decimal("6.50"), "M2", Decimal("22"))
    assert preco_ml == Decimal("0.143")
    assert aviso is None


def test_preco_ml_orla_unidade_ml_usa_preco_direto() -> None:
    preco_ml, aviso = preco_ml_orla(Decimal("0.50"), "ML", Decimal("22"))
    assert preco_ml == Decimal("0.50")
    assert aviso is None


def test_preco_ml_orla_unidade_desconhecida_avisa() -> None:
    preco_ml, aviso = preco_ml_orla(Decimal("6.50"), "UND", Decimal("22"))
    assert preco_ml is None
    assert aviso == AVISO_UNIDADE_ORLA


def test_preco_ml_orla_sem_preco() -> None:
    preco_ml, aviso = preco_ml_orla(None, "M2", Decimal("22"))
    assert preco_ml is None
    assert aviso is None


def test_calcular_custo_orla() -> None:
    # ML * preco_ml (price already per linear metre).
    assert calcular_custo_orla(Decimal("41.4"), Decimal("0.143")) == Decimal("5.9202")
    assert calcular_custo_orla(Decimal("0"), None) == Decimal("0")
    assert calcular_custo_orla(Decimal("6.2"), None) is None
    assert calcular_custo_orla(None, Decimal("0.5")) is None


def test_somar_custo_orlas() -> None:
    assert somar_custo_orlas(Decimal("3.10"), Decimal("2")) == Decimal("5.10")
    assert somar_custo_orlas(Decimal("0"), Decimal("0")) == Decimal("0")
    assert somar_custo_orlas(None, Decimal("2")) is None


def test_detalhe_custo_completo_m2() -> None:
    # codigo 1111, comp=2500, larg=600, esp=19, qt=1 -> ml_fina=6.6, largura=22
    resultado = calcular_orlas_detalhe(
        "1111",
        Decimal("2500"),
        Decimal("600"),
        Decimal("19"),
        Decimal("1"),
        ref_fina="ORL0002",
        preco_fina=Decimal("6.50"),
        unidade_fina="M2",
    )
    assert resultado.ml_orla_fina == Decimal("6.6")
    assert resultado.ml_orla_grossa == Decimal("0")
    assert resultado.largura_orla_mm == Decimal("22")
    # preco_ml = 6.50 * 22/1000 = 0.143 ; custo = 6.6 * 0.143 = 0.9438
    assert resultado.custo_orla_fina == Decimal("0.9438")
    assert resultado.custo_orlas == Decimal("0.9438")
    assert resultado.aviso is None
    assert len(resultado.lados) == 4


def test_detalhe_unidade_desconhecida_preenche_aviso() -> None:
    resultado = calcular_orlas_detalhe(
        "2222",
        Decimal("2500"),
        Decimal("600"),
        Decimal("19"),
        Decimal("1"),
        ref_grossa="ORLX",
        preco_grossa=Decimal("6.50"),
        unidade_grossa="UND",
    )
    assert resultado.ml_orla_grossa == Decimal("6.6")
    assert resultado.custo_orla_grossa is None
    assert resultado.custo_orlas is None
    assert resultado.aviso == AVISO_UNIDADE_ORLA


def test_detalhe_0000_sem_custo() -> None:
    resultado = calcular_orlas_detalhe(
        "0000", Decimal("2500"), Decimal("600"), Decimal("19"), Decimal("1")
    )
    assert resultado.ml_orla_fina == Decimal("0")
    assert resultado.ml_orla_grossa == Decimal("0")
    assert resultado.custo_orlas == Decimal("0")
    assert resultado.aviso is None


def test_detalhe_dados_reais_2111() -> None:
    # codigo 2111, comp=2000, larg=1000, qt=1 -> ml_fina=4.300, ml_grossa=2.100.
    resultado = calcular_orlas_detalhe(
        "2111",
        Decimal("2000"),
        Decimal("1000"),
        Decimal("19"),
        Decimal("1"),
        ref_fina="ORL0002",
        preco_fina=Decimal("6.50"),
        unidade_fina="M2",
        ref_grossa="ORL0003",
        preco_grossa=Decimal("11.50"),
        unidade_grossa="M2",
    )
    assert resultado.ml_orla_fina == Decimal("4.3")
    assert resultado.ml_orla_grossa == Decimal("2.1")
    assert resultado.largura_orla_mm == Decimal("22")
    assert resultado.custo_orla_fina == Decimal("0.6149")
    assert resultado.custo_orla_grossa == Decimal("0.5313")
    assert resultado.custo_orlas == Decimal("1.1462")
    assert resultado.aviso is None


def test_detalhe_sem_espessura_avisa() -> None:
    # No thickness (esp_real None at the helper level) and an M2 orla -> warning.
    resultado = calcular_orlas_detalhe(
        "2111",
        Decimal("2000"),
        Decimal("1000"),
        None,
        Decimal("1"),
        ref_fina="ORL0002",
        preco_fina=Decimal("6.50"),
        unidade_fina="M2",
    )
    assert resultado.largura_orla_mm is None
    assert resultado.custo_orla_fina is None
    assert resultado.aviso == AVISO_ESPESSURA_ORLA
