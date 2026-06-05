"""Import checks for the Orcamento item repository."""

from __future__ import annotations


def test_orcamento_item_repository_imports() -> None:
    from app.repositories.orcamento_item_repository import OrcamentoItemRepository, OrcamentoItemResumo

    assert OrcamentoItemRepository is not None
    assert OrcamentoItemResumo is not None
