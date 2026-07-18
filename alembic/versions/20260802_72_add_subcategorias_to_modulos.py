"""Add one-level subcategories to the module library.

A module category can now have subcategories: ``def_modulo_categorias`` gains a
``parent_id`` (self-reference; NULL = top-level category, set = subcategory of
that category — one level only). Modules gain an optional ``subcategoria``
(the codigo of a subcategory whose parent is the module's ``categoria``).
Additive and backwards-compatible: existing categories/modules stay top-level.

Revision ID: 20260802_72
Revises: 20260801_71
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260802_72"
down_revision: str | Sequence[str] | None = "20260801_71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add parent_id to categories and subcategoria to modules."""
    op.add_column(
        "def_modulo_categorias",
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_def_modulo_categorias_parent_id",
        "def_modulo_categorias",
        ["parent_id"],
    )
    op.create_foreign_key(
        "fk_def_modulo_categorias_parent",
        "def_modulo_categorias",
        "def_modulo_categorias",
        ["parent_id"],
        ["id"],
    )

    op.add_column(
        "def_modulos",
        sa.Column("subcategoria", sa.String(60), nullable=True),
    )
    op.create_index(
        "ix_def_modulos_subcategoria",
        "def_modulos",
        ["subcategoria"],
    )


def downgrade() -> None:
    """Drop the subcategory support (modules keep their top-level category)."""
    op.drop_index("ix_def_modulos_subcategoria", table_name="def_modulos")
    op.drop_column("def_modulos", "subcategoria")
    op.drop_constraint(
        "fk_def_modulo_categorias_parent",
        "def_modulo_categorias",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_def_modulo_categorias_parent_id",
        table_name="def_modulo_categorias",
    )
    op.drop_column("def_modulo_categorias", "parent_id")
