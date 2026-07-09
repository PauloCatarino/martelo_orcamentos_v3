"""Tests for the OrcamentoItemValuesetLinha service."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaResumo,
)
from app.repositories.orcamento_valueset_linha_repository import OrcamentoValuesetLinhaResumo
from app.services import orcamento_item_valueset_linha_service as service_module


def _item_resumo(**kwargs) -> OrcamentoItemValuesetLinhaResumo:
    base = {
        "id": 1,
        "orcamento_item_id": 30,
        "chave": "MATERIAL_CAIXOTE",
        "codigo_opcao": "MATERIAL_CAIXOTE",
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
        "origem_orcamento_valueset_linha_id": None,
        "origem_orcamento_versao_id": None,
        "origem_modelo_id": None,
        "origem_modelo_codigo": None,
        "origem_dados": None,
        "herdado_do_orcamento": True,
        "editado_localmente": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return OrcamentoItemValuesetLinhaResumo(**base)


def _versao_resumo(**kwargs) -> OrcamentoValuesetLinhaResumo:
    base = {
        "id": 2,
        "orcamento_versao_id": 20,
        "chave": "MATERIAL_CAIXOTE",
        "codigo_opcao": "MATERIAL_CAIXOTE",
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
    base = {"id": 88, "codigo": "COZINHA_STANDARD"}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _modelo_linha(**kwargs):
    base = {
        "id": 1,
        "chave": "MATERIAL_FRENTES",
        "codigo_opcao": "MDF",
        "nome_opcao": "MDF B3002",
        "padrao": True,
        "prioridade": 1,
        "ordem": 1,
        "descricao": None,
        "materia_prima_id": None,
        "ref_materia_prima": "FRT0001",
        "descricao_materia_prima": "MDF B3002",
        "valor_texto": None,
        "origem": None,
        "ref_le": "FRT0001",
        "descricao_no_orcamento": "MDF B3002 19mm",
        "preco_tabela": Decimal("10"),
        "margem_percentagem": Decimal("10"),
        "desconto_percentagem": Decimal("32"),
        "preco_liquido": Decimal("7.48"),
        "unidade": "m2",
        "desperdicio_percentagem": None,
        "tipo_materia_prima": "MDF",
        "familia_materia_prima": "LACADO",
        "coresp_orla_0_4": "ORLA_A",
        "coresp_orla_1_0": None,
        "comp_mp": Decimal("2750"),
        "larg_mp": Decimal("1830"),
        "esp_mp": Decimal("19"),
        "observacoes": None,
        "ativo": True,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


class _FakeItemRepository:
    rows: list[OrcamentoItemValuesetLinhaResumo] = []
    opcao_existing: OrcamentoItemValuesetLinhaResumo | None = None
    item_default: OrcamentoItemValuesetLinhaResumo | None = None
    by_id: OrcamentoItemValuesetLinhaResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    set_padrao_calls: list = []
    clear_calls: list = []
    deactivated_ids: list = []
    deactivate_result = True
    activate_result = True

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self):
        return self.rows

    def list_active(self):
        return self.rows

    def list_by_orcamento_item(self, orcamento_item_id: int):
        return self.rows

    def list_active_by_orcamento_item(self, orcamento_item_id: int):
        return self.rows

    def list_by_item_chave(self, orcamento_item_id: int, chave: str):
        return self.rows

    def get_by_id(self, id: int):
        return self.by_id if self.by_id is not None else _item_resumo(id=id)

    def get_by_item_chave(self, orcamento_item_id: int, chave: str):
        return None

    def get_by_item_chave_opcao(self, orcamento_item_id: int, chave: str, codigo_opcao: str):
        return self.opcao_existing

    def get_default_by_item_chave(self, orcamento_item_id: int, chave: str):
        return self.item_default

    def create(self, **fields):
        self.__class__.created_payload = fields
        return _item_resumo(id=1, **fields)

    def update(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        return _item_resumo(id=id, **fields)

    def deactivate(self, id: int) -> bool:
        self.__class__.deactivated_ids.append(id)
        return self.deactivate_result

    def activate(self, id: int) -> bool:
        return self.activate_result

    def set_padrao(self, id: int, padrao: bool) -> bool:
        self.__class__.set_padrao_calls.append((id, padrao))
        return True

    def clear_padrao_for_chave(self, orcamento_item_id: int, chave: str, exclude_id=None) -> None:
        self.__class__.clear_calls.append((orcamento_item_id, chave, exclude_id))


class _FakeOrcamentoRepository:
    versao_default: OrcamentoValuesetLinhaResumo | None = None
    versao_rows: list = []

    def __init__(self, _session: object) -> None:
        pass

    def get_default_by_versao_chave(self, orcamento_versao_id: int, chave: str):
        return self.versao_default

    def list_by_orcamento_versao(self, orcamento_versao_id: int):
        return self.versao_rows


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
        self.item = None

    def get(self, _model, _id):
        return self.item

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeItemRepository.rows = []
    _FakeItemRepository.opcao_existing = None
    _FakeItemRepository.item_default = None
    _FakeItemRepository.by_id = None
    _FakeItemRepository.created_payload = None
    _FakeItemRepository.updated_payload = None
    _FakeItemRepository.set_padrao_calls = []
    _FakeItemRepository.clear_calls = []
    _FakeItemRepository.deactivated_ids = []
    _FakeItemRepository.deactivate_result = True
    _FakeItemRepository.activate_result = True
    _FakeOrcamentoRepository.versao_default = None
    _FakeOrcamentoRepository.versao_rows = []
    _FakeModeloRepository.modelo = None
    _FakeModeloLinhaRepository.linhas = []


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(
        service_module, "OrcamentoItemValuesetLinhaRepository", _FakeItemRepository
    )
    monkeypatch.setattr(
        service_module, "OrcamentoValuesetLinhaRepository", _FakeOrcamentoRepository
    )
    monkeypatch.setattr(service_module, "DefValuesetModeloRepository", _FakeModeloRepository)
    monkeypatch.setattr(
        service_module, "DefValuesetModeloLinhaRepository", _FakeModeloLinhaRepository
    )
    session = _FakeSession()
    return service_module.OrcamentoItemValuesetLinhaService(session=session), session


def test_criar_linha_do_item(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.criar_linha(
        service_module.CriarOrcamentoItemValuesetLinhaData(
            orcamento_item_id=30,
            chave="material_portas",
            ref_materia_prima="PORTA-01",
        )
    )

    payload = _FakeItemRepository.created_payload
    assert payload is not None
    assert payload["chave"] == "MATERIAL_PORTAS"
    assert payload["codigo_opcao"] == "MATERIAL_PORTAS"
    assert payload["herdado_do_orcamento"] is True
    assert payload["editado_localmente"] is False
    assert result.ref_materia_prima == "PORTA-01"
    assert session.committed is True


def test_duplicar_chave_e_opcao_recusada_no_item(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeItemRepository.opcao_existing = _item_resumo(id=2, codigo_opcao="BLUM_RETA")

    try:
        service.criar_linha(
            service_module.CriarOrcamentoItemValuesetLinhaData(
                orcamento_item_id=30,
                chave="FERRAGEM_DOBRADICA",
                codigo_opcao="BLUM_RETA",
            )
        )
    except ValueError as error:
        assert "opcao" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_varias_opcoes_mesma_chave_permitidas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeItemRepository.opcao_existing = None

    service.criar_linha(
        service_module.CriarOrcamentoItemValuesetLinhaData(
            orcamento_item_id=30,
            chave="FERRAGEM_DOBRADICA",
            codigo_opcao="SALICE_RETA",
        )
    )

    assert _FakeItemRepository.created_payload["codigo_opcao"] == "SALICE_RETA"
    assert session.committed is True


def test_criar_linha_item_com_prioridade(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.criar_linha(
        service_module.CriarOrcamentoItemValuesetLinhaData(
            orcamento_item_id=30,
            chave="FERRAGEM_DOBRADICA",
            codigo_opcao="SALICE_RETA",
            prioridade=2,
        )
    )

    assert _FakeItemRepository.created_payload["prioridade"] == 2
    assert session.committed is True


def test_criar_linha_item_prioridade_invalida_recusada(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha(
            service_module.CriarOrcamentoItemValuesetLinhaData(
                orcamento_item_id=30,
                chave="FERRAGEM_DOBRADICA",
                codigo_opcao="SALICE_RETA",
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
    _FakeItemRepository.item_default = _item_resumo(id=7, prioridade=1, codigo_opcao="BLUM_RETA")

    result = service.obter_padrao_por_chave(30, "ferragem_dobradica")

    assert result is not None
    assert result.id == 7


def test_definir_como_padrao(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeItemRepository.by_id = _item_resumo(
        id=5, orcamento_item_id=30, chave="FERRAGEM_DOBRADICA", codigo_opcao="SALICE_RETA"
    )

    assert service.definir_como_padrao(5) is True
    assert (30, "FERRAGEM_DOBRADICA", 5) in _FakeItemRepository.clear_calls
    assert (5, True) in _FakeItemRepository.set_padrao_calls
    assert session.committed is True


def test_resolver_prefere_padrao_do_item(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemRepository.item_default = _item_resumo(id=3, ref_materia_prima="ITEM")
    _FakeOrcamentoRepository.versao_default = _versao_resumo(id=4, ref_materia_prima="VERSAO")

    result = service.obter_valor_resolvido(30, 20, "material_caixote")

    assert result == _item_resumo(id=3, ref_materia_prima="ITEM")


def test_resolver_usa_orcamento_quando_item_nao_tem_padrao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemRepository.item_default = None
    _FakeOrcamentoRepository.versao_default = _versao_resumo(id=4, ref_materia_prima="VERSAO")

    result = service.obter_valor_resolvido(30, 20, "material_caixote")

    assert result == _versao_resumo(id=4, ref_materia_prima="VERSAO")


def test_resolver_devolve_none_sem_padrao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemRepository.item_default = None
    _FakeOrcamentoRepository.versao_default = None

    assert service.obter_valor_resolvido(30, 20, "material_caixote") is None


def test_criar_a_partir_do_orcamento_cria_linhas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeOrcamentoRepository.versao_rows = [
        _versao_resumo(
            id=7,
            chave="MATERIAL_FRENTES",
            codigo_opcao="MDF",
            preco_liquido=Decimal("7.48"),
            margem_percentagem=Decimal("10"),
            desconto_percentagem=Decimal("32"),
            comp_mp=Decimal("2750"),
            coresp_orla_0_4="ORLA_A",
            prioridade=2,
        )
    ]
    _FakeItemRepository.opcao_existing = None

    result = service.criar_a_partir_do_orcamento(30)

    assert result.criadas == 1
    assert result.atualizadas == 0
    assert result.ignoradas == 0
    assert result.total_origem == 1

    payload = _FakeItemRepository.created_payload
    assert payload["origem_dados"] == "VALUESET_ORCAMENTO"
    assert payload["origem_orcamento_valueset_linha_id"] == 7
    assert payload["origem_orcamento_versao_id"] == 20
    assert payload["herdado_do_orcamento"] is True
    assert payload["editado_localmente"] is False
    assert payload["ativo"] is True
    assert payload["preco_liquido"] == Decimal("7.48")
    assert payload["margem_percentagem"] == Decimal("10")
    assert payload["desconto_percentagem"] == Decimal("32")
    assert payload["comp_mp"] == Decimal("2750")
    assert payload["coresp_orla_0_4"] == "ORLA_A"
    assert payload["prioridade"] == 2
    assert session.committed is True


def test_criar_a_partir_atualiza_linha_nao_editada(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeOrcamentoRepository.versao_rows = [_versao_resumo(id=7)]
    _FakeItemRepository.opcao_existing = _item_resumo(id=5, editado_localmente=False)

    result = service.criar_a_partir_do_orcamento(30)

    assert result.criadas == 0
    assert result.atualizadas == 1
    assert result.ignoradas == 0
    assert _FakeItemRepository.updated_payload is not None
    assert _FakeItemRepository.updated_payload["id"] == 5


def test_criar_a_partir_protege_linha_editada(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeOrcamentoRepository.versao_rows = [_versao_resumo(id=7)]
    _FakeItemRepository.opcao_existing = _item_resumo(id=5, editado_localmente=True)

    result = service.criar_a_partir_do_orcamento(30)

    assert result.criadas == 0
    assert result.atualizadas == 0
    assert result.ignoradas == 1
    assert _FakeItemRepository.updated_payload is None


def test_criar_a_partir_ignora_linhas_inativas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeOrcamentoRepository.versao_rows = [_versao_resumo(id=7, ativo=False)]
    _FakeItemRepository.opcao_existing = None

    result = service.criar_a_partir_do_orcamento(30)

    assert result.criadas == 0
    assert result.total_origem == 0
    assert _FakeItemRepository.created_payload is None


def test_criar_a_partir_item_inexistente_levanta(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = None

    try:
        service.criar_a_partir_do_orcamento(999)
    except ValueError as error:
        assert "item" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_importar_modelo_para_item_cria_linhas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeModeloRepository.modelo = _modelo(id=88, codigo="COZINHA_STANDARD")
    _FakeModeloLinhaRepository.linhas = [_modelo_linha()]
    _FakeItemRepository.opcao_existing = None

    result = service.importar_modelo_para_item(30, 88)

    assert result.modelo_codigo == "COZINHA_STANDARD"
    assert result.criadas == 1
    assert result.atualizadas == 0
    assert result.ignoradas == 0
    assert result.total_origem == 1

    payload = _FakeItemRepository.created_payload
    assert payload["origem_dados"] == "MODELO_VALUESET"
    assert payload["origem_modelo_id"] == 88
    assert payload["origem_modelo_codigo"] == "COZINHA_STANDARD"
    assert payload["origem_orcamento_valueset_linha_id"] is None
    assert payload["origem_orcamento_versao_id"] is None
    assert payload["editado_localmente"] is False
    assert payload["ativo"] is True
    assert payload["preco_liquido"] == Decimal("7.48")
    assert payload["margem_percentagem"] == Decimal("10")
    assert payload["desconto_percentagem"] == Decimal("32")
    assert payload["comp_mp"] == Decimal("2750")
    assert payload["coresp_orla_0_4"] == "ORLA_A"
    assert payload["prioridade"] == 1
    assert session.committed is True


def test_importar_modelo_para_item_atualiza_nao_editada(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeModeloRepository.modelo = _modelo()
    _FakeModeloLinhaRepository.linhas = [_modelo_linha()]
    _FakeItemRepository.opcao_existing = _item_resumo(id=5, editado_localmente=False)

    result = service.importar_modelo_para_item(30, 88)

    assert result.criadas == 0
    assert result.atualizadas == 1
    assert result.ignoradas == 0
    assert _FakeItemRepository.updated_payload is not None
    assert _FakeItemRepository.updated_payload["id"] == 5


def test_importar_modelo_para_item_protege_editada(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeModeloRepository.modelo = _modelo()
    _FakeModeloLinhaRepository.linhas = [_modelo_linha()]
    _FakeItemRepository.opcao_existing = _item_resumo(id=5, editado_localmente=True)

    result = service.importar_modelo_para_item(30, 88)

    assert result.criadas == 0
    assert result.atualizadas == 0
    assert result.ignoradas == 1
    assert _FakeItemRepository.updated_payload is None


def test_importar_modelo_para_item_ignora_inativas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeModeloRepository.modelo = _modelo()
    _FakeModeloLinhaRepository.linhas = [_modelo_linha(ativo=False)]
    _FakeItemRepository.opcao_existing = None

    result = service.importar_modelo_para_item(30, 88)

    assert result.criadas == 0
    assert result.total_origem == 0
    assert _FakeItemRepository.created_payload is None


def test_importar_modelo_para_item_modelo_inexistente_levanta(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeModeloRepository.modelo = None

    try:
        service.importar_modelo_para_item(30, 999)
    except ValueError as error:
        assert "modelo" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_substituir_por_modelo_desativa_ativas_e_cria(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeModeloRepository.modelo = _modelo(id=88, codigo="COZINHA_STANDARD")
    _FakeModeloLinhaRepository.linhas = [
        _modelo_linha(id=1, chave="MATERIAL_FRENTES", codigo_opcao="MDF"),
        _modelo_linha(id=2, chave="FERRAGEM_CORREDICA", codigo_opcao="SILVER"),
    ]
    _FakeItemRepository.rows = [
        _item_resumo(id=5, chave="MATERIAL_LATERAIS", codigo_opcao="AGL"),
        _item_resumo(id=6, chave="FERRAGEM_DOBRADICA", codigo_opcao="BLUM"),
    ]
    _FakeItemRepository.opcao_existing = None

    result = service.substituir_por_modelo(30, 88)

    assert result.modelo_codigo == "COZINHA_STANDARD"
    assert result.desativadas == 2
    assert result.criadas == 2
    assert result.atualizadas == 0
    assert result.ignoradas == 0
    assert result.total_origem == 2
    assert 5 in _FakeItemRepository.deactivated_ids
    assert 6 in _FakeItemRepository.deactivated_ids

    payload = _FakeItemRepository.created_payload
    assert payload["origem_dados"] == "MODELO_VALUESET"
    assert payload["origem_modelo_codigo"] == "COZINHA_STANDARD"
    assert payload["ativo"] is True
    assert payload["editado_localmente"] is False
    assert session.committed is True


def test_substituir_por_modelo_sem_linhas_ativas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeModeloRepository.modelo = _modelo()
    _FakeModeloLinhaRepository.linhas = [_modelo_linha()]
    _FakeItemRepository.rows = []
    _FakeItemRepository.opcao_existing = None

    result = service.substituir_por_modelo(30, 88)

    assert result.desativadas == 0
    assert result.criadas == 1
    assert _FakeItemRepository.deactivated_ids == []


def test_substituir_por_modelo_reativa_colisao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    service.session.item = SimpleNamespace(id=30, orcamento_versao_id=20)
    _FakeModeloRepository.modelo = _modelo()
    _FakeModeloLinhaRepository.linhas = [_modelo_linha()]
    _FakeItemRepository.rows = [_item_resumo(id=5)]
    _FakeItemRepository.opcao_existing = _item_resumo(id=5, ativo=False)

    result = service.substituir_por_modelo(30, 88)

    assert result.desativadas == 1
    assert result.criadas == 0
    assert result.atualizadas == 1
    payload = _FakeItemRepository.updated_payload
    assert payload["id"] == 5
    assert payload["ativo"] is True
    assert payload["origem_dados"] == "MODELO_VALUESET"


def test_editar_linha_item_recalcula_preco_liquido(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.editar_linha(
        5,
        service_module.EditarOrcamentoItemValuesetLinhaData(
            orcamento_item_id=30,
            chave="MATERIAL_FRENTES",
            codigo_opcao="MDF",
            preco_tabela=Decimal("10"),
            margem_percentagem=Decimal("10"),
            desconto_percentagem=Decimal("10"),
        ),
    )

    payload = _FakeItemRepository.updated_payload
    assert payload["id"] == 5
    assert payload["preco_liquido"] == Decimal("9.90")
    assert session.committed is True


def test_editar_linha_item_marca_editado(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.editar_linha(
        5,
        service_module.EditarOrcamentoItemValuesetLinhaData(
            orcamento_item_id=30,
            chave="MATERIAL_FRENTES",
            codigo_opcao="MDF",
            origem_dados="EDITADO_LOCALMENTE",
            editado_localmente=True,
        ),
    )

    payload = _FakeItemRepository.updated_payload
    assert payload["editado_localmente"] is True
    assert payload["origem_dados"] == "EDITADO_LOCALMENTE"


def test_copiar_snapshot_item_sem_chave(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemRepository.by_id = _item_resumo(
        id=5,
        ref_le="FRT0001",
        preco_tabela=Decimal("10"),
        comp_mp=Decimal("2750"),
        prioridade=3,
    )

    snapshot = service.copiar_snapshot_linha(5)

    assert snapshot["ref_le"] == "FRT0001"
    assert snapshot["preco_tabela"] == Decimal("10")
    assert snapshot["comp_mp"] == Decimal("2750")
    assert snapshot["prioridade"] == 3
    assert "chave" not in snapshot
    assert "codigo_opcao" not in snapshot


def test_colar_snapshot_item_mantem_chave_e_recalcula(monkeypatch) -> None:
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

    payload = _FakeItemRepository.updated_payload
    assert payload["id"] == 5
    assert payload["prioridade"] == 2
    assert payload["ref_le"] == "FRT0001"
    assert payload["comp_mp"] == Decimal("2750")
    assert payload["preco_liquido"] == Decimal("9.90")
    assert payload["editado_localmente"] is True
    assert payload["origem_dados"] == "EDITADO_LOCALMENTE"
    assert "chave" not in payload
    assert "codigo_opcao" not in payload
    assert session.committed is True


def test_limpar_snapshot_item_mantem_chave(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.limpar_snapshot_linha(5)

    payload = _FakeItemRepository.updated_payload
    assert payload["id"] == 5
    assert "prioridade" not in payload  # limpar dados não mexe na prioridade
    assert payload["ref_le"] is None
    assert payload["preco_tabela"] is None
    assert payload["preco_liquido"] is None
    assert payload["comp_mp"] is None
    assert payload["editado_localmente"] is True
    assert payload["origem_dados"] == "EDITADO_LOCALMENTE"
    assert "chave" not in payload
    assert "codigo_opcao" not in payload
    assert session.committed is True


def test_desativar_linha_item_marca_editado(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_linha(5) is True

    payload = _FakeItemRepository.updated_payload
    assert payload["id"] == 5
    assert payload["ativo"] is False
    assert payload["editado_localmente"] is True
    assert session.committed is True


def test_ativar_linha_item_marca_editado(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.ativar_linha(5) is True

    payload = _FakeItemRepository.updated_payload
    assert payload["id"] == 5
    assert payload["ativo"] is True
    assert payload["editado_localmente"] is True
    assert session.committed is True
