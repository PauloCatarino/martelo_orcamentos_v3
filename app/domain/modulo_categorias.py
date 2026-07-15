"""Module library categories and scopes (phase 8U.0; manageable in phase 6).

Categories group the reusable modules by zone (roupeiros, cozinhas, a customer
name, ...). Since phase 6 they live in the ``def_modulo_categorias`` table and
the user manages them; this module keeps the seeded set, the code
normalisation (slug) and the label fallback used by the UI. The scope says
whether a module belongs to one user or is global.
"""

from __future__ import annotations

# Seeded categories / zones (the user can add more in the library page).
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
    """Normalize a category code to its slug (UPPER, '_' between words).

    Empty/None falls back to OUTROS. Unknown codes are KEPT as-is (phase 6:
    categories are user-managed, so a code outside the seeded set is a valid
    category, e.g. a customer name).
    """
    if not valor:
        return OUTROS

    normalizado = "_".join(valor.strip().upper().split())
    return normalizado or OUTROS


def get_modulo_categoria_label(
    valor: str | None, labels: dict[str, str] | None = None
) -> str:
    """Return the friendly label for a module category.

    ``labels`` is the {codigo: nome} mapping loaded from the categories table;
    without it (or for a code missing there) the seeded labels apply, and any
    other code falls back to a title-cased version of itself.
    """
    codigo = normalize_modulo_categoria(valor)
    if labels and codigo in labels:
        return labels[codigo]
    if codigo in MODULO_CATEGORIA_LABELS:
        return MODULO_CATEGORIA_LABELS[codigo]
    return codigo.replace("_", " ").title()


def get_modulo_categoria_options() -> tuple[tuple[str, str], ...]:
    """Return the SEEDED module categories as (code, label) pairs.

    Static fallback only — the UI should prefer the manageable list from
    DefModuloCategoriaService.listar_opcoes().
    """
    return tuple(MODULO_CATEGORIA_LABELS.items())


def normalize_modulo_ambito(valor: str | None) -> str:
    """Normalize a module scope, falling back to UTILIZADOR."""
    if not valor:
        return AMBITO_UTILIZADOR

    normalizado = valor.strip().upper()
    return normalizado if normalizado in MODULO_AMBITO_LABELS else AMBITO_UTILIZADOR


def pode_gerir_modulo(
    modulo_ambito: str | None,
    modulo_user_id: int | None,
    *,
    user_id: int | None,
    is_admin: bool,
) -> bool:
    """Whether a user can edit/delete/convert a module (phase 6 permissions).

    GLOBAL modules are managed only by administrators; UTILIZADOR modules by
    their owner or an administrator.
    """
    if is_admin:
        return True
    if normalize_modulo_ambito(modulo_ambito) == AMBITO_GLOBAL:
        return False
    return user_id is not None and modulo_user_id == user_id
