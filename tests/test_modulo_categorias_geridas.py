"""Tests for the manageable module-library categories (phase 6)."""

from __future__ import annotations

import pytest

from sqlalchemy import select

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import DefModulo, DefModuloCategoria, User
from app.domain.modulo_categorias import (
    AMBITO_GLOBAL,
    AMBITO_UTILIZADOR,
    OUTROS,
    pode_gerir_modulo,
)
from app.services.def_modulo_categoria_service import DefModuloCategoriaService
from app.services.def_modulo_service import DefModuloService


def _criar_user(session, username: str = "paulo") -> int:
    user = User(
        username=username,
        nome=username,
        email=f"{username}@teste.local",
        password_hash="x",
        role="user",
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user.id


def _criar_modulo(
    session,
    *,
    codigo: str = "MOD_1",
    categoria: str = OUTROS,
    ambito: str = AMBITO_UTILIZADOR,
    user_id: int | None = None,
) -> DefModulo:
    modulo = DefModulo(
        codigo=codigo,
        nome=codigo,
        ambito=ambito,
        user_id=user_id,
        categoria=categoria,
        ativo=True,
    )
    session.add(modulo)
    session.flush()
    return modulo


# ---------------------------------------------------------------------------
# Seed / migração das categorias existentes


def test_seed_cria_as_quatro_categorias_iniciais(session) -> None:
    categorias = DefModuloCategoriaService(session).listar()

    codigos = {categoria.codigo for categoria in categorias}
    assert codigos == {"ROUPEIROS", "COZINHAS", "MOVEIS_WC", "OUTROS"}
    assert all(categoria.ativo for categoria in categorias)


def test_seed_importa_categoria_legada_usada_por_modulo(session) -> None:
    user_id = _criar_user(session)
    _criar_modulo(
        session, codigo="MOD_LEGADO", categoria="ANTIGA", user_id=user_id
    )

    categorias = DefModuloCategoriaService(session).listar()

    legada = next(c for c in categorias if c.codigo == "ANTIGA")
    assert legada.ativo is True
    assert legada.modulos_em_uso == 1


# ---------------------------------------------------------------------------
# Criar / renomear / arquivar / eliminar


def test_criar_categoria_com_nome_de_cliente(session) -> None:
    categoria = DefModuloCategoriaService(session).criar("Cliente Silva")

    assert categoria.codigo == "CLIENTE_SILVA"
    assert categoria.nome == "Cliente Silva"
    assert categoria.ativo is True


def test_criar_categoria_duplicada_da_erro(session) -> None:
    service = DefModuloCategoriaService(session)
    service.criar("Cliente Silva")

    with pytest.raises(ValueError, match="Já existe"):
        service.criar("  cliente   silva  ")


def test_renomear_categoria_mantem_o_codigo(session) -> None:
    service = DefModuloCategoriaService(session)
    criada = service.criar("Cliente Silva")

    renomeada = service.renomear(criada.id, "Cliente Silva & Filhos")

    assert renomeada.codigo == "CLIENTE_SILVA"
    assert renomeada.nome == "Cliente Silva & Filhos"


def test_arquivar_e_reativar_categoria(session) -> None:
    service = DefModuloCategoriaService(session)
    criada = service.criar("Sazonal")

    arquivada = service.arquivar(criada.id)
    assert arquivada.ativo is False
    # Archived categories leave the pickers but keep existing modules.
    assert "SAZONAL" not in dict(service.listar_opcoes())
    assert "SAZONAL" in service.labels()

    reativada = service.reativar(criada.id)
    assert reativada.ativo is True
    assert "SAZONAL" in dict(service.listar_opcoes())


def test_outros_nao_pode_ser_arquivada_nem_eliminada(session) -> None:
    service = DefModuloCategoriaService(session)
    outros = next(c for c in service.listar() if c.codigo == OUTROS)

    with pytest.raises(ValueError, match="recurso"):
        service.arquivar(outros.id)
    with pytest.raises(ValueError, match="recurso"):
        service.eliminar(outros.id)


def test_eliminar_categoria_em_uso_da_erro(session) -> None:
    service = DefModuloCategoriaService(session)
    criada = service.criar("Cliente Silva")
    user_id = _criar_user(session)
    _criar_modulo(
        session, codigo="MOD_SILVA", categoria="CLIENTE_SILVA", user_id=user_id
    )

    with pytest.raises(ValueError, match="em uso"):
        service.eliminar(criada.id)


def test_eliminar_categoria_sem_uso(session) -> None:
    service = DefModuloCategoriaService(session)
    criada = service.criar("Temporária")

    assert service.eliminar(criada.id) is True
    assert session.execute(
        select(DefModuloCategoria).where(
            DefModuloCategoria.codigo == "TEMPORÁRIA"
        )
    ).scalars().first() is None


# ---------------------------------------------------------------------------
# Subcategorias (um nível)


def test_criar_subcategoria_dentro_de_categoria(session) -> None:
    service = DefModuloCategoriaService(session)
    roupeiros = next(c for c in service.listar() if c.codigo == "ROUPEIROS")

    sub = service.criar("Cliente Silva", parent_id=roupeiros.id)

    assert sub.parent_id == roupeiros.id
    assert sub.parent_nome == "Roupeiros"


def test_nao_permite_subcategoria_de_subcategoria(session) -> None:
    service = DefModuloCategoriaService(session)
    roupeiros = next(c for c in service.listar() if c.codigo == "ROUPEIROS")
    sub = service.criar("Cliente Silva", parent_id=roupeiros.id)

    with pytest.raises(ValueError, match="um nível"):
        service.criar("Projeto A", parent_id=sub.id)


def test_arvore_agrupa_subcategorias(session) -> None:
    service = DefModuloCategoriaService(session)
    roupeiros = next(c for c in service.listar() if c.codigo == "ROUPEIROS")
    service.criar("Cliente Silva", parent_id=roupeiros.id)

    arvore = dict((topo.codigo, subs) for topo, subs in service.listar_arvore())

    assert [s.codigo for s in arvore["ROUPEIROS"]] == ["CLIENTE_SILVA"]
    assert arvore["OUTROS"] == []


def test_opcoes_excluem_subcategorias(session) -> None:
    service = DefModuloCategoriaService(session)
    roupeiros = next(c for c in service.listar() if c.codigo == "ROUPEIROS")
    service.criar("Cliente Silva", parent_id=roupeiros.id)

    codigos = dict(service.listar_opcoes())
    assert "ROUPEIROS" in codigos
    assert "CLIENTE_SILVA" not in codigos


def test_nao_elimina_categoria_com_subcategorias(session) -> None:
    service = DefModuloCategoriaService(session)
    roupeiros = next(c for c in service.listar() if c.codigo == "ROUPEIROS")
    service.criar("Cliente Silva", parent_id=roupeiros.id)

    with pytest.raises(ValueError, match="subcategorias"):
        service.eliminar(roupeiros.id)


def test_subcategoria_conta_modulos_pela_coluna_subcategoria(session) -> None:
    user_id = _criar_user(session)
    service = DefModuloCategoriaService(session)
    roupeiros = next(c for c in service.listar() if c.codigo == "ROUPEIROS")
    sub = service.criar("Cliente Silva", parent_id=roupeiros.id)

    modulo = _criar_modulo(
        session, codigo="MOD_SUB", categoria="ROUPEIROS", user_id=user_id
    )
    modulo.subcategoria = "CLIENTE_SILVA"
    session.flush()

    atualizada = next(c for c in service.listar() if c.id == sub.id)
    assert atualizada.modulos_em_uso == 1


# ---------------------------------------------------------------------------
# Módulos antigos preservados + filtros


def test_modulo_antigo_preservado_e_filtravel_por_categoria_nova(session) -> None:
    user_id = _criar_user(session)
    service = DefModuloCategoriaService(session)
    service.criar("Cliente Silva")
    _criar_modulo(
        session, codigo="MOD_A", categoria="CLIENTE_SILVA", user_id=user_id
    )
    _criar_modulo(session, codigo="MOD_B", categoria=OUTROS, user_id=user_id)

    modulos = DefModuloService(session)
    filtrados = modulos.listar_por_ambito_utilizador(
        user_id, categoria="CLIENTE_SILVA"
    )

    assert [modulo.codigo for modulo in filtrados] == ["MOD_A"]
    todos = modulos.listar_por_ambito_utilizador(user_id)
    assert {modulo.codigo for modulo in todos} == {"MOD_A", "MOD_B"}


# ---------------------------------------------------------------------------
# Permissões Utilizador/Global


def test_pode_gerir_modulo_matriz_de_permissoes() -> None:
    # Owner manages their own UTILIZADOR module.
    assert pode_gerir_modulo(AMBITO_UTILIZADOR, 7, user_id=7, is_admin=False)
    # Another user cannot.
    assert not pode_gerir_modulo(AMBITO_UTILIZADOR, 7, user_id=8, is_admin=False)
    # GLOBAL modules only by admins.
    assert not pode_gerir_modulo(AMBITO_GLOBAL, None, user_id=7, is_admin=False)
    assert pode_gerir_modulo(AMBITO_GLOBAL, None, user_id=7, is_admin=True)
    # Admin manages everything.
    assert pode_gerir_modulo(AMBITO_UTILIZADOR, 7, user_id=9, is_admin=True)
    # Anonymous session manages nothing.
    assert not pode_gerir_modulo(
        AMBITO_UTILIZADOR, 7, user_id=None, is_admin=False
    )


# ---------------------------------------------------------------------------
# Conversões reversíveis


def test_converter_utilizador_para_global_e_de_volta(session) -> None:
    user_id = _criar_user(session)
    modulo = _criar_modulo(
        session, codigo="MOD_CONV", user_id=user_id, ambito=AMBITO_UTILIZADOR
    )
    service = DefModuloService(session)

    convertido = service.converter_ambito(
        modulo.id, AMBITO_GLOBAL, acting_user_id=user_id, is_admin=True
    )
    assert convertido.ambito == AMBITO_GLOBAL
    assert convertido.user_id is None

    de_volta = service.converter_ambito(
        modulo.id, AMBITO_UTILIZADOR, acting_user_id=user_id, is_admin=True
    )
    assert de_volta.ambito == AMBITO_UTILIZADOR
    assert de_volta.user_id == user_id


def test_converter_global_sem_admin_da_erro(session) -> None:
    user_id = _criar_user(session)
    modulo = _criar_modulo(
        session, codigo="MOD_GLOBAL", ambito=AMBITO_GLOBAL, user_id=None
    )

    with pytest.raises(ValueError, match="permissão"):
        DefModuloService(session).converter_ambito(
            modulo.id,
            AMBITO_UTILIZADOR,
            acting_user_id=user_id,
            is_admin=False,
        )


def test_dono_converte_o_seu_modulo_para_global(session) -> None:
    user_id = _criar_user(session)
    modulo = _criar_modulo(
        session, codigo="MOD_MEU", user_id=user_id, ambito=AMBITO_UTILIZADOR
    )

    convertido = DefModuloService(session).converter_ambito(
        modulo.id, AMBITO_GLOBAL, acting_user_id=user_id, is_admin=False
    )

    assert convertido.ambito == AMBITO_GLOBAL


def test_outro_utilizador_nao_converte_modulo_alheio(session) -> None:
    dono_id = _criar_user(session, "dono")
    outro_id = _criar_user(session, "outro")
    modulo = _criar_modulo(
        session, codigo="MOD_ALHEIO", user_id=dono_id, ambito=AMBITO_UTILIZADOR
    )

    with pytest.raises(ValueError, match="permissão"):
        DefModuloService(session).converter_ambito(
            modulo.id, AMBITO_GLOBAL, acting_user_id=outro_id, is_admin=False
        )
