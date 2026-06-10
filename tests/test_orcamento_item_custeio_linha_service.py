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
        "chave_valueset_acabamento_sup": None,
        "chave_valueset_acabamento_inf": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _componente(**kwargs):
    base = {
        "id": 1,
        "def_peca_pai_id": 1,
        "tipo_componente": "PECA",
        "def_peca_componente_id": None,
        "referencia_componente": None,
        "descricao": "Componente",
        "ordem": 1,
        "quantidade": Decimal("1"),
        "regra_quantidade": "FIXA",
        "obrigatorio": True,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _materia(**kwargs):
    base = {
        "id": 7,
        "ref_le": "MP0001",
        "referencia_fornecedor": None,
        "descricao": "AGL Linho Cancun 19mm",
        "tipo_original_excel": None,
        "familia_original_excel": None,
        "tipo_martelo": "PLACA",
        "familia_martelo": "AGLOMERADO",
        "coresp_orla_0_4": None,
        "coresp_orla_1_0": None,
        "desperdicio_percentagem": None,
        "unidade": "m2",
        "preco_tabela": Decimal("8.62"),
        "desconto": Decimal("0.36"),
        "margem": Decimal("0.05"),
        "preco_liquido": Decimal("5.79"),
        "comprimento": Decimal("2750"),
        "largura": Decimal("1830"),
        "espessura": Decimal("19"),
        "fornecedor": None,
        "origem_dados": "EXCEL",
        "ativo": True,
        "observacoes": None,
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
        "linha_pai_id": None,
        "nivel": 0,
        "ordem": None,
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
        "custo_orla_fina": None,
        "custo_orla_grossa": None,
        "custo_orlas": None,
        "custo_mp": None,
        "custo_ferragem": None,
        "custo_acabamento": None,
        "custo_corte": None,
        "custo_orlagem": None,
        "custo_producao": None,
        "consumo_ml_unitario": None,
        "consumo_ml_total": None,
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
    created_payloads: list = []
    updated_payload: dict | None = None
    updated_payloads: list = []
    deactivate_result = True
    deactivated_id: int | None = None
    activate_result = True
    activated_id: int | None = None
    deleted_ids: list | None = None
    lote_call: tuple | None = None
    lote_count = 0

    def __init__(self, _session: object) -> None:
        pass

    def delete_linhas(self, ids: list[int]) -> int:
        self.__class__.deleted_ids = list(ids)
        return len(self.__class__.deleted_ids)

    def atualizar_flag_exclusao(self, orcamento_item_id, campo, valor) -> int:
        self.__class__.lote_call = (orcamento_item_id, campo, bool(valor))
        return self.__class__.lote_count

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
        self.__class__.created_payloads.append(fields)
        return _resumo(id=len(self.created_payloads), **fields)

    def update_linha(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        self.__class__.updated_payloads.append({"id": id, **fields})
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

    def get_by_codigo(self, codigo: str):
        for peca in self.pecas.values():
            if peca.codigo == codigo:
                return peca
        return None


class _FakeComponenteRepository:
    componentes: list = []

    def __init__(self, _session: object) -> None:
        pass

    def list_by_peca_pai_id(self, def_peca_pai_id: int):
        return self.componentes


class _FakePecaOperacaoRepository:
    ligacoes_por_peca: dict = {}

    def __init__(self, _session: object) -> None:
        pass

    def list_active_by_def_peca(self, def_peca_id: int):
        return self.ligacoes_por_peca.get(def_peca_id, [])


class _FakeOperacaoRepository:
    operacoes: dict = {}

    def __init__(self, _session: object) -> None:
        pass

    def get_by_id(self, id: int):
        return self.operacoes.get(id)


class _FakeMaquinaRepository:
    maquinas: dict = {}

    def __init__(self, _session: object) -> None:
        pass

    def get_by_id(self, id: int):
        return self.maquinas.get(id)


class _FakeMateriaPrimaRepository:
    materia = None
    materias_por_ref: dict = {}

    def __init__(self, _session: object) -> None:
        pass

    def get_by_id(self, id: int):
        return self.materia

    def get_by_ref_le(self, ref_le: str):
        return self.materias_por_ref.get(ref_le)


class _FakeItemValuesetRepository:
    default_linha = None
    chave_rows: list = []
    by_id = None
    defaults_by_chave: dict = {}

    def __init__(self, _session: object) -> None:
        pass

    def get_default_by_item_chave(self, orcamento_item_id: int, chave: str):
        if chave in self.defaults_by_chave:
            return self.defaults_by_chave[chave]
        return self.default_linha

    def list_by_item_chave(self, orcamento_item_id: int, chave: str):
        return self.chave_rows

    def get_by_id(self, id: int):
        return self.by_id


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.item = None

    def get(self, _model, _id):
        return self.item

    def commit(self) -> None:
        self.committed = True

    def expire_all(self) -> None:
        pass


def _reset() -> None:
    _FakeRepository.all_rows = []
    _FakeRepository.active_rows = []
    _FakeRepository.lote_call = None
    _FakeRepository.lote_count = 0
    _FakeRepository.versao_rows = []
    _FakeRepository.by_id = None
    _FakeRepository.created_payload = None
    _FakeRepository.created_payloads = []
    _FakeRepository.updated_payload = None
    _FakeRepository.updated_payloads = []
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None
    _FakeRepository.activate_result = True
    _FakeRepository.activated_id = None
    _FakeRepository.deleted_ids = None
    _FakePecaRepository.pecas = {}
    _FakeComponenteRepository.componentes = []
    _FakeItemValuesetRepository.default_linha = None
    _FakeItemValuesetRepository.chave_rows = []
    _FakeItemValuesetRepository.by_id = None
    _FakeItemValuesetRepository.defaults_by_chave = {}
    _FakeMateriaPrimaRepository.materia = None
    _FakeMateriaPrimaRepository.materias_por_ref = {}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {}
    _FakeOperacaoRepository.operacoes = {}
    _FakeMaquinaRepository.maquinas = {}


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "OrcamentoItemCusteioLinhaRepository", _FakeRepository)
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakePecaRepository)
    monkeypatch.setattr(
        service_module, "DefPecaComponenteRepository", _FakeComponenteRepository
    )
    monkeypatch.setattr(
        service_module, "OrcamentoItemValuesetLinhaRepository", _FakeItemValuesetRepository
    )
    monkeypatch.setattr(
        service_module, "DefMateriaPrimaRepository", _FakeMateriaPrimaRepository
    )
    monkeypatch.setattr(
        service_module, "DefPecaOperacaoRepository", _FakePecaOperacaoRepository
    )
    monkeypatch.setattr(service_module, "DefOperacaoRepository", _FakeOperacaoRepository)
    monkeypatch.setattr(service_module, "DefMaquinaRepository", _FakeMaquinaRepository)
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


def test_adicionar_peca_composta_cria_principal_e_componentes(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(id=1, codigo="GAVETA", tipo_peca="COMPOSTA", chave_valueset_material=None),
        2: _peca(id=2, codigo="FRENTE_GAV", chave_valueset_material="MATERIAL_FRENTES"),
    }
    _FakeComponenteRepository.componentes = [
        _componente(
            id=10, tipo_componente="PECA", def_peca_componente_id=2, quantidade=Decimal("2")
        )
    ]
    _FakeItemValuesetRepository.default_linha = _vs_linha(ref_le="LE_FR")

    result = service.adicionar_pecas_da_biblioteca(10, [1])

    assert result.criadas == 1
    assert result.componentes == 1
    assert result.ignoradas == 0

    payloads = _FakeRepository.created_payloads
    assert len(payloads) == 2

    principal = payloads[0]
    assert principal["tipo_linha"] == "PECA_COMPOSTA"
    assert principal["nivel"] == 0
    assert principal["linha_pai_id"] is None
    assert principal["def_peca_id"] == 1

    sub = payloads[1]
    assert sub["tipo_linha"] == "PECA"
    assert sub["nivel"] == 1
    assert sub["linha_pai_id"] == 1
    assert sub["def_peca_id"] == 2
    assert sub["chave_valueset"] == "MATERIAL_FRENTES"
    assert sub["ref_le"] == "LE_FR"
    assert sub["qt_und"] == Decimal("2")
    assert sub["origem_tipo"] == "PECA_COMPOSTA"
    assert session.committed is True


def test_adicionar_peca_composta_sem_componentes(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1, codigo="GAVETA", tipo_peca="COMPOSTA")}
    _FakeComponenteRepository.componentes = []

    result = service.adicionar_pecas_da_biblioteca(10, [1])

    assert result.criadas == 1
    assert result.componentes == 0
    assert any("sem componentes" in aviso.lower() for aviso in result.avisos)
    assert len(_FakeRepository.created_payloads) == 1
    assert _FakeRepository.created_payloads[0]["tipo_linha"] == "PECA_COMPOSTA"


