"""Tests for the Orcamento service."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.repositories.orcamento_repository import OrcamentoCriado, OrcamentoResumo
from app.services import orcamento_service as service_module


class _FakeRepository:
    rows: list[OrcamentoResumo] = []
    next_number = "260002"
    next_ano: int | None = None
    created_payload: dict[str, object] | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_orcamentos(self) -> list[OrcamentoResumo]:
        return self.rows

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
        ano=2026,
        num_orcamento="260001",
        numero_versao=1,
        cliente_nome="Cliente Teste",
        obra="Obra Teste",
        estado="rascunho",
        preco_total=Decimal("123.45"),
        created_at=datetime(2026, 6, 5, 10, 30),
    )
    _FakeRepository.rows = [row]
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)

    service = service_module.OrcamentoService(session=object())

    assert service.list_orcamentos() == [row]


def test_orcamento_service_cria_orcamento_com_proximo_numero(monkeypatch) -> None:
    _FakeRepository.next_number = "260002"
    _FakeRepository.next_ano = None
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.OrcamentoService(session=session)
    result = service.criar_orcamento_simples(
        service_module.CriarOrcamentoSimplesData(
            nome_cliente="Cliente Novo",
            email_cliente="cliente@teste.local",
            telefone_cliente="912345678",
            obra="Obra Nova",
            descricao="Descricao",
            localizacao="Local",
            ref_cliente="REF",
            created_by_id=7,
            ano=2026,
        )
    )

    assert _FakeRepository.next_ano == 2026
    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["num_orcamento"] == "260002"
    assert _FakeRepository.created_payload["created_by_id"] == 7
    assert result.codigo_versao == "260002_01"
    assert session.committed is True


def test_orcamento_service_valida_campos_obrigatorios(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)
    service = service_module.OrcamentoService(session=_FakeSession())

    try:
        service.criar_orcamento_simples(
            service_module.CriarOrcamentoSimplesData(
                nome_cliente="",
                email_cliente=None,
                telefone_cliente=None,
                obra="Obra",
                descricao=None,
                localizacao=None,
                ref_cliente=None,
            )
        )
    except ValueError as error:
        assert "nome_cliente" in str(error)
    else:
        raise AssertionError("Expected ValueError")
