"""Tests for the SystemSetting service."""

from __future__ import annotations

from app.repositories.system_setting_repository import SystemSettingResumo
from app.services import system_setting_service as service_module


def _resumo(**kwargs) -> SystemSettingResumo:
    base = {
        "id": 1,
        "chave": "pasta_base_orcamentos",
        "valor": "",
        "descricao": "Pasta base dos Orcamentos",
        "tipo": "pasta",
        "grupo": "Orcamentos",
        "ativo": True,
    }
    base.update(kwargs)
    return SystemSettingResumo(**base)


class _FakeRepository:
    all_rows: list[SystemSettingResumo] = []
    group_rows: list[SystemSettingResumo] = []
    by_key: SystemSettingResumo | None = None
    requested_group: str | None = None
    requested_key: str | None = None
    updated_payload: tuple[str, str | None] | None = None
    upsert_payload: dict[str, object] | None = None
    update_results: dict[str, SystemSettingResumo | None] = {}

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self) -> list[SystemSettingResumo]:
        return self.all_rows

    def list_by_group(self, grupo: str) -> list[SystemSettingResumo]:
        self.__class__.requested_group = grupo
        return self.group_rows

    def get_by_key(self, chave: str) -> SystemSettingResumo | None:
        self.__class__.requested_key = chave
        return self.by_key

    def update_setting(self, chave: str, valor: str | None) -> SystemSettingResumo | None:
        self.__class__.updated_payload = (chave, valor)
        if chave in self.update_results:
            return self.update_results[chave]
        return self.by_key

    def upsert_setting(self, **kwargs) -> SystemSettingResumo:
        self.__class__.upsert_payload = kwargs
        return _resumo(
            chave=kwargs["chave"],
            valor=kwargs["valor"],
            descricao=kwargs.get("descricao"),
            tipo=kwargs.get("tipo", "texto"),
            grupo=kwargs.get("grupo"),
            ativo=kwargs.get("ativo", True),
        )


class _FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    def commit(self) -> None:
        self.commit_count += 1


def _reset() -> None:
    _FakeRepository.all_rows = []
    _FakeRepository.group_rows = []
    _FakeRepository.by_key = None
    _FakeRepository.requested_group = None
    _FakeRepository.requested_key = None
    _FakeRepository.updated_payload = None
    _FakeRepository.upsert_payload = None
    _FakeRepository.update_results = {}


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "SystemSettingRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.SystemSettingService(session=session), session


def test_listar_configuracoes(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.all_rows = [_resumo(chave="modelo_openai_texto", valor="gpt-4o-mini")]

    assert service.listar_configuracoes() == [
        _resumo(chave="modelo_openai_texto", valor="gpt-4o-mini")
    ]


def test_listar_por_grupo_normaliza(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.group_rows = [_resumo(grupo="IA")]

    assert service.listar_por_grupo(" IA ") == [_resumo(grupo="IA")]
    assert _FakeRepository.requested_group == "IA"


def test_obter_valor_devolve_valor_existente(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_key = _resumo(chave="provedor_resposta_ia", valor="openai")

    assert service.obter_valor(" provedor_resposta_ia ") == "openai"
    assert _FakeRepository.requested_key == "provedor_resposta_ia"


def test_obter_valor_devolve_default_quando_nao_existe(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    assert service.obter_valor("inexistente", default="x") == "x"


def test_guardar_valor_atualiza_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_key = _resumo(chave="ficheiro_log")

    result = service.guardar_valor(" ficheiro_log ", " C:/log.txt ")

    assert _FakeRepository.updated_payload == ("ficheiro_log", "C:/log.txt")
    assert result.chave == "ficheiro_log"
    assert session.commit_count == 1


def test_guardar_valor_cria_quando_nao_existe(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.guardar_valor("nova_chave", "valor")

    assert _FakeRepository.upsert_payload is not None
    assert _FakeRepository.upsert_payload["chave"] == "nova_chave"
    assert _FakeRepository.upsert_payload["valor"] == "valor"
    assert result.chave == "nova_chave"
    assert session.commit_count == 1


def test_guardar_varios_guarda_e_faz_um_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.update_results = {
        "a": _resumo(chave="a", valor="1"),
        "b": _resumo(chave="b", valor="2"),
    }

    results = service.guardar_varios({"a": " 1 ", "b": "2"})

    assert [result.chave for result in results] == ["a", "b"]
    assert session.commit_count == 1


def test_chave_obrigatoria(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.guardar_valor("   ", "valor")
    except ValueError as error:
        assert "chave" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.commit_count == 0
