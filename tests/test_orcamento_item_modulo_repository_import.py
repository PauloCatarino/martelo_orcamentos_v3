"""Import checks for the Orcamento item module repository."""

from __future__ import annotations


def test_orcamento_item_modulo_repository_imports() -> None:
    from app.repositories.orcamento_item_modulo_repository import (
        OrcamentoItemModuloRepository,
        OrcamentoItemModuloResumo,
    )

    assert OrcamentoItemModuloRepository is not None
    assert OrcamentoItemModuloResumo is not None
