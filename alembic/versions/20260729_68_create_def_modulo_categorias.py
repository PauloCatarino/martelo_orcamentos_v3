"""Create the manageable module-library categories table (phase 6)."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260729_68"
down_revision: str | Sequence[str] | None = "20260728_67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_SEED = (
    ("ROUPEIROS", "Roupeiros"),
    ("COZINHAS", "Cozinhas"),
    ("MOVEIS_WC", "Móveis WC"),
    ("OUTROS", "Outros"),
)


def upgrade() -> None:
    """Additive migration: categories table seeded with the fixed set.

    Modules keep referencing categories by codigo (string), so every existing
    module is preserved untouched. Any category code already used by a module
    but missing from the seed is imported as its own (active) category.
    """
    op.create_table(
        "def_modulo_categorias",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(60), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("codigo", name="uq_def_modulo_categorias_codigo"),
    )

    connection = op.get_bind()
    for codigo, nome in _SEED:
        connection.execute(
            sa.text(
                "INSERT INTO def_modulo_categorias (codigo, nome, ativo) "
                "VALUES (:codigo, :nome, 1)"
            ),
            {"codigo": codigo, "nome": nome},
        )

    # Import any legacy/unknown category code already used by a module.
    connection.execute(
        sa.text(
            """
            INSERT INTO def_modulo_categorias (codigo, nome, ativo)
            SELECT DISTINCT m.categoria, m.categoria, 1
            FROM def_modulos m
            WHERE m.categoria IS NOT NULL
              AND TRIM(m.categoria) <> ''
              AND m.categoria NOT IN (
                  SELECT c.codigo FROM def_modulo_categorias c
              )
            """
        )
    )


def downgrade() -> None:
    """Remove the categories table (modules keep their category codes)."""
    op.drop_table("def_modulo_categorias")
