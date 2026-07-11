"""Tests for the DefPeca service."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.repositories.def_peca_repository import DefPecaResumo
from app.services import def_peca_service as service_module
from app.services.def_operacao_service import CriarDefOperacaoData, DefOperacaoService
from app.services.def_peca_componente_service import (
    CriarDefPecaComponenteData,
    DefPecaComponenteService,
)
from app.services.def_peca_operacao_service import (
    CriarDefPecaOperacaoData,
    DefPecaOperacaoService,
)


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class _FakeRepository:
    rows: list[DefPecaResumo] = []
    created_payload: dict[str, object] | None = None
    updated_payload: dict[str, object] | None = None
    deactivate_result = True
    deactivated_id: int | None = None
    activate_result = True
    activated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self) -> list[DefPecaResumo]:
        return self.rows

    def list_ativas_para_biblioteca(self) -> list[DefPecaResumo]:
        return [row for row in self.rows if row.ativo]

    def create_def_peca(self, **kwargs) -> DefPecaResumo:
        self.__class__.created_payload = kwargs
        return DefPecaResumo(
            id=1,
            codigo=kwargs["codigo"],
            nome=kwargs["nome"],
            descricao=kwargs["descricao"],
            grupo=kwargs["grupo"],
            tipo_peca=kwargs["tipo_peca"],
            ativo=kwargs["ativo"],
            orla_c1=kwargs["orla_c1"],
            orla_c2=kwargs["orla_c2"],
            orla_l1=kwargs["orla_l1"],
            orla_l2=kwargs["orla_l2"],
            chave_valueset_material=kwargs["chave_valueset_material"],
            permite_acabamento=kwargs["permite_acabamento"],
            chave_valueset_acabamento_sup=kwargs["chave_valueset_acabamento_sup"],
            chave_valueset_acabamento_inf=kwargs["chave_valueset_acabamento_inf"],
        )

    def update_def_peca(self, **kwargs) -> DefPecaResumo:
        self.__class__.updated_payload = kwargs
        return DefPecaResumo(
            id=kwargs["id"],
            codigo=kwargs["codigo"],
            nome=kwargs["nome"],
            descricao=kwargs["descricao"],
            grupo=kwargs["grupo"],
            tipo_peca=kwargs["tipo_peca"],
            ativo=kwargs["ativo"],
            orla_c1=kwargs["orla_c1"],
            orla_c2=kwargs["orla_c2"],
            orla_l1=kwargs["orla_l1"],
            orla_l2=kwargs["orla_l2"],
            chave_valueset_material=kwargs["chave_valueset_material"],
            permite_acabamento=kwargs["permite_acabamento"],
            chave_valueset_acabamento_sup=kwargs["chave_valueset_acabamento_sup"],
            chave_valueset_acabamento_inf=kwargs["chave_valueset_acabamento_inf"],
        )

    def deactivate_def_peca(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result

    def activate_def_peca(self, id: int) -> bool:
        self.__class__.activated_id = id
        return self.activate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def test_def_peca_service_lista_pecas(monkeypatch) -> None:
    _FakeRepository.rows = []
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)

    service = service_module.DefPecaService(session=object())

    assert service.listar_pecas() == []


def test_def_peca_service_lista_ativas_para_biblioteca(monkeypatch) -> None:
    _FakeRepository.rows = [
        DefPecaResumo(
            id=1,
            codigo="COSTA",
            nome="Costa",
            descricao=None,
            grupo="COSTAS",
            tipo_peca="SIMPLES",
            ativo=True,
        ),
        DefPecaResumo(
            id=2,
            codigo="VELHA",
            nome="Peca velha",
            descricao=None,
            grupo="COSTAS",
            tipo_peca="SIMPLES",
            ativo=False,
        ),
    ]
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)

    service = service_module.DefPecaService(session=object())
    result = service.listar_ativas_para_biblioteca()

    assert [peca.codigo for peca in result] == ["COSTA"]


def test_def_peca_service_cria_peca_com_tipo_default(monkeypatch) -> None:
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    result = service.criar_peca(
        service_module.CriarDefPecaData(
            codigo=" LAT ",
            nome=" Lateral ",
            descricao="Peca lateral",
            grupo="Roupeiros",
            tipo_peca=None,
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["codigo"] == "LAT"
    assert _FakeRepository.created_payload["nome"] == "Lateral"
    assert _FakeRepository.created_payload["tipo_peca"] == "SIMPLES"
    assert _FakeRepository.created_payload["orla_c1"] == 0
    assert _FakeRepository.created_payload["orla_c2"] == 0
    assert _FakeRepository.created_payload["orla_l1"] == 0
    assert _FakeRepository.created_payload["orla_l2"] == 0
    assert result.tipo_peca == "SIMPLES"
    assert session.committed is True


def test_def_peca_service_normaliza_tipo_ao_editar(monkeypatch) -> None:
    _FakeRepository.updated_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    result = service.editar_peca(
        8,
        service_module.EditarDefPecaData(
            codigo="PC",
            nome="Peca Composta",
            descricao=None,
            grupo=None,
            tipo_peca=" composta ",
            ativo=True,
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 8
    assert _FakeRepository.updated_payload["tipo_peca"] == "COMPOSTA"
    assert _FakeRepository.updated_payload["natureza"] == "CONJUNTO"
    assert result.tipo_peca == "COMPOSTA"
    assert session.committed is True


def test_def_peca_service_guarda_classificacao_unificada(monkeypatch) -> None:
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service_module.DefPecaService(session=session).criar_peca(
        service_module.CriarDefPecaData(
            codigo="PRAT",
            nome="Prateleira",
            natureza=" material ",
            orientacao=" horizontal ",
            funcao="  Prateleira móvel  ",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["natureza"] == "MATERIAL"
    assert _FakeRepository.created_payload["orientacao"] == "HORIZONTAL"
    assert _FakeRepository.created_payload["funcao"] == "Prateleira móvel"


def test_conjunto_virtual_fica_sem_material(monkeypatch) -> None:
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service_module.DefPecaService(session=session).criar_peca(
        service_module.CriarDefPecaData(
            codigo="CJ",
            nome="Conjunto",
            natureza="CONJUNTO",
            chave_valueset_material="PLACA",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["sem_material"] is True
    assert _FakeRepository.created_payload["chave_valueset_material"] is None


def test_def_peca_service_normaliza_orlas_ao_criar(monkeypatch) -> None:
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    result = service.criar_peca(
        service_module.CriarDefPecaData(
            codigo="TAMPO",
            nome="Tampo",
            orla_c1="2",
            orla_c2=2,
            orla_l1="x",
            orla_l2="1",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["orla_c1"] == 2
    assert _FakeRepository.created_payload["orla_c2"] == 2
    assert _FakeRepository.created_payload["orla_l1"] == 0
    assert _FakeRepository.created_payload["orla_l2"] == 1
    assert result.orla_c1 == 2
    assert result.orla_l2 == 1
    assert session.committed is True


def test_def_peca_service_normaliza_valuesets_ao_criar(monkeypatch) -> None:
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    result = service.criar_peca(
        service_module.CriarDefPecaData(
            codigo="PORTA",
            nome="Porta",
            chave_valueset_material=" material_portas ",
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_FACE_SUP",
            chave_valueset_acabamento_inf="",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["chave_valueset_material"] == "MATERIAL_PORTAS"
    assert _FakeRepository.created_payload["permite_acabamento"] is True
    assert _FakeRepository.created_payload["chave_valueset_acabamento_sup"] == "ACABAMENTO_FACE_SUP"
    assert _FakeRepository.created_payload["chave_valueset_acabamento_inf"] is None
    assert result.chave_valueset_material == "MATERIAL_PORTAS"
    assert result.permite_acabamento is True
    assert session.committed is True


def test_def_peca_service_preserva_chave_valueset_personalizada_ao_criar(
    monkeypatch,
) -> None:
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    result = service.criar_peca(
        service_module.CriarDefPecaData(
            codigo="NIV",
            nome="Nivelador",
            chave_valueset_material=" niveladores/pendurais ",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert (
        _FakeRepository.created_payload["chave_valueset_material"]
        == "NIVELADORES/PENDURAIS"
    )
    assert result.chave_valueset_material == "NIVELADORES/PENDURAIS"
    assert session.committed is True


def test_def_peca_service_sem_material_limpa_chave(monkeypatch) -> None:
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    service.criar_peca(
        service_module.CriarDefPecaData(
            codigo="RASGO_EXTRA",
            nome="Rasgo extra",
            chave_valueset_material="MATERIAL_PORTAS",
            sem_material=True,
        )
    )

    # A service piece drops the material key and stores the flag.
    assert _FakeRepository.created_payload["sem_material"] is True
    assert _FakeRepository.created_payload["chave_valueset_material"] is None


def test_def_peca_service_normaliza_orlas_ao_editar(monkeypatch) -> None:
    _FakeRepository.updated_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    result = service.editar_peca(
        8,
        service_module.EditarDefPecaData(
            codigo="PORTA",
            nome="Porta",
            orla_c1="2",
            orla_c2="2",
            orla_l1="2",
            orla_l2="2",
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["orla_c1"] == 2
    assert _FakeRepository.updated_payload["orla_c2"] == 2
    assert _FakeRepository.updated_payload["orla_l1"] == 2
    assert _FakeRepository.updated_payload["orla_l2"] == 2
    assert result.orla_c1 == 2
    assert result.orla_l2 == 2
    assert session.committed is True


def test_def_peca_service_guarda_formulas_dimensionais_normalizadas(monkeypatch) -> None:
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service_module.DefPecaService(session=session).criar_peca(
        service_module.CriarDefPecaData(
            codigo="PORTA_2",
            nome="Porta dupla",
            formula_comp="hm",
            formula_larg="lm/2",
            formula_esp=None,
        )
    )

    assert _FakeRepository.created_payload["formula_comp"] == "HM"
    assert _FakeRepository.created_payload["formula_larg"] == "LM/2"
    assert _FakeRepository.created_payload["formula_esp"] is None


def test_def_peca_service_rejeita_formula_de_cabecalho_com_pai(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    try:
        service_module.DefPecaService(session=session).criar_peca(
            service_module.CriarDefPecaData(
                codigo="INVALIDA",
                nome="Inválida",
                formula_comp="PAI_COMP",
            )
        )
    except ValueError as error:
        assert "PAI_COMP" in str(error)
    else:
        raise AssertionError("Expected ValueError")
    assert session.committed is False


def test_def_peca_service_normaliza_valuesets_ao_editar(monkeypatch) -> None:
    _FakeRepository.updated_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    result = service.editar_peca(
        8,
        service_module.EditarDefPecaData(
            codigo="LAT",
            nome="Lateral",
            chave_valueset_material="MATERIAL_LATERAIS",
            permite_acabamento=False,
            chave_valueset_acabamento_sup=None,
            chave_valueset_acabamento_inf="ACABAMENTO_FACE_INF",
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["chave_valueset_material"] == "MATERIAL_LATERAIS"
    assert _FakeRepository.updated_payload["permite_acabamento"] is False
    assert _FakeRepository.updated_payload["chave_valueset_acabamento_sup"] is None
    assert _FakeRepository.updated_payload["chave_valueset_acabamento_inf"] == "ACABAMENTO_FACE_INF"
    assert result.chave_valueset_acabamento_inf == "ACABAMENTO_FACE_INF"
    assert session.committed is True


def test_def_peca_service_preserva_chave_valueset_personalizada_ao_editar(
    monkeypatch,
) -> None:
    _FakeRepository.updated_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    result = service.editar_peca(
        8,
        service_module.EditarDefPecaData(
            codigo="NIV",
            nome="Nivelador",
            chave_valueset_material=" niveladores/pendurais ",
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert (
        _FakeRepository.updated_payload["chave_valueset_material"]
        == "NIVELADORES/PENDURAIS"
    )
    assert result.chave_valueset_material == "NIVELADORES/PENDURAIS"
    assert session.committed is True


def test_duplicar_peca_copia_dados_operacoes_e_componentes(session) -> None:
    peca_service = service_module.DefPecaService(session=session)
    operacao_service = DefOperacaoService(session=session)
    peca_operacao_service = DefPecaOperacaoService(session=session)
    componente_service = DefPecaComponenteService(session=session)

    corte = operacao_service.criar_operacao(
        CriarDefOperacaoData(codigo="CORTE", nome="Corte")
    )
    cnc = operacao_service.criar_operacao(CriarDefOperacaoData(codigo="CNC", nome="CNC"))

    simples = peca_service.criar_peca(
        service_module.CriarDefPecaData(
            codigo="LAT",
            nome="Lateral",
            descricao="Lateral base",
            grupo="Roupeiros",
            tipo_peca="SIMPLES",
            orla_c1=2,
            orla_c2=1,
            orla_l1=0,
            orla_l2=2,
            chave_valueset_material="MATERIAL_LATERAIS",
            permite_acabamento=True,
            chave_valueset_acabamento_sup="ACABAMENTO_SUP",
            chave_valueset_acabamento_inf="ACABAMENTO_INF",
            sem_material=False,
            ativo=False,
        )
    )
    peca_operacao_service.adicionar_operacao_a_peca(
        CriarDefPecaOperacaoData(
            def_peca_id=simples.id,
            def_operacao_id=cnc.id,
            ordem=2,
            regra_calculo="POR_PECA",
            quantidade_base=Decimal("1"),
            tempo_setup_minutos=Decimal("2"),
            tempo_por_unidade_minutos=Decimal("0.5"),
            unidade_tempo="min",
            obrigatorio=False,
            ativo=True,
            observacoes="CNC lateral",
        )
    )
    peca_operacao_service.adicionar_operacao_a_peca(
        CriarDefPecaOperacaoData(
            def_peca_id=simples.id,
            def_operacao_id=corte.id,
            ordem=1,
            regra_calculo="POR_M2",
            quantidade_base=Decimal("2"),
            obrigatorio=True,
            ativo=False,
            observacoes="Corte lateral",
        )
    )

    copia_simples = peca_service.duplicar_peca(simples.id, "LAT_COPIA")
    operacoes_copia_simples = peca_operacao_service.listar_operacoes_da_peca(
        copia_simples.id
    )
    componentes_copia_simples = componente_service.listar_componentes(copia_simples.id)

    assert copia_simples.codigo == "LAT_COPIA"
    assert copia_simples.nome == "Lateral (cópia)"
    assert copia_simples.ativo is True
    assert copia_simples.descricao == simples.descricao
    assert copia_simples.grupo == simples.grupo
    assert copia_simples.tipo_peca == simples.tipo_peca
    assert copia_simples.orla_c1 == simples.orla_c1
    assert copia_simples.orla_c2 == simples.orla_c2
    assert copia_simples.orla_l1 == simples.orla_l1
    assert copia_simples.orla_l2 == simples.orla_l2
    assert copia_simples.chave_valueset_material == simples.chave_valueset_material
    assert copia_simples.permite_acabamento == simples.permite_acabamento
    assert (
        copia_simples.chave_valueset_acabamento_sup
        == simples.chave_valueset_acabamento_sup
    )
    assert (
        copia_simples.chave_valueset_acabamento_inf
        == simples.chave_valueset_acabamento_inf
    )
    assert copia_simples.sem_material == simples.sem_material
    assert len(operacoes_copia_simples) == 2
    assert len(componentes_copia_simples) == 0
    assert [operacao.ordem for operacao in operacoes_copia_simples] == [1, 2]
    assert [operacao.def_operacao_id for operacao in operacoes_copia_simples] == [
        corte.id,
        cnc.id,
    ]
    assert operacoes_copia_simples[0].regra_calculo == "POR_M2"
    assert operacoes_copia_simples[1].tempo_setup_minutos == Decimal("2.0000")
    assert operacoes_copia_simples[1].unidade_tempo == "MIN"

    prateleira = peca_service.criar_peca(
        service_module.CriarDefPecaData(codigo="PRAT", nome="Prateleira")
    )
    composta = peca_service.criar_peca(
        service_module.CriarDefPecaData(
            codigo="GAV",
            nome="Gaveta",
            descricao="Gaveta composta",
            grupo="Gavetas",
            tipo_peca="COMPOSTA",
            sem_material=True,
        )
    )
    peca_operacao_service.adicionar_operacao_a_peca(
        CriarDefPecaOperacaoData(
            def_peca_id=composta.id,
            def_operacao_id=corte.id,
            ordem=1,
            regra_calculo="POR_PECA",
        )
    )
    componente_service.criar_componente(
        CriarDefPecaComponenteData(
            def_peca_pai_id=composta.id,
            tipo_componente="PECA",
            def_peca_componente_id=prateleira.id,
            quantidade=Decimal("2"),
            regra_quantidade="FIXA",
            observacoes="Frente e costa",
        )
    )
    componente_service.criar_componente(
        CriarDefPecaComponenteData(
            def_peca_pai_id=composta.id,
            tipo_componente="FERRAGEM",
            referencia_componente="CORR-01",
            descricao="Corrediça",
            quantidade=Decimal("2"),
            regra_quantidade="FIXA",
            obrigatorio=False,
            ativo=False,
            observacoes="Par de corrediças",
        )
    )

    copia_composta = peca_service.duplicar_peca(
        composta.id,
        "GAV_COPIA",
        novo_nome="Gaveta variante",
    )
    operacoes_copia_composta = peca_operacao_service.listar_operacoes_da_peca(
        copia_composta.id
    )
    componentes_copia_composta = componente_service.listar_componentes(copia_composta.id)

    assert copia_composta.codigo == "GAV_COPIA"
    assert copia_composta.nome == "Gaveta variante"
    assert copia_composta.tipo_peca == "COMPOSTA"
    assert copia_composta.sem_material is True
    assert copia_composta.ativo is True
    assert len(operacoes_copia_composta) == 1
    assert len(componentes_copia_composta) == 2
    assert [componente.ordem for componente in componentes_copia_composta] == [1, 2]
    assert componentes_copia_composta[0].tipo_componente == "PECA"
    assert componentes_copia_composta[0].def_peca_componente_id == prateleira.id
    assert componentes_copia_composta[0].quantidade == Decimal("2.000")
    assert componentes_copia_composta[1].tipo_componente == "FERRAGEM"
    assert componentes_copia_composta[1].referencia_componente == "CORR-01"
    assert componentes_copia_composta[1].obrigatorio is False
    assert componentes_copia_composta[1].ativo is False


def test_gravar_peca_como_usa_dados_novos_e_copia_ligacoes(session) -> None:
    peca_service = service_module.DefPecaService(session=session)
    operacao_service = DefOperacaoService(session=session)
    peca_operacao_service = DefPecaOperacaoService(session=session)
    componente_service = DefPecaComponenteService(session=session)

    corte = operacao_service.criar_operacao(
        CriarDefOperacaoData(codigo="CORTE", nome="Corte")
    )
    filho = peca_service.criar_peca(
        service_module.CriarDefPecaData(codigo="FILHO", nome="Filho")
    )
    original = peca_service.criar_peca(
        service_module.CriarDefPecaData(
            codigo="ORIG",
            nome="Original",
            tipo_peca="COMPOSTA",
        )
    )
    peca_operacao_service.adicionar_operacao_a_peca(
        CriarDefPecaOperacaoData(
            def_peca_id=original.id,
            def_operacao_id=corte.id,
            ordem=3,
            regra_calculo="POR_PECA",
            obrigatorio=False,
        )
    )
    componente_service.criar_componente(
        CriarDefPecaComponenteData(
            def_peca_pai_id=original.id,
            tipo_componente="PECA",
            def_peca_componente_id=filho.id,
            quantidade=Decimal("2"),
            regra_quantidade="FIXA",
        )
    )

    nova = peca_service.gravar_peca_como(
        original.id,
        service_module.CriarDefPecaData(
            codigo="FORM",
            nome="Nome do formulario",
            descricao="Descricao nova",
            grupo="Grupo novo",
            tipo_peca="SIMPLES",
            orla_c1=1,
            orla_c2=2,
            sem_material=True,
            ativo=False,
        ),
    )
    operacoes = peca_operacao_service.listar_operacoes_da_peca(nova.id)
    componentes = componente_service.listar_componentes(nova.id)

    assert nova.codigo == "FORM"
    assert nova.nome == "Nome do formulario"
    assert nova.descricao == "Descricao nova"
    assert nova.grupo == "Grupo novo"
    assert nova.tipo_peca == "SIMPLES"
    assert nova.orla_c1 == 1
    assert nova.orla_c2 == 2
    assert nova.sem_material is True
    assert nova.ativo is False
    assert len(operacoes) == 1
    assert operacoes[0].def_operacao_id == corte.id
    assert operacoes[0].ordem == 3
    assert len(componentes) == 1
    assert componentes[0].def_peca_componente_id == filho.id


def test_def_peca_service_valida_codigo_obrigatorio(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()
    service = service_module.DefPecaService(session=session)

    try:
        service.criar_peca(service_module.CriarDefPecaData(codigo="", nome="Lateral"))
    except ValueError as error:
        assert "codigo" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_def_peca_service_valida_nome_obrigatorio(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()
    service = service_module.DefPecaService(session=session)

    try:
        service.criar_peca(service_module.CriarDefPecaData(codigo="LAT", nome=""))
    except ValueError as error:
        assert "nome" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_def_peca_service_valida_codigo_obrigatorio_ao_editar(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()
    service = service_module.DefPecaService(session=session)

    try:
        service.editar_peca(
            5,
            service_module.EditarDefPecaData(codigo="   ", nome="Porta"),
        )
    except ValueError as error:
        assert "codigo" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_def_peca_service_desativa_peca_existente(monkeypatch) -> None:
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)

    assert service.desativar_peca(10) is True
    assert _FakeRepository.deactivated_id == 10
    assert session.committed is True


def test_def_peca_service_desativa_peca_inexistente_sem_commit(monkeypatch) -> None:
    _FakeRepository.deactivate_result = False
    _FakeRepository.deactivated_id = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)

    assert service.desativar_peca(11) is False
    assert _FakeRepository.deactivated_id == 11
    assert session.committed is False


def test_def_peca_service_ativa_peca_existente(monkeypatch) -> None:
    _FakeRepository.activate_result = True
    _FakeRepository.activated_id = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)

    assert service.ativar_peca(10) is True
    assert _FakeRepository.activated_id == 10
    assert session.committed is True


def test_def_peca_service_ativa_peca_inexistente_sem_commit(monkeypatch) -> None:
    _FakeRepository.activate_result = False
    _FakeRepository.activated_id = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)

    assert service.ativar_peca(11) is False
    assert _FakeRepository.activated_id == 11
    assert session.committed is False