def test_adicionar_componente_sem_valueset(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(id=1, tipo_peca="COMPOSTA"),
        2: _peca(id=2, chave_valueset_material="MATERIAL_FRENTES"),
    }
    _FakeComponenteRepository.componentes = [_componente(def_peca_componente_id=2)]
    _FakeItemValuesetRepository.default_linha = None
    _FakeItemValuesetRepository.chave_rows = []

    result = service.adicionar_pecas_da_biblioteca(10, [1])

    assert result.componentes == 1
    sub = _FakeRepository.created_payloads[1]
    assert "Sem ValueSet" in sub["observacoes"]


def test_adicionar_componente_ferragem_resolve_chave_da_def_peca_filha(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            codigo="PORTA+DOBRADICA",
            tipo_peca="COMPOSTA",
            chave_valueset_material=None,
        ),
        3: _peca(id=3, codigo="DOBRADICA", chave_valueset_material="FERRAGEM_DOBRADICA"),
    }
    # The DOBRADICA component links by code (referencia_componente), not by id.
    _FakeComponenteRepository.componentes = [
        _componente(
            id=20,
            tipo_componente="FERRAGEM",
            def_peca_componente_id=None,
            referencia_componente="DOBRADICA",
            descricao="Dobradiça",
        )
    ]
    _FakeItemValuesetRepository.default_linha = _vs_linha(
        codigo_opcao="DOBRADICA_STANDARD",
        ref_le="FER0015",
        descricao_no_orcamento="Dobradiça reta Blum",
        unidade="UND",
        preco_liquido=Decimal("1.25"),
    )

    result = service.adicionar_pecas_da_biblioteca(10, [1])

    assert result.componentes == 1
    sub = _FakeRepository.created_payloads[1]
    assert sub["tipo_linha"] == "FERRAGEM"
    assert sub["chave_valueset"] == "FERRAGEM_DOBRADICA"
    assert sub["mat_default"] == "DOBRADICA_STANDARD"
    assert sub["ref_le"] == "FER0015"
    assert sub["descricao_no_orcamento"] == "Dobradiça reta Blum"
    assert sub["unidade"] == "UND"
    assert sub["preco_liquido"] == Decimal("1.25")
    assert sub["origem_tipo"] == "PECA_COMPOSTA"
    assert sub["linha_pai_id"] == 1
    assert sub["nivel"] == 1
    assert sub["editado_localmente"] is False
    assert sub["ativo"] is True


def test_adicionar_componente_def_peca_sem_chave(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(id=1, tipo_peca="COMPOSTA"),
        2: _peca(id=2, codigo="PUXADOR", chave_valueset_material=None),
    }
    _FakeComponenteRepository.componentes = [_componente(def_peca_componente_id=2)]

    result = service.adicionar_pecas_da_biblioteca(10, [1])

    assert result.componentes == 1
    sub = _FakeRepository.created_payloads[1]
    assert "Componente sem chave ValueSet" in sub["observacoes"]


def test_adicionar_componente_sem_def_peca_associada(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1, tipo_peca="COMPOSTA")}
    _FakeComponenteRepository.componentes = [
        _componente(
            tipo_componente="FERRAGEM",
            def_peca_componente_id=None,
            referencia_componente="DESCONHECIDO",
            descricao="Peça livre",
        )
    ]

    result = service.adicionar_pecas_da_biblioteca(10, [1])

    assert result.componentes == 1
    sub = _FakeRepository.created_payloads[1]
    assert sub["tipo_linha"] == "FERRAGEM"
    assert sub["nivel"] == 1
    assert sub["linha_pai_id"] == 1
    assert "sem definição de peça associada" in sub["observacoes"]


