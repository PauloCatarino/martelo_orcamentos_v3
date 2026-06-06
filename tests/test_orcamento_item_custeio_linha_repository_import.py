"""Import checks for the OrcamentoItemCusteioLinha repository."""

from __future__ import annotations

import dataclasses


def test_repository_imports() -> None:
    from app.repositories.orcamento_item_custeio_linha_repository import (
        OrcamentoItemCusteioLinhaRepository,
        OrcamentoItemCusteioLinhaResumo,
    )

    assert OrcamentoItemCusteioLinhaRepository is not None
    assert OrcamentoItemCusteioLinhaResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.orcamento_item_custeio_linha_repository import (
        OrcamentoItemCusteioLinhaRepository,
    )

    for method in (
        "list_by_orcamento_item",
        "list_active_by_orcamento_item",
        "get_by_id",
        "create_linha",
        "update_linha",
        "deactivate_linha",
        "activate_linha",
    ):
        assert hasattr(OrcamentoItemCusteioLinhaRepository, method)


def test_resumo_has_expected_fields() -> None:
    from app.repositories.orcamento_item_custeio_linha_repository import (
        OrcamentoItemCusteioLinhaResumo,
    )

    field_names = {field.name for field in dataclasses.fields(OrcamentoItemCusteioLinhaResumo)}
    expected = {
        "id",
        "orcamento_item_id",
        "tipo_linha",
        "descricao",
        "quantidade",
        "custo_unitario",
        "custo_total",
        "preco_unitario",
        "preco_total",
        "override_manual",
        "editado_localmente",
        "ativo",
    }
    assert expected <= field_names
