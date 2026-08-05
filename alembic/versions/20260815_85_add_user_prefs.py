"""Tabela user_prefs: preferencias pessoais fora da system_settings."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260815_85"
down_revision: str | Sequence[str] | None = "20260814_84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: Prefixos das chaves que eram preferencias pessoais guardadas na
#: `system_settings`. O que vem a seguir aos dois pontos e' o id do utilizador.
PREFIXOS = (
    "producao_preparacao_validacoes",
    "producao_email_projeto",
    "producao_impressao_prioridades",
    "producao_colunas",
    "producao_vistas",
)


def upgrade() -> None:
    """Separar o gosto de cada um do que e' da casa.

    A `system_settings` guarda o que e' do SISTEMA — caminhos do servidor,
    credenciais do PHC/iMos, o interruptor da escrita no iMos — e por isso o
    login por utilizador trancou-a a so'-leitura para quem nao e' administrador.
    So' que as escolhas PESSOAIS estavam la' dentro, e ficaram refens dessa
    tranca: a Andreia (conta normal) levava

        (1142) INSERT command denied to user 'Andreia' for table 'system_settings'

    ao gravar as Preferencias da Preparacao. O mesmo valia para a ordem de
    impressao, as colunas e as vistas da Producao.

    As linhas que ja' existem sao COPIADAS para ca' (nao movidas): ninguem perde
    o que escolheu, e se algo correr mal os valores antigos ainda la' estao.
    """
    op.create_table(
        "user_prefs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("chave", sa.String(length=120), nullable=False),
        sa.Column("valor", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "chave", name="uq_user_prefs_user_chave"),
    )
    op.create_index("ix_user_prefs_user_id", "user_prefs", ["user_id"])

    _copiar_das_definicoes()


def _copiar_das_definicoes() -> None:
    """Trazer as preferencias que estavam na `system_settings`.

    A chave antiga era `<prefixo>:<user_id>`; aqui separa-se nas duas colunas.
    O sufixo "default" (sem sessao) fica no utilizador 0. Chaves com sufixo que
    nao seja um numero sao ignoradas — nao ha' utilizador a quem as atribuir.
    """
    ligacao = op.get_bind()
    for prefixo in PREFIXOS:
        linhas = ligacao.execute(
            sa.text(
                "SELECT chave, valor FROM system_settings WHERE chave LIKE :padrao"
            ),
            {"padrao": f"{prefixo}:%"},
        ).all()

        for chave, valor in linhas:
            sufixo = str(chave).split(":", 1)[1] if ":" in str(chave) else ""
            if sufixo == "default":
                user_id = 0
            elif sufixo.isdigit():
                user_id = int(sufixo)
            else:
                continue

            ligacao.execute(
                sa.text(
                    "INSERT INTO user_prefs (user_id, chave, valor) "
                    "VALUES (:user_id, :chave, :valor)"
                ),
                {"user_id": user_id, "chave": prefixo, "valor": valor},
            )


def downgrade() -> None:
    """Deitar fora a tabela. Os valores antigos continuam na system_settings."""
    op.drop_index("ix_user_prefs_user_id", table_name="user_prefs")
    op.drop_table("user_prefs")
