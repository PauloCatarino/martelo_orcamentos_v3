"""Import checks for the DefPeca repository."""

from __future__ import annotations


def test_def_peca_repository_imports() -> None:
    from app.repositories.def_peca_repository import DefPecaRepository, DefPecaResumo

    assert DefPecaRepository is not None
    assert DefPecaResumo is not None


def test_def_peca_repository_has_biblioteca_method() -> None:
    from app.repositories.def_peca_repository import DefPecaRepository

    for method in ("list_all", "list_ativas_para_biblioteca"):
        assert hasattr(DefPecaRepository, method)
