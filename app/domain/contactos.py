"""Formatting rules for contact details.

Phone numbers are typed in every possible way (with spaces, with dots, with
+351, glued together). They are stored in one shape so the supplier list reads
evenly: Portuguese numbers as ``999 999 999``.
"""

from __future__ import annotations

import re

#: Um número nacional tem nove dígitos e lê-se em grupos de três.
DIGITOS_TELEFONE_NACIONAL = 9
TAMANHO_GRUPO = 3
INDICATIVO_PORTUGAL = "351"


def formatar_telefone(valor: str | None) -> str | None:
    """Normalizar um telefone para ``999 999 999``.

    Números que não sejam nacionais (com indicativo de outro país, extensões,
    ou simplesmente com outro número de dígitos) ficam como o utilizador os
    escreveu: mais vale um contacto estranho do que um contacto estragado.
    """
    texto = (valor or "").strip()
    if not texto:
        return None

    digitos = re.sub(r"\D", "", texto)

    # +351 912 345 678 é o mesmo que 912 345 678.
    if digitos.startswith(INDICATIVO_PORTUGAL) and len(digitos) == (
        len(INDICATIVO_PORTUGAL) + DIGITOS_TELEFONE_NACIONAL
    ):
        digitos = digitos[len(INDICATIVO_PORTUGAL) :]

    if len(digitos) != DIGITOS_TELEFONE_NACIONAL:
        return texto

    grupos = [
        digitos[inicio : inicio + TAMANHO_GRUPO]
        for inicio in range(0, DIGITOS_TELEFONE_NACIONAL, TAMANHO_GRUPO)
    ]
    return " ".join(grupos)
