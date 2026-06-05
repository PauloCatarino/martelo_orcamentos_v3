"""Tests for the Orcamento service."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.repositories.orcamento_repository import OrcamentoResumo
from app.services import orcamento_service as service_module


class _FakeRepository:
    rows: list[OrcamentoResumo] = []

    def __init__(self, _session: object) -> None:
        pass

    def list_orcamentos(self) -> list[OrcamentoResumo]:
        return self.rows


def test_orcamento_service_returns_empty_list_when_repository_is_empty(monkeypatch) -> None:
    _FakeRepository.rows = []
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)

    service = service_module.OrcamentoService(session=object())

    assert service.list_orcamentos() == []


def test_orcamento_service_returns_repository_rows(monkeypatch) -> None:
    row = OrcamentoResumo(
        ano=2026,
        num_orcamento="260001",
        numero_versao=1,
        cliente_nome="Cliente Teste",
        obra="Obra Teste",
        estado="rascunho",
        preco_total=Decimal("123.45"),
        created_at=datetime(2026, 6, 5, 10, 30),
    )
    _FakeRepository.rows = [row]
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)

    service = service_module.OrcamentoService(session=object())

    assert service.list_orcamentos() == [row]
