"""Date normalization helpers."""

from __future__ import annotations

import re
from datetime import date, datetime


_DATE_RE = re.compile(r"^(\d{1,4})[-/](\d{1,2})[-/](\d{1,4})$")


def normalizar_data(valor: str | None) -> str:
    """Return a date as ``dd-mm-aaaa`` or an empty string when invalid."""
    if valor is None:
        return ""

    if isinstance(valor, datetime):
        return valor.strftime("%d-%m-%Y")

    if isinstance(valor, date):
        return valor.strftime("%d-%m-%Y")

    texto = str(valor).strip()
    if not texto:
        return ""

    match = _DATE_RE.match(texto)
    if match is None:
        return ""

    parte_1, parte_2, parte_3 = match.groups()
    if len(parte_1) == 4:
        ano, mes, dia = parte_1, parte_2, parte_3
    elif len(parte_3) == 4:
        dia, mes, ano = parte_1, parte_2, parte_3
    else:
        return ""

    try:
        data = date(int(ano), int(mes), int(dia))
    except ValueError:
        return ""

    return data.strftime("%d-%m-%Y")
