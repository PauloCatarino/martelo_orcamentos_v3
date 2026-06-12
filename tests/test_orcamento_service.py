"""Tests for the Orcamento service."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.domain.precos import MargensOrcamento
from app.repositories.orcamento_repository import (
    OrcamentoCriado,
    OrcamentoResumo,
    OrcamentoVersaoCriada,
)
from app.services import orcamento_service as service_module


class _FakeRepository:
    rows: list[OrcamentoResumo] = []
    next_number = "260002"
    next_ano: int | None = None
    created_payload: dict[str, object] | None = None
    nova_versao_payload: tuple | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_orcamentos(self) -> list[OrcamentoResumo]:
        return self.rows

    def get_orcamento_by_versao_id(self, orcamento_versao_id: int) -> OrcamentoResumo | None:
        for row in self.rows:
            if row.orcamento_versao_id == orcamento_versao_id:
                return row

        return None

    def get_next_num_orcamento(self, ano: int) -> str:
        self.__class__.next_ano = ano
        return self.next_number

    def create_orcamento_com_versao_01(self, **kwargs) -> OrcamentoCriado:
        self.__class__.created_payload = kwargs
        return OrcamentoCriado(
            ano=kwargs["ano"],
            num_orcamento=kwargs["num_orcamento"],
            numero_versao=1,
            codigo_versao=f"{kwargs['num_orcamento']}_01",
            cliente_nome=kwargs["nome_cliente"],
        )

    def criar_nova_versao(
        self, orcamento_versao_id: int, created_by_id: int | None = None
    ) -> OrcamentoVersaoCriada:
        self.__class__.nova_versao_payload = (orcamento_versao_id, created_by_id)
        return OrcamentoVersaoCriada(
            orcamento_id=1,
            orcamento_versao_id=orcamento_versao_id + 1,
            numero_versao=2,
            codigo_versao="260001_02",
        )


class _FakeMargensRepository:
    """Fake default-margins repository for the initial-margins resolution."""

    margens_standard: MargensOrcamento | None = None
    margens_por_cliente: dict[int, MargensOrcamento] = {}
    margens_por_user: dict[int, MargensOrcamento] = {}
    cliente_id_por_contacto: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def get_margens_ativas_standard(self) -> MargensOrcamento | None:
        return self.margens_standard

    def get_margens_ativas_por_cliente(self, cliente_id: int) -> MargensOrcamento | None:
        return self.margens_por_cliente.get(cliente_id)

    def get_margens_ativas_por_user(self, user_id: int) -> MargensOrcamento | None:
        return self.margens_por_user.get(user_id)

    def find_cliente_id_por_contacto(self, nome, email) -> int | None:
        return self.cliente_id_por_contacto

    @classmethod
    def reset(cls) -> None:
        cls.margens_standard = None
        cls.margens_por_cliente = {}
        cls.margens_por_user = {}
        cls.cliente_id_por_contacto = None


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def test_orcamento_service_returns_empty_list_when_repository_is_empty(monkeypatch) -> None:
    _FakeRepository.rows = []
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)

    service = service_module.OrcamentoService(session=object())

    assert service.list_orcamentos() == []


def test_orcamento_service_returns_repository_rows(monkeypatch) -> None:
    row = OrcamentoResumo(
        orcamento_id=1,
        orcamento_versao_id=10,
        ano=2026,
        num_orcamento="260001",
        numero_versao=1,
        codigo_versao="260001_01",
        cliente_nome="Cliente Teste",
        obra="Obra Teste",
        descricao="Descricao Teste",
        localizacao="Local Teste",
        ref_cliente="REF-TESTE",
        estado="rascunho",
        preco_total=Decimal("123.45"),
        created_at=datetime(2026, 6, 5, 10, 30),
    )
    _FakeRepository.rows = [row]
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)

    service = service_module.OrcamentoService(session=object())

    assert service.list_orcamentos() == [row]


def test_orcamento_service_get_orcamento_by_versao_id(monkeypatch) -> None:
    row = OrcamentoResumo(
        orcamento_id=1,
        orcamento_versao_id=10,
        ano=2026,
        num_orcamento="260001",
        numero_versao=1,
        codigo_versao="260001_01",
        cliente_nome="Cliente Teste",
        obra="Obra Teste",
        descricao="Descricao Teste",
        localizacao="Local Teste",
        ref_cliente="REF-TESTE",
        estado="rascunho",
        preco_total=Decimal("200.00"),
        created_at=datetime(2026, 6, 5, 10, 30),
    )
    _FakeRepository.rows = [row]
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)

    service = service_module.OrcamentoService(session=object())

    assert service.get_orcamento_by_versao_id(10) == row
    assert service.get_orcamento_by_versao_id(999) is None


def _make_service(monkeypatch) -> tuple[service_module.OrcamentoService, _FakeSession]:
    _FakeRepository.next_ano = None
    _FakeRepository.created_payload = None
    _FakeRepository.nova_versao_payload = None
    _FakeMargensRepository.reset()
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)
    monkeypatch.setattr(
        service_module, "DefMargemPadraoRepository", _FakeMargensRepository
    )
    session = _FakeSession()
    return service_module.OrcamentoService(session=session), session


def _criar_data(**overrides) -> service_module.CriarOrcamentoSimplesData:
    base = {
        "nome_cliente": "Cliente Novo",
        "email_cliente": "cliente@teste.local",
        "telefone_cliente": "912345678",
        "obra": "Obra Nova",
        "descricao": "Descricao",
        "localizacao": "Local",
        "ref_cliente": "REF",
        "created_by_id": 7,
        "ano": 2026,
    }
    base.update(overrides)
    return service_module.CriarOrcamentoSimplesData(**base)


def test_orcamento_service_cria_orcamento_com_proximo_numero(monkeypatch) -> None:
    _FakeRepository.next_number = "260002"
    service, session = _make_service(monkeypatch)

    result = service.criar_orcamento_simples(_criar_data())

    assert _FakeRepository.next_ano == 2026
    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["num_orcamento"] == "260002"
    assert _FakeRepository.created_payload["created_by_id"] == 7
    assert result.codigo_versao == "260002_01"
    assert session.committed is True


def test_orcamento_service_valida_campos_obrigatorios(monkeypatch) -> None:
    service, _session = _make_service(monkeypatch)

    try:
        service.criar_orcamento_simples(
            _criar_data(nome_cliente="", email_cliente=None, telefone_cliente=None)
        )
    except ValueError as error:
        assert "nome_cliente" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_criar_orcamento_aplica_margens_standard(monkeypatch) -> None:
    service, _session = _make_service(monkeypatch)
    standard = MargensOrcamento(margem_lucro_pct=Decimal("10"))
    _FakeMargensRepository.margens_standard = standard

    service.criar_orcamento_simples(_criar_data())

    assert _FakeRepository.created_payload["margens"] == standard


def test_criar_orcamento_aplica_margens_do_cliente(monkeypatch) -> None:
    service, _session = _make_service(monkeypatch)
    do_cliente = MargensOrcamento(margem_lucro_pct=Decimal("20"))
    _FakeMargensRepository.cliente_id_por_contacto = 4
    _FakeMargensRepository.margens_por_cliente = {4: do_cliente}
    _FakeMargensRepository.margens_standard = MargensOrcamento(
        margem_lucro_pct=Decimal("10")
    )

    service.criar_orcamento_simples(_criar_data(margens_escolha="CLIENTE"))

    assert _FakeRepository.created_payload["margens"] == do_cliente


def test_criar_orcamento_aplica_margens_do_utilizador(monkeypatch) -> None:
    service, _session = _make_service(monkeypatch)
    do_user = MargensOrcamento(margem_lucro_pct=Decimal("30"))
    _FakeMargensRepository.margens_por_user = {7: do_user}

    service.criar_orcamento_simples(_criar_data(margens_escolha="UTILIZADOR"))

    assert _FakeRepository.created_payload["margens"] == do_user


def test_criar_orcamento_sem_registo_aplicavel_fica_a_zeros(monkeypatch) -> None:
    """No applicable record -> margens None (column defaults = zeros)."""
    service, _session = _make_service(monkeypatch)

    # STANDARD chosen but no record; CLIENTE chosen but contact unknown;
    # UTILIZADOR chosen but the user has no record.
    service.criar_orcamento_simples(_criar_data())
    assert _FakeRepository.created_payload["margens"] is None

    service.criar_orcamento_simples(_criar_data(margens_escolha="CLIENTE"))
    assert _FakeRepository.created_payload["margens"] is None

    service.criar_orcamento_simples(_criar_data(margens_escolha="UTILIZADOR"))
    assert _FakeRepository.created_payload["margens"] is None


def test_duplicar_versao_delegada_ao_repositorio(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    result = service.duplicar_versao(10, created_by_id=7)

    assert _FakeRepository.nova_versao_payload == (10, 7)
    assert result.numero_versao == 2
    assert session.committed is True
