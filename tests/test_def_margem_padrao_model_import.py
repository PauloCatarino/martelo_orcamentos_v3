"""Import checks for the DefMargemPadrao model."""

from __future__ import annotations


def test_def_margem_padrao_model_imports() -> None:
    from app.models import DefMargemPadrao

    assert DefMargemPadrao is not None
    assert DefMargemPadrao.__tablename__ == "def_margens_padrao"

    columns = DefMargemPadrao.__table__.columns
    for nome in (
        "ambito",
        "cliente_id",
        "user_id",
        "margem_lucro_pct",
        "margem_mp_pct",
        "margem_mao_obra_pct",
        "margem_acabamentos_pct",
        "custos_administrativos_pct",
        "ativo",
    ):
        assert nome in columns

    constraint_names = {
        constraint.name for constraint in DefMargemPadrao.__table__.constraints
    }
    assert "uq_def_margens_padrao_cliente" in constraint_names
    assert "uq_def_margens_padrao_user" in constraint_names


def test_margens_padrao_types() -> None:
    from app.domain.margens_padrao_types import (
        AMBITOS_MARGENS_PADRAO,
        normalize_ambito,
    )

    assert AMBITOS_MARGENS_PADRAO == ("STANDARD", "CLIENTE", "UTILIZADOR")
    assert normalize_ambito(" cliente ") == "CLIENTE"
    assert normalize_ambito("OUTRO") is None
    assert normalize_ambito(None) is None
