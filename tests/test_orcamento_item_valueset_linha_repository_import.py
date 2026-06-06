"""Import checks for the OrcamentoItemValuesetLinha repository."""

from __future__ import annotations


def test_repository_imports() -> None:
    from app.repositories.orcamento_item_valueset_linha_repository import (
        OrcamentoItemValuesetLinhaRepository,
        OrcamentoItemValuesetLinhaResumo,
    )

    assert OrcamentoItemValuesetLinhaRepository is not None
    assert OrcamentoItemValuesetLinhaResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.orcamento_item_valueset_linha_repository import (
        OrcamentoItemValuesetLinhaRepository,
    )

    for method in (
        "list_all",
        "list_active",
        "get_by_id",
        "list_by_orcamento_item",
        "get_by_item_chave",
        "create",
        "update",
        "deactivate",
        "activate",
    ):
        assert hasattr(OrcamentoItemValuesetLinhaRepository, method)
