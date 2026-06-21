"""Tests for the Orcamento item service."""

from __future__ import annotations

from decimal import Decimal

from app.domain.precos import BlocosCusto, MargensOrcamento
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
    delete_result = True
    deleted_item_id: int | None = None
    sum_total = Decimal("0")
    summed_versao_id: int | None = None
    updated_versao_total: tuple[int, Decimal] | None = None

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
            orcamento_versao_id=kwargs["orcamento_versao_id"],
            ordem=kwargs["ordem"],
            codigo=kwargs["codigo"],
            tipo_item=kwargs["tipo_item"],
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
            orcamento_versao_id=20,
            ordem=2,
            codigo=kwargs["codigo"],
            tipo_item=kwargs["tipo_item"],
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

    def delete_item(self, item_id: int) -> bool:
        self.__class__.deleted_item_id = item_id
        return self.delete_result

    def sum_preco_total_by_versao(self, orcamento_versao_id: int) -> Decimal:
        self.__class__.summed_versao_id = orcamento_versao_id
        return self.sum_total

    def update_preco_total_versao(self, orcamento_versao_id: int, preco_total: Decimal) -> bool:
        self.__class__.updated_versao_total = (orcamento_versao_id, preco_total)
        return True

    precos_escritos: list[int] = []

    def get_margens_versao(self, orcamento_versao_id: int) -> MargensOrcamento:
        return MargensOrcamento()

    def update_preco_item(
        self, item_id: int, preco_unitario: Decimal, preco_total: Decimal
    ) -> bool:
        self.__class__.precos_escritos.append(item_id)
        return True

    tipo_producao_default: str | None = "STD"
    updated_tipo_default: tuple | None = None
    updated_tipo_item: tuple | None = None

    def get_tipo_producao_default(self, orcamento_versao_id: int) -> str | None:
        return self.tipo_producao_default

    def update_tipo_producao_default(
        self, orcamento_versao_id: int, tipo_producao: str
    ) -> bool:
        self.__class__.updated_tipo_default = (orcamento_versao_id, tipo_producao)
        return True

    def update_tipo_producao(self, item_id: int, tipo_producao: str | None) -> bool:
        self.__class__.updated_tipo_item = (item_id, tipo_producao)
        return True


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
        orcamento_versao_id=11,
        ordem=1,
        codigo="ITEM-001",
        tipo_item="ROUPEIRO_CORRER",
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
    _FakeRepository.sum_total = Decimal("75.25")
    _FakeRepository.summed_versao_id = None
    _FakeRepository.updated_versao_total = None
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
            tipo_item="ROUPEIRO_ABRIR",
        )
    )

    assert _FakeRepository.next_order_versao_id == 20
    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["ordem"] == 3
    assert _FakeRepository.created_payload["tipo_item"] == "ROUPEIRO_ABRIR"
    assert _FakeRepository.created_payload["preco_total"] == Decimal("31.00")
    assert _FakeRepository.summed_versao_id == 20
    assert _FakeRepository.updated_versao_total == (20, Decimal("75.25"))
    assert result.preco_total == Decimal("31.00")
    assert result.tipo_item == "ROUPEIRO_ABRIR"
    assert session.committed is True


