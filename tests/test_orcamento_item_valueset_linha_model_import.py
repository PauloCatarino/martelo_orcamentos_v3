"""Import checks for the OrcamentoItemValuesetLinha model."""

from __future__ import annotations


def test_model_imports() -> None:
    from app.models.orcamento_item_valueset_linha import OrcamentoItemValuesetLinha

    assert OrcamentoItemValuesetLinha is not None


def test_model_is_registered_in_models() -> None:
    from app.models import OrcamentoItemValuesetLinha

    assert OrcamentoItemValuesetLinha is not None


def test_tablename_columns_and_foreign_keys() -> None:
    from app.models.orcamento_item_valueset_linha import OrcamentoItemValuesetLinha

    assert OrcamentoItemValuesetLinha.__tablename__ == "orcamento_item_valueset_linhas"
    table = OrcamentoItemValuesetLinha.__table__
    columns = set(table.columns.keys())
    assert {
        "id",
        "orcamento_item_id",
        "chave",
        "codigo_opcao",
        "nome_opcao",
        "padrao",
        "ordem",
        "descricao",
        "materia_prima_id",
        "ref_materia_prima",
        "descricao_materia_prima",
        "valor_texto",
        "origem",
        "herdado_do_orcamento",
        "editado_localmente",
        "ativo",
        "observacoes",
        "created_at",
        "updated_at",
    } <= columns
    fk_targets = {fk.column.table.name for fk in table.foreign_keys}
    assert {"orcamento_items", "def_materias_primas"} <= fk_targets


def test_model_has_snapshot_and_origin_columns() -> None:
    from app.models.orcamento_item_valueset_linha import OrcamentoItemValuesetLinha

    columns = set(OrcamentoItemValuesetLinha.__table__.columns.keys())
    assert {
        "ref_le",
        "descricao_no_orcamento",
        "preco_tabela",
        "margem_percentagem",
        "desconto_percentagem",
        "preco_liquido",
        "unidade",
        "desperdicio_percentagem",
        "tipo_materia_prima",
        "familia_materia_prima",
        "coresp_orla_0_4",
        "coresp_orla_1_0",
        "comp_mp",
        "larg_mp",
        "esp_mp",
        "origem_orcamento_valueset_linha_id",
        "origem_orcamento_versao_id",
        "origem_dados",
    } <= columns

    fk_targets = {
        fk.column.table.name for fk in OrcamentoItemValuesetLinha.__table__.foreign_keys
    }
    assert {"orcamento_valueset_linhas", "orcamento_versoes"} <= fk_targets


def test_unique_indexes_and_relationships() -> None:
    from app.models.orcamento_item_valueset_linha import OrcamentoItemValuesetLinha

    table = OrcamentoItemValuesetLinha.__table__
    unique_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("orcamento_item_id", "chave", "codigo_opcao") in unique_sets

    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("orcamento_item_id",) in indexed_columns
    assert ("chave",) in indexed_columns
    assert ("materia_prima_id",) in indexed_columns
    assert ("ativo",) in indexed_columns
    assert hasattr(OrcamentoItemValuesetLinha, "orcamento_item")
    assert hasattr(OrcamentoItemValuesetLinha, "materia_prima")