def test_recalcular_medidas_do_item(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(
        altura=Decimal("2750"), largura=Decimal("1830"), profundidade=Decimal("560")
    )
    _FakeRepository.active_rows = [
        _resumo(
            id=5,
            qt_mod=Decimal("2"),
            qt_und=Decimal("3"),
            comp=Decimal("1000"),
            larg=Decimal("500"),
            esp=Decimal("19"),
        )
    ]

    atualizadas = service.recalcular_medidas_do_item(30)

    assert atualizadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["id"] == 5
    assert payload["quantidade"] == Decimal("6")
    assert payload["comp_real"] == Decimal("1000")
    assert payload["larg_real"] == Decimal("500")
    assert payload["esp_real"] == Decimal("19")
    assert payload["area_m2"] == Decimal("0.5")
    assert payload["perimetro_ml"] == Decimal("3")
    assert session.committed is True


def test_recalcular_medidas_qt_total_default_e_sem_medidas(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(altura=None, largura=None, profundidade=None)
    _FakeRepository.active_rows = [_resumo(id=5, qt_mod=None, qt_und=None)]

    service.recalcular_medidas_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["quantidade"] == Decimal("1")
    assert payload["comp_real"] is None
    assert payload["area_m2"] is None
    assert payload["perimetro_ml"] is None


def test_recalcular_medidas_so_altera_campos_de_medida(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(
        altura=Decimal("100"), largura=Decimal("50"), profundidade=None
    )
    _FakeRepository.active_rows = [_resumo(id=5, ref_le="LE01", chave_valueset="MATERIAL_X")]

    service.recalcular_medidas_do_item(30)

    payload = _FakeRepository.updated_payload
    # Only quantity/measure fields are updated; ValueSet snapshot is untouched.
    assert set(payload.keys()) == {
        "id",
        "qt_mod",
        "qt_und",
        "quantidade",
        "comp_real",
        "larg_real",
        "esp_real",
        "area_m2",
        "perimetro_ml",
    }


def test_recalcular_medidas_item_inexistente_levanta(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = None

    try:
        service.recalcular_medidas_do_item(999)
    except ValueError as error:
        assert "item" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_atualizar_medidas_linha_recalcula_qt_total(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(
        altura=Decimal("2750"), largura=Decimal("1830"), profundidade=Decimal("560")
    )
    _FakeRepository.by_id = _resumo(id=5)

    service.atualizar_medidas_linha(5, qt_mod="2", qt_und="3", comp=None, larg=None, esp=None)

    payload = _FakeRepository.updated_payload
    assert payload["id"] == 5
    assert payload["qt_mod"] == Decimal("2")
    assert payload["qt_und"] == Decimal("3")
    assert payload["quantidade"] == Decimal("6")
    # Editing quantities/measures must NOT flag the line as locally edited.
    assert "editado_localmente" not in payload
    assert session.committed is True


def test_atualizar_medidas_linha_resolve_variaveis_e_area(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    service.session.item = SimpleNamespace(
        altura=Decimal("2750"), largura=Decimal("1830"), profundidade=Decimal("560")
    )
    _FakeRepository.by_id = _resumo(id=5)

    service.atualizar_medidas_linha(5, qt_mod="1", qt_und="1", comp="H", larg="L", esp="19")

    payload = _FakeRepository.updated_payload
    # Raw text/expression is kept.
    assert payload["comp"] == "H"
    assert payload["larg"] == "L"
    assert payload["esp"] == "19"
    # Evaluated results.
    assert payload["comp_real"] == Decimal("2750")
    assert payload["larg_real"] == Decimal("1830")
    assert payload["esp_real"] == Decimal("19")
    assert payload["area_m2"] == Decimal("5.0325")
    assert payload["perimetro_ml"] == Decimal("9.16")
    assert "editado_localmente" not in payload


def test_atualizar_medidas_descricao_nao_marca_editado(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    service.session.item = SimpleNamespace(
        altura=Decimal("100"), largura=Decimal("50"), profundidade=None
    )
    _FakeRepository.by_id = _resumo(id=5, editado_localmente=False)

    # Editing Comp / Descrição livre directly in the table must not flag the line.
    service.atualizar_medidas_linha(
        5, qt_mod="1", qt_und="1", comp="100", larg="50", esp=None, descricao="MÓDULO 1"
    )

    payload = _FakeRepository.updated_payload
    assert "editado_localmente" not in payload
    assert payload["descricao"] == "MÓDULO 1"


def test_atualizar_medidas_linha_valor_invalido_nao_rebenta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    service.session.item = SimpleNamespace(
        altura=Decimal("100"), largura=Decimal("50"), profundidade=None
    )
    _FakeRepository.by_id = _resumo(id=5)

    service.atualizar_medidas_linha(5, qt_mod="1", qt_und="1", comp="xyz", larg=None, esp=None)

    payload = _FakeRepository.updated_payload
    assert payload["comp"] == "xyz"
    assert payload["comp_real"] is None
    assert payload["area_m2"] is None


def test_atualizar_medidas_linha_nao_altera_valueset(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    service.session.item = SimpleNamespace(
        altura=Decimal("100"), largura=Decimal("50"), profundidade=None
    )
    _FakeRepository.by_id = _resumo(id=5, ref_le="LE01", chave_valueset="MATERIAL_X")

    service.atualizar_medidas_linha(5, qt_mod="1", qt_und="1", comp=None, larg=None, esp=None)

    payload = _FakeRepository.updated_payload
    assert "ref_le" not in payload
    assert "chave_valueset" not in payload
    assert "preco_liquido" not in payload


def test_inserir_divisao_independente(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.inserir_divisao_independente(30)

    payload = _FakeRepository.created_payload
    assert payload["tipo_linha"] == "DIVISAO_INDEPENDENTE"
    assert payload["codigo"] == "DIVISAO"
    assert payload["descricao"] == "Divisão independente"
    assert payload["origem_tipo"] == "MANUAL"
    assert payload["comp"] == "H"
    assert payload["larg"] == "L"
    assert payload["esp"] == "P"
    assert payload["editado_localmente"] is True
    assert payload["ativo"] is True
    # The division line does not carry material/ValueSet data.
    assert "chave_valueset" not in payload
    assert "ref_le" not in payload
    assert "preco_liquido" not in payload
    assert session.committed is True


def test_recalcular_com_divisao_propaga_contexto_local(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    session.item = SimpleNamespace(
        altura=Decimal("2750"), largura=Decimal("1830"), profundidade=Decimal("560")
    )
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="DIVISAO_INDEPENDENTE", comp="H", larg="L", esp="P"),
        _resumo(id=2, tipo_linha="PECA", comp="HM", larg="LM", esp="PM"),
    ]

    service.recalcular_medidas_do_item(30)

    payloads = {p["id"]: p for p in _FakeRepository.updated_payloads}
    # Division computes HM/LM/PM from the global context.
    assert payloads[1]["comp_real"] == Decimal("2750")
    assert payloads[1]["larg_real"] == Decimal("1830")
    assert payloads[1]["esp_real"] == Decimal("560")
    assert payloads[1]["area_m2"] == Decimal("5.0325")
    # Line below uses the division's local context.
    assert payloads[2]["comp_real"] == Decimal("2750")
    assert payloads[2]["larg_real"] == Decimal("1830")
    assert payloads[2]["esp_real"] == Decimal("560")
    assert session.committed is True


def test_recalcular_linha_antes_de_divisao_com_hm_nao_rebenta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    service.session.item = SimpleNamespace(
        altura=Decimal("2750"), largura=Decimal("1830"), profundidade=Decimal("560")
    )
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="PECA", comp="HM", larg="LM", esp="PM"),
    ]

    service.recalcular_medidas_do_item(30)

    payload = _FakeRepository.updated_payloads[0]
    assert payload["comp_real"] is None
    assert payload["larg_real"] is None
    assert payload["area_m2"] is None


def test_recalcular_nova_divisao_altera_contexto(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    service.session.item = SimpleNamespace(
        altura=Decimal("2750"), largura=Decimal("1830"), profundidade=Decimal("560")
    )
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="DIVISAO_INDEPENDENTE", comp="1000", larg="500", esp="20"),
        _resumo(id=2, tipo_linha="PECA", comp="HM", larg="LM", esp="PM"),
        _resumo(id=3, tipo_linha="DIVISAO_INDEPENDENTE", comp="2000", larg="800", esp="30"),
        _resumo(id=4, tipo_linha="PECA", comp="HM", larg="LM", esp="PM"),
    ]

    service.recalcular_medidas_do_item(30)

    payloads = {p["id"]: p for p in _FakeRepository.updated_payloads}
    assert payloads[2]["comp_real"] == Decimal("1000")
    assert payloads[2]["larg_real"] == Decimal("500")
    assert payloads[2]["esp_real"] == Decimal("20")
    assert payloads[4]["comp_real"] == Decimal("2000")
    assert payloads[4]["larg_real"] == Decimal("800")
    assert payloads[4]["esp_real"] == Decimal("30")


def test_aplicar_materia_prima_na_linha(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(
        id=5, tipo_linha="PECA", chave_valueset="MATERIAL_COSTAS", def_peca_id=3
    )
    _FakeMateriaPrimaRepository.materia = _materia(id=7)

    service.aplicar_materia_prima_na_linha(5, 7)

    payload = _FakeRepository.updated_payload
    assert payload["id"] == 5
    assert payload["ref_le"] == "MP0001"
    assert payload["descricao_no_orcamento"] == "AGL Linho Cancun 19mm"
    assert payload["unidade"] == "m2"
    assert payload["preco_liquido"] == Decimal("5.79")
    assert payload["tipo_materia_prima"] == "PLACA"
    assert payload["familia_materia_prima"] == "AGLOMERADO"
    assert payload["comp_mp"] == Decimal("2750")
    assert payload["larg_mp"] == Decimal("1830")
    assert payload["esp_mp"] == Decimal("19")
    assert payload["origem_material"] == "MATERIA_PRIMA_LOCAL"
    assert payload["material_editado_localmente"] is True
    assert payload["editado_localmente"] is True
    # Structure is preserved (not part of the update).
    assert "chave_valueset" not in payload
    assert "def_peca_id" not in payload
    assert "tipo_linha" not in payload
    assert "quantidade" not in payload
    assert session.committed is True


def test_aplicar_materia_prima_divisao_recusada(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="DIVISAO_INDEPENDENTE")
    _FakeMateriaPrimaRepository.materia = _materia()

    try:
        service.aplicar_materia_prima_na_linha(5, 7)
    except ValueError as error:
        assert "divis" in str(error).lower()
    else:
        raise AssertionError("Expected ValueError")

    assert _FakeRepository.updated_payload is None


def test_aplicar_materia_prima_composta_recusada(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="PECA_COMPOSTA")

    try:
        service.aplicar_materia_prima_na_linha(5, 7)
    except ValueError as error:
        assert "composta" in str(error).lower()
    else:
        raise AssertionError("Expected ValueError")

    assert _FakeRepository.updated_payload is None


def test_limpar_material_linha(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="PECA", chave_valueset="MATERIAL_COSTAS")

    service.limpar_material_linha(5)

    payload = _FakeRepository.updated_payload
    assert payload["ref_le"] is None
    assert payload["preco_liquido"] is None
    assert payload["comp_mp"] is None
    assert payload["mat_default"] is None
    assert payload["tipo_materia_prima"] is None
    assert payload["origem_material"] == "LIMPO_LOCALMENTE"
    assert payload["material_editado_localmente"] is True
    assert payload["editado_localmente"] is True
    # Key/def_peca are preserved.
    assert "chave_valueset" not in payload
    assert "def_peca_id" not in payload
    assert session.committed is True


def test_atualizar_material_local_linha(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="FERRAGEM")

    service.atualizar_material_local_linha(
        5, {"ref_le": "FER0015", "preco_liquido": Decimal("1.25"), "unidade": "UND"}
    )

    payload = _FakeRepository.updated_payload
    assert payload["ref_le"] == "FER0015"
    assert payload["preco_liquido"] == Decimal("1.25")
    assert payload["unidade"] == "UND"
    assert payload["origem_material"] == "EDITADO_LOCALMENTE"
    assert payload["material_editado_localmente"] is True
    assert payload["editado_localmente"] is True
    # Fields not sent are not touched.
    assert "mat_default" not in payload
    assert session.committed is True


def test_listar_linhas_custeio_por_chave(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="PECA", chave_valueset="MATERIAL_COSTAS"),
        _resumo(id=2, tipo_linha="PECA", chave_valueset="FERRAGEM_DOBRADICA"),
        _resumo(id=3, tipo_linha="DIVISAO_INDEPENDENTE", chave_valueset="MATERIAL_COSTAS"),
        _resumo(id=4, tipo_linha="PECA_COMPOSTA", chave_valueset="MATERIAL_COSTAS"),
        _resumo(id=5, tipo_linha="PECA", chave_valueset=None),
        _resumo(id=6, tipo_linha="FERRAGEM", chave_valueset="MATERIAL_COSTAS"),
    ]

    result = service.listar_linhas_custeio_por_chave(30, "material_costas")

    assert [linha.id for linha in result] == [1, 6]


def test_listar_linhas_custeio_por_chave_vazia(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    assert service.listar_linhas_custeio_por_chave(30, None) == []


def test_aplicar_valueset_item_em_linhas_custeio(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeItemValuesetRepository.by_id = _vs_linha(
        id=9,
        ref_le="LE99",
        descricao_no_orcamento="MDF B3002",
        unidade="m2",
        preco_liquido=Decimal("3.5"),
        comp_mp=Decimal("2750"),
        coresp_orla_0_4="ORLA_A",
    )
    _FakeRepository.by_id = _resumo(
        id=5,
        tipo_linha="PECA",
        chave_valueset="MATERIAL_COSTAS",
        comp="1000",
        qt_und=Decimal("2"),
        def_peca_id=3,
    )

    atualizadas = service.aplicar_valueset_item_em_linhas_custeio(9, [5])

    assert atualizadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["id"] == 5
    assert payload["ref_le"] == "LE99"
    assert payload["descricao_no_orcamento"] == "MDF B3002"
    assert payload["unidade"] == "m2"
    assert payload["preco_liquido"] == Decimal("3.5")
    assert payload["comp_mp"] == Decimal("2750")
    assert payload["coresp_orla_0_4"] == "ORLA_A"
    assert payload["mat_default"] == "AGL_19"
    assert payload["origem_material"] == "VALUESET_ITEM"
    assert payload["material_editado_localmente"] is False
    # Measures, quantities, key and def_peca are preserved (not in the update).
    assert "comp" not in payload
    assert "qt_und" not in payload
    assert "chave_valueset" not in payload
    assert "def_peca_id" not in payload
    assert "editado_localmente" not in payload
    assert session.committed is True


def test_aplicar_valueset_ignora_divisao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemValuesetRepository.by_id = _vs_linha(id=9)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="DIVISAO_INDEPENDENTE")

    atualizadas = service.aplicar_valueset_item_em_linhas_custeio(9, [5])

    assert atualizadas == 0
    assert _FakeRepository.updated_payload is None


def test_aplicar_valueset_linha_inexistente_levanta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemValuesetRepository.by_id = None

    try:
        service.aplicar_valueset_item_em_linhas_custeio(999, [5])
    except ValueError as error:
        assert "valueset" in str(error).lower()
    else:
        raise AssertionError("Expected ValueError")


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


def test_recalcular_orlas_do_item_ignora_divisao_e_composta(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            codigo_orlas="2222",
            comp_real=Decimal("2500"),
            larg_real=Decimal("600"),
            quantidade=Decimal("1"),
        ),
        _resumo(id=2, tipo_linha="DIVISAO_INDEPENDENTE", codigo_orlas="2222"),
        _resumo(id=3, tipo_linha="PECA_COMPOSTA", codigo_orlas="2222"),
    ]

    atualizadas = service.recalcular_orlas_do_item(30)

    assert atualizadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["id"] == 1
    assert payload["ml_orla_grossa"] == Decimal("6.6")
    assert payload["ml_orla_fina"] == Decimal("0")
    assert session.committed is True


def test_recalcular_orlas_do_item_resolve_preco(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeMateriaPrimaRepository.materias_por_ref = {
        "ORL0003": SimpleNamespace(preco_liquido=Decimal("11.50"), unidade="M2")
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            codigo_orlas="2222",
            comp_real=Decimal("2500"),
            larg_real=Decimal("600"),
            esp_real=Decimal("19"),
            quantidade=Decimal("1"),
            coresp_orla_1_0="ORL0003",
        ),
    ]

    service.recalcular_orlas_do_item(30)

    payload = _FakeRepository.updated_payload
    # ml_grossa = 6.6 ; largura(esp 19) = 22 ; preco_ml = 11.50 * 22/1000 = 0.253
    # custo = 6.6 * 0.253 = 1.6698 (M2 -> ML conversion applied).
    assert payload["ml_orla_grossa"] == Decimal("6.6")
    assert payload["custo_orla_grossa"] == Decimal("1.6698")
    assert payload["custo_orlas"] == Decimal("1.6698")


def test_recalcular_orlas_fallback_esp_mp_quando_esp_real_vazio(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeMateriaPrimaRepository.materias_por_ref = {
        "ORL0002": SimpleNamespace(preco_liquido=Decimal("6.50"), unidade="M2"),
        "ORL0003": SimpleNamespace(preco_liquido=Decimal("11.50"), unidade="M2"),
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            codigo_orlas="2111",
            comp_real=Decimal("2000"),
            larg_real=Decimal("1000"),
            esp_real=None,  # no esp formula -> must fall back to esp_mp
            esp_mp=Decimal("19"),
            quantidade=Decimal("1"),
            coresp_orla_0_4="ORL0002",
            coresp_orla_1_0="ORL0003",
        ),
    ]

    service.recalcular_orlas_do_item(30)

    payload = _FakeRepository.updated_payload
    # esp_mp 19 -> largura 22 -> M2 prices converted to ML.
    assert payload["ml_orla_fina"] == Decimal("4.3")
    assert payload["ml_orla_grossa"] == Decimal("2.1")
    assert payload["custo_orla_fina"] == Decimal("0.6149")
    assert payload["custo_orla_grossa"] == Decimal("0.5313")
    assert payload["custo_orlas"] == Decimal("1.1462")
    assert "observacoes" not in payload


def test_recalcular_orlas_unidade_desconhecida_preenche_observacao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeMateriaPrimaRepository.materias_por_ref = {
        "ORLX": SimpleNamespace(preco_liquido=Decimal("6.50"), unidade="UND")
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            codigo_orlas="2222",
            comp_real=Decimal("2500"),
            larg_real=Decimal("600"),
            esp_real=Decimal("19"),
            quantidade=Decimal("1"),
            coresp_orla_1_0="ORLX",
        ),
    ]

    service.recalcular_orlas_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["ml_orla_grossa"] == Decimal("6.6")
    assert payload["custo_orla_grossa"] is None
    assert payload["custo_orlas"] is None
    assert "unidade da orla" in payload["observacoes"]


def test_recalcular_orlas_so_altera_campos_de_orla(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="PECA", codigo_orlas="0000", chave_valueset="MATERIAL_X")
    ]

    service.recalcular_orlas_do_item(30)

    payload = _FakeRepository.updated_payload
    assert set(payload.keys()) == {
        "id",
        "ml_orla_fina",
        "ml_orla_grossa",
        "custo_orla_fina",
        "custo_orla_grossa",
        "custo_orlas",
    }
    # Measures and ValueSet are not touched.
    assert "comp_real" not in payload
    assert "chave_valueset" not in payload


def test_inserir_peca_simples_preenche_esp_do_material(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(id=1, tipo_peca="SIMPLES", chave_valueset_material="MATERIAL_COSTAS")
    }
    _FakeItemValuesetRepository.default_linha = _vs_linha(id=9, esp_mp=Decimal("19"))

    result = service.adicionar_pecas_da_biblioteca(10, [1])

    assert result.criadas == 1
    payload = _FakeRepository.created_payload
    assert payload["tipo_linha"] == "PECA"
    assert payload["esp"] == "19"
    assert payload["esp_mp"] == Decimal("19")


def test_inserir_peca_composta_principal_nao_recebe_esp(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(id=1, tipo_peca="COMPOSTA", chave_valueset_material="MATERIAL_COSTAS")
    }
    _FakeComponenteRepository.componentes = []
    _FakeItemValuesetRepository.default_linha = _vs_linha(id=9, esp_mp=Decimal("19"))

    service.adicionar_pecas_da_biblioteca(10, [1])

    principal = _FakeRepository.created_payloads[0]
    assert principal["tipo_linha"] == "PECA_COMPOSTA"
    assert "esp" not in principal


def test_aplicar_materia_prima_preenche_esp(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="PECA")
    _FakeMateriaPrimaRepository.materia = _materia(id=7, espessura=Decimal("12"))

    service.aplicar_materia_prima_na_linha(5, 7)

    payload = _FakeRepository.updated_payload
    assert payload["esp"] == "12"
    assert payload["esp_mp"] == Decimal("12")


def test_aplicar_materia_prima_copia_desperdicio_e_orlas(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="PECA")
    _FakeMateriaPrimaRepository.materia = _materia(
        id=7,
        desperdicio_percentagem=Decimal("0.10"),
        coresp_orla_0_4="ORL0002",
        coresp_orla_1_0="ORL0003",
        tipo_martelo=None,
        familia_martelo=None,
        tipo_original_excel="AGLOMERADO",
        familia_original_excel="PLACAS",
    )

    service.aplicar_materia_prima_na_linha(5, 7)

    payload = _FakeRepository.updated_payload
    assert payload["desperdicio_percentagem"] == Decimal("10")  # normalized to human
    assert payload["coresp_orla_0_4"] == "ORL0002"
    assert payload["coresp_orla_1_0"] == "ORL0003"
    assert payload["tipo_materia_prima"] == "AGLOMERADO"
    assert payload["familia_materia_prima"] == "PLACAS"


def test_aplicar_valueset_atualiza_esp(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeItemValuesetRepository.by_id = _vs_linha(id=9, esp_mp=Decimal("19"))
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="PECA")

    service.aplicar_valueset_item_em_linhas_custeio(9, [5])

    payload = _FakeRepository.updated_payload
    assert payload["esp"] == "19"


def test_recalcular_custo_mp_m2(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            unidade="M2",
            area_m2=Decimal("0.5"),
            quantidade=Decimal("6"),
            preco_liquido=Decimal("10"),
            desperdicio_percentagem=Decimal("0.20"),
        ),
    ]

    result = service.recalcular_custo_materia_prima_do_item(30)

    assert result.processadas == 1
    assert result.calculadas == 1
    assert result.ignoradas == 0
    payload = _FakeRepository.updated_payload
    assert payload["custo_mp"] == Decimal("36")
    assert "observacoes" not in payload


def test_recalcular_custo_mp_ignora_divisao_e_composta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="DIVISAO_INDEPENDENTE", unidade="M2"),
        _resumo(id=2, tipo_linha="PECA_COMPOSTA", unidade="M2"),
    ]

    result = service.recalcular_custo_materia_prima_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 2
    assert _FakeRepository.updated_payload is None


