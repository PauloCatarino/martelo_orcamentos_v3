"""Technical identities for ValueSet options.

The UI exposes only the friendly option name.  These helpers keep the
technical identity deterministic for new rows while leaving existing codes
unchanged during edits.
"""

from __future__ import annotations

import re
import unicodedata


def normalizar_codigo_opcao(valor: str | None) -> str:
    """Normalize a technical option code to the database convention."""
    texto = unicodedata.normalize("NFKD", valor or "")
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_").upper()
    return texto[:100]


def base_codigo_opcao(
    *,
    chave: str,
    nome_opcao: str | None,
    ref_le: str | None,
    ref_materia_prima: str | None,
) -> str:
    """Build the preferred stable code for a newly created option.

    A selected material reference wins over the friendly label.  Free options
    use the friendly label, and the ValueSet key is the final non-empty
    fallback for callers that still use the service API directly.
    """
    if ref_le and normalizar_codigo_opcao(ref_le):
        return f"LE_{normalizar_codigo_opcao(ref_le)}"[:100]
    if ref_materia_prima and normalizar_codigo_opcao(ref_materia_prima):
        return f"MP_{normalizar_codigo_opcao(ref_materia_prima)}"[:100]

    base = normalizar_codigo_opcao(nome_opcao)
    if base:
        return f"OP_{base}"[:100]
    return normalizar_codigo_opcao(chave) or "OPCAO"
