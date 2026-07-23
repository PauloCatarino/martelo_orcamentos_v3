"""Create the per-obra occurrence log (diary)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260807_77"
down_revision: str | Sequence[str] | None = "20260806_76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: producao_ocorrencias.

    Diário da obra: uma linha por acontecimento, com data, quem escreveu e o
    texto. Serve para o que os clientes reportam depois da entrega (ferragem
    em falta, peça danificada) e para notas que não devem sujar os campos da
    obra. ``user_id`` fica a NULL se a conta for apagada — o registo tem de
    sobreviver a saídas de pessoal.
    """
    op.create_table(
        "producao_ocorrencias",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "producao_id",
            sa.BigInteger(),
            sa.ForeignKey("producao.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        #: Nome de quem escreveu, guardado à cabeça: se a conta desaparecer,
        #: o diário continua a dizer quem registou.
        sa.Column("autor", sa.String(length=255), nullable=True),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_producao_ocorrencias_producao",
        "producao_ocorrencias",
        ["producao_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_producao_ocorrencias_producao", table_name="producao_ocorrencias"
    )
    op.drop_table("producao_ocorrencias")
