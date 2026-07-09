"""Database-level safeguards for user-controlled costing inputs."""

from __future__ import annotations

from sqlalchemy import CheckConstraint

from app.models import OrcamentoItem, OrcamentoItemCusteioLinha


def _check_names(model) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, CheckConstraint) and constraint.name
    }


def test_orcamento_item_tem_checks_de_dimensoes_quantidade_e_preco() -> None:
    assert {
        "ck_oi_altura_pos",
        "ck_oi_largura_pos",
        "ck_oi_profundidade_pos",
        "ck_oi_quantidade_pos",
        "ck_oi_preco_unitario_nonneg",
    } <= _check_names(OrcamentoItem)


def test_linha_custeio_tem_checks_de_quantidades_medidas_e_material() -> None:
    assert {
        "ck_oicl_qt_mod_pos",
        "ck_oicl_qt_und_nonneg",
        "ck_oicl_quantidade_nonneg",
        "ck_oicl_comp_real_pos",
        "ck_oicl_preco_liquido_nonneg",
        "ck_oicl_desperdicio_nonneg",
        "ck_oicl_comp_mp_nonneg",
        "ck_oicl_acab_sup_preco_nonneg",
    } <= _check_names(OrcamentoItemCusteioLinha)
