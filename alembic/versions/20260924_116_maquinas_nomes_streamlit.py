"""Máquinas: os nomes com que aparecem nos tempos do Streamlit.

Pedido do Paulo (24-09-2026): no custo de produção da Lista Material, cada
linha de horas do Streamlit (HKL 300, Orla 2, ABD, V310…) tem de levar o €/h
da máquina definida no Martelo. Os nomes do Streamlit não são os códigos do
Martelo; este campo faz a ponte e fica para as obras seguintes.

Revision ID: 20260924_116
Revises: 20260924_115
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_116"
down_revision: str | Sequence[str] | None = "20260924_115"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "def_maquinas",
        sa.Column("nomes_streamlit", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    # Migração aditiva: os nomes que o utilizador escreveu não se apagam num
    # downgrade automático.
    pass
