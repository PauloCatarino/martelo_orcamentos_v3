"""Tests for the Orcamento item module service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.orcamento_item_modulo_repository import OrcamentoItemModuloResumo
from app.services import orcamento_item_modulo_service as service_module


class _FakeRepository:
    rows: list[OrcamentoItemModuloResumo] = []
    requested_item_id: int | None = None
    next_order = 1
    next_order_item_id: int | None = None
    created_payload: dict[str, object] | None = None
    modulo_by_id: OrcamentoItemModuloResumo | None = None
    requested_modulo_id: int | None = None
    updated_payload: dict[str, object] | None = None
    delete_result = True
    deleted_modulo_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_by_item_id(self, orcamento_item_id: int) -> list[OrcamentoItemModuloResumo]:
        self.__class__.requested_item_id = orcamento_item_id
        return self.rows

    def get_next_ordem(self, orcamento_item_id: int) -> int:
        self.__class__.next_order_item_id = orcamento_item_id
        return self.next_order

    def create_modulo(self, **kwargs) -> OrcamentoItemModuloResumo:
        self.__class__.created_payload = kwargs
        return OrcamentoItemModuloResumo(
            id=99,
            orcamento_item_id=kwargs["orcamento_item_id"],
            ordem=kwargs["ordem"],
            nome=kwargs["nome"],
            descricao=kwargs["descricao"],
            altura=kwargs["altura"],
            largura=kwargs["largura"],
            profundidade=kwargs["profundidade"],
            quantidade=kwargs["quantidade"],
        )

    def get_modulo_by_id(self, modulo_id: int) -> OrcamentoItemModuloResumo | None:
        self.__class__.requested_modulo_id = modulo_id
        return self.modulo_by_id

    def update_modulo(self, **kwargs) -> OrcamentoItemModuloResumo:
        self.__class__.updated_payload = kwargs
        return OrcamentoItemModuloResumo(
            id=kwargs["modulo_id"],
            orcamento_item_id=20,
            ordem=2,
            nome=kwargs["nome"],
            descricao=kwargs["descricao"],
            altura=kwargs["altura"],
            largura=kwargs["largura"],
            profundidade=kwargs["profundidade"],
            quantidade=kwargs["quantidade"],
        )

    def delete_modulo(self, modulo_id: int) -> bool:
        self.__class__.deleted_modulo_id = modulo_id
        return self.delete_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def test_modulo_service_returns_empty_list(monkeypatch) -> None:
    _FakeRepository.rows = []
    _FakeRepository.requested_item_id = None
    monkeypatch.setattr(service_module, "OrcamentoItemModuloRepository", _FakeRepository)

    service = service_module.OrcamentoItemModuloService(session=object())

    assert service.listar_modulos(10) == []
    assert _FakeRepository.requested_item_id == 10


def test_modulo_service_cria_modulo_com_proxima_ordem(monkeypatch) -> None:
    _FakeRepository.next_order = 3
    _FakeRepository.next_order_item_id = None
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "OrcamentoItemModuloRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.OrcamentoItemModuloService(session=session)
    result = service.criar_modulo_simples(
        service_module.CriarOrcamentoItemModuloSimplesData(
            orcamento_item_id=20,
            nome="Modulo Superior",
            descricao="Teste",
            altura=Decimal("700"),
            largura=Decimal("800"),
            profundidade=Decimal("600"),
            quantidade=Decimal("1"),
        )
    )

    assert _FakeRepository.next_order_item_id == 20
    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["ordem"] == 3
    assert _FakeRepository.created_payload["nome"] == "Modulo Superior"
    assert result.ordem == 3
    assert session.committed is True


def test_modulo_service_valida_nome_obrigatorio(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "OrcamentoItemModuloRepository", _FakeRepository)
    service = service_module.OrcamentoItemModuloService(session=_FakeSession())

    try:
        service.criar_modulo_simples(
            service_module.CriarOrcamentoItemModuloSimplesData(
                orcamento_item_id=20,
                nome="",
                descricao=None,
                altura=None,
                largura=None,
                profundidade=None,
                quantidade=Decimal("1"),
            )
        )
    except ValueError as error:
        assert "nome" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_modulo_service_valida_quantidade_positiva(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "OrcamentoItemModuloRepository", _FakeRepository)
    service = service_module.OrcamentoItemModuloService(session=_FakeSession())

    try:
        service.criar_modulo_simples(
            service_module.CriarOrcamentoItemModuloSimplesData(
                orcamento_item_id=20,
                nome="Modulo",
                descricao=None,
                altura=None,
                largura=None,
                profundidade=None,
                quantidade=Decimal("0"),
            )
        )
    except ValueError as error:
        assert "quantidade" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_modulo_service_obtem_modulo_por_id(monkeypatch) -> None:
    row = OrcamentoItemModuloResumo(
        id=5,
        orcamento_item_id=20,
        ordem=1,
        nome="Modulo",
        descricao=None,
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=Decimal("1"),
    )
    _FakeRepository.modulo_by_id = row
    _FakeRepository.requested_modulo_id = None
    monkeypatch.setattr(service_module, "OrcamentoItemModuloRepository", _FakeRepository)

    service = service_module.OrcamentoItemModuloService(session=object())

    assert service.get_modulo_by_id(5) == row
    assert _FakeRepository.requested_modulo_id == 5


def test_modulo_service_edita_modulo(monkeypatch) -> None:
    _FakeRepository.updated_payload = None
    monkeypatch.setattr(service_module, "OrcamentoItemModuloRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.OrcamentoItemModuloService(session=session)
    result = service.editar_modulo_simples(
        8,
        service_module.EditarOrcamentoItemModuloSimplesData(
            nome="Modulo Editado",
            descricao="Editado",
            altura=Decimal("700"),
            largura=None,
            profundidade=None,
            quantidade=Decimal("2"),
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["modulo_id"] == 8
    assert _FakeRepository.updated_payload["nome"] == "Modulo Editado"
    assert result.nome == "Modulo Editado"
    assert session.committed is True


def test_modulo_service_remove_modulo_existente(monkeypatch) -> None:
    _FakeRepository.delete_result = True
    _FakeRepository.deleted_modulo_id = None
    monkeypatch.setattr(service_module, "OrcamentoItemModuloRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.OrcamentoItemModuloService(session=session)

    assert service.remover_modulo(12) is True
    assert _FakeRepository.deleted_modulo_id == 12
    assert session.committed is True


def test_modulo_service_remove_modulo_inexistente_sem_commit(monkeypatch) -> None:
    _FakeRepository.delete_result = False
    _FakeRepository.deleted_modulo_id = None
    monkeypatch.setattr(service_module, "OrcamentoItemModuloRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.OrcamentoItemModuloService(session=session)

    assert service.remover_modulo(13) is False
    assert _FakeRepository.deleted_modulo_id == 13
    assert session.committed is False
