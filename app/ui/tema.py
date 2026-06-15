"""Lança Encanto brown/beige theme for the costing table (phase 8V.4).

Presentation only: colours, bold/italic/uppercase and the per-line-type style.
``estilo_linha_custeio`` is a pure function (no Qt) so it can be unit-tested;
the page maps the returned :class:`EstiloLinha` onto QTableWidget items.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    PECA_COMPOSTA,
    SEPARADOR,
)

# --- Palette (Lança Encanto) -------------------------------------------------
CASTANHO_ESCURO = "#5A3E2B"   # text / strong accent
CASTANHO_MEDIO = "#8B6F4E"    # medium brown
BEGE_AREIA = "#EFE7DA"        # sand beige (highlight background)
BEGE_CLARO = "#F7F2EA"        # light beige (alternated rows)
CINZA_CASTANHO = "#D9CFC2"    # brown-grey (separator / secondary)
TEXTO_NORMAL = "#2E2A26"      # normal text

# Role colours derived from the palette.
DIVISAO_FUNDO = CASTANHO_MEDIO       # division block header background
DIVISAO_TEXTO = "#FFFFFF"            # light text for contrast on the division
SEPARADOR_FUNDO = CINZA_CASTANHO     # discreet separator background
ZEBRA_BASE = "#FFFFFF"               # normal rows (even)
ZEBRA_ALT = BEGE_CLARO               # normal rows (odd)

# Composite header: the beige highlight is applied ONLY to the structural
# columns; the remaining columns of that row keep the normal/zebra background.
COLUNAS_REALCE_COMPOSTA = (
    "Tipo linha",
    "Código",
    "Descrição livre",
    "Def. Peça",
    "Descrição",
    "Linha pai",
    "Nível",
    "QT mod",
    "QT und",
)


@dataclass(frozen=True)
class EstiloLinha:
    """Visual style of one costing row (mapped to Qt by the page)."""

    fundo: str | None = None          # row background; None -> use the zebra colour
    texto: str | None = None          # text colour
    negrito: bool = False
    italico: bool = False
    maiusculas: bool = False
    realce_estrutural: bool = False   # composite header: beige on structural cols


def cor_zebra(indice_linha: int) -> str:
    """Return the alternating (zebra) background of a normal row by index."""
    return ZEBRA_ALT if indice_linha % 2 else ZEBRA_BASE


def estilo_linha_custeio(tipo_linha, *, eh_filho: bool = False) -> EstiloLinha:
    """Return the style for a costing line, by type (and composite-child flag).

    - DIVISÃO: full brown background, white bold UPPERCASE text (block header);
    - PEÇA COMPOSTA: bold dark-brown text, beige highlight on structural columns;
    - SEPARADOR: discreet brown-grey background, no text;
    - composite CHILD (linha_pai set): italic, medium-brown text (zebra bg);
    - NORMAL line: normal text on the zebra background.
    """
    if tipo_linha == DIVISAO_INDEPENDENTE:
        return EstiloLinha(
            fundo=DIVISAO_FUNDO,
            texto=DIVISAO_TEXTO,
            negrito=True,
            maiusculas=True,
        )
    if tipo_linha == PECA_COMPOSTA:
        return EstiloLinha(
            texto=CASTANHO_ESCURO,
            negrito=True,
            realce_estrutural=True,
        )
    if tipo_linha == SEPARADOR:
        return EstiloLinha(fundo=SEPARADOR_FUNDO)
    if eh_filho:
        return EstiloLinha(texto=CASTANHO_MEDIO, italico=True)
    return EstiloLinha(texto=TEXTO_NORMAL)
