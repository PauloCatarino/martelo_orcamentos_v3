"""Helpers for finishing (acabamento) area calculations on cost lines (phase 8M).

Only areas are computed here (no finishing cost yet). The piece ``area_m2`` is
unitary, so the total area is ``area_m2 * qt_total``. A face counts only when it
has a finish different from empty / ``SEM_ACABAMENTO``.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.medidas import normalizar_numero

SEM_ACABAMENTO = "SEM_ACABAMENTO"
AVISO_ACABAMENTO_DADOS_INCOMPLETOS = (
    "Área de acabamento não calculada: área ou quantidade em falta."
)


def tem_acabamento(valor) -> bool:
    """Return True when a finishing face is set (not empty / SEM_ACABAMENTO)."""
    if valor is None:
        return False

    texto = str(valor).strip()
    if not texto:
        return False

    return texto.upper() != SEM_ACABAMENTO


def calcular_areas_acabamento(
    area_m2,
    qt_total,
    acabamento_face_sup,
    acabamento_face_inf,
) -> tuple[Decimal | None, Decimal | None, str | None]:
    """Return (area_acab_sup, area_acab_inf, aviso) for one line.

    A face with a finish gets ``area_m2 * qt_total``; a face without a finish
    gets 0. With no finish on either face -> (None, None, None). A finish present
    but no area -> (None, None, aviso). Never raises.
    """
    tem_sup = tem_acabamento(acabamento_face_sup)
    tem_inf = tem_acabamento(acabamento_face_inf)
    if not tem_sup and not tem_inf:
        return None, None, None

    area = normalizar_numero(area_m2)
    if area is None:
        return None, None, AVISO_ACABAMENTO_DADOS_INCOMPLETOS

    qt = normalizar_numero(qt_total)
    if qt is None:
        qt = Decimal("1")
    area_total = area * qt

    area_sup = area_total if tem_sup else Decimal("0")
    area_inf = area_total if tem_inf else Decimal("0")
    return area_sup, area_inf, None
