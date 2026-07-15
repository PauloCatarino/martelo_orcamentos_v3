"""Create the child table of PHC orders per budget version (phase 5)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_67"
down_revision: str | Sequence[str] | None = "20260727_66"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive migration: child table + import of the legacy enc_phc value.

    ``orcamento_versoes.enc_phc`` is kept for compatibility and mirrors the
    principal order from now on.
    """
    op.create_table(
        "orcamento_versao_encomendas_phc",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "orcamento_versao_id",
            sa.BigInteger(),
            sa.ForeignKey("orcamento_versoes.id"),
            nullable=False,
        ),
        sa.Column("numero", sa.String(64), nullable=False),
        sa.Column(
            "is_principal",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "orcamento_versao_id",
            "numero",
            name="uq_versao_encomenda_phc_numero",
        ),
    )
    op.create_index(
        "ix_orcamento_versao_encomendas_phc_orcamento_versao_id",
        "orcamento_versao_encomendas_phc",
        ["orcamento_versao_id"],
    )

    # Import each existing enc_phc as the first (principal) order of its
    # version. Legacy values remain untouched in orcamento_versoes.enc_phc.
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO orcamento_versao_encomendas_phc
                (orcamento_versao_id, numero, is_principal)
            SELECT id, TRIM(enc_phc), 1
            FROM orcamento_versoes
            WHERE enc_phc IS NOT NULL AND TRIM(enc_phc) <> ''
            """
        )
    )


def downgrade() -> None:
    """Remove the PHC orders child table."""
    op.drop_index(
        "ix_orcamento_versao_encomendas_phc_orcamento_versao_id",
        table_name="orcamento_versao_encomendas_phc",
    )
    op.drop_table("orcamento_versao_encomendas_phc")
