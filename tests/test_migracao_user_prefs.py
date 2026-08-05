"""A migração 85 tem de trazer as preferências que já existiam.

Ninguém pode perder as suas escolhas ao atualizar: as chaves antigas da
`system_settings` (``<prefixo>:<user_id>``) passam a linhas da `user_prefs`,
com o utilizador na sua própria coluna.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import text

MIGRACAO = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260815_85_add_user_prefs.py"
)


@pytest.fixture()
def modulo():
    especificacao = importlib.util.spec_from_file_location("migracao_85", MIGRACAO)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def _preparar(session) -> None:
    """A tabela antiga com preferências de dois utilizadores e uma do sistema."""
    session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS system_settings "
            "(chave VARCHAR(120) PRIMARY KEY, valor TEXT)"
        )
    )
    session.execute(text("DELETE FROM system_settings"))
    for chave, valor in (
        ("producao_colunas:2", "colunas do dois"),
        ("producao_vistas:2", "vistas do dois"),
        ("producao_colunas:9", "colunas do nove"),
        ("producao_preparacao_validacoes:default", "sem sessão"),
        ("pasta_base_orcamentos", "\\\\SERVER_LE\\..."),  # do sistema: fica
    ):
        session.execute(
            text("INSERT INTO system_settings (chave, valor) VALUES (:c, :v)"),
            {"c": chave, "v": valor},
        )
    session.execute(text("DELETE FROM user_prefs"))
    session.commit()


def test_copia_as_preferencias_de_cada_utilizador(session, modulo, monkeypatch) -> None:
    _preparar(session)
    monkeypatch.setattr(modulo.op, "get_bind", lambda: session, raising=False)

    modulo._copiar_das_definicoes()
    session.commit()

    copiadas = {
        (linha.user_id, linha.chave): linha.valor
        for linha in session.execute(
            text("SELECT user_id, chave, valor FROM user_prefs")
        ).all()
    }
    assert copiadas[(2, "producao_colunas")] == "colunas do dois"
    assert copiadas[(2, "producao_vistas")] == "vistas do dois"
    assert copiadas[(9, "producao_colunas")] == "colunas do nove"


def test_o_sufixo_default_vai_para_o_utilizador_zero(
    session, modulo, monkeypatch
) -> None:
    _preparar(session)
    monkeypatch.setattr(modulo.op, "get_bind", lambda: session, raising=False)

    modulo._copiar_das_definicoes()
    session.commit()

    valor = session.execute(
        text(
            "SELECT valor FROM user_prefs "
            "WHERE user_id = 0 AND chave = 'producao_preparacao_validacoes'"
        )
    ).scalar()
    assert valor == "sem sessão"


def test_nao_leva_as_definicoes_do_sistema(session, modulo, monkeypatch) -> None:
    _preparar(session)
    monkeypatch.setattr(modulo.op, "get_bind", lambda: session, raising=False)

    modulo._copiar_das_definicoes()
    session.commit()

    chaves = [
        linha.chave
        for linha in session.execute(text("SELECT chave FROM user_prefs")).all()
    ]
    assert "pasta_base_orcamentos" not in chaves


def test_as_antigas_ficam_onde_estavam(session, modulo, monkeypatch) -> None:
    # Copiadas, não movidas: se algo correr mal, os valores ainda lá estão.
    _preparar(session)
    monkeypatch.setattr(modulo.op, "get_bind", lambda: session, raising=False)

    modulo._copiar_das_definicoes()
    session.commit()

    total = session.execute(text("SELECT COUNT(*) FROM system_settings")).scalar()
    assert total == 5
