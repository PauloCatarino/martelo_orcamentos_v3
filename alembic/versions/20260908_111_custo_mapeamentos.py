"""Mapeamentos de custos fora das configurações protegidas.

As associações antigas continuam a ser lidas, sem remover configurações.
"""
from alembic import op
import sqlalchemy as sa

revision = '20260908_111'
down_revision = '20260907_110'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('lista_material_custo_mapeamentos',
                    sa.Column('chave', sa.String(100), primary_key=True),
                    sa.Column('valor', sa.Text(), nullable=False))


def downgrade():
    raise RuntimeError('Reversão automática desativada para preservar os mapeamentos de custos.')
