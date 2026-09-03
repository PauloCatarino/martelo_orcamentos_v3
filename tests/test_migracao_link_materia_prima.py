"""A migração que dá um link à ficha da matéria-prima."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRACAO = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260903_102_link_na_materia_prima.py"
)


def _carregar_migracao():
    spec = importlib.util.spec_from_file_location("migracao_link_materia_prima", MIGRACAO)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _base_com_materias_primas() -> sa.Engine:
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table(
        "def_materias_primas",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ref_le", sa.String(100)),
        sa.Column("descricao", sa.Text, nullable=False),
    )
    metadata.create_all(engine)
    return engine


def _colunas(connection) -> set[str]:
    inspector = sa.inspect(connection)
    return {coluna["name"] for coluna in inspector.get_columns("def_materias_primas")}


def test_migracao_acrescenta_a_coluna_e_pode_correr_duas_vezes() -> None:
    engine = _base_com_materias_primas()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        # Correr outra vez não pode rebentar: a coluna já lá está.
        migracao.upgrade()
        colunas = _colunas(connection)

    engine.dispose()
    assert "link" in colunas


def test_migracao_nao_apaga_os_materiais_que_ja_existem() -> None:
    engine = _base_com_materias_primas()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO def_materias_primas (ref_le, descricao) "
                "VALUES ('FER0016', 'DOBRADIÇA BLUM RETA 107º (MOLA) + CALÇO H0')"
            )
        )
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        linhas = connection.execute(
            sa.text("SELECT ref_le, link FROM def_materias_primas")
        ).mappings().all()

    engine.dispose()
    assert len(linhas) == 1
    assert linhas[0]["ref_le"] == "FER0016"
    # Os materiais que já existiam ficam sem link, que é o normal.
    assert linhas[0]["link"] is None


def test_downgrade_tira_a_coluna_e_pode_correr_sem_ela() -> None:
    engine = _base_com_materias_primas()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        migracao.downgrade()
        # Sem a coluna, voltar a descer não pode rebentar.
        migracao.downgrade()
        colunas = _colunas(connection)

    engine.dispose()
    assert "link" not in colunas
