"""Add database checks for costing and item inputs.

Revision ID: 20260711_50
Revises: 20260710_49
Create Date: 2026-07-11
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "20260711_50"
down_revision: str | Sequence[str] | None = "20260710_49"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ITEM = "orcamento_items"
_LINHA = "orcamento_item_custeio_linhas"

_ITEM_CHECKS = (
    ("ck_oi_altura_pos", "altura IS NULL OR altura > 0"),
    ("ck_oi_largura_pos", "largura IS NULL OR largura > 0"),
    ("ck_oi_profundidade_pos", "profundidade IS NULL OR profundidade > 0"),
    ("ck_oi_quantidade_pos", "quantidade > 0"),
    ("ck_oi_preco_unitario_nonneg", "preco_unitario IS NULL OR preco_unitario >= 0"),
)

_LINHA_CHECKS = (
    ("ck_oicl_qt_mod_pos", "qt_mod IS NULL OR qt_mod > 0"),
    ("ck_oicl_qt_und_nonneg", "qt_und IS NULL OR qt_und >= 0"),
    ("ck_oicl_quantidade_nonneg", "quantidade >= 0"),
    ("ck_oicl_comp_real_pos", "comp_real IS NULL OR comp_real > 0"),
    ("ck_oicl_larg_real_pos", "larg_real IS NULL OR larg_real > 0"),
    ("ck_oicl_esp_real_pos", "esp_real IS NULL OR esp_real > 0"),
    (
        "ck_oicl_preco_liquido_nonneg",
        "preco_liquido IS NULL OR preco_liquido >= 0",
    ),
    (
        "ck_oicl_desperdicio_nonneg",
        "desperdicio_percentagem IS NULL OR desperdicio_percentagem >= 0",
    ),
    ("ck_oicl_comp_mp_nonneg", "comp_mp IS NULL OR comp_mp >= 0"),
    ("ck_oicl_larg_mp_nonneg", "larg_mp IS NULL OR larg_mp >= 0"),
    ("ck_oicl_esp_mp_nonneg", "esp_mp IS NULL OR esp_mp >= 0"),
    (
        "ck_oicl_acab_sup_preco_nonneg",
        "acabamento_sup_preco_liquido IS NULL OR acabamento_sup_preco_liquido >= 0",
    ),
    (
        "ck_oicl_acab_inf_preco_nonneg",
        "acabamento_inf_preco_liquido IS NULL OR acabamento_inf_preco_liquido >= 0",
    ),
    (
        "ck_oicl_acab_sup_desp_nonneg",
        "acabamento_sup_desperdicio_percentagem IS NULL OR "
        "acabamento_sup_desperdicio_percentagem >= 0",
    ),
    (
        "ck_oicl_acab_inf_desp_nonneg",
        "acabamento_inf_desperdicio_percentagem IS NULL OR "
        "acabamento_inf_desperdicio_percentagem >= 0",
    ),
)


def upgrade() -> None:
    """Prevent invalid financial inputs even outside the application services."""
    for nome, condicao in _ITEM_CHECKS:
        op.create_check_constraint(nome, _ITEM, condicao)
    for nome, condicao in _LINHA_CHECKS:
        op.create_check_constraint(nome, _LINHA, condicao)


def downgrade() -> None:
    """Remove the input validation checks."""
    for nome, _condicao in reversed(_LINHA_CHECKS):
        op.drop_constraint(nome, _LINHA, type_="check")
    for nome, _condicao in reversed(_ITEM_CHECKS):
        op.drop_constraint(nome, _ITEM, type_="check")
