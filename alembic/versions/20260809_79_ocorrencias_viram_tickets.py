"""Turn the obra diary into tickets: classification, state, owner, attachments."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260809_79"
down_revision: str | Sequence[str] | None = "20260808_78"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: Colunas novas de producao_ocorrencias, na ordem em que são criadas.
_COLUNAS_NOVAS = (
    "numero",
    "assunto",
    "tipo",
    "gravidade",
    "origem",
    "estado",
    "responsavel",
    "responsavel_membro_id",
    "custo_estimado",
    "resolvido_em",
    "resolvido_por",
    "updated_at",
    "enviado_em",
    "enviado_para",
    "enviado_via",
)


def upgrade() -> None:
    """Additive: equipa_membros, anexos e as colunas de classificação.

    Nada se perde: os registos que já existem passam a tickets de tipo "outro"
    e estado "aberto", e recebem número sequencial por ordem de escrita.
    """
    op.create_table(
        "equipa_membros",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        #: Endereço do Microsoft Teams — é ele que abre a conversa certa.
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column(
            "ativo", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("nome", name="uq_equipa_membros_nome"),
    )

    op.add_column(
        "producao_ocorrencias", sa.Column("numero", sa.Integer(), nullable=True)
    )
    op.add_column(
        "producao_ocorrencias", sa.Column("assunto", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "producao_ocorrencias",
        sa.Column("tipo", sa.String(length=40), nullable=True, server_default="outro"),
    )
    op.add_column(
        "producao_ocorrencias",
        sa.Column(
            "gravidade", sa.String(length=20), nullable=True, server_default="media"
        ),
    )
    op.add_column(
        "producao_ocorrencias",
        sa.Column(
            "origem", sa.String(length=20), nullable=True, server_default="cliente"
        ),
    )
    op.add_column(
        "producao_ocorrencias",
        sa.Column(
            "estado", sa.String(length=20), nullable=True, server_default="aberto"
        ),
    )
    op.add_column(
        "producao_ocorrencias",
        sa.Column("responsavel", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "producao_ocorrencias",
        sa.Column("responsavel_membro_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "producao_ocorrencias",
        sa.Column("custo_estimado", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "producao_ocorrencias", sa.Column("resolvido_em", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "producao_ocorrencias",
        sa.Column("resolvido_por", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "producao_ocorrencias", sa.Column("updated_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "producao_ocorrencias", sa.Column("enviado_em", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "producao_ocorrencias",
        sa.Column("enviado_para", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "producao_ocorrencias",
        sa.Column("enviado_via", sa.String(length=20), nullable=True),
    )

    op.create_foreign_key(
        "fk_producao_ocorrencias_membro",
        "producao_ocorrencias",
        "equipa_membros",
        ["responsavel_membro_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_producao_ocorrencias_tipo", "producao_ocorrencias", ["tipo"]
    )
    op.create_index(
        "ix_producao_ocorrencias_estado", "producao_ocorrencias", ["estado"]
    )

    op.create_table(
        "producao_ocorrencia_anexos",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "ocorrencia_id",
            sa.BigInteger(),
            sa.ForeignKey("producao_ocorrencias.id", ondelete="CASCADE"),
            nullable=False,
        ),
        #: Caminho na pasta da obra; a imagem não entra na base de dados.
        sa.Column("caminho", sa.String(length=1024), nullable=False),
        sa.Column("nome_original", sa.String(length=255), nullable=True),
        sa.Column("legenda", sa.String(length=255), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_producao_ocorrencia_anexos_ocorrencia",
        "producao_ocorrencia_anexos",
        ["ocorrencia_id", "ordem"],
    )

    _preencher_registos_antigos()


def _preencher_registos_antigos() -> None:
    """Give existing diary lines a tipo, an estado and a per-obra number.

    Numera por ordem de escrita dentro de cada obra, para o T1 do diário antigo
    ser mesmo o primeiro que foi escrito.
    """
    ligacao = op.get_bind()
    ligacao.execute(
        sa.text(
            "UPDATE producao_ocorrencias SET tipo = 'outro' WHERE tipo IS NULL"
        )
    )
    ligacao.execute(
        sa.text(
            "UPDATE producao_ocorrencias SET estado = 'aberto' WHERE estado IS NULL"
        )
    )
    ligacao.execute(
        sa.text(
            "UPDATE producao_ocorrencias SET gravidade = 'media' WHERE gravidade IS NULL"
        )
    )
    ligacao.execute(
        sa.text(
            "UPDATE producao_ocorrencias SET origem = 'cliente' WHERE origem IS NULL"
        )
    )

    linhas = ligacao.execute(
        sa.text(
            "SELECT id, producao_id FROM producao_ocorrencias "
            "ORDER BY producao_id, created_at, id"
        )
    ).fetchall()

    contadores: dict[int, int] = {}
    for identificador, producao_id in linhas:
        proximo = contadores.get(producao_id, 0) + 1
        contadores[producao_id] = proximo
        ligacao.execute(
            sa.text("UPDATE producao_ocorrencias SET numero = :n WHERE id = :i"),
            {"n": proximo, "i": identificador},
        )


def downgrade() -> None:
    op.drop_index(
        "ix_producao_ocorrencia_anexos_ocorrencia",
        table_name="producao_ocorrencia_anexos",
    )
    op.drop_table("producao_ocorrencia_anexos")

    op.drop_index("ix_producao_ocorrencias_estado", table_name="producao_ocorrencias")
    op.drop_index("ix_producao_ocorrencias_tipo", table_name="producao_ocorrencias")
    op.drop_constraint(
        "fk_producao_ocorrencias_membro", "producao_ocorrencias", type_="foreignkey"
    )
    for coluna in reversed(_COLUNAS_NOVAS):
        op.drop_column("producao_ocorrencias", coluna)

    op.drop_table("equipa_membros")
