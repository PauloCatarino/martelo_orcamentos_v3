"""Import checks for the DefValuesetModelo repository."""

from __future__ import annotations


def test_repository_imports() -> None:
    from app.repositories.def_valueset_modelo_repository import (
        DefValuesetModeloRepository,
        DefValuesetModeloResumo,
    )

    assert DefValuesetModeloRepository is not None
    assert DefValuesetModeloResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.def_valueset_modelo_repository import DefValuesetModeloRepository

    for method in (
        "list_all",
        "list_active",
        "get_by_id",
        "get_by_codigo",
        "create",
        "update",
        "deactivate",
        "activate",
    ):
        assert hasattr(DefValuesetModeloRepository, method)