def test_recalcular_custo_mp_und_nao_avisa(monkeypatch) -> None:
    # UND is costed as Custo ferragem -> the MP recompute writes no UND note.
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="FERRAGEM", unidade="UND", preco_liquido=Decimal("6.50")),
    ]

    result = service.recalcular_custo_materia_prima_do_item(30)

    assert result.calculadas == 0
    payload = _FakeRepository.updated_payload
    assert payload["custo_mp"] is None
    assert "unidade UND" not in (payload.get("observacoes") or "")
    assert "unidade não validada" not in (payload.get("observacoes") or "")


def test_recalcular_custo_mp_limpa_observacao_obsoleta(monkeypatch) -> None:
    # An old obsolete MP note on a UND line is removed on the next recompute.
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="FERRAGEM",
            unidade="UND",
            preco_liquido=Decimal("6.50"),
            observacoes="Custo MP não calculado nesta fase: unidade UND.",
        ),
    ]

    service.recalcular_custo_materia_prima_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["observacoes"] is None  # obsolete note cleared


def test_recalcular_custo_mp_unidade_desconhecida(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="PECA", unidade="XPTO", preco_liquido=Decimal("6.50")),
    ]

    service.recalcular_custo_materia_prima_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_mp"] is None
    assert "Custo não calculado: unidade não validada." in payload["observacoes"]


