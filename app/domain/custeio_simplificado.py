"""Rules and default tariffs for the per-item simplified costing mode."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.medidas import normalizar_numero

MODALIDADE_CUSTEIO_STANDARD = "STANDARD"
MODALIDADE_CUSTEIO_SIMPLIFICADO = "SIMPLIFICADO"
MODALIDADES_CUSTEIO = (MODALIDADE_CUSTEIO_STANDARD, MODALIDADE_CUSTEIO_SIMPLIFICADO)
ORLAGEM_SIMPLIFICADA_PUR = "PUR"
ORLAGEM_SIMPLIFICADA_LASER = "LASER"
TIPOS_ORLAGEM_SIMPLIFICADA = (ORLAGEM_SIMPLIFICADA_PUR, ORLAGEM_SIMPLIFICADA_LASER)


def normalizar_modalidade_custeio(valor) -> str:
    texto = str(valor or "").strip().upper()
    return texto if texto in MODALIDADES_CUSTEIO else MODALIDADE_CUSTEIO_STANDARD


def normalizar_tipo_orlagem_simplificada(valor) -> str:
    texto = str(valor or "").strip().upper()
    return texto if texto in TIPOS_ORLAGEM_SIMPLIFICADA else ORLAGEM_SIMPLIFICADA_PUR


@dataclass(frozen=True)
class TarifaCusteioSimplificado:
    """Tariffs for one quantity tier; edge prices are for four sides."""

    minimo_pecas: int
    corte_por_peca: Decimal
    pur_4_lados: Decimal
    laser_4_lados: Decimal
    urgencia_por_peca: Decimal | None = None
    urgencia_fixa: Decimal | None = None
    sem_excel_por_peca: Decimal = Decimal("0.10")


TARIFAS_SIMPLIFICADO_PADRAO = (
    TarifaCusteioSimplificado(1, Decimal("2.40"), Decimal("3.60"), Decimal("4.60"), Decimal("2.30")),
    TarifaCusteioSimplificado(5, Decimal("1.95"), Decimal("3.00"), Decimal("4.00"), Decimal("1.85")),
    TarifaCusteioSimplificado(15, Decimal("1.55"), Decimal("2.60"), Decimal("3.60"), Decimal("1.70")),
    TarifaCusteioSimplificado(25, Decimal("1.15"), Decimal("2.40"), Decimal("3.40"), urgencia_fixa=Decimal("40.00")),
)


def escolher_escalao_simplificado(quantidade_total, tarifas=TARIFAS_SIMPLIFICADO_PADRAO) -> TarifaCusteioSimplificado:
    """Return the most favourable applicable tier; exactly 25 uses ``>=25``."""
    quantidade = normalizar_numero(quantidade_total) or Decimal("0")
    ordenadas = sorted(tarifas, key=lambda tarifa: tarifa.minimo_pecas)
    escolhida = ordenadas[0]
    for tarifa in ordenadas:
        if quantidade >= tarifa.minimo_pecas:
            escolhida = tarifa
    return escolhida


def contar_lados_orlados(codigo_orlas) -> int:
    """Count non-zero digits in a four-side code such as ``2000`` or ``2222``."""
    return sum(1 for digito in str(codigo_orlas or "")[:4] if digito in {"1", "2"})


def calcular_custo_simplificado_linha(quantidade, codigo_orlas, tipo_orlagem, tarifa: TarifaCusteioSimplificado) -> tuple[Decimal, Decimal]:
    """Return cutting and proportional edging costs for one piece cost line."""
    qt = normalizar_numero(quantidade) or Decimal("0")
    corte = tarifa.corte_por_peca * qt
    preco_4_lados = tarifa.laser_4_lados if normalizar_tipo_orlagem_simplificada(tipo_orlagem) == ORLAGEM_SIMPLIFICADA_LASER else tarifa.pur_4_lados
    orlagem = preco_4_lados / Decimal("4") * contar_lados_orlados(codigo_orlas) * qt
    return corte, orlagem


def calcular_opcoes_simplificado(quantidade_total, tarifa: TarifaCusteioSimplificado, *, urgente: bool, sem_excel: bool) -> tuple[Decimal, Decimal]:
    """Return the urgency and no-Excel surcharges for an item."""
    qt = normalizar_numero(quantidade_total) or Decimal("0")
    urgencia = (tarifa.urgencia_fixa or (tarifa.urgencia_por_peca or Decimal("0")) * qt) if urgente else Decimal("0")
    return urgencia, tarifa.sem_excel_por_peca * qt if sem_excel else Decimal("0")
