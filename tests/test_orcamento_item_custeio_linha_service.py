"""Tests for the OrcamentoItemCusteioLinha service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)
from app.services import orcamento_item_custeio_linha_service as service_module


def _resumo(**kwargs) -> OrcamentoItemCusteioLinhaResumo:
    base = {
        "id": 1,
        "orcamento_item_id": 10,
        "orcamento_item_modulo_id": None,
        "origem_tipo": None,
        "origem_id": None,
        "tipo_linha": "MANUAL",
        "codigo": None,
        "descricao": "Linha",
        "materia_prima_id": None,
        "ref_materia_prima": None,
        "descricao_materia_prima": None,
        "unidade": None,
        "quantidade": Decimal("1"),
        "comp": None,
        "larg": None,
        "esp": None,
        "area_m2": None,
        "perimetro_ml": None,
        "ml_orla_fina": None,
        "ml_orla_grossa": None,
        "custo_unitario": None,
        "custo_total": None,
        "margem_percentagem": None,
        "preco_unitario": None,
        "preco_total": None,
        "def_operacao_id": None,
        "def_maquina_id": None,
        "tempo_calculado": None,
        "tempo_manual": None,
        "override_manual": False,
        "editado_localmente": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return OrcamentoItemCusteioLinhaResumo(**base)


class _FakeRepository:
    all_rows: list[OrcamentoItemCusteioLinhaResumo] = []
    active_rows: list[OrcamentoItemCusteioLinhaResumo] = []
    by_id: OrcamentoItemCusteioLinhaResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    deactivated_id: int | None = None
    activate_result = True
    activated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_by_orcamento_item(self, orcamento_item_id: int):
        return self.all_rows

    def list_active_by_orcamento_item(self, orcamento_item_id: int):
        return self.active_rows

    def get_by_id(self, id: int):
        return self.by_id

    def create_linha(self, **fields):
        self.__class__.created_payload = fields
        return _resumo(id=1, **fields)

    def update_linha(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        return _resumo(id=id, **fields)

    def deactivate_linha(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result

    def activate_linha(self, id: int) -> bool:
        self.__class__.activated_id = id
        return self.activate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.all_rows = []
    _FakeRepository.active_rows = []
    _FakeRepository.by_id = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None
    _FakeRepository.activate_result = True
    _FakeRepository.activated_id = None


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "OrcamentoItemCusteioLinhaRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.OrcamentoItemCusteioLinhaService(session=session), session


def test_listar_linhas_do_item(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.all_rows = [_resumo(id=3)]

    assert service.listar_linhas_do_item(10) == [_resumo(id=3)]


def test_criar_linha_default_tipo_manual(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.criar_linha_manual(
        service_module.CriarLinhaCusteioData(
            orcamento_item_id=10, descricao="  Transporte interno  "
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["tipo_linha"] == "MANUAL"
    assert _FakeRepository.created_payload["descricao"] == "Transporte interno"
    assert _FakeRepository.created_payload["quantidade"] == Decimal("1")
    assert session.committed is True


def test_criar_linha_normaliza_tipo(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha_manual(
        service_module.CriarLinhaCusteioData(
            orcamento_item_id=10, descricao="Placa", tipo_linha="material_peca"
        )
    )

    assert _FakeRepository.created_payload["tipo_linha"] == "MATERIAL_PECA"


def test_criar_valida_orcamento_item_id(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha_manual(
            service_module.CriarLinhaCusteioData(orcamento_item_id=None, descricao="X")
        )
    except ValueError as error:
        assert "orcamento_item_id" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_valida_descricao(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha_manual(
            service_module.CriarLinhaCusteioData(orcamento_item_id=10, descricao="   ")
        )
    except ValueError as error:
        assert "descricao" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_calcula_custo_e_preco_total(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha_manual(
        service_module.CriarLinhaCusteioData(
            orcamento_item_id=10,
            descricao="Placa",
            quantidade=Decimal("3"),
            custo_unitario=Decimal("2"),
            preco_unitario=Decimal("5"),
        )
    )

    assert _FakeRepository.created_payload["custo_total"] == Decimal("6")
    assert _FakeRepository.created_payload["preco_total"] == Decimal("15")


def test_criar_respeita_total_explicito(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha_manual(
        service_module.CriarLinhaCusteioData(
            orcamento_item_id=10,
            descricao="Placa",
            quantidade=Decimal("3"),
            custo_unitario=Decimal("2"),
            custo_total=Decimal("99"),
        )
    )

    assert _FakeRepository.created_payload["custo_total"] == Decimal("99")


def test_editar_linha(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.editar_linha(
        7,
        service_module.EditarLinhaCusteioData(
            orcamento_item_id=10, descricao="Atualizada", tipo_linha="operacao"
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 7
    assert _FakeRepository.updated_payload["tipo_linha"] == "OPERACAO"
    assert session.committed is True


def test_desativar_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_linha(10) is True
    assert _FakeRepository.deactivated_id == 10
    assert session.committed is True


def test_desativar_inexistente_sem_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.deactivate_result = False

    assert service.desativar_linha(11) is False
    assert session.committed is False


def test_ativar_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.ativar_linha(7) is True
    assert _FakeRepository.activated_id == 7
    assert session.committed is True


def test_ativar_inexistente_sem_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.activate_result = False

    assert service.ativar_linha(8) is False
    assert session.committed is False
