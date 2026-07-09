"""Tests for the database-error message helper."""

from __future__ import annotations

from app.ui.helpers.erros import causa_tecnica, mensagem_erro_bd


class _FakeOrig(Exception):
    """Stand-in for a DBAPI error carried in SQLAlchemyError.orig."""


def _erro_com_orig(texto: str) -> Exception:
    error = Exception("(pymysql.err.OperationalError) wrapper")
    error.orig = _FakeOrig(texto)
    return error


def test_causa_usa_orig_quando_existe() -> None:
    error = _erro_com_orig("1054 (42S22): Unknown column 'prioridade' in 'field list'")

    assert (
        causa_tecnica(error)
        == "1054 (42S22): Unknown column 'prioridade' in 'field list'"
    )


def test_causa_usa_str_quando_sem_orig() -> None:
    error = ValueError("prioridade deve ser um inteiro >= 1")

    assert causa_tecnica(error) == "prioridade deve ser um inteiro >= 1"


def test_causa_apenas_primeira_linha() -> None:
    error = _erro_com_orig("no such column: prioridade\nSQL: SELECT ...\n[params]")

    assert causa_tecnica(error) == "no such column: prioridade"


def test_mensagem_combina_prefixo_e_causa() -> None:
    error = _erro_com_orig("no such column: prioridade")

    assert mensagem_erro_bd("Não foi possível guardar a linha.", error) == (
        "Não foi possível guardar a linha. (no such column: prioridade)"
    )


def test_mensagem_so_prefixo_quando_sem_causa() -> None:
    error = _erro_com_orig("   ")

    assert mensagem_erro_bd("Não foi possível guardar a linha.", error) == (
        "Não foi possível guardar a linha."
    )
