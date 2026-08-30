"""Marca do último recálculo do custeio, para os relatórios não recalcularem.

Até aqui, cada exportação dos Relatórios (PDF, Excel, Excel PHC, Resumo de
Custos, Plano de Corte) voltava a correr a pipeline COMPLETA do custeio dos
itens todos antes de escrever o ficheiro -- e a própria página já a tinha
corrido ao abrir. No orçamento 260868 isso são ~27 segundos e ~27 000 consultas
à base de cada vez: abrir os relatórios e exportar quatro formatos custava cinco
vezes o mesmo cálculo sobre dados que não mudaram entre eles.

O custeio atualiza-se onde tem de se atualizar: no botão "Atualizar Custos" do
orçamento. Os relatórios passam a LER o que está gravado. Para nunca sair um
relatório com números velhos, a versão guarda aqui um retrato do estado do
custeio no momento do último recálculo; se o retrato de hoje for outro, os
relatórios dizem-no à cara do utilizador e oferecem o recálculo.

As duas colunas ficam a NULL nos orçamentos que já existem -- o que os marca
como "por confirmar" até ao primeiro recálculo, que é o lado seguro.

Revision ID: 20260831_99
Revises: 20260830_98
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_99"
down_revision: str | Sequence[str] | None = "20260830_98"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "orcamento_versoes"
COLUNAS = (
    ("custeio_impressao_digital", sa.String(64)),
    ("custeio_recalculado_em", sa.DateTime()),
)


def _colunas(inspector) -> set[str]:
    return {col["name"] for col in inspector.get_columns(TABELA)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABELA not in inspector.get_table_names():
        return

    existentes = _colunas(inspector)
    for nome, tipo in COLUNAS:
        if nome in existentes:
            continue
        op.add_column(TABELA, sa.Column(nome, tipo, nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABELA not in inspector.get_table_names():
        return

    existentes = _colunas(inspector)
    for nome, _tipo in COLUNAS:
        if nome in existentes:
            op.drop_column(TABELA, nome)
