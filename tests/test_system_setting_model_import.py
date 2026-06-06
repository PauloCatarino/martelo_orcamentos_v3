"""Import checks for the SystemSetting model."""

from __future__ import annotations


def test_system_setting_model_imports() -> None:
    from app.models.system_setting import SystemSetting

    assert SystemSetting is not None


def test_system_setting_is_registered_in_models() -> None:
    from app.models import SystemSetting

    assert SystemSetting is not None


def test_system_setting_tablename() -> None:
    from app.models.system_setting import SystemSetting

    assert SystemSetting.__tablename__ == "system_settings"


def test_system_setting_has_expected_columns() -> None:
    from app.models.system_setting import SystemSetting

    columns = set(SystemSetting.__table__.columns.keys())
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
    assert expected <= columns


def test_system_setting_chave_unique_and_indexes() -> None:
    from app.models.system_setting import SystemSetting

    table = SystemSetting.__table__

    unique_columns: set[str] = set()
    for constraint in table.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            unique_columns |= {column.name for column in constraint.columns}
    assert "chave" in unique_columns

    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("grupo",) in indexed_columns
    assert ("tipo",) in indexed_columns
    assert ("ativo",) in indexed_columns
