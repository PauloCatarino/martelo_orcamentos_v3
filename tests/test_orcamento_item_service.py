"""Tests for the Orcamento item service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.services import orcamento_item_service as service_module


class _FakeRepository:
    rows: list[OrcamentoItemResumo] = []
    requested_versao_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_items_by_versao(self, orcamento_versao_id: int) -> list[OrcamentoItemResumo]:
        self.__class__.requested_versao_id = orcamento_versao_id
        return self.rows


def test_orcamento_item_service_returns_empty_list(monkeypatch) -> None:
    _FakeRepository.rows = []
    _FakeRepository.requested_versao_id = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)

    service = service_module.OrcamentoItemService(session=object())

    assert service.list_items_by_versao(10) == []
    assert _FakeRepository.requested_versao_id == 10


def test_orcamento_item_service_returns_repository_rows(monkeypatch) -> None:
    row = OrcamentoItemResumo(
        id=1,
        ordem=1,
        codigo="ITEM-001",
        item="Roupeiro",
        descricao="Teste",
        altura=Decimal("2400"),
        largura=Decimal("1800"),
        profundidade=Decimal("600"),
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("0"),
        preco_total=Decimal("0"),
    )
    _FakeRepository.rows = [row]
    _FakeRepository.requested_versao_id = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)

    service = service_module.OrcamentoItemService(session=object())

    assert service.list_items_by_versao(11) == [row]
    assert _FakeRepository.requested_versao_id == 11
