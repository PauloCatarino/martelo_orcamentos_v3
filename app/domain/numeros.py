"""Helpers for parsing and normalizing human numbers and percentages."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def parse_decimal_humano(texto: str | None) -> Decimal | None:
    """Parse a human decimal string into a Decimal.

    Accepts comma or dot as the decimal separator and ignores spaces, the euro
    sign and the percent sign. Returns None for empty input and raises
    ValueError for invalid input.

    Examples: "8,62" -> 8.62, "0,1" -> 0.1, "10,5" -> 10.5.
    """
    if texto is None:
        return None

    normalized = (
        texto.strip()
        .replace(" ", "")
        .replace("€", "")
        .replace("%", "")
        .replace(",", ".")
    )
    if not normalized:
        return None

    try:
        return Decimal(normalized)
    except InvalidOperation as error:
        raise ValueError("numero invalido") from error


def formatar_percentagem(valor: Decimal | None) -> str:
    """Format a human percentage for display, dropping needless decimals.

    Examples: None -> "", 10 -> "10%", 10.0 -> "10%", 6.8 -> "6.8%",
    12.50 -> "12.5%".
    """
    if valor is None:
        return ""

    return f"{format(valor.normalize(), 'f')}%"


def normalize_percentagem_humana(value: Decimal | None) -> Decimal | None:
    """Normalize an imported percentage into a human percentage.

    Values strictly between -1 and 1 are treated as fractions and multiplied by
    100 (0.1 -> 10, 0.32 -> 32). Values with magnitude >= 1 are assumed to be
    already in human percentage and kept as-is (5 -> 5, 36 -> 36).
    """
    if value is None:
        return None

    if Decimal(-1) < value < Decimal(1):
        return value * Decimal(100)

    return value
