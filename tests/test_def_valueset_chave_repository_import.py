"""Import checks for the DefValuesetChave repository."""

from __future__ import annotations

import dataclasses


def test_repository_imports() -> None:
    from app.repositories.def_valueset_chave_repository import (
        DefValuesetChaveRepository,
        DefValuesetChaveResumo,
    )

    assert DefValuesetChaveRepository is not None
    assert DefValuesetChaveResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.def_valueset_chave_repository import DefValuesetChaveRepository

    for method in (
        "list_all",
        "list_active",
        "list_by_tipo",
        "get_by_id",
        "get_by_codigo",
        "create_chave",
        "update_chave",
        "deactivate_chave",
        "activate_chave",
    ):
        assert hasattr(DefValuesetChaveRepository, method)


def test_resumo_has_expected_fields() -> None:
    from app.repositories.def_valueset_chave_repository import DefValuesetChaveResumo

    field_names = {field.name for field in dataclasses.fields(DefValuesetChaveResumo)}
    assert {
        "id",
        "codigo",
        "nome",
        "descricao",
        "tipo",
        "grupo",
        "sistema",
        "ativo",
        "ordem",
        "observacoes",
    } <= field_names
