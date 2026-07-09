"""Tests for the OrcamentoValuesetLinha service."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

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
        "ref_le": None,
        "descricao_no_orcamento": None,
        "preco_tabela": None,
        "margem_percentagem": None,
        "desconto_percentagem": None,
        "preco_liquido": None,
        "unidade": None,
        "desperdicio_percentagem": None,
        "tipo_materia_prima": None,
        "familia_materia_prima": None,
        "coresp_orla_0_4": None,
        "coresp_orla_1_0": None,
        "comp_mp": None,
        "larg_mp": None,
        "esp_mp": None,
        "origem_dados": None,
        "origem_modelo_id": None,
        "origem_modelo_codigo": None,
        "editado_localmente": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return OrcamentoValuesetLinhaResumo(**base)


def _modelo(**kwargs):
    base = {"id": 99, "codigo": "ROUPEIRO_STANDARD"}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _modelo_linha(**kwargs):
    base = {
        "id": 1,
        "def_valueset_modelo_id": 99,
        "chave": "MATERIAL_PORTAS",
        "codigo_opcao": "MDF_19",
        "nome_opcao": "MDF 19mm",
        "padrao": True,
        "prioridade": 1,
        "ordem": 1,
        "descricao": None,
        "materia_prima_id": None,
        "ref_materia_prima": "FRT0001",
        "descricao_materia_prima": "MDF lacado",
        "valor_texto": None,
        "origem": None,
        "ref_le": "FRT0001",
        "descricao_no_orcamento": "MDF lacado branco",
        "preco_tabela": Decimal("10"),
        "margem_percentagem": Decimal("10"),
        "desconto_percentagem": Decimal("32"),
        "preco_liquido": Decimal("7.48"),
        "unidade": "m2",
        "desperdicio_percentagem": None,
        "tipo_materia_prima": "MDF",
        "familia_materia_prima": "LACADO",
        "coresp_orla_0_4": None,
        "coresp_orla_1_0": None,
        "comp_mp": None,
        "larg_mp": None,
        "esp_mp": None,
        "origem_dados": "MATERIA_PRIMA",
        "editado_localmente": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


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


class _FakeModeloRepository:
    modelo = None

    def __init__(self, _session: object) -> None:
        pass

    def get_by_id(self, id: int):
        return self.modelo


class _FakeModeloLinhaRepository:
    linhas: list = []

    def __init__(self, _session: object) -> None:
        pass

    def list_by_modelo(self, modelo_id: int):
        return self.linhas


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
    _FakeModeloRepository.modelo = None
    _FakeModeloLinhaRepository.linhas = []


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "OrcamentoValuesetLinhaRepository", _FakeRepository)
    monkeypatch.setattr(service_module, "DefValuesetModeloRepository", _FakeModeloRepository)
    monkeypatch.setattr(
        service_module, "DefValuesetModeloLinhaRepository", _FakeModeloLinhaRepository
    )
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


def test_criar_linha_com_prioridade(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarOrcamentoValuesetLinhaData(
            orcamento_versao_id=20,
            chave="FERRAGEM_CORREDICA",
            codigo_opcao="HETTICH",
            prioridade=2,
        )
    )

    assert _FakeRepository.created_payload["prioridade"] == 2
    assert session.committed is True


def test_criar_linha_prioridade_invalida_recusada(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha(
            service_module.CriarOrcamentoValuesetLinhaData(
                orcamento_versao_id=20,
                chave="FERRAGEM_CORREDICA",
                codigo_opcao="HETTICH",
                prioridade=0,
            )
        )
    except ValueError as error:
        assert "prioridade" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_obter_padrao_por_chave(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.default_existing = _resumo(id=7, prioridade=1, codigo_opcao="BLUM_TANDEM")

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


def test_importar_modelo_cria_linhas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeModeloRepository.modelo = _modelo(id=99, codigo="ROUPEIRO_STANDARD")
    _FakeModeloLinhaRepository.linhas = [_modelo_linha()]
    _FakeRepository.opcao_existing = None

    result = service.importar_modelo_para_orcamento(20, 99)

    assert result.modelo_codigo == "ROUPEIRO_STANDARD"
    assert result.criadas == 1
    assert result.atualizadas == 0
    assert result.ignoradas == 0

    payload = _FakeRepository.created_payload
    assert payload["origem_dados"] == "MODELO_VALUESET"
    assert payload["origem_modelo_id"] == 99
    assert payload["origem_modelo_codigo"] == "ROUPEIRO_STANDARD"
    assert payload["prioridade"] == 1
    assert payload["editado_localmente"] is False
    assert payload["ativo"] is True
    assert payload["preco_liquido"] == Decimal("7.48")
    assert payload["margem_percentagem"] == Decimal("10")
    assert payload["desconto_percentagem"] == Decimal("32")
    assert session.committed is True


def test_importar_modelo_atualiza_linha_nao_editada(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeModeloRepository.modelo = _modelo()
    _FakeModeloLinhaRepository.linhas = [_modelo_linha()]
    _FakeRepository.opcao_existing = _resumo(id=5, editado_localmente=False)

    result = service.importar_modelo_para_orcamento(20, 99)

    assert result.criadas == 0
    assert result.atualizadas == 1
    assert result.ignoradas == 0
    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 5


def test_importar_modelo_protege_linha_editada_localmente(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeModeloRepository.modelo = _modelo()
    _FakeModeloLinhaRepository.linhas = [_modelo_linha()]
    _FakeRepository.opcao_existing = _resumo(id=5, editado_localmente=True)

    result = service.importar_modelo_para_orcamento(20, 99)

    assert result.criadas == 0
    assert result.atualizadas == 0
    assert result.ignoradas == 1
    assert _FakeRepository.updated_payload is None


def test_importar_modelo_ignora_linhas_inativas(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeModeloRepository.modelo = _modelo()
    _FakeModeloLinhaRepository.linhas = [_modelo_linha(ativo=False)]
    _FakeRepository.opcao_existing = None

    result = service.importar_modelo_para_orcamento(20, 99)

    assert result.criadas == 0
    assert _FakeRepository.created_payload is None


def test_importar_modelo_inexistente_levanta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeModeloRepository.modelo = None

    try:
        service.importar_modelo_para_orcamento(20, 999)
    except ValueError as error:
        assert "modelo" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_editar_linha_recalcula_preco_liquido(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.editar_linha(
        5,
        service_module.EditarOrcamentoValuesetLinhaData(
            orcamento_versao_id=20,
            chave="MATERIAL_PORTAS",
            codigo_opcao="MDF",
            preco_tabela=Decimal("10"),
            margem_percentagem=Decimal("10"),
            desconto_percentagem=Decimal("10"),
        ),
    )

    payload = _FakeRepository.updated_payload
    assert payload["id"] == 5
    assert payload["preco_liquido"] == Decimal("9.90")
    assert session.committed is True


def test_editar_linha_marca_editado_localmente(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.editar_linha(
        5,
        service_module.EditarOrcamentoValuesetLinhaData(
            orcamento_versao_id=20,
            chave="MATERIAL_PORTAS",
            codigo_opcao="MDF",
            origem_dados="EDITADO_LOCALMENTE",
            editado_localmente=True,
        ),
    )

    payload = _FakeRepository.updated_payload
    assert payload["editado_localmente"] is True
    assert payload["origem_dados"] == "EDITADO_LOCALMENTE"


def test_editar_linha_preserva_dimensoes_e_origem_modelo(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.editar_linha(
        5,
        service_module.EditarOrcamentoValuesetLinhaData(
            orcamento_versao_id=20,
            chave="MATERIAL_PORTAS",
            codigo_opcao="MDF",
            comp_mp=Decimal("2750"),
            larg_mp=Decimal("1830"),
            esp_mp=Decimal("19"),
            origem_modelo_id=99,
            origem_modelo_codigo="ROUPEIRO_STANDARD",
        ),
    )

    payload = _FakeRepository.updated_payload
    assert payload["comp_mp"] == Decimal("2750")
    assert payload["larg_mp"] == Decimal("1830")
    assert payload["esp_mp"] == Decimal("19")
    assert payload["origem_modelo_id"] == 99
    assert payload["origem_modelo_codigo"] == "ROUPEIRO_STANDARD"


def test_copiar_snapshot_devolve_campos_sem_chave(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(
        id=5,
        ref_le="FRT0001",
        preco_tabela=Decimal("10"),
        unidade="m2",
        comp_mp=Decimal("2750"),
        prioridade=3,
    )

    snapshot = service.copiar_snapshot_linha(5)

    assert snapshot["ref_le"] == "FRT0001"
    assert snapshot["preco_tabela"] == Decimal("10")
    assert snapshot["unidade"] == "m2"
    assert snapshot["comp_mp"] == Decimal("2750")
    assert snapshot["prioridade"] == 3
    assert "chave" not in snapshot
    assert "codigo_opcao" not in snapshot


def test_colar_snapshot_mantem_chave_e_recalcula(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    snapshot = {
        "ref_le": "FRT0001",
        "unidade": "m2",
        "comp_mp": Decimal("2750"),
        "preco_tabela": Decimal("10"),
        "margem_percentagem": Decimal("10"),
        "desconto_percentagem": Decimal("10"),
        "prioridade": 2,
    }

    service.aplicar_snapshot_linha(5, snapshot)

    payload = _FakeRepository.updated_payload
    assert payload["id"] == 5
    assert payload["prioridade"] == 2
    assert payload["ref_le"] == "FRT0001"
    assert payload["unidade"] == "m2"
    assert payload["comp_mp"] == Decimal("2750")
    assert payload["preco_liquido"] == Decimal("9.90")
    assert payload["editado_localmente"] is True
    assert payload["origem_dados"] == "EDITADO_LOCALMENTE"
    assert "chave" not in payload
    assert "codigo_opcao" not in payload
    assert session.committed is True


def test_limpar_snapshot_remove_campos_mantendo_chave(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.limpar_snapshot_linha(5)

    payload = _FakeRepository.updated_payload
    assert payload["id"] == 5
    assert "prioridade" not in payload  # limpar dados não mexe na prioridade
    assert payload["ref_le"] is None
    assert payload["preco_tabela"] is None
    assert payload["preco_liquido"] is None
    assert payload["unidade"] is None
    assert payload["comp_mp"] is None
    assert payload["larg_mp"] is None
    assert payload["esp_mp"] is None
    assert payload["editado_localmente"] is True
    assert payload["origem_dados"] == "EDITADO_LOCALMENTE"
    assert "chave" not in payload
    assert "codigo_opcao" not in payload
    assert session.committed is True


def test_limpar_snapshot_pode_adiar_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.limpar_snapshot_linha(5, commit=False)

    assert _FakeRepository.updated_payload["id"] == 5
    assert session.committed is False
