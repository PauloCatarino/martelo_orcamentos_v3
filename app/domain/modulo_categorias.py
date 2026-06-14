"""Module library categories and scopes (phase 8U.0).

Categories group the reusable modules by zone (roupeiros, cozinhas, ...); the
scope says whether a module belongs to one user or is global. Both normalise
with a safe fallback (OUTROS / UTILIZADOR).
"""

from __future__ import annotations

# Categories / zones (seeded set; extensible).
ROUPEIROS = "ROUPEIROS"
COZINHAS = "COZINHAS"
MOVEIS_WC = "MOVEIS_WC"
OUTROS = "OUTROS"

MODULO_CATEGORIAS = (ROUPEIROS, COZINHAS, MOVEIS_WC, OUTROS)

MODULO_CATEGORIA_LABELS = {
    ROUPEIROS: "Roupeiros",
    COZINHAS: "Cozinhas",
    MOVEIS_WC: "Móveis WC",
    OUTROS: "Outros",
}

# Scopes.
AMBITO_UTILIZADOR = "UTILIZADOR"
AMBITO_GLOBAL = "GLOBAL"

MODULO_AMBITOS = (AMBITO_UTILIZADOR, AMBITO_GLOBAL)

MODULO_AMBITO_LABELS = {
    AMBITO_UTILIZADOR: "Utilizador",
    AMBITO_GLOBAL: "Global",
}


def normalize_modulo_categoria(valor: str | None) -> str:
    """Normalize a module category, falling back to OUTROS."""
    if not valor:
        return OUTROS

    normalizado = valor.strip().upper()
    return normalizado if normalizado in MODULO_CATEGORIA_LABELS else OUTROS


def get_modulo_categoria_label(valor: str | None) -> str:
    """Return the friendly label for a module category."""
    return MODULO_CATEGORIA_LABELS[normalize_modulo_categoria(valor)]


def get_modulo_categoria_options() -> tuple[tuple[str, str], ...]:
    """Return the module categories as (code, label) pairs."""
    return tuple(MODULO_CATEGORIA_LABELS.items())


def normalize_modulo_ambito(valor: str | None) -> str:
    """Normalize a module scope, falling back to UTILIZADOR."""
    if not valor:
        return AMBITO_UTILIZADOR

    normalizado = valor.strip().upper()
    return normalizado if normalizado in MODULO_AMBITO_LABELS else AMBITO_UTILIZADOR
