"""Tests for the DefPecaComponente service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.def_peca_componente_repository import DefPecaComponenteResumo
from app.services import def_peca_componente_service as service_module


class _FakeRepository:
    rows: list[DefPecaComponenteResumo] = []
    requested_parent_id: int | None = None
    next_order = 1
    next_order_parent_id: int | None = None
    created_payload: dict[str, object] | None = None
    updated_payload: dict[str, object] | None = None
    deactivate_result = True
    deactivated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_by_peca_pai_id(self, def_peca_pai_id: int) -> list[DefPecaComponenteResumo]:
        self.__class__.requested_parent_id = def_peca_pai_id
        return self.rows

    def get_next_ordem(self, def_peca_pai_id: int) -> int:
        self.__class__.next_order_parent_id = def_peca_pai_id
        return self.next_order

    def create_componente(self, **kwargs) -> DefPecaComponenteResumo:
        self.__class__.created_payload = kwargs
        return DefPecaComponenteResumo(
            id=1,
            def_peca_pai_id=kwargs["def_peca_pai_id"],
            tipo_componente=kwargs["tipo_componente"],
            def_peca_componente_id=kwargs["def_peca_componente_id"],
            referencia_componente=kwargs["referencia_componente"],
            descricao=kwargs["descricao"],
            ordem=kwargs["ordem"],
            quantidade=kwargs["quantidade"],
            regra_quantidade=kwargs["regra_quantidade"],
            obrigatorio=kwargs["obrigatorio"],
            ativo=kwargs["ativo"],
            observacoes=kwargs["observacoes"],
        )

    def update_componente(self, **kwargs) -> DefPecaComponenteResumo:
        self.__class__.updated_payload = kwargs
        return DefPecaComponenteResumo(
            id=kwargs["id"],
            def_peca_pai_id=kwargs["def_peca_pai_id"],
            tipo_componente=kwargs["tipo_componente"],
            def_peca_componente_id=kwargs["def_peca_componente_id"],
            referencia_componente=kwargs["referencia_componente"],
            descricao=kwargs["descricao"],
            ordem=kwargs["ordem"],
            quantidade=kwargs["quantidade"],
            regra_quantidade=kwargs["regra_quantidade"],
            obrigatorio=kwargs["obrigatorio"],
            ativo=kwargs["ativo"],
            observacoes=kwargs["observacoes"],
        )

    def deactivate_componente(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def test_componente_service_lista_componentes(monkeypatch) -> None:
    _FakeRepository.rows = []
    _FakeRepository.requested_parent_id = None
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)

    service = service_module.DefPecaComponenteService(session=object())

    assert service.listar_componentes(5) == []
    assert _FakeRepository.requested_parent_id == 5


def test_componente_service_cria_componente_peca_com_proxima_ordem(monkeypatch) -> None:
    _FakeRepository.next_order = 3
    _FakeRepository.next_order_parent_id = None
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaComponenteService(session=session)
    result = service.criar_componente(
        service_module.CriarDefPecaComponenteData(
            def_peca_pai_id=10,
            tipo_componente="peca",
            def_peca_componente_id=20,
            quantidade=Decimal("2"),
            regra_quantidade=None,
        )
    )

    assert _FakeRepository.next_order_parent_id == 10
    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["ordem"] == 3
    assert _FakeRepository.created_payload["tipo_componente"] == "PECA"
    assert _FakeRepository.created_payload["regra_quantidade"] == "FIXA"
    assert result.def_peca_componente_id == 20
    assert session.committed is True


def test_componente_service_cria_componente_nao_peca_sem_def_peca(monkeypatch) -> None:
    _FakeRepository.next_order = 1
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaComponenteService(session=session)
    result = service.criar_componente(
        service_module.CriarDefPecaComponenteData(
            def_peca_pai_id=10,
            tipo_componente="ferragem",
            def_peca_componente_id=None,
            referencia_componente="DOB-01",
            descricao="Dobradica",
            quantidade=Decimal("3"),
            regra_quantidade=" por_comprimento ",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["tipo_componente"] == "FERRAGEM"
    assert _FakeRepository.created_payload["regra_quantidade"] == "POR_COMPRIMENTO"
    assert result.referencia_componente == "DOB-01"
    assert session.committed is True


def test_associado_guarda_zona_dimensao_e_numero_topos(monkeypatch) -> None:
    _FakeRepository.next_order = 1
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)
    session = _FakeSession()

    service_module.DefPecaComponenteService(session=session).criar_componente(
        service_module.CriarDefPecaComponenteData(
            def_peca_pai_id=10,
            tipo_componente="FERRAGEM",
            referencia_componente="CAVILHA",
            zona_aplicacao=" dois_topos ",
            dimensao_referencia=" medida_topo ",
            numero_topos=2,
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["zona_aplicacao"] == "DOIS_TOPOS"
    assert _FakeRepository.created_payload["dimensao_referencia"] == "MEDIDA_TOPO"
    assert _FakeRepository.created_payload["numero_topos"] == 2


def test_componente_service_normaliza_regra_legacy_altura(monkeypatch) -> None:
    _FakeRepository.created_payload = None
    _FakeRepository.next_order = 1
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaComponenteService(session=session)
    service.criar_componente(
        service_module.CriarDefPecaComponenteData(
            def_peca_pai_id=10,
            tipo_componente="PECA",
            def_peca_componente_id=20,
            regra_quantidade="POR_ALTURA_LARGURA",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["regra_quantidade"] == "POR_COMPRIMENTO_LARGURA"
    assert session.committed is True


def test_componente_service_edita_componente(monkeypatch) -> None:
    _FakeRepository.updated_payload = None
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaComponenteService(session=session)
    result = service.editar_componente(
        7,
        service_module.EditarDefPecaComponenteData(
            def_peca_pai_id=10,
            ordem=2,
            tipo_componente="mao_obra",
            def_peca_componente_id=None,
            referencia_componente="MO-01",
            descricao="Montagem",
            quantidade=Decimal("1.5"),
            regra_quantidade="",
            obrigatorio=False,
            ativo=True,
            observacoes="Teste",
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 7
    assert _FakeRepository.updated_payload["tipo_componente"] == "MAO_OBRA"
    assert _FakeRepository.updated_payload["regra_quantidade"] == "FIXA"
    assert result.obrigatorio is False
    assert session.committed is True


def test_componente_service_valida_parent_id_obrigatorio(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)
    session = _FakeSession()
    service = service_module.DefPecaComponenteService(session=session)

    try:
        service.criar_componente(
            service_module.CriarDefPecaComponenteData(
                def_peca_pai_id=None,
                tipo_componente="PECA",
                def_peca_componente_id=20,
            )
        )
    except ValueError as error:
        assert "def_peca_pai_id" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_componente_service_valida_quantidade_positiva(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)
    session = _FakeSession()
    service = service_module.DefPecaComponenteService(session=session)

    try:
        service.criar_componente(
            service_module.CriarDefPecaComponenteData(
                def_peca_pai_id=10,
                tipo_componente="PECA",
                def_peca_componente_id=20,
                quantidade=Decimal("0"),
            )
        )
    except ValueError as error:
        assert "quantidade" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_componente_service_valida_def_peca_componente_para_tipo_peca(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)
    session = _FakeSession()
    service = service_module.DefPecaComponenteService(session=session)

    try:
        service.criar_componente(
            service_module.CriarDefPecaComponenteData(
                def_peca_pai_id=10,
                tipo_componente="PECA",
                def_peca_componente_id=None,
            )
        )
    except ValueError as error:
        assert "def_peca_componente_id" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_componente_service_desativa_componente_existente(monkeypatch) -> None:
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaComponenteService(session=session)

    assert service.desativar_componente(9) is True
    assert _FakeRepository.deactivated_id == 9
    assert session.committed is True


def test_componente_service_desativa_componente_inexistente_sem_commit(monkeypatch) -> None:
    _FakeRepository.deactivate_result = False
    _FakeRepository.deactivated_id = None
    monkeypatch.setattr(service_module, "DefPecaComponenteRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaComponenteService(session=session)

    assert service.desativar_componente(11) is False
    assert _FakeRepository.deactivated_id == 11
    assert session.committed is False
