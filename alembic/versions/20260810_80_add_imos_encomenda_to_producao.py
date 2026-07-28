"""Add producao.imos_* (rasto da encomenda criada no iMos)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260810_80"
down_revision: str | Sequence[str] | None = "20260809_79"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: rasto da encomenda criada no iMos a partir da obra.

    O iMos não sabe que o Martelo o alimentou, e o Martelo não sabia o que já
    lá tinha criado: para saber se uma obra já tinha encomenda era preciso
    abrir o iX Organizer. Estas colunas guardam o que foi criado, quando e por
    quem, e são a base do aviso que evita criar a mesma encomenda duas vezes.

    Ficam a NULL nas obras existentes (não se sabe o que foi criado à mão).
    """
    op.add_column(
        "producao",
        sa.Column("imos_nome_encomenda", sa.String(length=30), nullable=True),
    )
    op.add_column("producao", sa.Column("imos_dir_id", sa.Integer(), nullable=True))
    op.add_column("producao", sa.Column("imos_criado_em", sa.DateTime(), nullable=True))
    op.add_column(
        "producao",
        sa.Column("imos_criado_por_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_producao_imos_nome_encomenda",
        "producao",
        ["imos_nome_encomenda"],
    )
    op.create_foreign_key(
        "fk_producao_imos_criado_por",
        "producao",
        "users",
        ["imos_criado_por_id"],
        ["id"],
    )


def downgrade() -> None:
    """Remove o rasto da encomenda iMos."""
    op.drop_constraint(
        "fk_producao_imos_criado_por", "producao", type_="foreignkey"
    )
    op.drop_index("ix_producao_imos_nome_encomenda", table_name="producao")
    op.drop_column("producao", "imos_criado_por_id")
    op.drop_column("producao", "imos_criado_em")
    op.drop_column("producao", "imos_dir_id")
    op.drop_column("producao", "imos_nome_encomenda")
