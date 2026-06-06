"""Tests for the DefOperacao service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.def_operacao_repository import DefOperacaoResumo
from app.services import def_operacao_service as service_module


def _resumo(**kwargs) -> DefOperacaoResumo:
    base = {
        "id": 1,
        "codigo": "CORTE_PAINEL",
        "nome": "Corte de painel",
        "descricao": None,
        "tipo_operacao": None,
        "unidade_calculo": None,
        "tempo_base": None,
        "tempo_setup": None,
        "custo_hora": None,
        "custo_minimo": None,
        "maquina_id": None,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return DefOperacaoResumo(**base)


class _FakeRepository:
    all_rows: list[DefOperacaoResumo] = []
    active_rows: list[DefOperacaoResumo] = []
    by_id: DefOperacaoResumo | None = None
    by_codigo: DefOperacaoResumo | None = None
    requested_codigo: str | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    deactivated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self) -> list[DefOperacaoResumo]:
        return self.all_rows

    def list_active(self) -> list[DefOperacaoResumo]:
        return self.active_rows

    def get_by_id(self, id: int) -> DefOperacaoResumo | None:
        return self.by_id

    def get_by_codigo(self, codigo: str) -> DefOperacaoResumo | None:
        self.__class__.requested_codigo = codigo
        return self.by_codigo

    def create_operacao(self, **kwargs) -> DefOperacaoResumo:
        self.__class__.created_payload = kwargs
        return _resumo(id=1, **kwargs)

    def update_operacao(self, **kwargs) -> DefOperacaoResumo:
        self.__class__.updated_payload = kwargs
        return _resumo(**kwargs)

    def deactivate_operacao(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.all_rows = []
    _FakeRepository.active_rows = []
    _FakeRepository.by_id = None
    _FakeRepository.by_codigo = None
    _FakeRepository.requested_codigo = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "DefOperacaoRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.DefOperacaoService(session=session), session


def test_listar_operacoes(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.all_rows = [_resumo(codigo="ORLAGEM_PECA")]

    assert service.listar_operacoes() == [_resumo(codigo="ORLAGEM_PECA")]


def test_obter_por_codigo_normaliza(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_codigo = _resumo(codigo="CNC_MECANIZACAO")

    result = service.obter_por_codigo(" cnc_mecanizacao ")

    assert _FakeRepository.requested_codigo == "CNC_MECANIZACAO"
    assert result.codigo == "CNC_MECANIZACAO"


def test_criar_operacao_normaliza_codigo_tipo_e_commita(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.criar_operacao(
        service_module.CriarDefOperacaoData(
            codigo=" corte_painel ",
            nome=" Corte de painel ",
            tipo_operacao=" corte ",
            unidade_calculo=" peca ",
            tempo_base=Decimal("0.15"),
            maquina_id=3,
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["codigo"] == "CORTE_PAINEL"
    assert _FakeRepository.created_payload["nome"] == "Corte de painel"
    assert _FakeRepository.created_payload["tipo_operacao"] == "CORTE"
    assert _FakeRepository.created_payload["unidade_calculo"] == "peca"
    assert _FakeRepository.created_payload["tempo_base"] == Decimal("0.15")
    assert _FakeRepository.created_payload["maquina_id"] == 3
    assert result.codigo == "CORTE_PAINEL"
    assert session.committed is True


def test_criar_operacao_recusa_codigo_duplicado(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_codigo = _resumo(id=9, codigo="CORTE_PAINEL")

    try:
        service.criar_operacao(
            service_module.CriarDefOperacaoData(codigo="CORTE_PAINEL", nome="Corte")
        )
    except ValueError as error:
        assert "codigo" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_editar_operacao_permite_mesmo_codigo(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_codigo = _resumo(id=5, codigo="CNC_MECANIZACAO")

    result = service.editar_operacao(
        5,
        service_module.EditarDefOperacaoData(
            codigo=" cnc_mecanizacao ",
            nome="CNC",
            tipo_operacao="desconhecido",
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 5
    assert _FakeRepository.updated_payload["codigo"] == "CNC_MECANIZACAO"
    assert _FakeRepository.updated_payload["tipo_operacao"] == "OUTRO"
    assert result.codigo == "CNC_MECANIZACAO"
    assert session.committed is True


def test_criar_operacao_valida_nome_obrigatorio(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_operacao(service_module.CriarDefOperacaoData(codigo="CNC", nome=" "))
    except ValueError as error:
        assert "nome" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_desativar_operacao_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_operacao(10) is True
    assert _FakeRepository.deactivated_id == 10
    assert session.committed is True


def test_desativar_operacao_inexistente_sem_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.deactivate_result = False

    assert service.desativar_operacao(11) is False
    assert _FakeRepository.deactivated_id == 11
    assert session.committed is False