def test_recalcular_custo_mp_so_altera_custo_mp(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            unidade="M2",
            area_m2=Decimal("0.5"),
            quantidade=Decimal("6"),
            preco_liquido=Decimal("10"),
            chave_valueset="MATERIAL_X",
            comp_real=Decimal("1000"),
        ),
    ]

    service.recalcular_custo_materia_prima_do_item(30)

    payload = _FakeRepository.updated_payload
    assert set(payload.keys()) == {"id", "custo_mp"}
    assert "comp_real" not in payload
    assert "chave_valueset" not in payload


def test_atualizar_material_local_marca_editado(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="PECA")

    service.atualizar_material_local_linha(5, {"desperdicio_percentagem": Decimal("35")})

    payload = _FakeRepository.updated_payload
    assert payload["desperdicio_percentagem"] == Decimal("35")
    assert payload["editado_localmente"] is True
    assert payload["material_editado_localmente"] is True
    assert session.committed is True


def test_eliminar_linhas(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    eliminadas = service.eliminar_linhas([3, 1, 2])

    assert eliminadas == 3
    assert _FakeRepository.deleted_ids == [3, 1, 2]
    assert session.committed is True


def test_eliminar_linhas_sem_ids(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    eliminadas = service.eliminar_linhas([])

    assert eliminadas == 0
    assert _FakeRepository.deleted_ids is None
    assert session.committed is False


def test_recalcular_custo_mp_preserva_observacao_de_orla(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="FERRAGEM",
            unidade="UND",
            preco_liquido=Decimal("6.50"),
            observacoes="Custo de orla não calculado: espessura da peça em falta.",
        ),
    ]

    service.recalcular_custo_materia_prima_do_item(30)

    payload = _FakeRepository.updated_payload
    # The orla note is preserved; no obsolete UND material-cost note is added (so
    # the observation may even be left unchanged).
    obs = payload.get("observacoes", _FakeRepository.active_rows[0].observacoes)
    assert "Custo de orla" in obs
    assert "unidade UND" not in obs


def test_recalcular_ferragens_und(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="FERRAGEM",
            unidade="UND",
            quantidade=Decimal("5"),
            preco_liquido=Decimal("2.53"),
            desperdicio_percentagem=Decimal("0.02"),
        ),
    ]

    result = service.recalcular_custos_ferragens_do_item(30)

    assert result.processadas == 1
    assert result.calculadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["custo_ferragem"] == Decimal("12.903")
    assert "observacoes" not in payload


def test_recalcular_ferragens_ignora_divisao_e_composta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="DIVISAO_INDEPENDENTE", unidade="UND"),
        _resumo(id=2, tipo_linha="PECA_COMPOSTA", unidade="UND"),
    ]

    result = service.recalcular_custos_ferragens_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 2
    assert _FakeRepository.updated_payload is None


def test_recalcular_ferragens_m2_nao_calcula(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            unidade="M2",
            quantidade=Decimal("5"),
            preco_liquido=Decimal("10"),
        ),
    ]

    result = service.recalcular_custos_ferragens_do_item(30)

    assert result.calculadas == 0
    payload = _FakeRepository.updated_payload
    assert payload["custo_ferragem"] is None
    assert "observacoes" not in payload  # M2 produces no hardware warning


def test_recalcular_ferragens_ml_deferido(monkeypatch) -> None:
    # ML lines are costed by the ML phase, not by the UND ferragem phase.
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="FERRAGEM",
            unidade="ML",
            quantidade=Decimal("5"),
            preco_liquido=Decimal("2.53"),
        ),
    ]

    service.recalcular_custos_ferragens_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_ferragem"] is None
    assert "observacoes" not in payload


def test_recalcular_ml_com_comp_real(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="FERRAGEM",
            unidade="ML",
            comp_real=Decimal("800"),
            quantidade=Decimal("2"),
            preco_liquido=Decimal("1.32"),
            desperdicio_percentagem=Decimal("10"),
        ),
    ]

    result = service.recalcular_custos_ml_do_item(30)

    assert result.processadas == 1
    assert result.calculadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["consumo_ml_unitario"] == Decimal("0.8")
    assert payload["consumo_ml_total"] == Decimal("1.6")
    assert payload["custo_ferragem"] == Decimal("2.3232")
    assert "observacoes" not in payload


def test_recalcular_ml_ignora_nao_ml(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="PECA", unidade="M2", comp_real=Decimal("800")),
        _resumo(id=2, tipo_linha="FERRAGEM", unidade="UND"),
        _resumo(id=3, tipo_linha="DIVISAO_INDEPENDENTE", unidade="ML"),
    ]

    result = service.recalcular_custos_ml_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 3
    assert _FakeRepository.updated_payload is None


def test_recalcular_ml_sem_dados_preenche_observacao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="FERRAGEM",
            unidade="ML",
            quantidade=Decimal("2"),
            preco_liquido=Decimal("1.32"),
        ),
    ]

    service.recalcular_custos_ml_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_ferragem"] is None
    assert "consumo ou preço em falta" in payload["observacoes"]


def test_recalcular_ml_so_altera_campos_ml(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="FERRAGEM",
            unidade="ML",
            comp_real=Decimal("800"),
            quantidade=Decimal("2"),
            preco_liquido=Decimal("1.32"),
            chave_valueset="FERRAGEM_X",
        ),
    ]

    service.recalcular_custos_ml_do_item(30)

    payload = _FakeRepository.updated_payload
    assert set(payload.keys()) == {
        "id",
        "consumo_ml_unitario",
        "consumo_ml_total",
        "custo_ferragem",
    }
    assert "chave_valueset" not in payload
    assert "custo_mp" not in payload


def test_recalcular_custo_total_sem_exclusoes(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            custo_mp=Decimal("10"),
            custo_ferragem=Decimal("2"),
            custo_orlas=Decimal("1.50"),
        ),
    ]

    result = service.recalcular_custo_total_do_item(30)

    assert result.processadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["custo_total"] == Decimal("13.50")


def test_recalcular_custo_total_com_exclusao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            custo_mp=Decimal("10"),
            custo_ferragem=Decimal("2"),
            custo_orlas=Decimal("1.50"),
            excluir_mp=True,
            excluir_orla=True,
        ),
    ]

    service.recalcular_custo_total_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_total"] == Decimal("2.00")


def test_recalcular_custo_total_ignora_divisao_e_composta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="DIVISAO_INDEPENDENTE", custo_mp=Decimal("10")),
        _resumo(id=2, tipo_linha="PECA_COMPOSTA", custo_mp=Decimal("10")),
    ]

    result = service.recalcular_custo_total_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 2
    assert _FakeRepository.updated_payload is None


