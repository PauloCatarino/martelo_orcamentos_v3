"""Tests for the OrcamentoItemCusteioLinha service."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)
from app.services import orcamento_item_custeio_linha_service as service_module


def _peca(**kwargs):
    base = {
        "id": 1,
        "codigo": "COSTA",
        "nome": "Costa",
        "descricao": None,
        "grupo": "COSTAS",
        "tipo_peca": "SIMPLES",
        "ativo": True,
        "orla_c1": 2,
        "orla_c2": 2,
        "orla_l1": 0,
        "orla_l2": 0,
        "chave_valueset_material": "MATERIAL_COSTAS",
        "permite_acabamento": False,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _vs_linha(**kwargs):
    base = {
        "id": 1,
        "ativo": True,
        "padrao": True,
        "codigo_opcao": "AGL_19",
        "nome_opcao": "AGL 19mm",
        "materia_prima_id": 5,
        "ref_materia_prima": "MP01",
        "descricao_materia_prima": "AGL",
        "ref_le": "LE01",
        "descricao_no_orcamento": "AGL Linho Cancun",
        "unidade": "m2",
        "preco_liquido": Decimal("5.79"),
        "desperdicio_percentagem": Decimal("5"),
        "tipo_materia_prima": "PLACA",
        "familia_materia_prima": "AGLOMERADO",
        "coresp_orla_0_4": "ORLA04",
        "coresp_orla_1_0": "ORLA10",
        "comp_mp": Decimal("2750"),
        "larg_mp": Decimal("1830"),
        "esp_mp": Decimal("19"),
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _resumo(**kwargs) -> OrcamentoItemCusteioLinhaResumo:
    base = {
        "id": 1,
        "orcamento_item_id": 10,
        "orcamento_item_modulo_id": None,
        "origem_tipo": None,
        "origem_id": None,
        "tipo_linha": "MANUAL",
        "codigo": None,
        "descricao": "Linha",
        "materia_prima_id": None,
        "ref_materia_prima": None,
        "descricao_materia_prima": None,
        "unidade": None,
        "quantidade": Decimal("1"),
        "comp": None,
        "larg": None,
        "esp": None,
        "area_m2": None,
        "perimetro_ml": None,
        "ml_orla_fina": None,
        "ml_orla_grossa": None,
        "custo_unitario": None,
        "custo_total": None,
        "margem_percentagem": None,
        "preco_unitario": None,
        "preco_total": None,
        "def_operacao_id": None,
        "def_maquina_id": None,
        "tempo_calculado": None,
        "tempo_manual": None,
        "override_manual": False,
        "editado_localmente": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return OrcamentoItemCusteioLinhaResumo(**base)


class _FakeRepository:
    all_rows: list[OrcamentoItemCusteioLinhaResumo] = []
    active_rows: list[OrcamentoItemCusteioLinhaResumo] = []
    versao_rows: list[OrcamentoItemCusteioLinhaResumo] = []
    by_id: OrcamentoItemCusteioLinhaResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    deactivated_id: int | None = None
    activate_result = True
    activated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_by_orcamento_item(self, orcamento_item_id: int):
        return self.all_rows

    def list_active_by_orcamento_item(self, orcamento_item_id: int):
        return self.active_rows

    def list_by_orcamento_versao(self, orcamento_versao_id: int):
        return self.versao_rows

    def get_by_id(self, id: int):
        return self.by_id

    def create_linha(self, **fields):
        self.__class__.created_payload = fields
        return _resumo(id=1, **fields)

    def update_linha(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        return _resumo(id=id, **fields)

    def deactivate_linha(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result

    def activate_linha(self, id: int) -> bool:
        self.__class__.activated_id = id
        return self.activate_result


class _FakePecaRepository:
    pecas: dict = {}

    def __init__(self, _session: object) -> None:
        pass

    def get_by_id(self, id: int):
        return self.pecas.get(id)


class _FakeItemValuesetRepository:
    default_linha = None
    chave_rows: list = []

    def __init__(self, _session: object) -> None:
        pass

    def get_default_by_item_chave(self, orcamento_item_id: int, chave: str):
        return self.default_linha

    def list_by_item_chave(self, orcamento_item_id: int, chave: str):
        return self.chave_rows


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.all_rows = []
    _FakeRepository.active_rows = []
    _FakeRepository.versao_rows = []
    _FakeRepository.by_id = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None
    _FakeRepository.activate_result = True
    _FakeRepository.activated_id = None
    _FakePecaRepository.pecas = {}
    _FakeItemValuesetRepository.default_linha = None
    _FakeItemValuesetRepository.chave_rows = []


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "OrcamentoItemCusteioLinhaRepository", _FakeRepository)
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakePecaRepository)
    monkeypatch.setattr(
        service_module, "OrcamentoItemValuesetLinhaRepository", _FakeItemValuesetRepository
    )
    session = _FakeSession()
    return service_module.OrcamentoItemCusteioLinhaService(session=session), session


def test_listar_linhas_do_item(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.all_rows = [_resumo(id=3)]

    assert service.listar_linhas_do_item(10) == [_resumo(id=3)]


def test_listar_linhas_da_versao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.versao_rows = [_resumo(id=4, orcamento_item_id=20)]

    assert service.listar_linhas_da_versao(99) == [_resumo(id=4, orcamento_item_id=20)]


def test_criar_linha_default_tipo_manual(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.criar_linha_manual(
        service_module.CriarLinhaCusteioData(
            orcamento_item_id=10, descricao="  Transporte interno  "
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["tipo_linha"] == "MANUAL"
    assert _FakeRepository.created_payload["descricao"] == "Transporte interno"
    assert _FakeRepository.created_payload["quantidade"] == Decimal("1")
    assert session.committed is True


def test_criar_linha_normaliza_tipo(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha_manual(
        service_module.CriarLinhaCusteioData(
            orcamento_item_id=10, descricao="Placa", tipo_linha="material_peca"
        )
    )

    assert _FakeRepository.created_payload["tipo_linha"] == "MATERIAL_PECA"


def test_criar_valida_orcamento_item_id(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha_manual(
            service_module.CriarLinhaCusteioData(orcamento_item_id=None, descricao="X")
        )
    except ValueError as error:
        assert "orcamento_item_id" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_valida_descricao(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha_manual(
            service_module.CriarLinhaCusteioData(orcamento_item_id=10, descricao="   ")
        )
    except ValueError as error:
        assert "descricao" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_calcula_custo_e_preco_total(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha_manual(
        service_module.CriarLinhaCusteioData(
            orcamento_item_id=10,
            descricao="Placa",
            quantidade=Decimal("3"),
            custo_unitario=Decimal("2"),
            preco_unitario=Decimal("5"),
        )
    )

    assert _FakeRepository.created_payload["custo_total"] == Decimal("6")
    assert _FakeRepository.created_payload["preco_total"] == Decimal("15")


def test_criar_respeita_total_explicito(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_linha_manual(
        service_module.CriarLinhaCusteioData(
            orcamento_item_id=10,
            descricao="Placa",
            quantidade=Decimal("3"),
            custo_unitario=Decimal("2"),
            custo_total=Decimal("99"),
        )
    )

    assert _FakeRepository.created_payload["custo_total"] == Decimal("99")


def test_editar_linha(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.editar_linha(
        7,
        service_module.EditarLinhaCusteioData(
            orcamento_item_id=10, descricao="Atualizada", tipo_linha="operacao"
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 7
    assert _FakeRepository.updated_payload["tipo_linha"] == "OPERACAO"
    assert session.committed is True


def test_desativar_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_linha(10) is True
    assert _FakeRepository.deactivated_id == 10
    assert session.committed is True


def test_desativar_inexistente_sem_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.deactivate_result = False

    assert service.desativar_linha(11) is False
    assert session.committed is False


def test_ativar_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.ativar_linha(7) is True
    assert _FakeRepository.activated_id == 7
    assert session.committed is True


def test_ativar_inexistente_sem_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.activate_result = False

    assert service.ativar_linha(8) is False
    assert session.committed is False


def test_adicionar_peca_simples_cria_linha_com_valueset(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(id=1, codigo="COSTA", chave_valueset_material="MATERIAL_COSTAS")
    }
    _FakeItemValuesetRepository.default_linha = _vs_linha(ref_le="LE01")

    result = service.adicionar_pecas_da_biblioteca(10, [1])

    assert result.criadas == 1
    assert result.ignoradas == 0

    payload = _FakeRepository.created_payload
    assert payload["tipo_linha"] == "PECA"
    assert payload["def_peca_id"] == 1
    assert payload["def_peca_codigo"] == "COSTA"
    assert payload["chave_valueset"] == "MATERIAL_COSTAS"
    assert payload["origem_tipo"] == "BIBLIOTECA_PECA"
    assert payload["qt_mod"] == Decimal("1")
    assert payload["qt_und"] == Decimal("1")
    assert payload["editado_localmente"] is False
    assert payload["ativo"] is True
    # ValueSet data copied
    assert payload["ref_le"] == "LE01"
    assert payload["preco_liquido"] == Decimal("5.79")
    assert payload["comp_mp"] == Decimal("2750")
    assert payload["coresp_orla_0_4"] == "ORLA04"
    assert payload["mat_default"] == "AGL_19"
    assert session.committed is True


def test_adicionar_peca_composta_ignorada(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {2: _peca(id=2, tipo_peca="COMPOSTA")}

    result = service.adicionar_pecas_da_biblioteca(10, [2])

    assert result.criadas == 0
    assert result.ignoradas == 1
    assert _FakeRepository.created_payload is None
    assert any("composta" in aviso.lower() for aviso in result.avisos)


def test_adicionar_peca_sem_valueset_cria_sem_mp(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(id=1, chave_valueset_material="MATERIAL_COSTAS")
    }
    _FakeItemValuesetRepository.default_linha = None
    _FakeItemValuesetRepository.chave_rows = []

    result = service.adicionar_pecas_da_biblioteca(10, [1])

    assert result.criadas == 1
    payload = _FakeRepository.created_payload
    assert payload["chave_valueset"] == "MATERIAL_COSTAS"
    assert "ref_le" not in payload
    assert "Sem ValueSet" in payload["observacoes"]


def test_adicionar_peca_sem_chave_valueset(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1, chave_valueset_material=None)}

    result = service.adicionar_pecas_da_biblioteca(10, [1])

    assert result.criadas == 1
    payload = _FakeRepository.created_payload
    assert payload["chave_valueset"] is None
    assert "sem chave ValueSet" in payload["observacoes"]


def test_resolver_valueset_prefere_padrao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemValuesetRepository.default_linha = _vs_linha(id=9)
    _FakeItemValuesetRepository.chave_rows = [_vs_linha(id=8)]

    resolvido = service.resolver_valueset_para_def_peca(
        10, _peca(chave_valueset_material="MATERIAL_COSTAS")
    )

    assert resolvido.id == 9


def test_resolver_valueset_usa_primeira_ativa_sem_padrao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemValuesetRepository.default_linha = None
    _FakeItemValuesetRepository.chave_rows = [
        _vs_linha(id=7, ativo=False),
        _vs_linha(id=8, ativo=True),
    ]

    resolvido = service.resolver_valueset_para_def_peca(
        10, _peca(chave_valueset_material="MATERIAL_COSTAS")
    )

    assert resolvido.id == 8
