"""Tests for the Orcamento service."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.domain.orcamento_estados import ESTADO_INICIAL
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
    update_payload: dict[str, object] | None = None
    dados_versao_payload: dict[str, object] | None = None
    enc_phc_payload: tuple[int, str | None] | None = None
    estado_payload: tuple[int, str] | None = None
    utilizador_payload: tuple[int, int | None] | None = None
    cliente_payload: tuple[int, int] | None = None
    nova_versao_payload: tuple | None = None
    ref_cliente_pesquisada: str | None = None
    numeros_existentes: set[tuple[int, str]] = set()

    def __init__(self, _session: object) -> None:
        pass

    def list_orcamentos(self) -> list[OrcamentoResumo]:
        return self.rows

    def find_by_ref_cliente(self, ref_cliente: str) -> list[OrcamentoResumo]:
        self.__class__.ref_cliente_pesquisada = ref_cliente
        return self.rows

    def get_orcamento_by_versao_id(self, orcamento_versao_id: int) -> OrcamentoResumo | None:
        for row in self.rows:
            if row.orcamento_versao_id == orcamento_versao_id:
                return row

        return None

    def get_next_num_orcamento(self, ano: int) -> str:
        self.__class__.next_ano = ano
        return self.next_number

    def num_orcamento_existe(self, ano: int, num_orcamento: str) -> bool:
        return (ano, num_orcamento) in self.numeros_existentes

    def create_orcamento_com_versao_01(self, **kwargs) -> OrcamentoCriado:
        self.__class__.created_payload = kwargs
        return OrcamentoCriado(
            ano=kwargs["ano"],
            num_orcamento=kwargs["num_orcamento"],
            numero_versao=1,
            codigo_versao=f"{kwargs['num_orcamento']}_01",
            cliente_nome="Cliente Teste",
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

    def duplicar_versao_profunda(
        self, orcamento_versao_id: int, created_by_id: int | None = None
    ) -> OrcamentoVersaoCriada:
        self.__class__.nova_versao_payload = (orcamento_versao_id, created_by_id)
        return OrcamentoVersaoCriada(
            orcamento_id=1,
            orcamento_versao_id=orcamento_versao_id + 1,
            numero_versao=2,
            codigo_versao="260001_02",
        )

    def update_orcamento(self, orcamento_id, **kwargs) -> bool:
        self.__class__.update_payload = kwargs
        return True

    def update_versao_dados(self, orcamento_versao_id, **kwargs) -> bool:
        self.__class__.dados_versao_payload = kwargs
        return True

    def update_enc_phc(self, orcamento_versao_id: int, enc_phc: str | None) -> bool:
        self.__class__.enc_phc_payload = (orcamento_versao_id, enc_phc)
        return True

    def update_estado(self, orcamento_versao_id: int, estado: str) -> bool:
        self.__class__.estado_payload = (orcamento_versao_id, estado)
        return True

    def update_utilizador(
        self, orcamento_versao_id: int, utilizador_id: int | None
    ) -> bool:
        self.__class__.utilizador_payload = (orcamento_versao_id, utilizador_id)
        return True

    def update_cliente(self, orcamento_id: int, cliente_id: int) -> bool:
        self.__class__.cliente_payload = (orcamento_id, cliente_id)
        return True


class _FakeMargensRepository:
    """Fake default-margins repository for the initial-margins resolution."""

    margens_standard: MargensOrcamento | None = None
    margens_por_cliente: dict[int, MargensOrcamento] = {}
    margens_por_user: dict[int, MargensOrcamento] = {}

    def __init__(self, _session: object) -> None:
        pass

    def get_margens_ativas_standard(self) -> MargensOrcamento | None:
        return self.margens_standard

    def get_margens_ativas_por_cliente(self, cliente_id: int) -> MargensOrcamento | None:
        return self.margens_por_cliente.get(cliente_id)

    def get_margens_ativas_por_user(self, user_id: int) -> MargensOrcamento | None:
        return self.margens_por_user.get(user_id)

    @classmethod
    def reset(cls) -> None:
        cls.margens_standard = None
        cls.margens_por_cliente = {}
        cls.margens_por_user = {}


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.added: list[object] = []
        self.current_versao: object | None = None

    def commit(self) -> None:
        self.committed = True

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def get(self, _model: object, _id: int) -> object | None:
        return self.current_versao


class _FakeEncomendasService:
    """Fake PHC-orders service capturing the replaced set (phase 5)."""

    substituir_payload: tuple[int, list] | None = None

    def __init__(self, _session: object) -> None:
        pass

    def substituir_encomendas(self, orcamento_versao_id: int, encomendas) -> list:
        self.__class__.substituir_payload = (orcamento_versao_id, list(encomendas))
        return list(encomendas)


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
        estado=ESTADO_INICIAL,
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
        estado=ESTADO_INICIAL,
        preco_total=Decimal("200.00"),
        created_at=datetime(2026, 6, 5, 10, 30),
    )
    _FakeRepository.rows = [row]
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)

    service = service_module.OrcamentoService(session=object())

    assert service.get_orcamento_by_versao_id(10) == row
    assert service.get_orcamento_by_versao_id(999) is None


def test_orcamento_service_find_orcamentos_por_ref_cliente(monkeypatch) -> None:
    row = OrcamentoResumo(
        orcamento_id=1,
        orcamento_versao_id=10,
        ano=2026,
        num_orcamento="260001",
        numero_versao=1,
        codigo_versao="260001_01",
        cliente_nome="Cliente Teste",
        obra="Obra Teste",
        descricao=None,
        localizacao=None,
        ref_cliente="REF-TESTE",
        estado=ESTADO_INICIAL,
        preco_total=Decimal("200.00"),
        created_at=datetime(2026, 6, 5, 10, 30),
    )
    _FakeRepository.rows = [row]
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)

    service = service_module.OrcamentoService(session=object())

    assert service.find_orcamentos_por_ref_cliente(" REF-TESTE ") == [row]
    assert _FakeRepository.ref_cliente_pesquisada == " REF-TESTE "


def _make_service(monkeypatch) -> tuple[service_module.OrcamentoService, _FakeSession]:
    _FakeRepository.next_number = "260002"
    _FakeRepository.next_ano = None
    _FakeRepository.created_payload = None
    _FakeRepository.update_payload = None
    _FakeRepository.dados_versao_payload = None
    _FakeRepository.enc_phc_payload = None
    _FakeRepository.estado_payload = None
    _FakeRepository.utilizador_payload = None
    _FakeRepository.cliente_payload = None
    _FakeRepository.nova_versao_payload = None
    _FakeRepository.ref_cliente_pesquisada = None
    _FakeRepository.numeros_existentes = set()
    _FakeMargensRepository.reset()
    _FakeEncomendasService.substituir_payload = None
    monkeypatch.setattr(service_module, "OrcamentoRepository", _FakeRepository)
    monkeypatch.setattr(
        service_module, "DefMargemPadraoRepository", _FakeMargensRepository
    )
    monkeypatch.setattr(
        service_module, "OrcamentoEncomendaPhcService", _FakeEncomendasService
    )
    session = _FakeSession()
    return service_module.OrcamentoService(session=session), session


def _criar_data(**overrides) -> service_module.CriarOrcamentoSimplesData:
    base = {
        "cliente_id": 4,
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
    assert _FakeRepository.created_payload["cliente_id"] == 4
    assert _FakeRepository.created_payload["num_orcamento"] == "260002"
    assert _FakeRepository.created_payload["created_by_id"] == 7
    assert result.codigo_versao == "260002_01"
    assert session.committed is True


def test_criar_orcamento_antigo_usa_numero_e_pasta_manual(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    result = service.criar_orcamento_simples(
        _criar_data(
            ano=2025,
            num_orcamento="1049",
            pasta_manual=r"\\SERVER_LE\Dep._Orcamentos\2025\1049_COSTA",
        )
    )

    # O número manual é usado tal e qual; a numeração sequencial não corre.
    assert _FakeRepository.next_ano is None
    assert _FakeRepository.created_payload["ano"] == 2025
    assert _FakeRepository.created_payload["num_orcamento"] == "1049"
    assert (
        _FakeRepository.created_payload["pasta_manual"]
        == r"\\SERVER_LE\Dep._Orcamentos\2025\1049_COSTA"
    )
    assert result.codigo_versao == "1049_01"
    assert session.committed is True


def test_criar_orcamento_antigo_rejeita_numero_duplicado(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)
    _FakeRepository.numeros_existentes = {(2025, "1049")}

    try:
        service.criar_orcamento_simples(
            _criar_data(ano=2025, num_orcamento="1049")
        )
    except ValueError as error:
        assert "1049" in str(error)
        assert "2025" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_orcamento_sem_numero_manual_mantem_sequencial(monkeypatch) -> None:
    service, _session = _make_service(monkeypatch)
    _FakeRepository.next_number = "260007"

    service.criar_orcamento_simples(_criar_data(num_orcamento="   "))

    assert _FakeRepository.next_ano == 2026
    assert _FakeRepository.created_payload["num_orcamento"] == "260007"
    assert _FakeRepository.created_payload["pasta_manual"] is None


def test_criar_orcamento_passa_enc_phc_e_info(monkeypatch) -> None:
    service, _session = _make_service(monkeypatch)

    service.criar_orcamento_simples(
        _criar_data(enc_phc="1028", info_1="A", info_2="B")
    )

    assert _FakeRepository.created_payload["enc_phc"] == "1028"
    assert _FakeRepository.created_payload["info_1"] == "A"
    assert _FakeRepository.created_payload["info_2"] == "B"


def test_criar_orcamento_aceita_obra_vazia(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    result = service.criar_orcamento_simples(_criar_data(obra=""))

    assert result.codigo_versao == "260002_01"
    assert _FakeRepository.created_payload["obra"] == ""
    assert session.committed is True


def test_editar_orcamento_passa_enc_phc_e_info(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)
    session.current_versao = type("Versao", (), {"estado": "Falta Or\u00e7amentar"})()

    result = service.editar_orcamento(
        1,
        service_module.EditarOrcamentoData(
            obra="X",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado="Enviado",
            enc_phc="1028",
            info_1="A",
            info_2="B",
            utilizador_id=7,
        ),
        orcamento_versao_id=10,
    )

    assert result is True
    # info_1/info_2 (e obra/descricao/localizacao) pertencem agora à versão.
    assert _FakeRepository.dados_versao_payload["info_1"] == "A"
    assert _FakeRepository.dados_versao_payload["info_2"] == "B"
    assert _FakeRepository.dados_versao_payload["obra"] == "X"
    # Legacy enc_phc becomes the single principal order (phase 5).
    versao_id, encomendas = _FakeEncomendasService.substituir_payload
    assert versao_id == 10
    assert [(enc.numero, enc.is_principal) for enc in encomendas] == [
        ("1028", True)
    ]
    assert _FakeRepository.estado_payload == (10, "Enviado")
    assert _FakeRepository.utilizador_payload == (10, 7)
    assert _FakeRepository.cliente_payload is None
    assert session.committed is True
    assert len(session.added) == 1
    evento = session.added[0]
    assert evento.orcamento_versao_id == 10
    assert evento.tipo == "estado"
    assert evento.descricao == "Estado: Falta Or\u00e7amentar \u2192 Enviado"


def test_editar_orcamento_nao_regista_historico_sem_mudar_estado(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)
    session.current_versao = type("Versao", (), {"estado": "Enviado"})()

    service.editar_orcamento(
        1,
        service_module.EditarOrcamentoData(
            obra="X",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado="Enviado",
        ),
        orcamento_versao_id=10,
    )

    assert session.added == []


def test_editar_orcamento_troca_cliente(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    service.editar_orcamento(
        1,
        service_module.EditarOrcamentoData(
            obra="X",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado="Enviado",
            utilizador_id=7,
            cliente_id=9,
        ),
        orcamento_versao_id=10,
    )

    assert _FakeRepository.cliente_payload == (1, 9)
    assert session.committed is True


def test_editar_orcamento_estado_invalido_levanta_valueerror(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    try:
        service.editar_orcamento(
            1,
            service_module.EditarOrcamentoData(
                obra="X",
                descricao=None,
                localizacao=None,
                ref_cliente=None,
                estado="rascunho",
            ),
            orcamento_versao_id=10,
        )
    except ValueError as error:
        assert "Estado" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert _FakeRepository.estado_payload is None
    assert _FakeRepository.utilizador_payload is None
    assert session.committed is False


def test_orcamento_service_valida_campos_obrigatorios(monkeypatch) -> None:
    service, _session = _make_service(monkeypatch)

    try:
        service.criar_orcamento_simples(_criar_data(cliente_id=None))
    except ValueError as error:
        assert "cliente_id" in str(error)
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
    _FakeMargensRepository.margens_por_cliente = {4: do_cliente}
    _FakeMargensRepository.margens_standard = MargensOrcamento(
        margem_lucro_pct=Decimal("10")
    )

    service.criar_orcamento_simples(
        _criar_data(margens_escolha="CLIENTE", cliente_id=4)
    )

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
    assert len(session.added) == 1
    evento = session.added[0]
    assert evento.orcamento_versao_id == result.orcamento_versao_id
    assert evento.tipo == "versao"
    assert evento.descricao == "Vers\u00e3o 260001_02 criada (duplicada)"
