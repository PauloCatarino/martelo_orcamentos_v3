"""Tests for the reusable module/article library service (phase 8U.0)."""

from __future__ import annotations

import pytest
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.domain.modulo_categorias import (
    AMBITO_GLOBAL,
    AMBITO_UTILIZADOR,
    COZINHAS,
    OUTROS,
    ROUPEIROS,
)
from decimal import Decimal

from app.models import DefModulo, DefModuloLinha
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.def_modulo_service import (
    CriarDefModuloData,
    CriarDefModuloLinhaData,
    DefModuloService,
    EditarDefModuloCabecalhoData,
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


def _linhas_roupeiro() -> list[CriarDefModuloLinhaData]:
    return [
        CriarDefModuloLinhaData(
            ordem=1, tipo_linha="DIVISAO_INDEPENDENTE", qt_mod="1", descricao_livre="Corpo"
        ),
        CriarDefModuloLinhaData(
            ordem=2,
            tipo_linha="PECA",
            def_peca_codigo="LATERAL",
            comp="H",
            larg="P",
            esp="19",
            chave_valueset="MATERIAL_LATERAIS",
            codigo_orlas="2200",
            qt_und="2",
        ),
        CriarDefModuloLinhaData(
            ordem=3,
            tipo_linha="FERRAGEM",
            def_peca_codigo="PE_NIVELADOR",
            chave_valueset="FERRAGEM_PE_NIVELADOR",
            def_regra_quantidade_id=None,
            linha_pai_ordem=2,
            nivel=1,
        ),
    ]


def _criar_roupeiro(service, *, codigo="ROUP_2P", user_id=7) -> int:
    com_linhas = service.criar(
        CriarDefModuloData(
            codigo=codigo,
            nome="Roupeiro 2 portas",
            descricao="Roupeiro base com pés",
            ambito=AMBITO_UTILIZADOR,
            user_id=user_id,
            categoria=ROUPEIROS,
            linhas=_linhas_roupeiro(),
        )
    )
    return com_linhas.modulo.id


def test_criar_modulo_com_linhas(session) -> None:
    service = DefModuloService(session)

    com_linhas = service.criar(
        CriarDefModuloData(
            codigo=" roup 2p ",
            nome="Roupeiro 2 portas",
            ambito=AMBITO_UTILIZADOR,
            user_id=7,
            categoria="roupeiros",
            linhas=_linhas_roupeiro(),
        )
    )

    assert com_linhas.modulo.codigo == "ROUP_2P"  # trimmed/upper/underscored
    assert com_linhas.modulo.categoria == ROUPEIROS
    assert com_linhas.modulo.user_id == 7
    assert len(com_linhas.linhas) == 3
    assert [linha.ordem for linha in com_linhas.linhas] == [1, 2, 3]
    # Structure-only fields are stored as text/formulas.
    lateral = com_linhas.linhas[1]
    assert lateral.comp == "H"
    assert lateral.chave_valueset == "MATERIAL_LATERAIS"
    assert lateral.codigo_orlas == "2200"
    # Composite parent-by-order is kept for resolution on import.
    assert com_linhas.linhas[2].linha_pai_ordem == 2


def test_criar_recusa_codigo_duplicado(session) -> None:
    service = DefModuloService(session)
    _criar_roupeiro(service, codigo="DUP")

    with pytest.raises(ValueError):
        _criar_roupeiro(service, codigo="DUP")


def test_criar_utilizador_exige_user_id(session) -> None:
    service = DefModuloService(session)

    with pytest.raises(ValueError):
        service.criar(
            CriarDefModuloData(
                codigo="X", nome="X", ambito=AMBITO_UTILIZADOR, user_id=None
            )
        )


def test_obter_com_linhas(session) -> None:
    service = DefModuloService(session)
    modulo_id = _criar_roupeiro(service)

    com_linhas = service.obter_com_linhas(modulo_id)

    assert com_linhas is not None
    assert com_linhas.modulo.id == modulo_id
    assert len(com_linhas.linhas) == 3
    assert service.obter_com_linhas(9999) is None


def test_listar_por_ambito_e_categoria(session) -> None:
    service = DefModuloService(session)
    # User 7: a roupeiro and a cozinha; user 9: another roupeiro; one GLOBAL.
    _criar_roupeiro(service, codigo="ROUP_7", user_id=7)
    service.criar(
        CriarDefModuloData(
            codigo="COZ_7", nome="Cozinha base", ambito=AMBITO_UTILIZADOR,
            user_id=7, categoria=COZINHAS,
        )
    )
    _criar_roupeiro(service, codigo="ROUP_9", user_id=9)
    service.criar(
        CriarDefModuloData(
            codigo="GLB_1", nome="Módulo global", ambito=AMBITO_GLOBAL,
            categoria=ROUPEIROS,
        )
    )

    do_user_7 = service.listar_por_ambito_utilizador(7)
    assert {m.codigo for m in do_user_7} == {"ROUP_7", "COZ_7"}

    roupeiros_7 = service.listar_por_ambito_utilizador(7, categoria=ROUPEIROS)
    assert {m.codigo for m in roupeiros_7} == {"ROUP_7"}

    globais = service.listar_globais()
    assert {m.codigo for m in globais} == {"GLB_1"}
    # A GLOBAL module is not listed under a user scope.
    assert "GLB_1" not in {m.codigo for m in do_user_7}


def test_pesquisa_por_termo_com_percent(session) -> None:
    service = DefModuloService(session)
    service.criar(
        CriarDefModuloData(
            codigo="ROUP_CANTO", nome="Roupeiro de canto 2 portas",
            ambito=AMBITO_UTILIZADOR, user_id=7, categoria=ROUPEIROS,
        )
    )
    service.criar(
        CriarDefModuloData(
            codigo="ROUP_RETO", nome="Roupeiro reto 3 portas",
            ambito=AMBITO_UTILIZADOR, user_id=7, categoria=ROUPEIROS,
        )
    )

    # '%'-separated tokens: ALL must match (canto AND 2 portas).
    encontrados = service.listar_por_ambito_utilizador(7, termo="canto%2 portas")
    assert {m.codigo for m in encontrados} == {"ROUP_CANTO"}

    # Single token matches both.
    assert len(service.listar_por_ambito_utilizador(7, termo="roupeiro")) == 2

    # Non-matching token -> none.
    assert service.listar_por_ambito_utilizador(7, termo="canto%reto") == []


def test_editar_cabecalho(session) -> None:
    service = DefModuloService(session)
    modulo_id = _criar_roupeiro(service)

    resultado = service.editar_cabecalho(
        modulo_id,
        EditarDefModuloCabecalhoData(
            nome="Roupeiro renomeado",
            categoria=COZINHAS,
            ambito=AMBITO_UTILIZADOR,
            user_id=7,
        ),
    )

    assert resultado.nome == "Roupeiro renomeado"
    assert resultado.categoria == COZINHAS


def test_eliminar_apaga_modulo_e_linhas(session) -> None:
    service = DefModuloService(session)
    modulo_id = _criar_roupeiro(service)
    assert (
        session.execute(
            select(DefModuloLinha).where(DefModuloLinha.def_modulo_id == modulo_id)
        ).scalars().all()
    )

    assert service.eliminar(modulo_id) is True

    assert service.obter_com_linhas(modulo_id) is None
    # The lines were cascade-deleted.
    restantes = session.execute(
        select(DefModuloLinha).where(DefModuloLinha.def_modulo_id == modulo_id)
    ).scalars().all()
    assert restantes == []
    # Deleting a missing module is a no-op.
    assert service.eliminar(9999) is False


# --- Save selected costing lines as a module (phase 8U.1) --------------------


def _inserir_custeio(session, **fields):
    base = dict(
        orcamento_item_id=10,
        tipo_linha="PECA",
        descricao="Linha",
        quantidade=Decimal("1"),
        nivel=0,
        ativo=True,
    )
    base.update(fields)
    return OrcamentoItemCusteioLinhaRepository(session).create_linha(**base)


def _cenario_roupeiro(session):
    """Division + simple piece + composite header + child + standalone hardware."""
    div = _inserir_custeio(
        session, tipo_linha="DIVISAO_INDEPENDENTE", ordem=1, descricao="Corpo",
        comp="HM", larg="LM",
    )
    simples = _inserir_custeio(
        session, tipo_linha="PECA", ordem=2, def_peca_codigo="LATERAL",
        descricao="Lateral", comp="H", larg="P", esp="19",
        chave_valueset="MATERIAL_LATERAIS", codigo_orlas="2200",
        qt_mod=Decimal("1"), qt_und=Decimal("2"),
    )
    composta = _inserir_custeio(
        session, tipo_linha="PECA_COMPOSTA", ordem=3, def_peca_id=5,
        def_peca_codigo="GAVETA", descricao="Gaveta",
    )
    filho = _inserir_custeio(
        session, tipo_linha="FERRAGEM", ordem=4, nivel=1, linha_pai_id=composta.id,
        def_peca_codigo="CORREDICA", descricao="Corrediça",
        comp="LM", larg="PM", qt_und=Decimal("4"),
    )
    pe = _inserir_custeio(
        session, tipo_linha="FERRAGEM", ordem=5, def_peca_codigo="PE", descricao="Pé",
    )
    session.commit()
    return div, simples, composta, filho, pe


def test_guardar_de_linhas_custeio_topo_e_estrutura(session) -> None:
    div, simples, composta, filho, pe = _cenario_roupeiro(session)
    service = DefModuloService(session)

    com_linhas = service.guardar_de_linhas_custeio(
        orcamento_item_id=10,
        linha_ids=[div.id, simples.id, composta.id, filho.id, pe.id],
        codigo="ROUP_2P",
        nome="Roupeiro 2 portas",
        ambito=AMBITO_UTILIZADOR,
        user_id=7,
        categoria=ROUPEIROS,
    )

    linhas = com_linhas.linhas
    # Top-level lines PLUS the composite's child (phase 8U.2): division, simple
    # piece, composite header, composite child (CORREDICA), standalone hardware.
    assert [linha.tipo_linha for linha in linhas] == [
        "DIVISAO_INDEPENDENTE",
        "PECA",
        "PECA_COMPOSTA",
        "FERRAGEM",
        "FERRAGEM",
    ]
    assert [linha.ordem for linha in linhas] == [1, 2, 3, 4, 5]

    # Composite header saved by def_peca_id, as an aggregator (no comp/larg).
    composta_linha = next(l for l in linhas if l.tipo_linha == "PECA_COMPOSTA")
    assert composta_linha.def_peca_id == 5
    assert composta_linha.linha_pai_ordem is None
    assert composta_linha.comp is None
    assert composta_linha.larg is None

    # The composite CHILD is saved with its measure formulas + parent ordem.
    corredica = next(l for l in linhas if l.def_peca_codigo == "CORREDICA")
    assert corredica.nivel == 1
    assert corredica.linha_pai_ordem == 3  # points to the header's ordem
    assert corredica.comp == "LM"
    assert corredica.larg == "PM"
    assert corredica.qt_und == "4"

    # The standalone hardware stays top-level (no parent).
    pe_linha = next(l for l in linhas if l.def_peca_codigo == "PE")
    assert pe_linha.linha_pai_ordem is None

    # Division free text in descricao_livre; measure formulas kept as TEXT.
    divisao_linha = linhas[0]
    assert divisao_linha.descricao_livre == "Corpo"
    assert divisao_linha.comp == "HM"
    simples_linha = linhas[1]
    assert simples_linha.comp == "H"
    assert simples_linha.larg == "P"
    assert simples_linha.chave_valueset == "MATERIAL_LATERAIS"
    assert simples_linha.codigo_orlas == "2200"
    assert simples_linha.qt_und == "2"  # stored as text
    assert simples_linha.descricao == "Lateral"

    # Header scoped to the user.
    assert com_linhas.modulo.user_id == 7
    assert com_linhas.modulo.ambito == AMBITO_UTILIZADOR


def test_guardar_so_o_filho_inclui_o_cabecalho(session) -> None:
    composta = _inserir_custeio(
        session, tipo_linha="PECA_COMPOSTA", ordem=1, def_peca_id=5,
        def_peca_codigo="GAVETA", descricao="Gaveta",
    )
    filho = _inserir_custeio(
        session, tipo_linha="FERRAGEM", ordem=2, nivel=1, linha_pai_id=composta.id,
        descricao="Corrediça",
    )
    session.commit()
    service = DefModuloService(session)

    com_linhas = service.guardar_de_linhas_custeio(
        orcamento_item_id=10, linha_ids=[filho.id], codigo="GAV", nome="Gaveta",
        user_id=7,
    )

    # Selecting only the child saves its composite header AND the child itself.
    assert [linha.tipo_linha for linha in com_linhas.linhas] == [
        "PECA_COMPOSTA",
        "FERRAGEM",
    ]
    assert com_linhas.linhas[0].def_peca_id == 5
    assert com_linhas.linhas[0].linha_pai_ordem is None
    assert com_linhas.linhas[1].linha_pai_ordem == 1  # child -> header ordem


def test_guardar_codigo_duplicado_nao_cria(session) -> None:
    linha = _inserir_custeio(session, ordem=1)
    session.commit()
    service = DefModuloService(session)
    service.guardar_de_linhas_custeio(
        orcamento_item_id=10, linha_ids=[linha.id], codigo="DUP", nome="X", user_id=7
    )

    with pytest.raises(ValueError):
        service.guardar_de_linhas_custeio(
            orcamento_item_id=10, linha_ids=[linha.id], codigo="DUP", nome="Y",
            user_id=7,
        )

    # Only the first module was created.
    modulos = session.execute(select(DefModulo)).scalars().all()
    assert [m.codigo for m in modulos] == ["DUP"]


def test_guardar_ambito_global_nao_grava_user(session) -> None:
    linha = _inserir_custeio(session, ordem=1)
    session.commit()
    service = DefModuloService(session)

    com_linhas = service.guardar_de_linhas_custeio(
        orcamento_item_id=10, linha_ids=[linha.id], codigo="GLB", nome="Global",
        ambito=AMBITO_GLOBAL, user_id=99, categoria=OUTROS,
    )

    assert com_linhas.modulo.ambito == AMBITO_GLOBAL
    assert com_linhas.modulo.user_id is None  # global -> no owner


def test_guardar_sem_linhas_selecionadas_erro(session) -> None:
    service = DefModuloService(session)
    with pytest.raises(ValueError):
        service.guardar_de_linhas_custeio(
            orcamento_item_id=10, linha_ids=[], codigo="X", nome="X", user_id=7
        )


# --- Listing for the save dialog + overwrite (phase 8U.1.1) ------------------


def test_listar_modulos_para_dialogo_com_contagem(session) -> None:
    service = DefModuloService(session)
    _criar_roupeiro(service, codigo="ROUP_7", user_id=7)  # 3 lines
    service.criar(
        CriarDefModuloData(
            codigo="COZ_7", nome="Cozinha base", ambito=AMBITO_UTILIZADOR,
            user_id=7, categoria=COZINHAS,
        )
    )  # 0 lines
    _criar_roupeiro(service, codigo="ROUP_9", user_id=9)  # other user
    service.criar(
        CriarDefModuloData(
            codigo="GLB_1", nome="Módulo global", ambito=AMBITO_GLOBAL,
            categoria=ROUPEIROS, linhas=_linhas_roupeiro(),
        )
    )  # 3 lines, global

    utilizador, globais = service.listar_modulos_para_dialogo(7)

    contagem_user = {item.modulo.codigo: item.num_linhas for item in utilizador}
    assert contagem_user == {"ROUP_7": 3, "COZ_7": 0}  # not user 9, not global
    contagem_global = {item.modulo.codigo: item.num_linhas for item in globais}
    assert contagem_global == {"GLB_1": 3}


def test_substituir_modulo_recria_linhas_mantem_codigo(session) -> None:
    service = DefModuloService(session)
    modulo_id = _criar_roupeiro(service, codigo="ROUP_2P", user_id=7)
    antes = service.obter_com_linhas(modulo_id)
    assert len(antes.linhas) == 3
    assert "LATERAL" in {linha.def_peca_codigo for linha in antes.linhas}

    resultado = service.substituir_modulo(
        modulo_id,
        CriarDefModuloData(
            codigo="IGNORADO",  # the code is fixed on replace
            nome="Roupeiro renovado",
            descricao="Nova descrição",
            ambito=AMBITO_UTILIZADOR,
            user_id=7,
            categoria=COZINHAS,
            linhas=[
                CriarDefModuloLinhaData(
                    ordem=1, tipo_linha="PECA", def_peca_codigo="TOPO", comp="L"
                ),
            ],
        ),
    )

    # Same id/code; header updated.
    assert resultado.modulo.id == modulo_id
    assert resultado.modulo.codigo == "ROUP_2P"
    assert resultado.modulo.nome == "Roupeiro renovado"
    assert resultado.modulo.categoria == COZINHAS
    # Old lines replaced by the new selection (the old LATERAL is gone).
    assert len(resultado.linhas) == 1
    assert resultado.linhas[0].def_peca_codigo == "TOPO"
    assert "LATERAL" not in {linha.def_peca_codigo for linha in resultado.linhas}
    # Persisted: exactly the new line remains in the DB.
    restantes = session.execute(
        select(DefModuloLinha).where(DefModuloLinha.def_modulo_id == modulo_id)
    ).scalars().all()
    assert len(restantes) == 1
    assert restantes[0].def_peca_codigo == "TOPO"


def test_substituir_modulo_inexistente_erro(session) -> None:
    service = DefModuloService(session)
    with pytest.raises(ValueError):
        service.substituir_modulo(
            9999,
            CriarDefModuloData(codigo="X", nome="X", user_id=7),
        )


def test_substituir_de_linhas_custeio_mantem_codigo(session) -> None:
    div, simples, composta, filho, pe = _cenario_roupeiro(session)
    service = DefModuloService(session)
    original = service.guardar_de_linhas_custeio(
        orcamento_item_id=10,
        linha_ids=[div.id, simples.id],
        codigo="ROUP_2P",
        nome="Roupeiro 2 portas",
        user_id=7,
        categoria=ROUPEIROS,
    )
    modulo_id = original.modulo.id
    assert len(original.linhas) == 2

    resultado = service.substituir_de_linhas_custeio(
        modulo_id=modulo_id,
        orcamento_item_id=10,
        linha_ids=[composta.id, filho.id, pe.id],
        nome="Roupeiro substituído",
        ambito=AMBITO_UTILIZADOR,
        user_id=7,
        categoria=COZINHAS,
    )

    assert resultado.modulo.id == modulo_id
    assert resultado.modulo.codigo == "ROUP_2P"  # unchanged
    assert resultado.modulo.nome == "Roupeiro substituído"
    assert resultado.modulo.categoria == COZINHAS
    # Composite header + its child (CORREDICA) + the standalone hardware (PE).
    assert [linha.tipo_linha for linha in resultado.linhas] == [
        "PECA_COMPOSTA",
        "FERRAGEM",
        "FERRAGEM",
    ]
    assert {l.def_peca_codigo for l in resultado.linhas} == {
        "GAVETA",
        "CORREDICA",
        "PE",
    }
