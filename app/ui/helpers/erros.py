"""Helpers for turning database errors into user-facing messages."""

from __future__ import annotations


def causa_tecnica(error: Exception) -> str:
    """Return a short, single-line technical cause for a database error.

    Prefers the underlying DBAPI error (``error.orig``) when present, since it
    carries the real reason (e.g. "no such column: prioridade"); otherwise falls
    back to ``str(error)``. Only the first line is kept, to stay compact.
    """
    origem = getattr(error, "orig", None)
    bruto = str(origem) if origem is not None else str(error)
    primeira_linha = bruto.strip().splitlines()[0] if bruto.strip() else ""

    return primeira_linha.strip()


def mensagem_erro_bd(prefixo: str, error: Exception) -> str:
    """Combine a friendly prefix with the technical cause of a database error.

    Example: ``"Não foi possível guardar a linha. (no such column: prioridade)"``.
    When no cause can be extracted, only the prefix is returned.
    """
    causa = causa_tecnica(error)
    if not causa:
        return prefixo

    return f"{prefixo} ({causa})"
