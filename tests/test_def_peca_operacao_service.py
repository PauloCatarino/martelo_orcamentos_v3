"""Tests for the DefPecaOperacao service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.def_peca_operacao_repository import DefPecaOperacaoResumo
from app.services import def_peca_operacao_service as service_module


def _resumo(**kwargs) -> DefPecaOperacaoResumo:
    base = {
        "id": 1,
        "def_peca_id": 10,
        "def_operacao_id": 20,
        "ordem": 1,
        "regra_calculo": None,
        "quantidade_base": None,
        "obrigatorio": True,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return DefPecaOperacaoResumo(**base)


class _FakeRepository:
    existing_links: list[DefPecaOperacaoResumo] = []
    active_links: list[DefPecaOperacaoResumo] = []
    by_id: DefPecaOperacaoResumo | None = None
    requested_peca_id: int | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    deactivated_id: int | None = None
    activate_result = True
    activated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_by_def_peca(self, def_peca_id: int) -> list[DefPecaOperacaoResumo]:
        self.__class__.requested_peca_id = def_peca_id
        return self.existing_links

    def list_active_by_def_peca(self, def_peca_id: int) -> list[DefPecaOperacaoResumo]:
        return self.active_links

    def get_by_id(self, id: int) -> DefPecaOperacaoResumo | None:
        return self.by_id

    def create_peca_operacao(self, **kwargs) -> DefPecaOperacaoResumo:
        self.__class__.created_payload = kwargs
        return _resumo(id=1, **kwargs)

    def update_peca_operacao(self, **kwargs) -> DefPecaOperacaoResumo:
        self.__class__.updated_payload = kwargs
        return _resumo(**kwargs)

    def deactivate_peca_operacao(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result

    def activate_peca_operacao(self, id: int) -> bool:
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
    _FakeRepository.requested_peca_id = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None
    _FakeRepository.activate_result = True
    _FakeRepository.activated_id = None


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "DefPecaOperacaoRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.DefPecaOperacaoService(session=session), session


def test_listar_operacoes_da_peca(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.existing_links = [_resumo(id=3)]

    assert service.listar_operacoes_da_peca(10) == [_resumo(id=3)]
    assert _FakeRepository.requested_peca_id == 10


def test_listar_operacoes_ativas_da_peca(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_links = [_resumo(id=4, ativo=True)]

    assert service.listar_operacoes_ativas_da_peca(10) == [_resumo(id=4, ativo=True)]


def test_adicionar_normaliza_ordem_e_regra(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.adicionar_operacao_a_peca(
        service_module.CriarDefPecaOperacaoData(
            def_peca_id=10,
            def_operacao_id=20,
            ordem=0,
            regra_calculo=" por_m2 ",
            quantidade_base=Decimal("1.5"),
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["def_peca_id"] == 10
    assert _FakeRepository.created_payload["def_operacao_id"] == 20
    assert _FakeRepository.created_payload["ordem"] == 1
    assert _FakeRepository.created_payload["regra_calculo"] == "POR_M2"
    assert _FakeRepository.created_payload["quantidade_base"] == Decimal("1.5")
    assert result.def_operacao_id == 20
    assert session.committed is True


def test_adicionar_propaga_tempos(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.adicionar_operacao_a_peca(
        service_module.CriarDefPecaOperacaoData(
            def_peca_id=10,
            def_operacao_id=20,
            tempo_setup_minutos=Decimal("2"),
            tempo_por_unidade_minutos=Decimal("0.35"),
            unidade_tempo="ml",
        )
    )

    payload = _FakeRepository.created_payload
    assert payload["tempo_setup_minutos"] == Decimal("2")
    assert payload["tempo_por_unidade_minutos"] == Decimal("0.35")
    assert payload["unidade_tempo"] == "ML"  # normalized to upper-case


def test_editar_propaga_tempos(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.editar_operacao_da_peca(
        5,
        service_module.EditarDefPecaOperacaoData(
            def_peca_id=10,
            def_operacao_id=20,
            tempo_setup_minutos=Decimal("1"),
            tempo_por_unidade_minutos=Decimal("0.20"),
            unidade_tempo="FURO",
        ),
    )

    payload = _FakeRepository.updated_payload
    assert payload["tempo_setup_minutos"] == Decimal("1")
    assert payload["tempo_por_unidade_minutos"] == Decimal("0.20")
    assert payload["unidade_tempo"] == "FURO"


def test_adicionar_regra_vazia_fica_none(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.adicionar_operacao_a_peca(
        service_module.CriarDefPecaOperacaoData(
            def_peca_id=10, def_operacao_id=21, regra_calculo="   "
        )
    )

    assert _FakeRepository.created_payload["regra_calculo"] is None


def test_adicionar_valida_def_peca_id(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.adicionar_operacao_a_peca(
            service_module.CriarDefPecaOperacaoData(def_peca_id=None, def_operacao_id=20)
        )
    except ValueError as error:
        assert "def_peca_id" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_adicionar_valida_def_operacao_id(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.adicionar_operacao_a_peca(
            service_module.CriarDefPecaOperacaoData(def_peca_id=10, def_operacao_id=None)
        )
    except ValueError as error:
        assert "def_operacao_id" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_adicionar_recusa_duplicada(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.existing_links = [_resumo(id=5, def_operacao_id=20)]

    try:
        service.adicionar_operacao_a_peca(
            service_module.CriarDefPecaOperacaoData(def_peca_id=10, def_operacao_id=20)
        )
    except ValueError as error:
        assert "associada" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_editar_permite_a_propria_ligacao(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.existing_links = [_resumo(id=5, def_operacao_id=20)]

    service.editar_operacao_da_peca(
        5,
        service_module.EditarDefPecaOperacaoData(
            def_peca_id=10, def_operacao_id=20, ordem=2
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 5
    assert _FakeRepository.updated_payload["ordem"] == 2
    assert session.committed is True


def test_editar_recusa_duplicada_de_outra_ligacao(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.existing_links = [_resumo(id=5, def_operacao_id=20)]

    try:
        service.editar_operacao_da_peca(
            7,
            service_module.EditarDefPecaOperacaoData(def_peca_id=10, def_operacao_id=20),
        )
    except ValueError as error:
        assert "associada" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_desativar_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_operacao_da_peca(10) is True
    assert _FakeRepository.deactivated_id == 10
    assert session.committed is True


def test_desativar_inexistente_sem_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.deactivate_result = False

    assert service.desativar_operacao_da_peca(11) is False
    assert session.committed is False


def test_ativar_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.ativar_operacao_da_peca(7) is True
    assert _FakeRepository.activated_id == 7
    assert session.committed is True


def test_ativar_inexistente_sem_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.activate_result = False

    assert service.ativar_operacao_da_peca(8) is False
    assert session.committed is False