def test_atualizar_exclusao_linha_recalcula_total(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(
        id=5,
        tipo_linha="PECA",
        custo_mp=Decimal("10"),
        custo_ferragem=Decimal("2"),
        custo_orlas=Decimal("1.50"),
    )

    service.atualizar_exclusao_linha(5, "excluir_mp", True)

    payload = _FakeRepository.updated_payload
    assert payload["excluir_mp"] is True
    assert payload["custo_total"] == Decimal("3.50")
    assert session.committed is True


def test_atualizar_exclusao_linha_campo_invalido(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="PECA")

    try:
        service.atualizar_exclusao_linha(5, "excluir_xpto", True)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_atualizar_exclusao_em_lote(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.lote_count = 4
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="PECA", custo_mp=Decimal("10")),
    ]

    result = service.atualizar_exclusao_em_lote(30, "excluir_mp", True)

    assert result.linhas_atualizadas == 4
    assert result.campo == "excluir_mp"
    assert result.valor is True
    assert _FakeRepository.lote_call == (30, "excluir_mp", True)
    # custo_total was recomputed afterwards.
    assert _FakeRepository.updated_payload is not None
    assert "custo_total" in _FakeRepository.updated_payload


def test_atualizar_exclusao_em_lote_campo_invalido(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    try:
        service.atualizar_exclusao_em_lote(30, "excluir_xpto", True)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    assert _FakeRepository.lote_call is None


def test_recalcular_areas_acabamento_sup_e_inf(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            area_m2=Decimal("2.1"),
            quantidade=Decimal("2"),
            acabamento_face_sup="LACADO",
            acabamento_face_inf="SEM_ACABAMENTO",
        ),
    ]

    result = service.recalcular_areas_acabamento_do_item(30)

    assert result.processadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["area_acabamento_sup"] == Decimal("4.2")
    assert payload["area_acabamento_inf"] == Decimal("0")
    assert "observacoes" not in payload


def test_recalcular_areas_acabamento_sem_acabamento(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="FERRAGEM",
            unidade="UND",
            acabamento_face_sup=None,
            acabamento_face_inf=None,
        ),
    ]

    service.recalcular_areas_acabamento_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["area_acabamento_sup"] is None
    assert payload["area_acabamento_inf"] is None


def test_recalcular_areas_acabamento_sem_area_observacao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            area_m2=None,
            acabamento_face_sup="LACADO",
        ),
    ]

    service.recalcular_areas_acabamento_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["area_acabamento_sup"] is None
    assert "Área de acabamento" in payload["observacoes"]


def test_recalcular_areas_acabamento_ignora_divisao_e_composta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="DIVISAO_INDEPENDENTE", acabamento_face_sup="LACADO"),
        _resumo(id=2, tipo_linha="PECA_COMPOSTA", acabamento_face_sup="LACADO"),
    ]

    result = service.recalcular_areas_acabamento_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 2
    assert _FakeRepository.updated_payload is None


def test_aplicar_acabamento_face_superior(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
        )
    }
    _FakeItemValuesetRepository.defaults_by_chave = {
        "ACABAMENTO_FACE_SUP": _vs_linha(codigo_opcao="LACADO_BRANCO")
    }
    _FakeRepository.active_rows = [_resumo(id=1, tipo_linha="PECA", def_peca_id=1)]

    result = service.aplicar_acabamentos_do_item(30)

    assert result.processadas == 1
    assert result.aplicadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["acabamento_face_sup"] == "LACADO_BRANCO"
    assert payload["acabamento_face_inf"] == "SEM_ACABAMENTO"
    assert "observacoes" not in payload


def test_aplicar_acabamento_ambas_as_faces(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
            chave_valueset_acabamento_inf="ACABAMENTO_FACE_INF",
        )
    }
    _FakeItemValuesetRepository.defaults_by_chave = {
        "ACABAMENTO_FACE_SUP": _vs_linha(codigo_opcao="LACADO_BRANCO"),
        "ACABAMENTO_FACE_INF": _vs_linha(codigo_opcao="LACADO_BRANCO"),
    }
    _FakeRepository.active_rows = [_resumo(id=1, tipo_linha="PECA", def_peca_id=1)]

    service.aplicar_acabamentos_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["acabamento_face_sup"] == "LACADO_BRANCO"
    assert payload["acabamento_face_inf"] == "LACADO_BRANCO"


def test_aplicar_acabamento_peca_sem_acabamento(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1, permite_acabamento=False)}
    _FakeRepository.active_rows = [_resumo(id=1, tipo_linha="PECA", def_peca_id=1)]

    result = service.aplicar_acabamentos_do_item(30)

    assert result.aplicadas == 0
    payload = _FakeRepository.updated_payload
    assert payload["acabamento_face_sup"] == "SEM_ACABAMENTO"
    assert payload["acabamento_face_inf"] == "SEM_ACABAMENTO"


def test_aplicar_acabamento_ignora_ferragem_divisao_composta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="FERRAGEM", def_peca_id=3),
        _resumo(id=2, tipo_linha="DIVISAO_INDEPENDENTE"),
        _resumo(id=3, tipo_linha="PECA_COMPOSTA", def_peca_id=1),
        _resumo(id=4, tipo_linha="PECA", def_peca_id=None),  # no def_peca
    ]

    result = service.aplicar_acabamentos_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 4
    assert _FakeRepository.updated_payload is None


def test_recalcular_custo_acabamento_superior(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
        )
    }
    _FakeItemValuesetRepository.defaults_by_chave = {
        "ACABAMENTO_FACE_SUP": _vs_linha(
            codigo_opcao="LACAGEM",
            preco_liquido=Decimal("18.0"),
            desperdicio_percentagem=Decimal("1"),
        )
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            acabamento_face_sup="LACAGEM",
            area_acabamento_sup=Decimal("2.0"),
            acabamento_face_inf="SEM_ACABAMENTO",
        ),
    ]

    result = service.recalcular_custo_acabamento_do_item(30)

    assert result.calculadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["custo_acabamento"] == Decimal("36.36")
    assert "observacoes" not in payload


def test_recalcular_custo_acabamento_ambas_faces(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
            chave_valueset_acabamento_inf="ACABAMENTO_FACE_INF",
        )
    }
    vs = _vs_linha(
        codigo_opcao="LACAGEM",
        preco_liquido=Decimal("18.0"),
        desperdicio_percentagem=Decimal("1"),
    )
    _FakeItemValuesetRepository.defaults_by_chave = {
        "ACABAMENTO_FACE_SUP": vs,
        "ACABAMENTO_FACE_INF": vs,
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            acabamento_face_sup="LACAGEM",
            area_acabamento_sup=Decimal("2.0"),
            acabamento_face_inf="LACAGEM",
            area_acabamento_inf=Decimal("2.0"),
        ),
    ]

    service.recalcular_custo_acabamento_do_item(30)

    assert _FakeRepository.updated_payload["custo_acabamento"] == Decimal("72.72")


def test_recalcular_custo_acabamento_sem_acabamento(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            acabamento_face_sup="SEM_ACABAMENTO",
            acabamento_face_inf="SEM_ACABAMENTO",
        ),
    ]

    service.recalcular_custo_acabamento_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_acabamento"] == Decimal("0")
    assert "observacoes" not in payload


def test_recalcular_custo_acabamento_sem_area_nao_duplica(monkeypatch) -> None:
    # With a finish but no area, the cost recompute leaves the cost empty and does
    # NOT add an "área de acabamento" note (the dimensions diagnostic is written by
    # recalcular_areas_acabamento_do_item).
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
        )
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            acabamento_face_sup="LACAGEM",
            area_acabamento_sup=None,
        ),
    ]

    service.recalcular_custo_acabamento_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_acabamento"] is None
    assert "observacoes" not in payload  # no duplicate finishing note


def test_recalcular_areas_acabamento_sem_area_avisa_dimensoes(monkeypatch) -> None:
    # The clear "dimensões Comp/Larg em falta" note comes from the area recompute.
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            acabamento_face_sup="LACAGEM",
            area_m2=None,
        ),
    ]

    service.recalcular_areas_acabamento_do_item(30)

    obs = _FakeRepository.updated_payload["observacoes"]
    assert "dimensões Comp/Larg em falta" in obs


def _ligacao_op(def_operacao_id: int):
    return SimpleNamespace(def_operacao_id=def_operacao_id)


def _operacao(
    codigo: str,
    maquina_id=None,
    tipo_operacao=None,
    unidade_calculo=None,
    tempo_base=None,
    tempo_setup=None,
):
    return SimpleNamespace(
        codigo=codigo,
        nome=codigo,
        maquina_id=maquina_id,
        tipo_operacao=tipo_operacao,
        unidade_calculo=unidade_calculo,
        tempo_base=tempo_base,
        tempo_setup=tempo_setup,
    )


