"""Import checks for the DefMateriaPrima model."""

from __future__ import annotations


def test_def_materia_prima_model_imports() -> None:
    from app.models.def_materia_prima import DefMateriaPrima

    assert DefMateriaPrima is not None


def test_def_materia_prima_is_registered_in_models() -> None:
    from app.models import DefMateriaPrima

    assert DefMateriaPrima is not None


def test_def_materia_prima_tablename() -> None:
    from app.models.def_materia_prima import DefMateriaPrima

    assert DefMateriaPrima.__tablename__ == "def_materias_primas"


def test_def_materia_prima_has_expected_columns() -> None:
    from app.models.def_materia_prima import DefMateriaPrima

    columns = set(DefMateriaPrima.__table__.columns.keys())
    expected = {
        "id",
        "ref_le",
        "referencia_fornecedor",
        "descricao",
        "tipo_original_excel",
        "familia_original_excel",
        "tipo_martelo",
        "familia_martelo",
        "coresp_orla_0_4",
        "coresp_orla_1_0",
        "unidade",
        "desperdicio_percentagem",
        "preco_tabela",
        "desconto",
        "margem",
        "preco_liquido",
        "comprimento",
        "largura",
        "espessura",
        "fornecedor",
        "origem_dados",
        "ativo",
        "observacoes",
        "created_at",
        "updated_at",
    }
    assert expected <= columns


def test_def_materia_prima_descricao_required_ref_le_optional() -> None:
    from app.models.def_materia_prima import DefMateriaPrima

    table = DefMateriaPrima.__table__
    assert table.columns["descricao"].nullable is False
    assert table.columns["ref_le"].nullable is True


def test_def_materia_prima_ref_le_unique_and_indexes() -> None:
    from app.models.def_materia_prima import DefMateriaPrima

    table = DefMateriaPrima.__table__

    unique_columns: set[str] = set()
    for constraint in table.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            unique_columns |= {column.name for column in constraint.columns}
    assert "ref_le" in unique_columns

    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("tipo_martelo",) in indexed_columns
    assert ("familia_martelo",) in indexed_columns
    assert ("tipo_original_excel",) in indexed_columns
    assert ("familia_original_excel",) in indexed_columns
    assert ("ativo",) in indexed_columns
    assert ("origem_dados",) in indexed_columns
