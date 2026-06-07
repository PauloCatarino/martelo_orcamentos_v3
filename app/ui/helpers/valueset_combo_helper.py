"""Helpers to populate ValueSet key combo boxes from the database.

The combos load the active keys from ``def_valueset_chaves`` (DB first). If the
database has no keys yet, or fails, they fall back to the constants in
``app/domain/valueset_types.py`` so the UI never breaks.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.valueset_types import get_valueset_key_options
from app.services.def_valueset_chave_service import DefValuesetChaveService

SEM_CHAVE_LABEL = "Sem chave"


def _opcoes_da_base(tipo: str | None) -> list[tuple[str, str]]:
    """Return (codigo, nome) options from the database (empty on failure)."""
    try:
        with SessionLocal() as session:
            service = DefValuesetChaveService(session)
            chaves = service.listar_por_tipo(tipo) if tipo else service.listar_chaves_ativas()
    except SQLAlchemyError:
        return []

    return [(chave.codigo, chave.nome) for chave in chaves]


def _opcoes_fallback(tipo: str | None) -> list[tuple[str, str]]:
    """Return (codigo, nome) options from the domain constants."""
    opcoes = get_valueset_key_options()
    if tipo:
        prefixo = f"{tipo}_"
        opcoes = tuple((code, label) for code, label in opcoes if code.startswith(prefixo))

    return [(code, label) for code, label in opcoes]


def carregar_chaves_valueset_combo(
    combo: QComboBox, tipo: str | None = None, valor_atual: str | None = None
) -> None:
    """Populate a ValueSet key combo with active keys, keeping the current value.

    - Loads the active keys from the database first, with a domain fallback.
    - Always starts with a "Sem chave" option (data ``None``).
    - If ``valor_atual`` is a code not in the loaded options, it is added as
      "<codigo> (nao configurada)" so it is not lost on save, and selected.
    """
    combo.clear()
    combo.addItem(SEM_CHAVE_LABEL, None)

    opcoes = _opcoes_da_base(tipo) or _opcoes_fallback(tipo)
    codigos = {codigo for codigo, _ in opcoes}
    for codigo, nome in opcoes:
        combo.addItem(nome, codigo)

    if valor_atual:
        if valor_atual not in codigos:
            combo.addItem(f"{valor_atual} (nao configurada)", valor_atual)
        index = combo.findData(valor_atual)
        if index >= 0:
            combo.setCurrentIndex(index)
    else:
        combo.setCurrentIndex(0)


def obter_valor_chave_combo(combo: QComboBox) -> str | None:
    """Return the selected ValueSet key code (None for 'Sem chave')."""
    return combo.currentData()
