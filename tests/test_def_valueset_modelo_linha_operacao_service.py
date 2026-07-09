"""Tests for the ValueSet model line operation service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.def_valueset_modelo_linha_operacao_repository import (
    DefValuesetModeloLinhaOperacaoResumo,
)
from app.services import def_valueset_modelo_linha_operacao_service as service_module


def _resumo(**kwargs) -> DefValuesetModeloLinhaOperacaoResumo:
    base = {
        "id": 1,
        "def_valueset_modelo_linha_id": 10,
        "def_operacao_id": 20,
        "ordem": 1,
        "regra_calculo": None,
        "quantidade_base": None,
        "obrigatorio": True,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return DefValuesetModeloLinhaOperacaoResumo(**base)


class _FakeRepository:
    existing_links: list[DefValuesetModeloLinhaOperacaoResumo] = []
    active_links: list[DefValuesetModeloLinhaOperacaoResumo] = []
    by_id: DefValuesetModeloLinhaOperacaoResumo | None = None
    requested_linha_id: int | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    deactivated_id: int | None = None
    activate_result = True
    activated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_by_linha(
        self, def_valueset_modelo_linha_id: int
    ) -> list[DefValuesetModeloLinhaOperacaoResumo]:
        self.__class__.requested_linha_id = def_valueset_modelo_linha_id
        return self.existing_links

    def list_active_by_linha(
        self, def_valueset_modelo_linha_id: int
    ) -> list[DefValuesetModeloLinhaOperacaoResumo]:
        return self.active_links

    def get_by_id(self, id: int) -> DefValuesetModeloLinhaOperacaoResumo | None:
        return self.by_id

    def create(self, **kwargs) -> DefValuesetModeloLinhaOperacaoResumo:
        self.__class__.created_payload = kwargs
        return _resumo(id=1, **kwargs)

    def update(self, **kwargs) -> DefValuesetModeloLinhaOperacaoResumo:
        self.__class__.updated_payload = kwargs
        return _resumo(**kwargs)

    def deactivate(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result

    def activate(self, id: int) -> bool:
        self.__class__.activated_id = id
        return self.activate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.existing_links = []
    _FakeRepository.active_links = []
    _FakeRepository.by_id = None
    _FakeRepository.requested_linha_id = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None
    _FakeRepository.activate_result = True
    _FakeRepository.activated_id = None


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(
        service_module,
        "DefValuesetModeloLinhaOperacaoRepository",
        _FakeRepository,
    )
    session = _FakeSession()
    return service_module.DefValuesetModeloLinhaOperacaoService(session=session), session


def test_listar_operacoes_da_linha(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.existing_links = [_resumo(id=3)]

    assert service.listar_operacoes_da_linha(10) == [_resumo(id=3)]
    assert _FakeRepository.requested_linha_id == 10


def test_listar_operacoes_ativas_da_linha(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_links = [_resumo(id=4, ativo=True)]

    assert service.listar_operacoes_ativas_da_linha(10) == [_resumo(id=4, ativo=True)]


def test_adicionar_normaliza_ordem_regra_e_tempos(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.adicionar_operacao_a_linha(
        service_module.CriarDefValuesetModeloLinhaOperacaoData(
            def_valueset_modelo_linha_id=10,
            def_operacao_id=20,
            ordem=0,
            regra_calculo=" por_m2 ",
            quantidade_base=Decimal("1.5"),
            tempo_setup_minutos=Decimal("2"),
            tempo_por_unidade_minutos=Decimal("0.35"),
            unidade_tempo="ml",
        )
    )

    payload = _FakeRepository.created_payload
    assert payload is not None
    assert payload["def_valueset_modelo_linha_id"] == 10
    assert payload["def_operacao_id"] == 20
    assert payload["ordem"] == 1
    assert payload["regra_calculo"] == "POR_M2"
    assert payload["quantidade_base"] == Decimal("1.5")
    assert payload["tempo_setup_minutos"] == Decimal("2")
    assert payload["tempo_por_unidade_minutos"] == Decimal("0.35")
    assert payload["unidade_tempo"] == "ML"
    assert result.def_operacao_id == 20
    assert session.committed is True


def test_editar_permite_a_propria_ligacao(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.existing_links = [_resumo(id=5, def_operacao_id=20)]

    service.editar_operacao_da_linha(
        5,
        service_module.EditarDefValuesetModeloLinhaOperacaoData(
            def_valueset_modelo_linha_id=10,
            def_operacao_id=20,
            ordem=2,
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 5
    assert _FakeRepository.updated_payload["ordem"] == 2
    assert session.committed is True


def test_adicionar_recusa_duplicada(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.existing_links = [_resumo(id=5, def_operacao_id=20)]

    try:
        service.adicionar_operacao_a_linha(
            service_module.CriarDefValuesetModeloLinhaOperacaoData(
                def_valueset_modelo_linha_id=10,
                def_operacao_id=20,
            )
        )
    except ValueError as error:
        assert "associada" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_desativar_e_ativar(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_operacao_da_linha(5) is True
    assert _FakeRepository.deactivated_id == 5
    assert session.committed is True

    session.committed = False
    assert service.ativar_operacao_da_linha(5) is True
    assert _FakeRepository.activated_id == 5
    assert session.committed is True
