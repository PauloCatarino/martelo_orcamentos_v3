"""Mover as linhas selecionadas uma posição para cima ou para baixo.

Regra pura (sem base de dados nem Qt), usada pelas setas ↑/↓ dos items do
orçamento. As linhas selecionadas andam juntas, mantêm a ordem entre elas e
param quando chegam ao princípio ou ao fim da lista: com as linhas 1 e 2
selecionadas, ↑ não faz nada; com a 1 e a 3, ↑ só sobe a 3.
"""

from __future__ import annotations

from collections.abc import Iterable


def mover_selecao(
    ids: list[int], selecionados: Iterable[int], *, para_cima: bool
) -> list[int] | None:
    """Nova ordem dos ``ids``, ou None quando nada se mexe.

    ``ids`` é a lista completa pela ordem atual. Ids selecionados que não
    estejam na lista são ignorados.
    """
    alvo = {item_id for item_id in selecionados if item_id in ids}
    if not alvo:
        return None

    sequencia = list(ids)
    indices = [indice for indice, item_id in enumerate(sequencia) if item_id in alvo]
    if not para_cima:
        indices.reverse()

    movido = False
    for indice in indices:
        destino = indice - 1 if para_cima else indice + 1
        if destino < 0 or destino >= len(sequencia):
            continue
        if sequencia[destino] in alvo:
            continue  # encostado a outra selecionada que já não pôde andar
        sequencia[indice], sequencia[destino] = sequencia[destino], sequencia[indice]
        movido = True

    return sequencia if movido else None
