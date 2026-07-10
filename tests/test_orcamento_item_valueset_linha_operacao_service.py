"""Tests for the budget item ValueSet line operation service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.orcamento_item_valueset_linha_operacao_repository import (
    OrcamentoItemValuesetLinhaOperacaoResumo,
)
from app.services import orcamento_item_valueset_linha_operacao_service as service_module


def _resumo(**kwargs) -> OrcamentoItemValuesetLinhaOperacaoResumo:
    base = {
        "id": 1,
        "orcamento_item_valueset_linha_id": 10,
        "def_operacao_id": 20,
        "ordem": 1,
        "regra_calculo": None,
        "quantidade_base": None,
        "obrigatorio": True,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return OrcamentoItemValuesetLinhaOperacaoResumo(**base)


class _FakeRepository:
    existing_links: list[OrcamentoItemValuesetLinhaOperacaoResumo] = []
    active_links: list[OrcamentoItemValuesetLinhaOperacaoResumo] = []
    by_id: OrcamentoItemValuesetLinhaOperacaoResumo | None = None
    requested_linha_id: int | None = None
    created_payload: dict | None = None
    created_payloads: list[dict] = []
    updated_payload: dict | None = None
    deactivate_result = True
    deactivated_id: int | None = None
    activate_result = True
    activated_id: int | None = None
    deleted_linha_ids: list[int] = []
    deleted_count = 0

    def __init__(self, _session: object) -> None:
        pass

    def list_by_linha(
        self, orcamento_item_valueset_linha_id: int
    ) -> list[OrcamentoItemValuesetLinhaOperacaoResumo]:
        self.__class__.requested_linha_id = orcamento_item_valueset_linha_id
        return self.existing_links

    def list_active_by_linha(
        self, orcamento_item_valueset_linha_id: int
    ) -> list[OrcamentoItemValuesetLinhaOperacaoResumo]:
        return self.active_links

    def get_by_id(self, id: int) -> OrcamentoItemValuesetLinhaOperacaoResumo | None:
        return self.by_id

    def create(self, **kwargs) -> OrcamentoItemValuesetLinhaOperacaoResumo:
        self.__class__.created_payload = kwargs
        self.__class__.created_payloads.append(kwargs)
        return _resumo(id=1, **kwargs)

    def update(self, **kwargs) -> OrcamentoItemValuesetLinhaOperacaoResumo:
        self.__class__.updated_payload = kwargs
        return _resumo(**kwargs)

    def deactivate(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result

    def activate(self, id: int) -> bool:
        self.__class__.activated_id = id
        return self.activate_result

    def delete_by_linha(self, orcamento_item_valueset_linha_id: int) -> int:
        self.__class__.deleted_linha_ids.append(orcamento_item_valueset_linha_id)
        return self.deleted_count


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
    _FakeRepository.created_payloads = []
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None
    _FakeRepository.activate_result = True
    _FakeRepository.activated_id = None
    _FakeRepository.deleted_linha_ids = []
    _FakeRepository.deleted_count = 0


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(
        service_module,
        "OrcamentoItemValuesetLinhaOperacaoRepository",
        _FakeRepository,
    )
    session = _FakeSession()
    return service_module.OrcamentoItemValuesetLinhaOperacaoService(session=session), session


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
        service_module.CriarOrcamentoItemValuesetLinhaOperacaoData(
            orcamento_item_valueset_linha_id=10,
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
    assert payload["orcamento_item_valueset_linha_id"] == 10
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
        service_module.EditarOrcamentoItemValuesetLinhaOperacaoData(
            orcamento_item_valueset_linha_id=10,
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
            service_module.CriarOrcamentoItemValuesetLinhaOperacaoData(
                orcamento_item_valueset_linha_id=10,
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


def test_copiar_operacoes_de_substitui_e_nao_faz_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    origem = [
        _resumo(id=1, def_operacao_id=20, ordem=1, acao="SUBSTITUIR"),
        _resumo(id=2, def_operacao_id=21, ordem=2, acao="DESATIVAR"),
    ]

    total = service.copiar_operacoes_de(origem, 99)

    assert total == 2
    assert _FakeRepository.deleted_linha_ids == [99]
    assert len(_FakeRepository.created_payloads) == 2
    assert {
        payload["def_operacao_id"] for payload in _FakeRepository.created_payloads
    } == {20, 21}
    assert all(
        payload["orcamento_item_valueset_linha_id"] == 99
        for payload in _FakeRepository.created_payloads
    )
    assert [p["acao"] for p in _FakeRepository.created_payloads] == [
        "SUBSTITUIR",
        "DESATIVAR",
    ]
    assert session.committed is False


def test_copiar_operacoes_de_lista_vazia_so_limpa(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    total = service.copiar_operacoes_de([], 99)

    assert total == 0
    assert _FakeRepository.deleted_linha_ids == [99]
    assert _FakeRepository.created_payloads == []
    assert session.committed is False
