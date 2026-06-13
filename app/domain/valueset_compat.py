"""ValueSet option compatibility for the 'Mat. default' dropdown (IMOS logic).

A cost line's selectable material options come from the item ValueSet, filtered
by the TYPE of the line's key (def_valueset_chaves.tipo):

- MATERIAL lines see EVERY MATERIAL option (boards cross between
  fundos / portas / laterais / costas / tampos / prateleiras ...);
- FERRAGEM / SISTEMA_CORRER / ILUMINACAO / ACESSORIO lines see only the options
  of their OWN key (same family: pé -> pés, dobradiça -> dobradiças);
- ORLA / ACABAMENTO (and unknown / no key) are NOT handled here (own treatment).

Pure and deterministic.
"""

from __future__ import annotations

from collections.abc import Sequence

TIPO_MATERIAL = "MATERIAL"
TIPO_FERRAGEM = "FERRAGEM"
TIPO_SISTEMA_CORRER = "SISTEMA_CORRER"
TIPO_ILUMINACAO = "ILUMINACAO"
TIPO_ACESSORIO = "ACESSORIO"
TIPO_ORLA = "ORLA"
TIPO_ACABAMENTO = "ACABAMENTO"

# Hardware-like types: a line only mixes within its OWN key (same family).
_TIPOS_MESMA_CHAVE = (
    TIPO_FERRAGEM,
    TIPO_SISTEMA_CORRER,
    TIPO_ILUMINACAO,
    TIPO_ACESSORIO,
)


def _norm(chave) -> str:
    """Uppercase/strip a key code for lookups (empty for None)."""
    return (chave or "").strip().upper()


def tipo_da_chave(chave, chave_tipos: dict) -> str | None:
    """Return the type of a ValueSet key from the key->type map (or None)."""
    return chave_tipos.get(_norm(chave))


def opcoes_valueset_compativeis(
    chave_linha,
    opcoes: Sequence,
    chave_tipos: dict,
) -> list:
    """Return the ValueSet options compatible with a cost line's key.

    ``opcoes`` is a sequence of objects with a ``chave`` attribute; ``chave_tipos``
    maps each key code (any case) to its type. Returns the matching subset in the
    original order. Lines whose key type is MATERIAL get every MATERIAL option;
    FERRAGEM/SISTEMA_CORRER/ILUMINACAO/ACESSORIO get only their own key's options;
    ORLA/ACABAMENTO/unknown — or no key — get an empty list.
    """
    chave = _norm(chave_linha)
    if not chave:
        return []

    tipo = chave_tipos.get(chave)
    if tipo == TIPO_MATERIAL:
        return [
            opcao
            for opcao in opcoes
            if chave_tipos.get(_norm(getattr(opcao, "chave", None))) == TIPO_MATERIAL
        ]
    if tipo in _TIPOS_MESMA_CHAVE:
        return [
            opcao
            for opcao in opcoes
            if _norm(getattr(opcao, "chave", None)) == chave
        ]

    return []
