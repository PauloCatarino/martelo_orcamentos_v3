"""Import checks for the DefValuesetModeloLinha repository."""

from __future__ import annotations


def test_repository_imports() -> None:
    from app.repositories.def_valueset_modelo_linha_repository import (
        DefValuesetModeloLinhaRepository,
        DefValuesetModeloLinhaResumo,
    )

    assert DefValuesetModeloLinhaRepository is not None
    assert DefValuesetModeloLinhaResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.def_valueset_modelo_linha_repository import (
        DefValuesetModeloLinhaRepository,
    )

    for method in (
        "list_all",
        "list_active",
        "get_by_id",
        "list_by_modelo",
        "get_by_modelo_chave",
        "create",
        "update",
        "deactivate",
        "activate",
    ):
        assert hasattr(DefValuesetModeloLinhaRepository, method)