def test_aplicar_operacoes_preenche_operacoes_e_maquina(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1, codigo="PORTA_SIMPLES")}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {1: [_ligacao_op(2), _ligacao_op(3)]}
    _FakeOperacaoRepository.operacoes = {
        2: _operacao("CORTE", maquina_id=10),
        3: _operacao("ORLAGEM", maquina_id=11),
    }
    _FakeMaquinaRepository.maquinas = {
        10: SimpleNamespace(codigo="SECCIONADORA", nome="Seccionadora"),
        11: SimpleNamespace(codigo="ORLADORA", nome="Orladora"),
    }
    _FakeRepository.active_rows = [_resumo(id=1, tipo_linha="PECA", def_peca_id=1)]

    result = service.aplicar_operacoes_do_item(30)

    assert result.processadas == 1
    assert result.aplicadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["operacoes"] == "CORTE; ORLAGEM"
    assert payload["maquina"] == "SECCIONADORA; ORLADORA"


def test_aplicar_operacoes_sem_operacoes_fica_vazio(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {}
    _FakeRepository.active_rows = [_resumo(id=1, tipo_linha="PECA", def_peca_id=1)]

    result = service.aplicar_operacoes_do_item(30)

    assert result.aplicadas == 0
    payload = _FakeRepository.updated_payload
    assert payload["operacoes"] is None
    assert payload["maquina"] is None


def test_aplicar_operacoes_ignora_ferragem_divisao_composta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="FERRAGEM", def_peca_id=1),
        _resumo(id=2, tipo_linha="DIVISAO_INDEPENDENTE"),
        _resumo(id=3, tipo_linha="PECA_COMPOSTA", def_peca_id=1),
        _resumo(id=4, tipo_linha="PECA", def_peca_id=None),
    ]

    result = service.aplicar_operacoes_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 4
    assert _FakeRepository.updated_payload is None


def test_aplicar_operacoes_preserva_edicao_local(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {1: [_ligacao_op(2)]}
    _FakeOperacaoRepository.operacoes = {2: _operacao("CORTE")}
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            operacoes="OP MANUAL",
            editado_localmente=True,
        ),
    ]

    result = service.aplicar_operacoes_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 1
    assert _FakeRepository.updated_payload is None  # manual operations preserved


def test_recalcular_tempos_corte_orlagem_cnc(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {
        1: [_ligacao_op(2), _ligacao_op(3), _ligacao_op(4)]
    }
    _FakeOperacaoRepository.operacoes = {
        2: _operacao("CORTE_PAINEL", tipo_operacao="CORTE", unidade_calculo="PECA", tempo_base=Decimal("2")),
        3: _operacao("ORLAGEM_PECA", tipo_operacao="ORLAGEM", unidade_calculo="ML", tempo_base=Decimal("1")),
        4: _operacao("CNC_MECANIZACAO", tipo_operacao="CNC", unidade_calculo="PECA", tempo_base=Decimal("4")),
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            quantidade=Decimal("3"),
            ml_orla_fina=Decimal("2"),
            ml_orla_grossa=Decimal("3"),
        ),
    ]

    result = service.recalcular_tempos_producao_do_item(30)

    assert result.calculadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["tempo_corte"] == Decimal("6")  # 2 x 3
    assert payload["tempo_orlagem"] == Decimal("5")  # 1 x (2+3)
    assert payload["tempo_cnc"] == Decimal("12")  # 4 x 3
    assert "observacoes" not in payload


def test_recalcular_tempos_sem_dados_observacao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {1: [_ligacao_op(2)]}
    _FakeOperacaoRepository.operacoes = {
        2: _operacao("CORTE_PAINEL", tipo_operacao="CORTE", unidade_calculo="PECA"),
    }
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="PECA", def_peca_id=1, quantidade=Decimal("3")),
    ]

    service.recalcular_tempos_producao_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["tempo_corte"] is None
    assert "Tempos de produção não calculados" in payload["observacoes"]


def test_recalcular_tempos_ignora_ferragem_divisao_composta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="FERRAGEM", def_peca_id=1),
        _resumo(id=2, tipo_linha="DIVISAO_INDEPENDENTE"),
        _resumo(id=3, tipo_linha="PECA_COMPOSTA", def_peca_id=1),
    ]

    result = service.recalcular_tempos_producao_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 3
    assert _FakeRepository.updated_payload is None


def test_recalcular_tempos_preserva_edicao_local(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {1: [_ligacao_op(2)]}
    _FakeOperacaoRepository.operacoes = {
        2: _operacao("CORTE_PAINEL", tipo_operacao="CORTE", unidade_calculo="PECA", tempo_base=Decimal("2")),
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            quantidade=Decimal("3"),
            tempo_corte=Decimal("99"),
            editado_localmente=True,
        ),
    ]

    result = service.recalcular_tempos_producao_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 1
    assert _FakeRepository.updated_payload is None  # local times preserved


def _maquina_tarifa(codigo, preco_ml_std=None, custo_setup_peca_std=None):
    return SimpleNamespace(
        id=0,
        codigo=codigo,
        preco_ml_std=preco_ml_std,
        custo_setup_peca_std=custo_setup_peca_std,
    )


def test_recalcular_custos_producao_corte(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {1: [_ligacao_op(2)]}
    _FakeOperacaoRepository.operacoes = {
        2: _operacao("CORTE_PAINEL", tipo_operacao="CORTE", maquina_id=10),
    }
    _FakeMaquinaRepository.maquinas = {
        10: _maquina_tarifa("CORTE", preco_ml_std=Decimal("0.45"), custo_setup_peca_std=Decimal("0.05")),
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            perimetro_ml=Decimal("3.0"),
            quantidade=Decimal("2"),
        ),
    ]

    result = service.recalcular_custos_producao_do_item(30)

    assert result.calculadas == 1
    payload = _FakeRepository.updated_payload
    assert payload["custo_corte"] == Decimal("2.80")  # 3 x 2 x 0.45 + 2 x 0.05
    assert payload["custo_orlagem"] is None
    assert payload["custo_producao"] == Decimal("2.80")
    assert "observacoes" not in payload


def test_recalcular_custos_producao_orlagem(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {1: [_ligacao_op(3)]}
    _FakeOperacaoRepository.operacoes = {
        3: _operacao("ORLAGEM_PECA", tipo_operacao="ORLAGEM", maquina_id=11),
    }
    _FakeMaquinaRepository.maquinas = {
        11: _maquina_tarifa("ORLAGEM", preco_ml_std=Decimal("0.70"), custo_setup_peca_std=Decimal("0.10")),
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            ml_orla_fina=Decimal("2.4"),
            ml_orla_grossa=Decimal("2.0"),
            quantidade=Decimal("1"),
        ),
    ]

    service.recalcular_custos_producao_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_orlagem"] == Decimal("3.18")  # 4.4 x 0.70 + 1 x 0.10
    assert payload["custo_producao"] == Decimal("3.18")


def test_recalcular_custos_producao_corte_e_orlagem(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {1: [_ligacao_op(2), _ligacao_op(3)]}
    _FakeOperacaoRepository.operacoes = {
        2: _operacao("CORTE_PAINEL", tipo_operacao="CORTE", maquina_id=10),
        3: _operacao("ORLAGEM_PECA", tipo_operacao="ORLAGEM", maquina_id=11),
    }
    _FakeMaquinaRepository.maquinas = {
        10: _maquina_tarifa("CORTE", preco_ml_std=Decimal("0.45"), custo_setup_peca_std=Decimal("0.05")),
        11: _maquina_tarifa("ORLAGEM", preco_ml_std=Decimal("0.70"), custo_setup_peca_std=Decimal("0.10")),
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            perimetro_ml=Decimal("3.0"),
            ml_orla_fina=Decimal("2.4"),
            ml_orla_grossa=Decimal("2.0"),
            quantidade=Decimal("2"),
        ),
    ]

    service.recalcular_custos_producao_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_corte"] == Decimal("2.80")
    assert payload["custo_orlagem"] == Decimal("3.28")  # 4.4 x 0.70 + 2 x 0.10
    assert payload["custo_producao"] == Decimal("6.08")


def test_recalcular_custos_producao_sem_orla(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {1: [_ligacao_op(3)]}
    _FakeOperacaoRepository.operacoes = {
        3: _operacao("ORLAGEM_PECA", tipo_operacao="ORLAGEM", maquina_id=11),
    }
    _FakeMaquinaRepository.maquinas = {
        11: _maquina_tarifa("ORLAGEM", preco_ml_std=Decimal("0.70"), custo_setup_peca_std=Decimal("0.10")),
    }
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="PECA", def_peca_id=1, quantidade=Decimal("2")),
    ]

    service.recalcular_custos_producao_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_orlagem"] == Decimal("0")  # peça sem orla
    assert "observacoes" not in payload


