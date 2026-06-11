"""Production type (STD/SERIE) constants and rules (phase 8S.4).

The budget version sets the default production type for all its items
(``tipo_producao_default``); each item may override it with its own
``tipo_producao`` (NULL = inherit the version default).
"""

from __future__ import annotations

TIPO_PRODUCAO_STD = "STD"
TIPO_PRODUCAO_SERIE = "SERIE"

TIPOS_PRODUCAO = (TIPO_PRODUCAO_STD, TIPO_PRODUCAO_SERIE)


def normalize_tipo_producao(valor) -> str | None:
    """Return "STD"/"SERIE" for a recognized value, or None otherwise."""
    if valor is None:
        return None

    texto = str(valor).strip().upper()
    if texto in TIPOS_PRODUCAO:
        return texto

    return None


def tipo_producao_efetivo(tipo_item, tipo_default) -> str:
    """Resolve the effective production type of an item.

    The item's own type (exception) wins; otherwise the version default;
    unknown/missing values fall back to STD.
    """
    efetivo = normalize_tipo_producao(tipo_item)
    if efetivo is not None:
        return efetivo

    return normalize_tipo_producao(tipo_default) or TIPO_PRODUCAO_STD
