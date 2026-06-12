"""Tests for the price-building domain helpers (phase 8T.0)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.domain.precos import (
    BlocosCusto,
    MargensOrcamento,
    blocos_custo_da_linha,
    calcular_preco_total,
    calcular_preco_unitario,
    fator_margem,
    margem_lucro_efetiva_pct,
    somar_blocos_custo,
)

_CENTIMOS = Decimal("0.01")

# Validation example from the phase spec: mp 15%, mo 5%, acab 5%, admin 3%,
# lucro 10% over blocks 100/50/30 -> 225.47 EUR per unit.
_MARGENS_EXEMPLO = MargensOrcamento(
    margem_lucro_pct=Decimal("10"),
    margem_mp_pct=Decimal("15"),
    margem_mao_obra_pct=Decimal("5"),
    margem_acabamentos_pct=Decimal("5"),
    custos_administrativos_pct=Decimal("3"),
)
_BLOCOS_EXEMPLO = BlocosCusto(
    bloco_mp=Decimal("100"),
    bloco_producao=Decimal("50"),
    bloco_acabamento=Decimal("30"),
)


def _eur(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTIMOS, rounding=ROUND_HALF_UP)


def test_exemplo_de_validacao_da_fase() -> None:
    preco_unitario = calcular_preco_unitario(_BLOCOS_EXEMPLO, _MARGENS_EXEMPLO)

    assert _eur(preco_unitario) == Decimal("225.47")
    assert _BLOCOS_EXEMPLO.custo_produzido == Decimal("180")

    margem = margem_lucro_efetiva_pct(preco_unitario, _BLOCOS_EXEMPLO.custo_produzido)
    assert margem is not None
    assert margem.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) == Decimal("25.3")

    preco_total = calcular_preco_total(preco_unitario, Decimal("2"))
    assert _eur(preco_total) == Decimal("450.93")


def test_margens_a_zero_preco_igual_ao_custo() -> None:
    preco = calcular_preco_unitario(_BLOCOS_EXEMPLO, MargensOrcamento())

    assert preco == _BLOCOS_EXEMPLO.custo_produzido


def test_ajuste_negativo_e_somado_depois_das_margens() -> None:
    preco_sem_ajuste = calcular_preco_unitario(_BLOCOS_EXEMPLO, _MARGENS_EXEMPLO)
    preco_com_ajuste = calcular_preco_unitario(
        _BLOCOS_EXEMPLO, _MARGENS_EXEMPLO, ajuste_eur=Decimal("-10")
    )

    assert preco_com_ajuste == preco_sem_ajuste - Decimal("10")


def test_blocos_custo_da_linha_respeita_exclusoes() -> None:
    blocos = blocos_custo_da_linha(
        custo_mp=Decimal("100"),
        custo_orlas=Decimal("20"),
        custo_ferragem=Decimal("5"),
        custo_acabamento=Decimal("30"),
        custo_producao=Decimal("50"),
        excluir_producao=True,
        excluir_orla=True,
    )

    assert blocos.bloco_mp == Decimal("105")  # orlas excluded
    assert blocos.bloco_producao == Decimal("0")  # producao excluded
    assert blocos.bloco_acabamento == Decimal("30")


def test_blocos_custo_da_linha_trata_custos_em_falta_como_zero() -> None:
    blocos = blocos_custo_da_linha(custo_mp=None, custo_producao=None)

    assert blocos.bloco_mp == Decimal("0")
    assert blocos.bloco_producao == Decimal("0")
    assert blocos.custo_produzido == Decimal("0")


def test_blocos_custo_da_linha_expoe_parcelas_para_tooltips() -> None:
    blocos = blocos_custo_da_linha(
        custo_mp=Decimal("22.10"),
        custo_orlas=Decimal("4.15"),
        custo_ferragem=Decimal("2.56"),
        custo_producao=Decimal("143.18"),
        custo_corte=Decimal("61.20"),
        custo_orlagem=Decimal("45.80"),
        custo_cnc=Decimal("24.00"),
        custo_montagem_manual=Decimal("12.18"),
    )

    assert blocos.parcela_mp == Decimal("22.10")
    assert blocos.parcela_orlas == Decimal("4.15")
    assert blocos.parcela_ferragem == Decimal("2.56")
    assert blocos.bloco_mp == Decimal("28.81")
    assert blocos.parcela_corte == Decimal("61.20")
    assert blocos.parcela_orlagem == Decimal("45.80")
    assert blocos.parcela_cnc == Decimal("24.00")
    assert blocos.parcela_montagem_manual == Decimal("12.18")
    # The production parcels add up to the production block.
    assert (
        blocos.parcela_corte
        + blocos.parcela_orlagem
        + blocos.parcela_cnc
        + blocos.parcela_montagem_manual
        == blocos.bloco_producao
    )


def test_parcelas_de_producao_escaladas_pelo_fator_serie() -> None:
    # custo_producao stored on the line already carries the fator série; the
    # parcels are scaled by the same factor so they add up to the block.
    blocos = blocos_custo_da_linha(
        custo_producao=Decimal("45"),  # (40 + 10) x 0.9
        custo_corte=Decimal("40"),
        custo_orlagem=Decimal("10"),
        fator_serie=Decimal("0.9"),
    )

    assert blocos.parcela_corte == Decimal("36.0")
    assert blocos.parcela_orlagem == Decimal("9.0")
    assert blocos.parcela_corte + blocos.parcela_orlagem == blocos.bloco_producao


def test_parcelas_respeitam_excluir_producao() -> None:
    blocos = blocos_custo_da_linha(
        custo_producao=Decimal("50"),
        custo_corte=Decimal("40"),
        custo_orlagem=Decimal("10"),
        excluir_producao=True,
    )

    assert blocos.bloco_producao == Decimal("0")
    assert blocos.parcela_corte == Decimal("0")
    assert blocos.parcela_orlagem == Decimal("0")


def test_somar_blocos_custo() -> None:
    total = somar_blocos_custo(
        [
            BlocosCusto(Decimal("10"), Decimal("1"), Decimal("0.5")),
            BlocosCusto(Decimal("2"), Decimal("3"), Decimal("4")),
        ]
    )

    assert total == BlocosCusto(Decimal("12"), Decimal("4"), Decimal("4.5"))


def test_fator_margem_sem_heuristica_de_fracao() -> None:
    assert fator_margem(Decimal("15")) == Decimal("1.15")
    assert fator_margem(Decimal("0.5")) == Decimal("1.005")  # 0.5% (NOT 50%)
    assert fator_margem(None) == Decimal("1")


def test_margem_efetiva_none_sem_custo_produzido() -> None:
    assert margem_lucro_efetiva_pct(Decimal("100"), Decimal("0")) is None
    assert margem_lucro_efetiva_pct(None, Decimal("180")) is None
    assert margem_lucro_efetiva_pct(Decimal("100"), None) is None


def test_calcular_preco_total_sem_preco() -> None:
    assert calcular_preco_total(None, Decimal("2")) is None
    assert calcular_preco_total(Decimal("10"), None) == Decimal("10")
