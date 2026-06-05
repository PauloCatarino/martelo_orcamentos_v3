"""Import checks for the DefPecaComponente repository."""

from __future__ import annotations


def test_def_peca_componente_repository_imports() -> None:
    from app.repositories.def_peca_componente_repository import (
        DefPecaComponenteRepository,
        DefPecaComponenteResumo,
    )

    assert DefPecaComponenteRepository is not None
    assert DefPecaComponenteResumo is not None
