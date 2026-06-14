"""Module library search helpers (phase 8U.0/8U.1.1).

A V2-style search term is split by '%' into words that must ALL match the
module's searchable text (code + name + description + category). Shared by the
service listing and the save dialog so both filter the same way. Pure.
"""

from __future__ import annotations

from collections.abc import Sequence


def termo_tokens(termo: str | None) -> list[str]:
    """Split a search term by '%' into the words that must ALL match."""
    if not termo:
        return []

    return [token.strip().lower() for token in termo.split("%") if token.strip()]


def _texto_pesquisavel(modulo) -> str:
    return " ".join(
        parte
        for parte in (
            getattr(modulo, "codigo", None),
            getattr(modulo, "nome", None),
            getattr(modulo, "descricao", None),
            getattr(modulo, "categoria", None),
        )
        if parte
    ).lower()


def modulo_corresponde(modulo, tokens: Sequence[str]) -> bool:
    """Return True when every token is in the module's searchable text."""
    if not tokens:
        return True

    texto = _texto_pesquisavel(modulo)
    return all(token in texto for token in tokens)


def filtrar_por_termo(modulos: Sequence, termo: str | None) -> list:
    """Filter modules by a '%'-separated term (objects with codigo/nome/...)."""
    tokens = termo_tokens(termo)
    if not tokens:
        return list(modulos)

    return [modulo for modulo in modulos if modulo_corresponde(modulo, tokens)]
