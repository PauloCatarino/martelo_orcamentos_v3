"""Import checks for the DescricaoPredefinida model (phase P6a)."""

from __future__ import annotations


def test_descricao_predefinida_model_imports() -> None:
    from app.models.descricao_predefinida import DescricaoPredefinida

    assert DescricaoPredefinida is not None


def test_descricao_predefinida_is_registered_in_models() -> None:
    from app.models import DescricaoPredefinida

    assert DescricaoPredefinida is not None


def test_descricao_predefinida_tablename() -> None:
    from app.models.descricao_predefinida import DescricaoPredefinida

    assert DescricaoPredefinida.__tablename__ == "descricoes_predefinidas"


def test_descricao_predefinida_has_expected_columns() -> None:
    from app.models.descricao_predefinida import DescricaoPredefinida

    columns = set(DescricaoPredefinida.__table__.columns.keys())
    expected = {
        "id",
        "user_id",
        "texto",
        "tipo",
        "ordem",
        "created_at",
        "updated_at",
    }
    assert expected <= columns


def test_descricao_predefinida_user_fk_and_index() -> None:
    from app.models.descricao_predefinida import DescricaoPredefinida

    table = DescricaoPredefinida.__table__

    fk_targets = {
        foreign_key.target_fullname
        for foreign_key in table.columns["user_id"].foreign_keys
    }
    assert "users.id" in fk_targets

    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("user_id",) in indexed_columns
