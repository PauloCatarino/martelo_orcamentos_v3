"""Tests for the Orcamento item service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.services import orcamento_item_service as service_module


class _FakeRepository:
    rows: list[OrcamentoItemResumo] = []
    requested_versao_id: int | None = None
    next_order = 1
    next_order_versao_id: int | None = None
    created_payload: dict[str, object] | None = None
    item_by_id: OrcamentoItemResumo | None = None
    requested_item_id: int | None = None
    updated_payload: dict[str, object] | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_items_by_versao(self, orcamento_versao_id: int) -> list[OrcamentoItemResumo]:
        self.__class__.requested_versao_id = orcamento_versao_id
        return self.rows

    def get_next_ordem(self, orcamento_versao_id: int) -> int:
        self.__class__.next_order_versao_id = orcamento_versao_id
        return self.next_order

    def create_item(self, **kwargs) -> OrcamentoItemResumo:
        self.__class__.created_payload = kwargs
        return OrcamentoItemResumo(
            id=99,
            ordem=kwargs["ordem"],
            codigo=kwargs["codigo"],
            item=kwargs["item"],
            descricao=kwargs["descricao"],
            altura=kwargs["altura"],
            largura=kwargs["largura"],
            profundidade=kwargs["profundidade"],
            quantidade=kwargs["quantidade"],
            unidade=kwargs["unidade"],
            preco_unitario=kwargs["preco_unitario"],
            preco_total=kwargs["preco_total"],
        )

    def get_item_by_id(self, item_id: int) -> OrcamentoItemResumo | None:
        self.__class__.requested_item_id = item_id
        return self.item_by_id

    def update_item(self, **kwargs) -> OrcamentoItemResumo:
        self.__class__.updated_payload = kwargs
        return OrcamentoItemResumo(
            id=kwargs["item_id"],
            ordem=2,
            codigo=kwargs["codigo"],
            item=kwargs["item"],
            descricao=kwargs["descricao"],
            altura=kwargs["altura"],
            largura=kwargs["largura"],
            profundidade=kwargs["profundidade"],
            quantidade=kwargs["quantidade"],
            unidade=kwargs["unidade"],
            preco_unitario=kwargs["preco_unitario"],
            preco_total=kwargs["preco_total"],
        )


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


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


def test_orcamento_item_service_cria_item_com_proxima_ordem_e_preco_total(monkeypatch) -> None:
    _FakeRepository.next_order = 3
    _FakeRepository.next_order_versao_id = None
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.OrcamentoItemService(session=session)
    result = service.criar_item_simples(
        service_module.CriarOrcamentoItemSimplesData(
            orcamento_versao_id=20,
            codigo="ITEM-003",
            item="Roupeiro",
            descricao="Teste",
            altura=Decimal("2400"),
            largura=Decimal("1800"),
            profundidade=Decimal("600"),
            quantidade=Decimal("2"),
            unidade="un",
            preco_unitario=Decimal("15.50"),
        )
    )

    assert _FakeRepository.next_order_versao_id == 20
    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["ordem"] == 3
    assert _FakeRepository.created_payload["preco_total"] == Decimal("31.00")
    assert result.preco_total == Decimal("31.00")
    assert session.committed is True


def test_orcamento_item_service_valida_item_obrigatorio(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    service = service_module.OrcamentoItemService(session=_FakeSession())

    try:
        service.criar_item_simples(
            service_module.CriarOrcamentoItemSimplesData(
                orcamento_versao_id=20,
                codigo=None,
                item="",
                descricao=None,
                altura=None,
                largura=None,
                profundidade=None,
                quantidade=Decimal("1"),
                unidade="un",
                preco_unitario=Decimal("0"),
            )
        )
    except ValueError as error:
        assert "item" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_orcamento_item_service_valida_quantidade_positiva(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    service = service_module.OrcamentoItemService(session=_FakeSession())

    try:
        service.criar_item_simples(
            service_module.CriarOrcamentoItemSimplesData(
                orcamento_versao_id=20,
                codigo=None,
                item="Roupeiro",
                descricao=None,
                altura=None,
                largura=None,
                profundidade=None,
                quantidade=Decimal("0"),
                unidade="un",
                preco_unitario=Decimal("0"),
            )
        )
    except ValueError as error:
        assert "quantidade" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_orcamento_item_service_obtem_item_por_id(monkeypatch) -> None:
    row = OrcamentoItemResumo(
        id=5,
        ordem=2,
        codigo="ITEM-005",
        item="Mesa",
        descricao="Teste",
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("10"),
        preco_total=Decimal("10"),
    )
    _FakeRepository.item_by_id = row
    _FakeRepository.requested_item_id = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)

    service = service_module.OrcamentoItemService(session=object())

    assert service.get_item_by_id(5) == row
    assert _FakeRepository.requested_item_id == 5


def test_orcamento_item_service_edita_item_e_recalcula_preco_total(monkeypatch) -> None:
    _FakeRepository.updated_payload = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.OrcamentoItemService(session=session)
    result = service.editar_item_simples(
        8,
        service_module.EditarOrcamentoItemSimplesData(
            codigo="ITEM-008",
            item="Mesa",
            descricao="Editado",
            altura=None,
            largura=None,
            profundidade=None,
            quantidade=Decimal("3"),
            unidade="un",
            preco_unitario=Decimal("12.50"),
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["item_id"] == 8
    assert _FakeRepository.updated_payload["preco_total"] == Decimal("37.50")
    assert result.preco_total == Decimal("37.50")
    assert session.committed is True
