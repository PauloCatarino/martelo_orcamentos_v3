"""Add orcamentos.proposta_phc (PHC proposal number)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260808_78"
down_revision: str | Sequence[str] | None = "20260807_77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: orcamentos.proposta_phc.

    Guarda o número da proposta no PHC (``BO.OBRANO``) atribuído quando o
    orçamento é registado no PHC. Serve de ligação entre os dois sistemas e
    de guarda contra registar a mesma proposta duas vezes.

    Fica a NULL nos orçamentos existentes (ainda não registados no PHC).
    O ano é o do próprio orçamento — no PHC o ``OBRANO`` reinicia a cada ano,
    por isso o par (ano, número) é o que identifica a proposta.
    """
    op.add_column(
        "orcamentos",
        sa.Column("proposta_phc", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "ix_orcamentos_proposta_phc",
        "orcamentos",
        ["proposta_phc"],
    )


def downgrade() -> None:
    """Remove orcamentos.proposta_phc."""
    op.drop_index("ix_orcamentos_proposta_phc", table_name="orcamentos")
    op.drop_column("orcamentos", "proposta_phc")
