"""A migração que cria os componentes das matérias-primas compostas."""

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
    / "20260903_104_componentes_das_materias_primas.py"
)


def _carregar_migracao():
    spec = importlib.util.spec_from_file_location("migracao_componentes_mp", MIGRACAO)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _base() -> sa.Engine:
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table(
        "def_materias_primas",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ref_le", sa.String(100)),
        sa.Column("descricao", sa.Text, nullable=False),
    )
    sa.Table(
        "users",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    )
    metadata.create_all(engine)
    return engine


def _tabelas(connection) -> set[str]:
    return set(sa.inspect(connection).get_table_names())


def _colunas(connection, tabela: str) -> set[str]:
    return {c["name"] for c in sa.inspect(connection).get_columns(tabela)}


def test_cria_a_tabela_e_o_nome_imos_e_pode_correr_duas_vezes() -> None:
    engine = _base()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        # Correr outra vez não pode rebentar: já está tudo lá.
        migracao.upgrade()
        tabelas = _tabelas(connection)
        colunas_mp = _colunas(connection, "def_materias_primas")
        colunas_comp = _colunas(connection, "def_materias_primas_componentes")

    engine.dispose()
    assert "def_materias_primas_componentes" in tabelas
    assert "nome_imos" in colunas_mp
    # As três chaves da ponte, mais a referência do fornecedor como veio.
    assert {"nome_imos", "ref_phc", "ref_fornecedor_norm", "ref_fornecedor"} <= colunas_comp
    assert {"papel", "quantidade", "ordem", "ativo"} <= colunas_comp
    assert {"criado_por_id", "alterado_por_id", "created_at", "updated_at"} <= colunas_comp


def test_os_valores_por_omissao_sao_os_do_caso_normal() -> None:
    engine = _base()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO def_materias_primas (ref_le, descricao) "
                "VALUES ('FER0015', 'DOBRADICA BLUM RETA 107 (SOFT CLOSE) + CALCO H0')"
            )
        )
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        connection.execute(
            sa.text(
                "INSERT INTO def_materias_primas_componentes "
                "(materia_prima_id, nome_imos) VALUES (1, 'BL_CALCO_H0_174H7100E')"
            )
        )
        linha = connection.execute(
            sa.text(
                "SELECT papel, quantidade, ordem, ativo, nome_imos "
                "FROM def_materias_primas_componentes"
            )
        ).mappings().one()

    engine.dispose()
    # Um componente novo nasce SECUNDÁRIO: só quem manda na contagem é que se
    # declara principal, de propósito.
    assert linha["papel"] == "SECUNDARIO"
    assert float(linha["quantidade"]) == 1.0
    assert linha["ordem"] == 1
    assert linha["ativo"] in (1, True)
    assert linha["nome_imos"] == "BL_CALCO_H0_174H7100E"


def test_downgrade_desfaz_tudo_e_pode_correr_sem_nada() -> None:
    engine = _base()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        migracao.downgrade()
        migracao.downgrade()
        tabelas = _tabelas(connection)
        colunas_mp = _colunas(connection, "def_materias_primas")

    engine.dispose()
    assert "def_materias_primas_componentes" not in tabelas
    assert "nome_imos" not in colunas_mp
