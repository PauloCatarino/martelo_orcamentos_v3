"""Import checks for the Cliente repository."""

from __future__ import annotations


def test_cliente_repository_imports() -> None:
    from app.repositories.cliente_repository import (
        ClienteListaResumo,
        ClienteRepository,
    )

    assert ClienteRepository is not None
    assert ClienteListaResumo is not None
    assert hasattr(ClienteRepository, "list_temporarios")
    assert hasattr(ClienteRepository, "list_phc")
    assert hasattr(ClienteRepository, "list_todos")
    assert hasattr(ClienteRepository, "obter")
