"""Tests for the OrcamentoValuesetLinha service."""

from __future__ import annotations

from app.repositories.orcamento_valueset_linha_repository import OrcamentoValuesetLinhaResumo
from app.services import orcamento_valueset_linha_service as service_module


def _resumo(**kwargs) -> OrcamentoValuesetLinhaResumo:
    base = {
        "id": 1,
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


class _FakeRepository:
    duplicate: OrcamentoValuesetLinhaResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    activate_result = True
    rows: list[OrcamentoValuesetLinhaResumo] = []

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self):
        return self.rows

    def list_active(self):
        return self.rows

    def list_by_orcamento_versao(self, orcamento_versao_id: int):
        return self.rows

    def get_by_id(self, id: int):
        return _resumo(id=id)

    def get_by_versao_chave(self, orcamento_versao_id: int, chave: str):
        return self.duplicate

    def create(self, **fields):
        self.__class__.created_payload = fields
        return _resumo(id=1, **fields)

    def update(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        return _resumo(id=id, **fields)

    def deactivate(self, id: int) -> bool:
        return self.deactivate_result

    def activate(self, id: int) -> bool:
        return self.activate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.duplicate = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.activate_result = True
    _FakeRepository.rows = []


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "OrcamentoValuesetLinhaRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.OrcamentoValuesetLinhaService(session=session), session


def test_criar_linha_da_versao(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.criar_linha(
        service_module.CriarOrcamentoValuesetLinhaData(
            orcamento_versao_id=20,
            chave="ferragem_puxador",
            ref_materia_prima="PUX-01",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["chave"] == "FERRAGEM_PUXADOR"
    assert _FakeRepository.created_payload["editado_localmente"] is False
    assert result.ref_materia_prima == "PUX-01"
    assert session.committed is True


def test_criar_linha_valida_versao(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha(
            service_module.CriarOrcamentoValuesetLinhaData(
                orcamento_versao_id=None,
                chave="MATERIAL_CAIXOTE",
            )
        )
    except ValueError as error:
        assert "orcamento_versao_id" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_linha_recusa_chave_duplicada_na_versao(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.duplicate = _resumo(id=2)

    try:
        service.criar_linha(
            service_module.CriarOrcamentoValuesetLinhaData(
                orcamento_versao_id=20,
                chave="MATERIAL_CAIXOTE",
            )
        )
    except ValueError as error:
        assert "chave" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_editar_linha_permite_mesma_chave(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.duplicate = _resumo(id=5)

    result = service.editar_linha(
        5,
        service_module.EditarOrcamentoValuesetLinhaData(
            orcamento_versao_id=20,
            chave="MATERIAL_CAIXOTE",
            valor_texto="default",
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 5
    assert result.valor_texto == "default"
    assert session.committed is True
