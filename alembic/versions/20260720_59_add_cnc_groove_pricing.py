"""Add CNC groove capabilities, tariffs and piece-operation geometry.

Revision ID: 20260720_59
Revises: 20260719_58
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260720_59"
down_revision: str | Sequence[str] | None = "20260719_58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "def_maquinas",
        sa.Column("permite_rasgos", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("def_maquinas", sa.Column("preco_rasgo_ml_std", sa.Numeric(14, 4), nullable=True))
    op.add_column("def_maquinas", sa.Column("preco_rasgo_ml_serie", sa.Numeric(14, 4), nullable=True))
    op.add_column(
        "def_peca_operacoes",
        sa.Column("rasgo_qt_comp", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "def_peca_operacoes",
        sa.Column("rasgo_qt_larg", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("def_peca_operacoes", "rasgo_qt_larg")
    op.drop_column("def_peca_operacoes", "rasgo_qt_comp")
    op.drop_column("def_maquinas", "preco_rasgo_ml_serie")
    op.drop_column("def_maquinas", "preco_rasgo_ml_std")
    op.drop_column("def_maquinas", "permite_rasgos")
