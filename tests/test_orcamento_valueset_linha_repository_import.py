"""Import checks for the OrcamentoValuesetLinha repository."""

from __future__ import annotations


def test_repository_imports() -> None:
    from app.repositories.orcamento_valueset_linha_repository import (
        OrcamentoValuesetLinhaRepository,
        OrcamentoValuesetLinhaResumo,
    )

    assert OrcamentoValuesetLinhaRepository is not None
    assert OrcamentoValuesetLinhaResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.orcamento_valueset_linha_repository import (
        OrcamentoValuesetLinhaRepository,
    )

    for method in (
        "list_all",
        "list_active",
        "get_by_id",
        "list_by_orcamento_versao",
        "get_by_versao_chave",
        "create",
        "update",
        "deactivate",
        "activate",
    ):
        assert hasattr(OrcamentoValuesetLinhaRepository, method)