def test_recalcular_custos_producao_maquina_sem_tarifa(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakePecaOperacaoRepository.ligacoes_por_peca = {1: [_ligacao_op(2)]}
    _FakeOperacaoRepository.operacoes = {
        2: _operacao("CORTE_PAINEL", tipo_operacao="CORTE", maquina_id=10),
    }
    _FakeMaquinaRepository.maquinas = {10: _maquina_tarifa("CORTE", preco_ml_std=None)}
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            perimetro_ml=Decimal("3.0"),
            quantidade=Decimal("2"),
        ),
    ]

    service.recalcular_custos_producao_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_corte"] is None
    assert payload["custo_producao"] is None
    assert "tarifa €/ML em falta na máquina CORTE" in payload["observacoes"]


def test_recalcular_custos_producao_ignora_ferragem_divisao_composta(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="FERRAGEM", def_peca_id=1),
        _resumo(id=2, tipo_linha="DIVISAO_INDEPENDENTE"),
        _resumo(id=3, tipo_linha="PECA_COMPOSTA", def_peca_id=1),
    ]

    result = service.recalcular_custos_producao_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 3
    assert _FakeRepository.updated_payload is None


def test_custo_total_inclui_producao_respeita_exclusao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            custo_mp=Decimal("10"),
            custo_producao=Decimal("5"),
            excluir_producao=False,
        ),
        _resumo(
            id=2,
            tipo_linha="PECA",
            custo_mp=Decimal("10"),
            custo_producao=Decimal("5"),
            excluir_producao=True,
        ),
    ]

    service.recalcular_custo_total_do_item(30)

    payloads = {p["id"]: p for p in _FakeRepository.updated_payloads}
    assert payloads[1]["custo_total"] == Decimal("15")  # produção incluída
    assert payloads[2]["custo_total"] == Decimal("10")  # produção excluída


def test_recalcular_custo_acabamento_sem_preco_observacao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
        )
    }
    _FakeItemValuesetRepository.defaults_by_chave = {}
    _FakeItemValuesetRepository.default_linha = None
    _FakeItemValuesetRepository.chave_rows = []
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            acabamento_face_sup="LACAGEM",
            area_acabamento_sup=Decimal("2.0"),
        ),
    ]

    service.recalcular_custo_acabamento_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["custo_acabamento"] is None
    assert "preço do acabamento não encontrado" in payload["observacoes"]


def test_custo_acabamento_local_prevalece(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
        )
    }
    _FakeItemValuesetRepository.defaults_by_chave = {
        "ACABAMENTO_FACE_SUP": _vs_linha(
            preco_liquido=Decimal("18.0"), desperdicio_percentagem=Decimal("1")
        )
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            acabamento_face_sup="LACAGEM",
            area_acabamento_sup=Decimal("2.0"),
            acabamento_face_inf="SEM_ACABAMENTO",
            acabamento_editado_localmente=True,
            acabamento_sup_preco_liquido=Decimal("20.0"),
            acabamento_sup_desperdicio_percentagem=Decimal("1"),
        ),
    ]

    service.recalcular_custo_acabamento_do_item(30)

    # Local price 20 prevails over the ValueSet 18: 2 x 20 x 1.01 = 40.40.
    assert _FakeRepository.updated_payload["custo_acabamento"] == Decimal("40.40")


def test_custo_acabamento_local_desperdicio(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {1: _peca(id=1)}
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            acabamento_face_sup="LACAGEM",
            area_acabamento_sup=Decimal("2.0"),
            acabamento_editado_localmente=True,
            acabamento_sup_preco_liquido=Decimal("18.0"),
            acabamento_sup_desperdicio_percentagem=Decimal("5"),
        ),
    ]

    service.recalcular_custo_acabamento_do_item(30)

    # 2 x 18 x 1.05 = 37.80.
    assert _FakeRepository.updated_payload["custo_acabamento"] == Decimal("37.80")


def test_custo_acabamento_local_sem_preco_fallback_valueset(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
        )
    }
    _FakeItemValuesetRepository.defaults_by_chave = {
        "ACABAMENTO_FACE_SUP": _vs_linha(
            preco_liquido=Decimal("18.0"), desperdicio_percentagem=Decimal("1")
        )
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            acabamento_face_sup="LACAGEM",
            area_acabamento_sup=Decimal("2.0"),
            acabamento_editado_localmente=True,
            acabamento_sup_preco_liquido=None,  # empty local price -> ValueSet
        ),
    ]

    service.recalcular_custo_acabamento_do_item(30)

    assert _FakeRepository.updated_payload["custo_acabamento"] == Decimal("36.36")


def test_aplicar_acabamento_nao_sobrescreve_local(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
        )
    }
    _FakeItemValuesetRepository.defaults_by_chave = {
        "ACABAMENTO_FACE_SUP": _vs_linha(codigo_opcao="LACADO_BRANCO")
    }
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            def_peca_id=1,
            acabamento_face_sup="LACAGEM_ESPECIAL",
            acabamento_editado_localmente=True,
        ),
    ]

    result = service.aplicar_acabamentos_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 1
    assert _FakeRepository.updated_payload is None  # local edit preserved


def test_atualizar_acabamento_local_linha_marca_flag(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="PECA", def_peca_id=1)
    _FakeRepository.active_rows = [_FakeRepository.by_id]
    _FakePecaRepository.pecas = {1: _peca(id=1)}

    service.atualizar_acabamento_local_linha(
        5,
        {
            "acabamento_face_sup": "LACAGEM",
            "acabamento_sup_preco_liquido": Decimal("20.0"),
            "acabamento_sup_desperdicio_percentagem": Decimal("1"),
        },
    )

    saves = [
        p
        for p in _FakeRepository.updated_payloads
        if p.get("acabamento_editado_localmente") is True
    ]
    assert saves, "expected a local-finish save"
    assert saves[0]["acabamento_sup_preco_liquido"] == Decimal("20.0")
    assert saves[0]["acabamento_face_sup"] == "LACAGEM"
    # Editing finishing data also flips the visual "Editado localmente" flag.
    assert saves[0]["editado_localmente"] is True


def test_atualizar_acabamento_local_linha_nao_peca(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_id = _resumo(id=5, tipo_linha="FERRAGEM")

    try:
        service.atualizar_acabamento_local_linha(5, {"acabamento_face_sup": "LACAGEM"})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_recalcular_custo_acabamento_ignora_ferragem(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, tipo_linha="FERRAGEM", def_peca_id=3),
        _resumo(id=2, tipo_linha="DIVISAO_INDEPENDENTE"),
    ]

    result = service.recalcular_custo_acabamento_do_item(30)

    assert result.processadas == 0
    assert result.ignoradas == 2
    assert _FakeRepository.updated_payload is None


def test_custo_total_inclui_acabamento_respeita_exclusao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="PECA",
            custo_mp=Decimal("10"),
            custo_acabamento=Decimal("5"),
            excluir_acabamento=False,
        ),
        _resumo(
            id=2,
            tipo_linha="PECA",
            custo_mp=Decimal("10"),
            custo_acabamento=Decimal("5"),
            excluir_acabamento=True,
        ),
    ]

    service.recalcular_custo_total_do_item(30)

    payloads = {p["id"]: p for p in _FakeRepository.updated_payloads}
    assert payloads[1]["custo_total"] == Decimal("15")  # acabamento incluído
    assert payloads[2]["custo_total"] == Decimal("10")  # acabamento excluído


def test_aplicar_acabamento_valueset_sem_valor(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakePecaRepository.pecas = {
        1: _peca(
            id=1,
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
        )
    }
    _FakeItemValuesetRepository.defaults_by_chave = {}
    _FakeItemValuesetRepository.default_linha = None
    _FakeItemValuesetRepository.chave_rows = []
    _FakeRepository.active_rows = [_resumo(id=1, tipo_linha="PECA", def_peca_id=1)]

    service.aplicar_acabamentos_do_item(30)

    payload = _FakeRepository.updated_payload
    assert payload["acabamento_face_sup"] == "SEM_ACABAMENTO"
    assert "ACABAMENTO_FACE_SUP sem valor no ValueSet" in payload["observacoes"]


def test_recalcular_ferragens_so_altera_custo_ferragem(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(
            id=1,
            tipo_linha="FERRAGEM",
            unidade="UND",
            quantidade=Decimal("5"),
            preco_liquido=Decimal("2.53"),
            chave_valueset="FERRAGEM_X",
            comp_real=Decimal("100"),
        ),
    ]

    service.recalcular_custos_ferragens_do_item(30)

    payload = _FakeRepository.updated_payload
    assert set(payload.keys()) == {"id", "custo_ferragem"}
    assert "comp_real" not in payload
    assert "chave_valueset" not in payload
    assert "custo_mp" not in payload
