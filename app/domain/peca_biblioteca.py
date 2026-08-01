"""Text of a piece as it appears in the costing library list.

The library leaf is built from three things the user configures in different
places (library name / name, edge-banding code and whether it is a composite),
so this is the single place that assembles them. The Definições de Peças page
shows exactly the same text, to spare the user from guessing the final result.
"""

from __future__ import annotations

from app.domain.peca_types import COMPOSTA


def texto_biblioteca_peca(peca, codigo_orlas: str) -> str:
    """Return the library text of one piece: "Nome [orlas] (composta)"."""
    nome = getattr(peca, "nome_biblioteca", None) or peca.nome
    texto = f"{nome} [{codigo_orlas}]"
    if peca.tipo_peca == COMPOSTA:
        texto += " (composta)"

    return texto