def test_orcamento_item_service_usa_tipo_outro_por_defeito(monkeypatch) -> None:
    _FakeRepository.next_order = 1
    _FakeRepository.created_payload = None
    _FakeRepository.sum_total = Decimal("10.00")
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)

    service = service_module.OrcamentoItemService(session=_FakeSession())
    service.criar_item_simples(
        service_module.CriarOrcamentoItemSimplesData(
            orcamento_versao_id=20,
            codigo=None,
            item="Item Sem Tipo",
            descricao=None,
            altura=None,
            largura=None,
            profundidade=None,
            quantidade=Decimal("1"),
            unidade="un",
            preco_unitario=Decimal("10"),
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["tipo_item"] == "OUTRO"


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
        orcamento_versao_id=20,
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
    _FakeRepository.sum_total = Decimal("50.00")
    _FakeRepository.summed_versao_id = None
    _FakeRepository.updated_versao_total = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.OrcamentoItemService(session=session)
    result = service.editar_item_simples(
        8,
        service_module.EditarOrcamentoItemSimplesData(
            codigo="ITEM-008",
            tipo_item="MOVEL_WC",
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
    assert _FakeRepository.updated_payload["tipo_item"] == "MOVEL_WC"
    assert _FakeRepository.updated_payload["preco_total"] == Decimal("37.50")
    assert _FakeRepository.summed_versao_id == 20
    assert _FakeRepository.updated_versao_total == (20, Decimal("50.00"))
    assert result.preco_total == Decimal("37.50")
    assert result.tipo_item == "MOVEL_WC"
    assert session.committed is True


def test_orcamento_item_service_remove_item_existente(monkeypatch) -> None:
    _FakeRepository.item_by_id = OrcamentoItemResumo(
        id=12,
        orcamento_versao_id=21,
        ordem=1,
        codigo="ITEM-012",
        item="Mesa",
        descricao=None,
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("10"),
        preco_total=Decimal("10"),
    )
    _FakeRepository.delete_result = True
    _FakeRepository.deleted_item_id = None
    _FakeRepository.sum_total = Decimal("0")
    _FakeRepository.summed_versao_id = None
    _FakeRepository.updated_versao_total = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.OrcamentoItemService(session=session)

    assert service.remover_item(12) is True
    assert _FakeRepository.deleted_item_id == 12
    assert _FakeRepository.summed_versao_id == 21
    assert _FakeRepository.updated_versao_total == (21, Decimal("0"))
    assert session.committed is True


def test_orcamento_item_service_remove_item_inexistente_sem_commit(monkeypatch) -> None:
    _FakeRepository.item_by_id = None
    _FakeRepository.delete_result = False
    _FakeRepository.deleted_item_id = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.OrcamentoItemService(session=session)

    assert service.remover_item(13) is False
    assert _FakeRepository.deleted_item_id is None
    assert session.committed is False


def test_orcamento_item_service_recalcula_total_versao(monkeypatch) -> None:
    _FakeRepository.sum_total = Decimal("123.45")
    _FakeRepository.summed_versao_id = None
    _FakeRepository.updated_versao_total = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)

    service = service_module.OrcamentoItemService(session=_FakeSession())

    assert service.recalcular_total_versao(30) == Decimal("123.45")
    assert _FakeRepository.summed_versao_id == 30
    assert _FakeRepository.updated_versao_total == (30, Decimal("123.45"))


def test_get_tipo_producao_default_normaliza_para_std(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    service = service_module.OrcamentoItemService(session=_FakeSession())

    _FakeRepository.tipo_producao_default = "SERIE"
    assert service.get_tipo_producao_default(30) == "SERIE"

    _FakeRepository.tipo_producao_default = None
    assert service.get_tipo_producao_default(30) == "STD"


def test_definir_tipo_producao_default(monkeypatch) -> None:
    _FakeRepository.updated_tipo_default = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    session = _FakeSession()
    service = service_module.OrcamentoItemService(session=session)

    assert service.definir_tipo_producao_default(30, "serie") == "SERIE"
    assert _FakeRepository.updated_tipo_default == (30, "SERIE")
    assert session.committed is True


def test_definir_tipo_producao_default_invalido(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    service = service_module.OrcamentoItemService(session=_FakeSession())

    try:
        service.definir_tipo_producao_default(30, "XPTO")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_definir_tipo_producao_item_excecao_e_padrao(monkeypatch) -> None:
    _FakeRepository.updated_tipo_item = None
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    session = _FakeSession()
    service = service_module.OrcamentoItemService(session=session)

    assert service.definir_tipo_producao_item(5, "SERIE") == "SERIE"
    assert _FakeRepository.updated_tipo_item == (5, "SERIE")

    # None limpa a exceção (o item volta a herdar o padrão da versão).
    assert service.definir_tipo_producao_item(5, None) is None
    assert _FakeRepository.updated_tipo_item == (5, None)
    assert session.committed is True


def test_definir_tipo_producao_item_invalido(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    service = service_module.OrcamentoItemService(session=_FakeSession())

    try:
        service.definir_tipo_producao_item(5, "XPTO")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_get_tipo_producao_efetivo_do_item(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)
    service = service_module.OrcamentoItemService(session=_FakeSession())
    _FakeRepository.tipo_producao_default = "SERIE"

    herdado = OrcamentoItemResumo(
        id=1,
        orcamento_versao_id=30,
        ordem=1,
        codigo=None,
        item="Item",
        descricao=None,
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=None,
        preco_total=None,
    )
    assert service.get_tipo_producao_efetivo(herdado) == "SERIE"

    excecao = OrcamentoItemResumo(
        id=2,
        orcamento_versao_id=30,
        ordem=2,
        codigo=None,
        item="Item",
        descricao=None,
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=None,
        preco_total=None,
        tipo_producao="STD",
    )
    assert service.get_tipo_producao_efetivo(excecao) == "STD"


def test_criar_item_simples_propaga_preco_manual(monkeypatch) -> None:
    _FakeRepository.next_order = 1
    _FakeRepository.created_payload = None
    _FakeRepository.sum_total = Decimal("0")
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)

    service = service_module.OrcamentoItemService(session=_FakeSession())
    service.criar_item_simples(
        service_module.CriarOrcamentoItemSimplesData(
            orcamento_versao_id=20,
            codigo=None,
            item="Mesa externa",
            descricao=None,
            altura=None,
            largura=None,
            profundidade=None,
            quantidade=Decimal("1"),
            unidade="un",
            preco_unitario=Decimal("99"),
            preco_manual=True,
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["preco_manual"] is True


def test_editar_item_simples_propaga_preco_manual(monkeypatch) -> None:
    _FakeRepository.updated_payload = None
    _FakeRepository.sum_total = Decimal("0")
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)

    service = service_module.OrcamentoItemService(session=_FakeSession())
    service.editar_item_simples(
        8,
        service_module.EditarOrcamentoItemSimplesData(
            codigo=None,
            item="Mesa externa",
            descricao=None,
            altura=None,
            largura=None,
            profundidade=None,
            quantidade=Decimal("1"),
            unidade="un",
            preco_unitario=Decimal("99"),
            preco_manual=True,
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["preco_manual"] is True


def test_aplicar_precos_da_versao_ignora_item_manual(monkeypatch) -> None:
    normal = OrcamentoItemResumo(
        id=1,
        orcamento_versao_id=30,
        ordem=1,
        codigo=None,
        item="Item normal",
        descricao=None,
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("0"),
        preco_total=Decimal("0"),
        preco_manual=False,
    )
    manual = OrcamentoItemResumo(
        id=2,
        orcamento_versao_id=30,
        ordem=2,
        codigo=None,
        item="Item manual",
        descricao=None,
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("250"),
        preco_total=Decimal("250"),
        preco_manual=True,
    )
    _FakeRepository.rows = [normal, manual]
    _FakeRepository.precos_escritos = []
    _FakeRepository.sum_total = Decimal("0")
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeRepository)

    service = service_module.OrcamentoItemService(session=_FakeSession())
    # Both items HAVE cost blocks: the only reason the manual item is skipped is
    # the preco_manual flag (not the absence of costing).
    monkeypatch.setattr(
        service,
        "get_blocos_custo_por_item",
        lambda _versao_id: {
            1: BlocosCusto(bloco_mp=Decimal("10")),
            2: BlocosCusto(bloco_mp=Decimal("10")),
        },
    )

    service.aplicar_precos_da_versao(30)

    # The normal item got its price (re)written; the manual one did NOT.
    assert 1 in _FakeRepository.precos_escritos
    assert 2 not in _FakeRepository.precos_escritos
