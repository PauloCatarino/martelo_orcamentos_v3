"""Piloto aditivo do assistente IA para roupeiros de abrir."""

from __future__ import annotations
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260816_86"
down_revision: str | Sequence[str] | None = "20260815_85"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("def_modulos", sa.Column("largura_min_mm", sa.Numeric(12, 3), nullable=True))
    op.add_column("def_modulos", sa.Column("largura_preferida_mm", sa.Numeric(12, 3), nullable=True))
    op.add_column("def_modulos", sa.Column("largura_max_mm", sa.Numeric(12, 3), nullable=True))
    op.add_column("def_modulos", sa.Column("posicao_roupeiro", sa.String(20), nullable=True))
    op.add_column("def_modulos", sa.Column("permite_espelhar", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("def_modulos", sa.Column("tipo_item_compativel", sa.String(50), nullable=True))
    op.create_index("ix_def_modulos_tipo_item_compativel", "def_modulos", ["tipo_item_compativel"])

    op.create_table(
        "def_modulo_caracteristicas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("def_modulo_id", sa.BigInteger(), sa.ForeignKey("def_modulos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False, server_default="1"),
        sa.UniqueConstraint("def_modulo_id", "codigo", name="uq_def_mod_car_mod_cod"),
    )
    op.create_index("ix_def_modulo_caracteristicas_def_modulo_id", "def_modulo_caracteristicas", ["def_modulo_id"])
    op.create_index("ix_def_modulo_caracteristicas_codigo", "def_modulo_caracteristicas", ["codigo"])

    op.create_table(
        "ia_orcamento_analises",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("orcamento_item_id", sa.BigInteger(), sa.ForeignKey("orcamento_items.id"), nullable=False),
        sa.Column("documento_path", sa.String(1000), nullable=False),
        sa.Column("documento_hash", sa.String(64), nullable=False),
        sa.Column("pagina", sa.Integer(), nullable=False),
        sa.Column("zona_json", sa.Text(), nullable=True),
        sa.Column("fornecedor", sa.String(50), nullable=False),
        sa.Column("modelo", sa.String(150), nullable=False),
        sa.Column("resultado_json", sa.Text(), nullable=False),
        sa.Column("altura_confirmada_mm", sa.Numeric(12, 3), nullable=True),
        sa.Column("largura_confirmada_mm", sa.Numeric(12, 3), nullable=True),
        sa.Column("profundidade_confirmada_mm", sa.Numeric(12, 3), nullable=True),
        sa.Column("caracteristicas_confirmadas_json", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(30), nullable=False, server_default="ANALISADA"),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    for nome, colunas in (
        ("ix_ia_orcamento_analises_user_id", ["user_id"]),
        ("ix_ia_orcamento_analises_orcamento_item_id", ["orcamento_item_id"]),
        ("ix_ia_orcamento_analises_documento_hash", ["documento_hash"]),
    ):
        op.create_index(nome, "ia_orcamento_analises", colunas)

    op.create_table(
        "ia_orcamento_propostas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("analise_id", sa.BigInteger(), sa.ForeignKey("ia_orcamento_analises.id"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("posicao_top3", sa.Integer(), nullable=False),
        sa.Column("pontuacao", sa.Float(), nullable=False),
        sa.Column("explicacao", sa.Text(), nullable=True),
        sa.Column("proposta_original_json", sa.Text(), nullable=False),
        sa.Column("correcoes_json", sa.Text(), nullable=True),
        sa.Column("decisao", sa.String(30), nullable=False, server_default="PENDENTE"),
        sa.Column("motivo_rejeicao", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ia_orcamento_propostas_analise_id", "ia_orcamento_propostas", ["analise_id"])
    op.create_index("ix_ia_orcamento_propostas_user_id", "ia_orcamento_propostas", ["user_id"])

    op.create_table(
        "ia_orcamento_proposta_modulos",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("proposta_id", sa.BigInteger(), sa.ForeignKey("ia_orcamento_propostas.id"), nullable=False),
        sa.Column("def_modulo_id", sa.BigInteger(), sa.ForeignKey("def_modulos.id"), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("codigo_snapshot", sa.String(100), nullable=False),
        sa.Column("nome_snapshot", sa.String(150), nullable=False),
        sa.Column("largura_mm", sa.Numeric(12, 3), nullable=False),
        sa.Column("espelhado", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_index("ix_ia_prop_mod_proposta_id", "ia_orcamento_proposta_modulos", ["proposta_id"])
    op.create_index("ix_ia_prop_mod_def_modulo_id", "ia_orcamento_proposta_modulos", ["def_modulo_id"])

    op.add_column("orcamento_item_modulos", sa.Column("origem", sa.String(20), nullable=False, server_default="MANUAL"))
    op.add_column("orcamento_item_modulos", sa.Column("def_modulo_id", sa.BigInteger(), nullable=True))
    op.add_column("orcamento_item_modulos", sa.Column("ia_proposta_modulo_id", sa.BigInteger(), nullable=True))
    op.add_column("orcamento_item_modulos", sa.Column("codigo_origem_snapshot", sa.String(100), nullable=True))
    op.add_column("orcamento_item_modulos", sa.Column("nome_origem_snapshot", sa.String(150), nullable=True))
    op.create_foreign_key("fk_oim_def_modulo", "orcamento_item_modulos", "def_modulos", ["def_modulo_id"], ["id"])
    op.create_foreign_key("fk_oim_ia_prop_mod", "orcamento_item_modulos", "ia_orcamento_proposta_modulos", ["ia_proposta_modulo_id"], ["id"])
    op.create_index("ix_orcamento_item_modulos_def_modulo_id", "orcamento_item_modulos", ["def_modulo_id"])
    op.create_index("ix_orcamento_item_modulos_ia_proposta_modulo_id", "orcamento_item_modulos", ["ia_proposta_modulo_id"])

    _garantir_configuracao("provedor_visao_roupeiros", "Fornecedor de visão para roupeiros (openai / local)", "openai")
    _garantir_configuracao("modelo_openai_visao_roupeiros", "Modelo OpenAI de visão para roupeiros", "gpt-5.2")
    _garantir_configuracao("modelo_local_visao_roupeiros", "Modelo local de visão para roupeiros (Ollama)", "")
    _garantir_configuracao("endpoint_local_visao_roupeiros", "Endpoint local de visão para roupeiros", "http://localhost:11434")


def _garantir_configuracao(chave: str, descricao: str, valor: str) -> None:
    """Cria a configuração apenas quando ainda não existe; nunca altera escolhas atuais."""
    ligacao = op.get_bind()
    existe = ligacao.execute(
        sa.text("SELECT id FROM system_settings WHERE chave = :chave"), {"chave": chave}
    ).first()
    if existe is None:
        ligacao.execute(
            sa.text(
                "INSERT INTO system_settings "
                "(chave, valor, descricao, tipo, grupo, ativo, created_at, updated_at) "
                "VALUES (:chave, :valor, :descricao, 'texto', 'IA Roupeiros', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"chave": chave, "valor": valor, "descricao": descricao},
        )


def downgrade() -> None:
    """Remove apenas a estrutura aditiva do piloto autorizado.

    Os registos de ``orcamento_item_modulos`` e respetivas linhas de custeio
    permanecem; perdem somente os metadados que indicavam a origem IA.
    """
    op.drop_index(
        "ix_orcamento_item_modulos_ia_proposta_modulo_id",
        table_name="orcamento_item_modulos",
    )
    op.drop_index(
        "ix_orcamento_item_modulos_def_modulo_id",
        table_name="orcamento_item_modulos",
    )
    op.drop_constraint(
        "fk_oim_ia_prop_mod", "orcamento_item_modulos", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_oim_def_modulo", "orcamento_item_modulos", type_="foreignkey"
    )
    op.drop_column("orcamento_item_modulos", "nome_origem_snapshot")
    op.drop_column("orcamento_item_modulos", "codigo_origem_snapshot")
    op.drop_column("orcamento_item_modulos", "ia_proposta_modulo_id")
    op.drop_column("orcamento_item_modulos", "def_modulo_id")
    op.drop_column("orcamento_item_modulos", "origem")

    op.drop_index(
        "ix_ia_prop_mod_def_modulo_id",
        table_name="ia_orcamento_proposta_modulos",
    )
    op.drop_index(
        "ix_ia_prop_mod_proposta_id",
        table_name="ia_orcamento_proposta_modulos",
    )
    op.drop_table("ia_orcamento_proposta_modulos")

    op.drop_index(
        "ix_ia_orcamento_propostas_user_id",
        table_name="ia_orcamento_propostas",
    )
    op.drop_index(
        "ix_ia_orcamento_propostas_analise_id",
        table_name="ia_orcamento_propostas",
    )
    op.drop_table("ia_orcamento_propostas")

    op.drop_index(
        "ix_ia_orcamento_analises_documento_hash",
        table_name="ia_orcamento_analises",
    )
    op.drop_index(
        "ix_ia_orcamento_analises_orcamento_item_id",
        table_name="ia_orcamento_analises",
    )
    op.drop_index(
        "ix_ia_orcamento_analises_user_id",
        table_name="ia_orcamento_analises",
    )
    op.drop_table("ia_orcamento_analises")

    op.drop_index(
        "ix_def_modulo_caracteristicas_codigo",
        table_name="def_modulo_caracteristicas",
    )
    op.drop_index(
        "ix_def_modulo_caracteristicas_def_modulo_id",
        table_name="def_modulo_caracteristicas",
    )
    op.drop_table("def_modulo_caracteristicas")

    op.drop_index(
        "ix_def_modulos_tipo_item_compativel", table_name="def_modulos"
    )
    op.drop_column("def_modulos", "tipo_item_compativel")
    op.drop_column("def_modulos", "permite_espelhar")
    op.drop_column("def_modulos", "posicao_roupeiro")
    op.drop_column("def_modulos", "largura_max_mm")
    op.drop_column("def_modulos", "largura_preferida_mm")
    op.drop_column("def_modulos", "largura_min_mm")

    op.execute(
        sa.text(
            "DELETE FROM system_settings WHERE chave IN ("
            "'provedor_visao_roupeiros', "
            "'modelo_openai_visao_roupeiros', "
            "'modelo_local_visao_roupeiros', "
            "'endpoint_local_visao_roupeiros'"
            ")"
        )
    )
