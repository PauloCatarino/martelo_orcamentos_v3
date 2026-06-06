"""Import checks for the OrcamentoItemCusteioLinha model."""

from __future__ import annotations


def test_model_imports() -> None:
    from app.models.orcamento_item_custeio_linha import OrcamentoItemCusteioLinha

    assert OrcamentoItemCusteioLinha is not None


def test_model_is_registered_in_models() -> None:
    from app.models import OrcamentoItemCusteioLinha

    assert OrcamentoItemCusteioLinha is not None


def test_tablename() -> None:
    from app.models.orcamento_item_custeio_linha import OrcamentoItemCusteioLinha

    assert OrcamentoItemCusteioLinha.__tablename__ == "orcamento_item_custeio_linhas"


def test_has_expected_columns() -> None:
    from app.models.orcamento_item_custeio_linha import OrcamentoItemCusteioLinha

    columns = set(OrcamentoItemCusteioLinha.__table__.columns.keys())
    expected = {
        "id",
        "orcamento_item_id",
        "orcamento_item_modulo_id",
        "origem_tipo",
        "origem_id",
        "tipo_linha",
        "codigo",
        "descricao",
        "materia_prima_id",
        "ref_materia_prima",
        "descricao_materia_prima",
        "unidade",
        "quantidade",
        "comp",
        "larg",
        "esp",
        "area_m2",
        "perimetro_ml",
        "ml_orla_fina",
        "ml_orla_grossa",
        "custo_unitario",
        "custo_total",
        "margem_percentagem",
        "preco_unitario",
        "preco_total",
        "def_operacao_id",
        "def_maquina_id",
        "tempo_calculado",
        "tempo_manual",
        "override_manual",
        "editado_localmente",
        "ativo",
        "observacoes",
        "created_at",
        "updated_at",
    }
    assert expected <= columns


def test_required_and_optional_columns() -> None:
    from app.models.orcamento_item_custeio_linha import OrcamentoItemCusteioLinha

    table = OrcamentoItemCusteioLinha.__table__
    assert table.columns["orcamento_item_id"].nullable is False
    assert table.columns["tipo_linha"].nullable is False
    assert table.columns["descricao"].nullable is False
    assert table.columns["orcamento_item_modulo_id"].nullable is True
    assert table.columns["materia_prima_id"].nullable is True


def test_foreign_keys() -> None:
    from app.models.orcamento_item_custeio_linha import OrcamentoItemCusteioLinha

    table = OrcamentoItemCusteioLinha.__table__
    fk_targets = {fk.column.table.name for fk in table.foreign_keys}
    assert {
        "orcamento_items",
        "orcamento_item_modulos",
        "def_materias_primas",
        "def_operacoes",
        "def_maquinas",
    } <= fk_targets


def test_indexes() -> None:
    from app.models.orcamento_item_custeio_linha import OrcamentoItemCusteioLinha

    table = OrcamentoItemCusteioLinha.__table__
    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    for column in (
        "orcamento_item_id",
        "orcamento_item_modulo_id",
        "tipo_linha",
        "origem_tipo",
        "materia_prima_id",
        "def_operacao_id",
        "def_maquina_id",
        "ativo",
    ):
        assert (column,) in indexed_columns


def test_relationships() -> None:
    from app.models.orcamento_item_custeio_linha import OrcamentoItemCusteioLinha

    for relationship_name in (
        "orcamento_item",
        "orcamento_item_modulo",
        "materia_prima",
        "def_operacao",
        "def_maquina",
    ):
        assert hasattr(OrcamentoItemCusteioLinha, relationship_name)
