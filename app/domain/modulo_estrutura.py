"""Resolve which costing lines to save as a reusable module (phase 8U.1).

Only the TOP-LEVEL lines (nivel 0) are saved: independent divisions, simple
pieces, composite pieces (by their header, with def_peca_id) and standalone
hardware/operations. A selected composite CHILD (nivel > 0) is represented by
its composite header (we climb linha_pai_id to the top); children are never
saved individually — they re-expand from the def_peca on import. Pure.
"""

from __future__ import annotations

from collections.abc import Sequence


def _linha_de_topo(linha, por_id: dict):
    """Climb linha_pai_id to the top-level ancestor (nivel 0) of a line."""
    atual = linha
    visto: set[int] = set()
    while atual.linha_pai_id is not None and atual.id not in visto:
        visto.add(atual.id)
        pai = por_id.get(atual.linha_pai_id)
        if pai is None:
            break
        atual = pai

    return atual


def selecionar_linhas_topo(linhas: Sequence, linha_ids) -> list:
    """Return the ordered, de-duplicated TOP-LEVEL lines for the selection.

    ``linhas`` are the item's cost-line resumos (any order); ``linha_ids`` the
    selected ids. Composite children map to their header; nivel-0 lines stay as
    they are. The result is ordered by each line's own ordem (then id), so the
    saved module keeps the table order and its independent divisions. Pure.
    """
    por_id = {linha.id: linha for linha in linhas}
    selecionados = set(linha_ids)

    topo_ids: set[int] = set()
    for linha in linhas:
        if linha.id in selecionados:
            topo = _linha_de_topo(linha, por_id)
            if topo is not None:
                topo_ids.add(topo.id)

    topo = [por_id[topo_id] for topo_id in topo_ids]
    topo.sort(
        key=lambda linha: (linha.ordem if linha.ordem is not None else 0, linha.id)
    )

    return topo
