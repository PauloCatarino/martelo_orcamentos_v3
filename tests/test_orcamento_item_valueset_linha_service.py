"""Tests for the OrcamentoItemValuesetLinha service."""

from __future__ import annotations

from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaResumo,
)
from app.repositories.orcamento_valueset_linha_repository import OrcamentoValuesetLinhaResumo
from app.services import orcamento_item_valueset_linha_service as service_module


def _item_resumo(**kwargs) -> OrcamentoItemValuesetLinhaResumo:
    base = {
        "id": 1,
        "orcamento_item_id": 30,
        "chave": "MATERIAL_CAIXOTE",
        "descricao": None,
        "materia_prima_id": None,
        "ref_materia_prima": None,
        "descricao_materia_prima": None,
        "valor_texto": None,
        "origem": None,
        "herdado_do_orcamento": True,
        "editado_localmente": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return OrcamentoItemValuesetLinhaResumo(**base)


def _versao_resumo(**kwargs) -> OrcamentoValuesetLinhaResumo:
    base = {
        "id": 2,
        "orcamento_versao_id": 20,
        "chave": "MATERIAL_CAIXOTE",
        "descricao": None,
        "materia_prima_id": None,
        "ref_materia_prima": None,
        "descricao_materia_prima": None,
        "valor_texto": None,
        "origem": None,
        "editado_localmente": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return OrcamentoValuesetLinhaResumo(**base)


class _FakeItemRepository:
    duplicate: OrcamentoItemValuesetLinhaResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    rows: list[OrcamentoItemValuesetLinhaResumo] = []
    deactivate_result = True
    activate_result = True

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self):
        return self.rows

    def list_active(self):
        return self.rows

    def list_by_orcamento_item(self, orcamento_item_id: int):
        return self.rows

    def get_by_id(self, id: int):
        return _item_resumo(id=id)

    def get_by_item_chave(self, orcamento_item_id: int, chave: str):
        return self.duplicate

    def create(self, **fields):
        self.__class__.created_payload = fields
        return _item_resumo(id=1, **fields)

    def update(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        return _item_resumo(id=id, **fields)

    def deactivate(self, id: int) -> bool:
        return self.deactivate_result

    def activate(self, id: int) -> bool:
        return self.activate_result


class _FakeOrcamentoRepository:
    duplicate: OrcamentoValuesetLinhaResumo | None = None

    def __init__(self, _session: object) -> None:
        pass

    def get_by_versao_chave(self, orcamento_versao_id: int, chave: str):
        return self.duplicate


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeItemRepository.duplicate = None
    _FakeItemRepository.created_payload = None
    _FakeItemRepository.updated_payload = None
    _FakeItemRepository.rows = []
    _FakeItemRepository.deactivate_result = True
    _FakeItemRepository.activate_result = True
    _FakeOrcamentoRepository.duplicate = None


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(
        service_module, "OrcamentoItemValuesetLinhaRepository", _FakeItemRepository
    )
    monkeypatch.setattr(
        service_module, "OrcamentoValuesetLinhaRepository", _FakeOrcamentoRepository
    )
    session = _FakeSession()
    return service_module.OrcamentoItemValuesetLinhaService(session=session), session


def test_criar_linha_do_item(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.criar_linha(
        service_module.CriarOrcamentoItemValuesetLinhaData(
            orcamento_item_id=30,
            chave="material_portas",
            ref_materia_prima="PORTA-01",
        )
    )

    assert _FakeItemRepository.created_payload is not None
    assert _FakeItemRepository.created_payload["chave"] == "MATERIAL_PORTAS"
    assert _FakeItemRepository.created_payload["herdado_do_orcamento"] is True
    assert _FakeItemRepository.created_payload["editado_localmente"] is False
    assert result.ref_materia_prima == "PORTA-01"
    assert session.committed is True


def test_criar_linha_recusa_chave_duplicada_no_item(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeItemRepository.duplicate = _item_resumo(id=2)

    try:
        service.criar_linha(
            service_module.CriarOrcamentoItemValuesetLinhaData(
                orcamento_item_id=30,
                chave="MATERIAL_PORTAS",
            )
        )
    except ValueError as error:
        assert "chave" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_resolver_prefere_linha_ativa_do_item(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemRepository.duplicate = _item_resumo(id=3, ref_materia_prima="ITEM")
    _FakeOrcamentoRepository.duplicate = _versao_resumo(id=4, ref_materia_prima="VERSAO")

    result = service.obter_valor_resolvido(30, 20, "material_caixote")

    assert result == _item_resumo(id=3, ref_materia_prima="ITEM")


def test_resolver_usa_orcamento_quando_item_nao_existe_ou_inativo(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemRepository.duplicate = _item_resumo(id=3, ativo=False)
    _FakeOrcamentoRepository.duplicate = _versao_resumo(id=4, ref_materia_prima="VERSAO")

    result = service.obter_valor_resolvido(30, 20, "material_caixote")

    assert result == _versao_resumo(id=4, ref_materia_prima="VERSAO")


def test_resolver_devolve_none_sem_linha_ativa(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemRepository.duplicate = _item_resumo(id=3, ativo=False)
    _FakeOrcamentoRepository.duplicate = _versao_resumo(id=4, ativo=False)

    assert service.obter_valor_resolvido(30, 20, "material_caixote") is None
