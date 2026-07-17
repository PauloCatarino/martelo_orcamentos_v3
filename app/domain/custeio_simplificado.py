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

# The tier tariffs apply up to this thickness; above it the flat thick-board
# tariff (TarifaEspessuraGrossa) replaces cutting and edging per piece.
ESPESSURA_LIMITE_SIMPLIFICADO = Decimal("19")


def normalizar_modalidade_custeio(valor) -> str:
    texto = str(valor or "").strip().upper()
    return texto if texto in MODALIDADES_CUSTEIO else MODALIDADE_CUSTEIO_STANDARD


def normalizar_tipo_orlagem_simplificada(valor) -> str:
    texto = str(valor or "").strip().upper()
    return texto if texto in TIPOS_ORLAGEM_SIMPLIFICADA else ORLAGEM_SIMPLIFICADA_PUR


@dataclass(frozen=True)
class TarifaCusteioSimplificado:
    """Tariffs for one quantity tier; edge prices are for four sides.

    ``urgencia_item`` is charged ONCE per item (never multiplied by the piece
    quantity) — 2,30/1,85/1,70 on the first three tiers and 40,00 on >=25.
    """

    minimo_pecas: int
    corte_por_peca: Decimal
    pur_4_lados: Decimal
    laser_4_lados: Decimal
    urgencia_item: Decimal = Decimal("0")
    sem_excel_por_peca: Decimal = Decimal("0.10")


@dataclass(frozen=True)
class TarifaEspessuraGrossa:
    """Flat tariff for pieces thicker than 19 mm (no tiers, no PUR/LASER)."""

    corte_por_peca: Decimal = Decimal("2.85")
    orlagem_por_lado: Decimal = Decimal("1.15")


TARIFAS_SIMPLIFICADO_PADRAO = (
    TarifaCusteioSimplificado(1, Decimal("2.40"), Decimal("3.60"), Decimal("4.60"), Decimal("2.30")),
    TarifaCusteioSimplificado(5, Decimal("1.95"), Decimal("3.00"), Decimal("4.00"), Decimal("1.85")),
    TarifaCusteioSimplificado(15, Decimal("1.55"), Decimal("2.60"), Decimal("3.60"), Decimal("1.70")),
    TarifaCusteioSimplificado(25, Decimal("1.15"), Decimal("2.40"), Decimal("3.40"), Decimal("40.00")),
)

TARIFA_ESPESSURA_GROSSA_PADRAO = TarifaEspessuraGrossa()

ROTULOS_ESCALOES = {1: "1–4", 5: "5–14", 15: "15–24", 25: "≥25"}


def rotulo_escalao(tarifa: TarifaCusteioSimplificado) -> str:
    """Human label of a tier, e.g. ``5–14``."""
    return ROTULOS_ESCALOES.get(tarifa.minimo_pecas, str(tarifa.minimo_pecas))


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


def espessura_e_grossa(esp) -> bool:
    """True when the piece thickness is above the 19 mm tier limit."""
    espessura = normalizar_numero(esp)
    return espessura is not None and espessura > ESPESSURA_LIMITE_SIMPLIFICADO


def calcular_custo_simplificado_linha(
    quantidade,
    codigo_orlas,
    tipo_orlagem,
    tarifa: TarifaCusteioSimplificado,
    esp=None,
    tarifa_grossa: TarifaEspessuraGrossa = TARIFA_ESPESSURA_GROSSA_PADRAO,
) -> tuple[Decimal, Decimal]:
    """Return cutting and proportional edging costs for one piece cost line.

    Up to 19 mm the tier tariffs apply (PUR/LASER four-side prices); above
    19 mm the flat thick-board tariff replaces both (cut per piece and edging
    per edged side, ignoring PUR/LASER).
    """
    qt = normalizar_numero(quantidade) or Decimal("0")
    lados = contar_lados_orlados(codigo_orlas)
    if espessura_e_grossa(esp):
        corte = tarifa_grossa.corte_por_peca * qt
        orlagem = tarifa_grossa.orlagem_por_lado * lados * qt
        return corte, orlagem
    corte = tarifa.corte_por_peca * qt
    preco_4_lados = tarifa.laser_4_lados if normalizar_tipo_orlagem_simplificada(tipo_orlagem) == ORLAGEM_SIMPLIFICADA_LASER else tarifa.pur_4_lados
    orlagem = preco_4_lados / Decimal("4") * lados * qt
    return corte, orlagem


def calcular_opcoes_simplificado(quantidade_total, tarifa: TarifaCusteioSimplificado, *, urgente: bool, sem_excel: bool) -> tuple[Decimal, Decimal]:
    """Return the urgency and no-Excel surcharges for an item.

    Urgency is a FIXED amount per item (chosen by tier, never multiplied by
    the piece quantity); the no-Excel surcharge stays per piece.
    """
    qt = normalizar_numero(quantidade_total) or Decimal("0")
    urgencia = tarifa.urgencia_item if urgente else Decimal("0")
    return urgencia, tarifa.sem_excel_por_peca * qt if sem_excel else Decimal("0")
