"""Configuração da seleção de perfis pelo comprimento comercial."""
from alembic import op
import sqlalchemy as sa

revision = "20260912_113"
down_revision = "20260910_112"
branch_labels = None
depends_on = None


def upgrade():
    # A reparação pontual de uma base real pode acrescentar esta coluna antes
    # de executar migrações anteriores sem relação com perfis. Nesse caso,
    # a passagem posterior pela cadeia Alembic não deve tentar recriá-la.
    colunas = sa.inspect(op.get_bind()).get_columns("def_pecas")
    if not any(coluna["name"] == "selecao_perfil" for coluna in colunas):
        op.add_column("def_pecas", sa.Column("selecao_perfil", sa.String(20), nullable=False, server_default="AUTO"))


def downgrade():
    raise RuntimeError("Reversão destrutiva exige autorização explícita do utilizador.")
