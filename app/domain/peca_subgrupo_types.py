"""Sub-families used inside a piece group (e.g. FERRAGENS > DOBRADICAS).

The sub-family is only tidying: it adds one level to the Definições de Peças
and costing library trees. It is free text — these are the suggestions offered
in the dialogs, taken from the way the hardware catalog is organised in the V2.
"""

from __future__ import annotations

GRUPO_FERRAGENS = "FERRAGENS"

SUBGRUPOS_FERRAGENS: tuple[str, ...] = (
    "DOBRADICAS",
    "SUPORTES PRATELEIRA",
    "SPP (ACESSORIOS AJUSTAVEIS)",
    "PUXADORES",
    "CORREDICAS GAVETAS",
    "PES",
    "SISTEMAS ELEVATORIOS",
    "ILUMINACAO",
    "COZINHAS",
    "ROUPEIROS",
    "UNIOES CANTO SPP",
    "SISTEMAS CORRER",
)

SUBGRUPOS_SUGERIDOS: dict[str, tuple[str, ...]] = {
    GRUPO_FERRAGENS: SUBGRUPOS_FERRAGENS,
}


def normalize_subgrupo(valor: str | None) -> str | None:
    """Normalize a sub-family: uppercase, single spaces, empty becomes None."""
    if valor is None:
        return None

    normalizado = " ".join(str(valor).strip().upper().split())
    return normalizado or None


def get_subgrupo_options(grupo: str | None = None) -> tuple[str, ...]:
    """Suggestions for one group, falling back to every known sub-family."""
    sugeridos = SUBGRUPOS_SUGERIDOS.get(normalize_subgrupo(grupo) or "")
    if sugeridos is not None:
        return sugeridos

    return SUBGRUPOS_FERRAGENS
