"""Import checks for the DefMaquina repository."""

from __future__ import annotations

import dataclasses


def test_repository_imports() -> None:
    from app.repositories.def_maquina_repository import DefMaquinaRepository, DefMaquinaResumo

    assert DefMaquinaRepository is not None
    assert DefMaquinaResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.def_maquina_repository import DefMaquinaRepository

    for method in (
        "list_all",
        "list_active",
        "get_by_id",
        "get_by_codigo",
        "create_maquina",
        "update_maquina",
        "deactivate_maquina",
    ):
        assert hasattr(DefMaquinaRepository, method)


def test_resumo_has_expected_fields() -> None:
    from app.repositories.def_maquina_repository import DefMaquinaResumo

    field_names = {field.name for field in dataclasses.fields(DefMaquinaResumo)}
    expected = {
        "id",
        "codigo",
        "nome",
        "descricao",
        "tipo",
        "custo_hora",
        "ativo",
        "observacoes",
    }
    assert expected <= field_names
