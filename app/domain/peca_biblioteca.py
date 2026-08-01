"""Text of a piece as it appears in the costing library list.

The library leaf is built from things the user configures in different places
(library name / name, edge-banding code and whether it is a composite), so this
is the single place that assembles them. The Definições de Peças page shows
exactly the same text, to spare the user from guessing the final result.
"""

from __future__ import annotations

from app.domain.orla_types import format_orla_code
from app.domain.peca_types import COMPOSTA


def texto_biblioteca_peca(peca) -> str:
    """Return the library text of one piece: "Nome [orlas] (composta)".

    A piece that does not work with edging (hardware, bought profiles) shows no
    edging code: a "[0000]" there says nothing and only clutters the list.
    """
    partes = [getattr(peca, "nome_biblioteca", None) or peca.nome]
    if getattr(peca, "usa_orlas", True):
        partes.append(
            format_orla_code(peca.orla_c1, peca.orla_c2, peca.orla_l1, peca.orla_l2)
        )
    if peca.tipo_peca == COMPOSTA:
        partes.append("(composta)")

    return " ".join(partes)
