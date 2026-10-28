"""Produção → Escritório do Streamlit: o interruptor e os nomes de utilizador.

``streamlit_escrita_ativa`` (OFF) liga o envio para o Aprovisionamento que o
Martelo faz ao gravar uma obra que passa a Produção. A conta SQL do Martelo no
Streamlit pode escrever desde 28-10-2026 e é a mesma de todas as leituras: é
este interruptor que segura a escrita.

``streamlit_mapa_utilizadores`` (vazio) corrige à mão a ligação entre o
utilizador do Martelo e o do Streamlit (``paulo=paulo_catarino``), para quando
a ligação automática pelo nome da pessoa não chega.

Só acrescenta linhas a ``system_settings``; não cria tabelas.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261028_121"
down_revision: str | Sequence[str] | None = "20261019_120"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONFIGURACOES = (
    (
        "streamlit_escrita_ativa",
        "OFF",
        "Streamlit - Enviar para o Aprovisionamento ao gravar uma obra em Produção (ON/OFF)",
        "opcao",
    ),
    (
        "streamlit_mapa_utilizadores",
        "",
        "Streamlit - Utilizador Martelo=utilizador Streamlit, separados por ; "
        "(só quando a ligação pelo nome não chega; ex.: paulo=paulo_catarino)",
        "texto",
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
    for chave, valor, descricao, tipo in CONFIGURACOES:
        existe = connection.execute(
            sa.select(system_settings.c.chave).where(system_settings.c.chave == chave)
        ).first()
        if existe is None:
            connection.execute(
                system_settings.insert().values(
                    chave=chave,
                    valor=valor,
                    descricao=descricao,
                    tipo=tipo,
                    grupo="Streamlit",
                    ativo=True,
                )
            )


def downgrade() -> None:
    # Configurações potencialmente personalizadas: preservar em downgrade.
    pass
