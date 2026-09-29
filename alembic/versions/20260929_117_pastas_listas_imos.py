"""Pastas usadas para gerar no Martelo as listas de ferragens do iMos.

``pasta_listas_imos_rdl`` é onde estão os .rdl que o iMos usa (os mesmos que
o Report Builder edita). ``pasta_motor_relatorios`` fica vazia: só serve para
um PC sem o iX CAD 2023 nem o SQL Management Studio, onde o Martelo não
encontra sozinho as DLLs do ReportViewer.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260929_117"
down_revision: str | Sequence[str] | None = "20260924_116"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONFIGURACOES = (
    (
        "pasta_listas_imos_rdl",
        r"I:\Listas_SQL\LISTA_FERR_ACESSORIOS",
        "Pasta dos relatórios (.rdl) das listas de ferragens do iMos",
    ),
    (
        "pasta_motor_relatorios",
        "",
        "Pasta com as DLLs Microsoft.ReportViewer (só se o Martelo não as encontrar neste PC)",
    ),
)


def upgrade() -> None:
    """Criar as configurações apenas quando ainda não existem."""
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
    for chave, valor, descricao in CONFIGURACOES:
        existe = connection.execute(
            sa.select(system_settings.c.chave).where(system_settings.c.chave == chave)
        ).first()
        if existe is None:
            connection.execute(
                system_settings.insert().values(
                    chave=chave,
                    valor=valor,
                    descricao=descricao,
                    tipo="pasta",
                    grupo="IMOS",
                    ativo=True,
                )
            )


def downgrade() -> None:
    # Configurações potencialmente personalizadas: preservar em downgrade.
    pass
