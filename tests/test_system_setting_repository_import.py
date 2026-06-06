"""Import checks for the SystemSetting repository."""

from __future__ import annotations

import dataclasses


def test_repository_imports() -> None:
    from app.repositories.system_setting_repository import (
        SystemSettingRepository,
        SystemSettingResumo,
    )

    assert SystemSettingRepository is not None
    assert SystemSettingResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.system_setting_repository import SystemSettingRepository

    for method in (
        "list_all",
        "list_by_group",
        "get_by_key",
        "upsert_setting",
        "update_setting",
    ):
        assert hasattr(SystemSettingRepository, method)


def test_resumo_has_expected_fields() -> None:
    from app.repositories.system_setting_repository import SystemSettingResumo

    field_names = {field.name for field in dataclasses.fields(SystemSettingResumo)}
    expected = {
        "id",
        "chave",
        "valor",
        "descricao",
        "tipo",
        "grupo",
        "ativo",
        "created_at",
        "updated_at",
    }
    assert expected <= field_names
