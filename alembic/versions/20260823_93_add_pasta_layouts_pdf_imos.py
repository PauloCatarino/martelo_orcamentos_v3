"""Adicionar o caminho local dos PDFs de layouts exportados pelo iMos."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260823_93"
down_revision: str | Sequence[str] | None = "20260821_92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CHAVE = "pasta_layouts_pdf_imos"
VALOR_DEFAULT = r"C:\IMOS_Output_Batches\PDF_MultiSheet_Layout"
DESCRICAO = "Pasta onde vão os PDFs dos Layouts da obra"


def upgrade() -> None:
    """Criar a configuração apenas quando ainda não existe."""
    system_settings = sa.table(
        "system_settings",
        sa.column("chave", sa.String),
        sa.column("valor", sa.Text),
        sa.column("descricao", sa.Text),
        sa.column("tipo", sa.String),
        sa.column("grupo", sa.String),
        sa.column("ativo", sa.Boolean),
    )
    connection = op.get_bind()
    existe = connection.execute(
        sa.select(system_settings.c.chave).where(system_settings.c.chave == CHAVE)
    ).first()
    if existe is None:
        connection.execute(
            system_settings.insert().values(
                chave=CHAVE,
                valor=VALOR_DEFAULT,
                descricao=DESCRICAO,
                tipo="pasta",
                grupo="IMOS",
                ativo=True,
            )
        )


def downgrade() -> None:
    # Configuração potencialmente personalizada: preservar em downgrade.
    pass
