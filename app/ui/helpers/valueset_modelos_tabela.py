"""Columns of a ValueSet models table, shared by the page and the import dialog.

The user picks a model in two different places — the Modelos ValueSet page and
the "Importar Modelo ValueSet" dialog — and expects to read the same thing in
both. Keeping the columns here stops the two from drifting apart.
"""

from __future__ import annotations

COLUNAS_MODELO_VALUESET: tuple[str, ...] = (
    "Código",
    "Nome",
    "Descrição",
    "Observações",
    "Tipo",
    "Âmbito",
    "Dono/Utilizador",
    "Ativo",
)

# Free text that often does not fit its column: shown whole in the tooltip.
COLUNAS_COM_DICA: frozenset[str] = frozenset({"Descrição", "Observações"})


def modelo_e_global(modelo) -> bool:
    """True when a model is shared with everyone."""
    ambito = (getattr(modelo, "ambito", None) or "").strip().upper()
    return ambito == "GLOBAL" or bool(getattr(modelo, "visivel_para_todos", False))


def dono_modelo_valueset(modelo) -> str:
    """Owner label: GLOBAL for shared models, else the owner username."""
    if modelo_e_global(modelo):
        return "GLOBAL"

    return getattr(modelo, "owner_username", None) or ""


def valores_modelo_valueset(modelo) -> list[str]:
    """One row of text for a model, in the same order as the columns."""
    return [
        modelo.codigo,
        modelo.nome,
        modelo.descricao or "",
        getattr(modelo, "observacoes", None) or "",
        modelo.tipo or "",
        modelo.ambito,
        dono_modelo_valueset(modelo),
        "Sim" if modelo.ativo else "Não",
    ]
