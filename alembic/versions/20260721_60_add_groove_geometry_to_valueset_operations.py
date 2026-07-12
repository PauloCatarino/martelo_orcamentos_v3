"""Add CNC groove geometry to ValueSet operation snapshots.

Revision ID: 20260721_60
Revises: 20260720_59
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260721_60"
down_revision: str | Sequence[str] | None = "20260720_59"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in (
        "def_valueset_modelo_linha_operacoes",
        "orcamento_valueset_linha_operacoes",
        "orcamento_item_valueset_linha_operacoes",
    ):
        op.add_column(table, sa.Column("rasgo_qt_comp", sa.Integer(), nullable=False, server_default="0"))
        op.add_column(table, sa.Column("rasgo_qt_larg", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    for table in reversed((
        "def_valueset_modelo_linha_operacoes",
        "orcamento_valueset_linha_operacoes",
        "orcamento_item_valueset_linha_operacoes",
    )):
        op.drop_column(table, "rasgo_qt_larg")
        op.drop_column(table, "rasgo_qt_comp")
