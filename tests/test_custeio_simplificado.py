from decimal import Decimal

from app.domain.custeio_simplificado import (
    ORLAGEM_SIMPLIFICADA_LASER,
    ORLAGEM_SIMPLIFICADA_PUR,
    calcular_custo_simplificado_linha,
    calcular_opcoes_simplificado,
    escolher_escalao_simplificado,
)


def test_escaloes_incluem_25_no_preco_mais_favoravel():
    assert escolher_escalao_simplificado(4).corte_por_peca == Decimal("2.40")
    assert escolher_escalao_simplificado(5).corte_por_peca == Decimal("1.95")
    assert escolher_escalao_simplificado(15).corte_por_peca == Decimal("1.55")
    assert escolher_escalao_simplificado(24).corte_por_peca == Decimal("1.55")
    assert escolher_escalao_simplificado(25).corte_por_peca == Decimal("1.15")


def test_orlagem_e_proporcional_aos_lados_reais():
    tarifa = escolher_escalao_simplificado(1)
    assert calcular_custo_simplificado_linha(2, "2222", ORLAGEM_SIMPLIFICADA_PUR, tarifa) == (Decimal("4.80"), Decimal("7.20"))
    assert calcular_custo_simplificado_linha(2, "2000", ORLAGEM_SIMPLIFICADA_PUR, tarifa) == (Decimal("4.80"), Decimal("1.80"))
    assert calcular_custo_simplificado_linha(1, "1100", ORLAGEM_SIMPLIFICADA_LASER, tarifa) == (Decimal("2.40"), Decimal("2.30"))


def test_urgencia_e_sem_excel_sao_aplicados_no_fim_do_item():
    tarifa = escolher_escalao_simplificado(25)
    assert calcular_opcoes_simplificado(25, tarifa, urgente=True, sem_excel=True) == (Decimal("40.00"), Decimal("2.50"))
    tarifa = escolher_escalao_simplificado(14)
    assert calcular_opcoes_simplificado(14, tarifa, urgente=True, sem_excel=False) == (Decimal("25.90"), Decimal("0"))
