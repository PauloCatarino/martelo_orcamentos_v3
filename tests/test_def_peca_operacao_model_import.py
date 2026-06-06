"""Import checks for the DefPecaOperacao model."""

from __future__ import annotations


def test_def_peca_operacao_model_imports() -> None:
    from app.models.def_peca_operacao import DefPecaOperacao

    assert DefPecaOperacao is not None


def test_def_peca_operacao_is_registered_in_models() -> None:
    from app.models import DefPecaOperacao

    assert DefPecaOperacao is not None


def test_def_peca_operacao_tablename() -> None:
    from app.models.def_peca_operacao import DefPecaOperacao

    assert DefPecaOperacao.__tablename__ == "def_peca_operacoes"


def test_def_peca_operacao_has_expected_columns() -> None:
    from app.models.def_peca_operacao import DefPecaOperacao

    columns = set(DefPecaOperacao.__table__.columns.keys())
    expected = {
        "id",
        "def_peca_id",
        "def_operacao_id",
        "ordem",
        "regra_calculo",
        "quantidade_base",
        "obrigatorio",
        "ativo",
        "observacoes",
        "created_at",
        "updated_at",
    }
    assert expected <= columns


def test_def_peca_operacao_required_foreign_keys() -> None:
    from app.models.def_peca_operacao import DefPecaOperacao

    table = DefPecaOperacao.__table__
    assert table.columns["def_peca_id"].nullable is False
    assert table.columns["def_operacao_id"].nullable is False

    fk_targets = {fk.column.table.name for fk in table.foreign_keys}
    assert {"def_pecas", "def_operacoes"} <= fk_targets


def test_def_peca_operacao_unique_and_indexes() -> None:
    from app.models.def_peca_operacao import DefPecaOperacao

    table = DefPecaOperacao.__table__

    unique_columns: set[str] = set()
    for constraint in table.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            unique_columns |= {column.name for column in constraint.columns}
    assert {"def_peca_id", "def_operacao_id"} <= unique_columns

    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("def_peca_id",) in indexed_columns
    assert ("def_operacao_id",) in indexed_columns
    assert ("ativo",) in indexed_columns


def test_def_peca_has_operacoes_relationship() -> None:
    from app.models.def_peca import DefPeca

    assert hasattr(DefPeca, "operacoes")
