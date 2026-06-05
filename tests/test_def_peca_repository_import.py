"""Import checks for the DefPeca repository."""

from __future__ import annotations


def test_def_peca_repository_imports() -> None:
    from app.repositories.def_peca_repository import DefPecaRepository, DefPecaResumo

    assert DefPecaRepository is not None
    assert DefPecaResumo is not None
