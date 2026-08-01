"""Add def_pecas.usa_orlas (a peça leva orlas ou nao)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260814_84"
down_revision: str | Sequence[str] | None = "20260813_83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Additive: marcar quais as peças que trabalham com orlas.

    Uma ferragem nao leva orlas, e mostrar-lhe "[0000]" no nome da biblioteca
    so' suja a lista. Este visto diz se a peça trabalha com orlas: quando esta
    desligado, o codigo de orlas nao entra no nome e a orlagem nao e' de
    esperar.

    As peças existentes que ja tem alguma orla ficam com o visto ligado; as que
    tem as quatro a zero ficam com ele desligado, que e' a leitura correta do
    que esta la' hoje.
    """
    op.add_column(
        "def_pecas",
        sa.Column(
            "usa_orlas",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.execute(
        """
        UPDATE def_pecas
           SET usa_orlas = 0
         WHERE orla_c1 = 0 AND orla_c2 = 0 AND orla_l1 = 0 AND orla_l2 = 0
        """
    )


def downgrade() -> None:
    """Remove o visto das orlas."""
    op.drop_column("def_pecas", "usa_orlas")
