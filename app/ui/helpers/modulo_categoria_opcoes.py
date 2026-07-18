"""Shared loading of the manageable module categories for UI pickers (phase 6).

Every combo/list of categories should use these helpers so new, renamed and
archived categories appear consistently. On any database problem the seeded
static set is the safe fallback.
"""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.modulo_categorias import (
    MODULO_CATEGORIA_LABELS,
    get_modulo_categoria_options,
)
from app.services.def_modulo_categoria_service import DefModuloCategoriaService


def carregar_opcoes_categorias() -> tuple[tuple[str, str], ...]:
    """Return the ACTIVE categories as (codigo, nome) pairs for pickers."""
    try:
        with SessionLocal() as session:
            opcoes = DefModuloCategoriaService(session).listar_opcoes()
            session.commit()
    except SQLAlchemyError:
        opcoes = ()
    return opcoes or get_modulo_categoria_options()


def carregar_arvore_categorias() -> dict[str, tuple[tuple[str, str], ...]]:
    """Return {categoria_codigo: ((sub_codigo, sub_nome), ...)} for ACTIVE nodes.

    Used by pickers that offer a subcategory choice dependent on the selected
    top-level category. On any database problem an empty mapping is returned.
    """
    try:
        with SessionLocal() as session:
            arvore = DefModuloCategoriaService(session).listar_arvore(
                incluir_arquivadas=False
            )
            session.commit()
    except SQLAlchemyError:
        return {}
    return {
        topo.codigo: tuple((sub.codigo, sub.nome) for sub in subs)
        for topo, subs in arvore
    }


def carregar_labels_categorias() -> dict[str, str]:
    """Return {codigo: nome} of every category (including archived)."""
    try:
        with SessionLocal() as session:
            labels = DefModuloCategoriaService(session).labels()
            session.commit()
    except SQLAlchemyError:
        labels = {}
    return labels or dict(MODULO_CATEGORIA_LABELS)
