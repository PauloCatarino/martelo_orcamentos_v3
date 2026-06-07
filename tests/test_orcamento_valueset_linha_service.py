"""Tests for the OrcamentoValuesetLinha service."""

from __future__ import annotations

from app.repositories.orcamento_valueset_linha_repository import OrcamentoValuesetLinhaResumo
from app.services import orcamento_valueset_linha_service as service_module


def _resumo(**kwargs) -> OrcamentoValuesetLinhaResumo:
    base = {
        "id": 1,
        "orcamento_versao_id": 20,
        "chave": "FERRAGEM_CORREDICA",
        "codigo_opcao": "FERRAGEM_CORREDICA",
        "nome_opcao": None,
        "padrao": False,
        "ordem": 1,
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
    rows: list[OrcamentoValuesetLinhaResumo] = []
    opcao_existing: OrcamentoValuesetLinhaResumo | None = None
    default_existing: OrcamentoValuesetLinhaResumo | None = None
    by_id: OrcamentoValuesetLinhaResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    set_padrao_calls: list = []
    clear_calls: list = []
    deactivate_result = True
    activate_result = True

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self):
        return self.rows

    def list_active(self):
        return self.rows

    def list_by_orcamento_versao(self, orcamento_versao_id: int):
        return self.rows

    def list_by_versao_chave(self, orcamento_versao_id: int, chave: str):
        return self.rows

    def get_by_id(self, id: int):
        return self.by_id if self.by_id is not None else _resumo(id=id)

    def get_by_versao_chave(self, orcamento_versao_id: int, chave: str):
        return None

    def get_by_versao_chave_opcao(self, orcamento_versao_id: int, chave: str, codigo_opcao: str):
        return self.opcao_existing

    def get_default_by_versao_chave(self, orcamento_versao_id: int, chave: str):
        return self.default_existing

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

    def set_padrao(self, id: int, padrao: bool) -> bool:
        self.__class__.set_padrao_calls.append((id, padrao))
        return True

    def clear_padrao_for_chave(self, orcamento_versao_id: int, chave: str, exclude_id=None) -> None:
        self.__class__.clear_calls.append((orcamento_versao_id, chave, exclude_id))


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.rows = []
    _FakeRepository.opcao_existing = None
    _FakeRepository.default_existing = None
    _FakeRepository.by_id = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.set_padrao_calls = []
    _FakeRepository.clear_calls = []
    _FakeRepository.deactivate_result = True
    _FakeRepository.activate_result = True


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "OrcamentoValuesetLinhaRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.OrcamentoValuesetLinhaService(session=session), session


def test_criar_linha_normaliza_chave_e_opcao_defaults(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarOrcamentoValuesetLinhaData(
            orcamento_versao_id=20,
            chave=" ferragem_corredica ",
        )
    )

    payload = _FakeRepository.created_payload
    assert payload["chave"] == "FERRAGEM_CORREDICA"
    assert payload["codigo_opcao"] == "FERRAGEM_CORREDICA"
    assert payload["padrao"] is False
    assert payload["ordem"] == 1
    assert session.committed is True


def test_criar_linha_valida_versao_obrigatoria(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha(
            service_module.CriarOrcamentoValuesetLinhaData(
                orcamento_versao_id=None,
                chave="FERRAGEM_CORREDICA",
            )
        )
    except ValueError as error:
        assert "orcamento_versao_id" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_varias_opcoes_mesma_chave_permitidas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.opcao_existing = None

    service.criar_linha(
        service_module.CriarOrcamentoValuesetLinhaData(
            orcamento_versao_id=20,
            chave="FERRAGEM_CORREDICA",
            codigo_opcao="HETTICH",
        )
    )

    assert _FakeRepository.created_payload["codigo_opcao"] == "HETTICH"
    assert session.committed is True


def test_duplicar_chave_e_opcao_recusada(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.opcao_existing = _resumo(id=2, codigo_opcao="BLUM_TANDEM")

    try:
        service.criar_linha(
            service_module.CriarOrcamentoValuesetLinhaData(
                orcamento_versao_id=20,
                chave="FERRAGEM_CORREDICA",
                codigo_opcao="BLUM_TANDEM",
            )
        )
    except ValueError as error:
        assert "opcao" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_so_uma_padrao_por_chave(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.default_existing = _resumo(id=5, padrao=True, codigo_opcao="BLUM_TANDEM")

    try:
        service.criar_linha(
            service_module.CriarOrcamentoValuesetLinhaData(
                orcamento_versao_id=20,
                chave="FERRAGEM_CORREDICA",
                codigo_opcao="HETTICH",
                padrao=True,
            )
        )
    except ValueError as error:
        assert "padrao" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_obter_padrao_por_chave(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.default_existing = _resumo(id=7, padrao=True, codigo_opcao="BLUM_TANDEM")

    result = service.obter_padrao_por_chave(20, "ferragem_corredica")

    assert result is not None
    assert result.id == 7


def test_definir_como_padrao(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(
        id=5, orcamento_versao_id=20, chave="FERRAGEM_CORREDICA", codigo_opcao="HETTICH"
    )

    assert service.definir_como_padrao(5) is True
    assert (20, "FERRAGEM_CORREDICA", 5) in _FakeRepository.clear_calls
    assert (5, True) in _FakeRepository.set_padrao_calls
    assert session.committed is True
