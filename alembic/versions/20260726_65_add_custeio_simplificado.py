"""Add per-item simplified costing settings and per-piece edging type."""

from __future__ import annotations
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260726_65"
down_revision: str | Sequence[str] | None = "20260725_64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orcamento_items", sa.Column("modalidade_custeio", sa.String(20), nullable=False, server_default="STANDARD"))
    op.add_column("orcamento_items", sa.Column("simplificado_urgente", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("orcamento_items", sa.Column("simplificado_sem_excel", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("orcamento_items", sa.Column("custo_simplificado_urgencia", sa.Numeric(14, 4), nullable=False, server_default="0"))
    op.add_column("orcamento_items", sa.Column("custo_simplificado_sem_excel", sa.Numeric(14, 4), nullable=False, server_default="0"))
    op.add_column("orcamento_item_custeio_linhas", sa.Column("tipo_orlagem_simplificado", sa.String(10), nullable=False, server_default="PUR"))


def downgrade() -> None:
    op.drop_column("orcamento_item_custeio_linhas", "tipo_orlagem_simplificado")
    for coluna in ("custo_simplificado_sem_excel", "custo_simplificado_urgencia", "simplificado_sem_excel", "simplificado_urgente", "modalidade_custeio"):
        op.drop_column("orcamento_items", coluna)
