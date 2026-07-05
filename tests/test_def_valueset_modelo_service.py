"""Tests for the DefValuesetModelo service."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo
from app.services import def_valueset_modelo_service as service_module


def _resumo(**kwargs) -> DefValuesetModeloResumo:
    base = {
        "id": 1,
        "codigo": "BASE",
        "nome": "Base",
        "descricao": None,
        "tipo": None,
        "ambito": "UTILIZADOR",
        "user_id": None,
        "visivel_para_todos": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return DefValuesetModeloResumo(**base)


class _FakeRepository:
    rows: list[DefValuesetModeloResumo] = []
    active_rows: list[DefValuesetModeloResumo] = []
    by_codigo: DefValuesetModeloResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    activate_result = True
    deactivated_id: int | None = None
    activated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self):
        return self.rows

    def list_active(self):
        return self.active_rows

    def get_by_id(self, id: int):
        return _resumo(id=id)

    def get_by_codigo(self, codigo: str):
        return self.by_codigo

    def create(self, **fields):
        self.__class__.created_payload = fields
        return _resumo(id=1, **fields)

    def update(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        return _resumo(id=id, **fields)

    def deactivate(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result

    def activate(self, id: int) -> bool:
        self.__class__.activated_id = id
        return self.activate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


class _FakeLinhaService:
    linhas: list[SimpleNamespace] = []
    created_data: list[object] = []
    listed_modelo_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def listar_linhas_do_modelo(self, modelo_id: int):
        self.__class__.listed_modelo_id = modelo_id
        return self.__class__.linhas

    def criar_linha(self, data):
        self.__class__.created_data.append(data)
        return SimpleNamespace(id=len(self.__class__.created_data))


def _reset() -> None:
    _FakeRepository.rows = []
    _FakeRepository.active_rows = []
    _FakeRepository.by_codigo = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.activate_result = True
    _FakeRepository.deactivated_id = None
    _FakeRepository.activated_id = None
    _FakeLinhaService.linhas = []
    _FakeLinhaService.created_data = []
    _FakeLinhaService.listed_modelo_id = None


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "DefValuesetModeloRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.DefValuesetModeloService(session=session), session


def test_listar_modelos(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.rows = [_resumo(id=3)]

    assert service.listar_modelos() == [_resumo(id=3)]


def test_listar_modelos_utilizador_e_globais(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, codigo="USER", ambito="UTILIZADOR", visivel_para_todos=False),
        _resumo(id=2, codigo="GLOB", ambito="GLOBAL", visivel_para_todos=False),
        _resumo(id=3, codigo="SHARED", ambito="UTILIZADOR", visivel_para_todos=True),
    ]

    utilizador = service.listar_modelos_utilizador()
    globais = service.listar_modelos_globais()

    assert [modelo.codigo for modelo in utilizador] == ["USER"]
    assert sorted(modelo.codigo for modelo in globais) == ["GLOB", "SHARED"]


def test_criar_modelo_normaliza_campos(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.criar_modelo(
        service_module.CriarDefValuesetModeloData(
            codigo=" BASE ",
            nome=" Modelo Base ",
            tipo=" roupeiro ",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["codigo"] == "BASE"
    assert _FakeRepository.created_payload["nome"] == "Modelo Base"
    assert _FakeRepository.created_payload["tipo"] == "roupeiro"
    assert result.codigo == "BASE"
    assert session.committed is True


def test_criar_modelo_inclui_ambito_e_codigo_upper(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_modelo(
        service_module.CriarDefValuesetModeloData(
            codigo="roupeiro standard",
            nome="Roupeiro standard",
            ambito="global",
            visivel_para_todos=True,
        )
    )

    payload = _FakeRepository.created_payload
    assert payload["codigo"] == "ROUPEIRO_STANDARD"
    assert payload["ambito"] == "GLOBAL"
    assert payload["visivel_para_todos"] is True


def test_criar_modelo_recusa_codigo_duplicado(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_codigo = _resumo(id=9, codigo="BASE")

    try:
        service.criar_modelo(
            service_module.CriarDefValuesetModeloData(codigo="BASE", nome="Base")
        )
    except ValueError as error:
        assert "codigo" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_editar_modelo_permite_mesmo_codigo_da_propria_linha(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_codigo = _resumo(id=5, codigo="BASE")

    result = service.editar_modelo(
        5,
        service_module.EditarDefValuesetModeloData(codigo="BASE", nome="Base Editada"),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 5
    assert result.nome == "Base Editada"
    assert session.committed is True


def test_duplicar_modelo_cria_modelo_e_copia_linhas(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    monkeypatch.setattr(
        service_module, "DefValuesetModeloLinhaService", _FakeLinhaService
    )
    _FakeLinhaService.linhas = [
        SimpleNamespace(
            chave="MATERIAL_LATERAIS",
            codigo_opcao="AGL_19",
            nome_opcao="Aglomerado 19",
            padrao=True,
            ordem=2,
            descricao="Linha base",
            materia_prima_id=10,
            ref_materia_prima="REF-10",
            descricao_materia_prima="Aglomerado",
            valor_texto="Aglomerado 19",
            origem="MODELO",
            ref_le="LE-10",
            descricao_no_orcamento="Aglomerado orcamento",
            preco_tabela=Decimal("10"),
            margem_percentagem=Decimal("20"),
            desconto_percentagem=Decimal("5"),
            preco_liquido=Decimal("11.40"),
            unidade="M2",
            desperdicio_percentagem=Decimal("7"),
            tipo_materia_prima="PLACA",
            familia_materia_prima="AGL",
            coresp_orla_0_4="ORLA04",
            coresp_orla_1_0="ORLA10",
            comp_mp=Decimal("2800"),
            larg_mp=Decimal("2070"),
            esp_mp=Decimal("19"),
            origem_dados="MATERIA_PRIMA",
            editado_localmente=False,
            ativo=True,
            observacoes="obs",
        )
    ]

    result = service.duplicar_modelo(
        7,
        service_module.CriarDefValuesetModeloData(
            codigo=" base copia ",
            nome="Base copia",
            tipo="Roupeiro",
            ambito="global",
            ativo=False,
        ),
    )

    assert result.modelo.codigo == "BASE_COPIA"
    assert result.linhas_copiadas == 1
    assert _FakeLinhaService.listed_modelo_id == 7
    assert len(_FakeLinhaService.created_data) == 1
    criada = _FakeLinhaService.created_data[0]
    assert criada.def_valueset_modelo_id == result.modelo.id
    assert criada.chave == "MATERIAL_LATERAIS"
    assert criada.codigo_opcao == "AGL_19"
    assert criada.padrao is True
    assert criada.preco_tabela == Decimal("10")
    assert criada.origem_dados == "MATERIA_PRIMA"


def test_desativar_e_ativar_modelo(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_modelo(10) is True
    assert _FakeRepository.deactivated_id == 10
    assert session.committed is True

    session.committed = False
    assert service.ativar_modelo(10) is True
    assert _FakeRepository.activated_id == 10
    assert session.committed is True
