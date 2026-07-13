"""Add revision identity to technical catalog pieces.

Revision ID: 20260722_61
Revises: 20260721_60
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_61"
down_revision: str | Sequence[str] | None = "20260721_60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MySQL DDL is not transactional. The guards make this migration safely
    # resumable if a server/driver error occurs after one of the ADD COLUMNs.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    colunas = {coluna["name"] for coluna in inspector.get_columns("def_pecas")}
    if "revisao_serie" not in colunas:
        op.add_column(
            "def_pecas", sa.Column("revisao_serie", sa.String(36), nullable=True)
        )
    if "revisao_numero" not in colunas:
        op.add_column(
            "def_pecas",
            sa.Column("revisao_numero", sa.Integer(), nullable=False, server_default="1"),
        )
    if "revisao_anterior_id" not in colunas:
        op.add_column(
            "def_pecas", sa.Column("revisao_anterior_id", sa.BigInteger(), nullable=True)
        )
    # Every existing catalog piece starts its own independent revision series.
    op.execute(
        sa.text(
            "UPDATE def_pecas SET revisao_serie = UUID() "
            "WHERE revisao_serie IS NULL"
        )
    )
    op.alter_column(
        "def_pecas",
        "revisao_serie",
        existing_type=sa.String(36),
        nullable=False,
    )

    inspector = sa.inspect(bind)
    indices = {indice["name"] for indice in inspector.get_indexes("def_pecas")}
    if "ix_def_pecas_revisao_serie" not in indices:
        op.create_index("ix_def_pecas_revisao_serie", "def_pecas", ["revisao_serie"])
    if "ix_def_pecas_revisao_anterior_id" not in indices:
        op.create_index(
            "ix_def_pecas_revisao_anterior_id", "def_pecas", ["revisao_anterior_id"]
        )

    unicos = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("def_pecas")
    }
    if "uq_def_pecas_revisao_serie_numero" not in unicos:
        op.create_unique_constraint(
            "uq_def_pecas_revisao_serie_numero",
            "def_pecas",
            ["revisao_serie", "revisao_numero"],
        )

    estrangeiras = {
        constraint["name"]
        for constraint in inspector.get_foreign_keys("def_pecas")
    }
    if "fk_def_pecas_revisao_anterior" not in estrangeiras:
        op.create_foreign_key(
            "fk_def_pecas_revisao_anterior",
            "def_pecas",
            "def_pecas",
            ["revisao_anterior_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    op.drop_constraint("fk_def_pecas_revisao_anterior", "def_pecas", type_="foreignkey")
    op.drop_constraint(
        "uq_def_pecas_revisao_serie_numero", "def_pecas", type_="unique"
    )
    op.drop_index("ix_def_pecas_revisao_anterior_id", table_name="def_pecas")
    op.drop_index("ix_def_pecas_revisao_serie", table_name="def_pecas")
    op.drop_column("def_pecas", "revisao_anterior_id")
    op.drop_column("def_pecas", "revisao_numero")
    op.drop_column("def_pecas", "revisao_serie")
