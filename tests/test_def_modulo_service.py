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
from app.models import DefModuloLinha
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
