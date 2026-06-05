"""Import checks for the Orcamento repository."""

from __future__ import annotations


def test_orcamento_repository_imports() -> None:
    from app.repositories.orcamento_repository import OrcamentoRepository, OrcamentoResumo

    assert OrcamentoRepository is not None
    assert OrcamentoResumo is not None
