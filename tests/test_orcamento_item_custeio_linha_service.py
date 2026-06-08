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


class _FakeMateriaPrimaRepository:
    materia = None

    def __init__(self, _session: object) -> None:
        pass

    def get_by_id(self, id: int):
        return self.materia


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
        self.item = None

    def get(self, _model, _id):
        return self.item

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.all_rows = []
    _FakeRepository.active_rows = []
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
    _FakePecaRepository.pecas = {}
    _FakeComponenteRepository.componentes = []
    _FakeItemValuesetRepository.default_linha = None
    _FakeItemValuesetRepository.chave_rows = []
    _FakeMateriaPrimaRepository.materia = None


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
    assert payload["editado_localmente"] is True
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
    assert payload["editado_localmente"] is True


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
