"""Import checks for the DefMateriaPrima repository."""

from __future__ import annotations

import dataclasses


def test_repository_imports() -> None:
    from app.repositories.def_materia_prima_repository import (
        DefMateriaPrimaRepository,
        DefMateriaPrimaResumo,
    )

    assert DefMateriaPrimaRepository is not None
    assert DefMateriaPrimaResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.def_materia_prima_repository import DefMateriaPrimaRepository

    for method in (
        "list_all",
        "list_active",
        "get_by_id",
        "get_by_ref_le",
        "create_materia_prima",
        "update_materia_prima",
        "deactivate_materia_prima",
    ):
        assert hasattr(DefMateriaPrimaRepository, method)


def test_resumo_has_expected_fields() -> None:
    from app.repositories.def_materia_prima_repository import DefMateriaPrimaResumo

    field_names = {field.name for field in dataclasses.fields(DefMateriaPrimaResumo)}
    expected = {
        "id",
        "ref_le",
        "descricao",
        "tipo_original_excel",
        "familia_original_excel",
        "tipo_martelo",
        "familia_martelo",
        "unidade",
        "preco_tabela",
        "preco_liquido",
        "origem_dados",
        "ativo",
    }
    assert expected <= field_names
