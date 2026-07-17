"""Parsing of measure blocks copied from Excel (tab-separated clipboard text).

Used by the costing table to paste the Comp/Larg columns of a piece list
directly onto the piece lines, instead of typing them one by one.
"""

from __future__ import annotations

import re

# One clipboard cell must be a plain number: digits with an optional single
# decimal separator (dot or comma). Anything else (letters, symbols, formulas)
# invalidates the block so it can never corrupt the costing maths.
_CELULA_NUMERICA = re.compile(r"^\d{1,7}([.,]\d{1,4})?$")


def parse_bloco_medidas_excel(texto: str | None) -> list[tuple[str, ...]] | None:
    """Parse Excel clipboard text into rows of numeric cells.

    Returns a list of row tuples with the numbers normalised to a dot decimal
    separator, or ``None`` when the text is not a purely numeric block (the
    caller then keeps the normal paste behaviour). Empty cells inside a row are
    kept as ``""`` (that column is skipped on that row); fully empty trailing
    rows are dropped.
    """
    if not texto or not texto.strip():
        return None
    linhas = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while linhas and not linhas[-1].strip():
        linhas.pop()
    resultado: list[tuple[str, ...]] = []
    for linha in linhas:
        celulas = []
        for celula in linha.split("\t"):
            valor = celula.strip()
            if valor and not _CELULA_NUMERICA.match(valor):
                return None
            celulas.append(valor.replace(",", "."))
        resultado.append(tuple(celulas))
    return resultado if resultado else None
