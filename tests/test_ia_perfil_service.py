"""Tests for the per-user AI profile service."""

from __future__ import annotations

import pytest

from app.models import User
from app.services.ia_perfil_service import (
    TIPOS_ENTRADA,
    TIPOS_POR_CHAVE,
    atualizar_entrada,
    contar_por_tipo,
    criar_entrada,
    eliminar_entrada,
    listar_entradas,
)


@pytest.fixture()
def utilizadores(session):
    paulo = User(
        username="paulo",
        nome="Paulo",
        email="paulo@exemplo.pt",
        password_hash="x",
        role="user",
    )
    ana = User(
        username="ana",
        nome="Ana",
        email="ana@exemplo.pt",
        password_hash="x",
        role="user",
    )
    session.add_all([paulo, ana])
    session.commit()
    return paulo, ana


def test_os_quadros_do_questionario_estao_todos_declarados() -> None:
    chaves = {tipo.chave for tipo in TIPOS_ENTRADA}

    assert {"pergunta", "movel", "material", "estado", "pessoa"} <= chaves
    assert {"cliente", "tempo", "ambigua", "aviso", "nao_quero"} <= chaves
    assert len(TIPOS_POR_CHAVE) == len(TIPOS_ENTRADA)


def test_criar_e_listar_entradas(session, utilizadores) -> None:
    paulo, _ana = utilizadores

    criar_entrada(
        session,
        user_id=paulo.id,
        tipo="movel",
        expressao="  roupeiro  ",
        significado="guarda-fatos",
        campos="Descrição produção",
    )
    session.commit()

    entradas = listar_entradas(session, paulo.id, "movel")
    assert len(entradas) == 1
    assert entradas[0].expressao == "roupeiro"  # espaços limpos
    assert entradas[0].campos == "Descrição produção"


def test_perfil_de_um_utilizador_nao_se_mistura_com_o_do_outro(
    session, utilizadores
) -> None:
    paulo, ana = utilizadores
    criar_entrada(session, user_id=paulo.id, tipo="movel", expressao="roupeiro")
    criar_entrada(session, user_id=ana.id, tipo="movel", expressao="closet")
    session.commit()

    assert [e.expressao for e in listar_entradas(session, paulo.id)] == ["roupeiro"]
    assert [e.expressao for e in listar_entradas(session, ana.id)] == ["closet"]


def test_nao_deixa_editar_o_perfil_de_outro(session, utilizadores) -> None:
    paulo, ana = utilizadores
    entrada = criar_entrada(
        session, user_id=paulo.id, tipo="movel", expressao="roupeiro"
    )
    session.commit()

    with pytest.raises(ValueError, match="não encontrada"):
        atualizar_entrada(session, entrada.id, user_id=ana.id, expressao="outro")

    with pytest.raises(ValueError, match="não encontrada"):
        eliminar_entrada(session, entrada.id, user_id=ana.id)


def test_expressao_vazia_e_recusada(session, utilizadores) -> None:
    paulo, _ana = utilizadores

    with pytest.raises(ValueError, match="Escreva a expressão"):
        criar_entrada(session, user_id=paulo.id, tipo="movel", expressao="   ")


def test_tipo_desconhecido_e_recusado(session, utilizadores) -> None:
    paulo, _ana = utilizadores

    with pytest.raises(ValueError, match="desconhecido"):
        criar_entrada(session, user_id=paulo.id, tipo="inventado", expressao="x")


def test_atualizar_e_eliminar(session, utilizadores) -> None:
    paulo, _ana = utilizadores
    entrada = criar_entrada(
        session, user_id=paulo.id, tipo="tempo", expressao="urgente"
    )
    session.commit()

    atualizar_entrada(
        session,
        entrada.id,
        user_id=paulo.id,
        expressao="urgente",
        significado="2 dias",
        campos="Data Entrega",
    )
    session.commit()
    assert listar_entradas(session, paulo.id)[0].significado == "2 dias"

    eliminar_entrada(session, entrada.id, user_id=paulo.id)
    session.commit()
    assert listar_entradas(session, paulo.id) == []


def test_contar_por_tipo(session, utilizadores) -> None:
    paulo, _ana = utilizadores
    criar_entrada(session, user_id=paulo.id, tipo="movel", expressao="roupeiro")
    criar_entrada(session, user_id=paulo.id, tipo="movel", expressao="closet")
    criar_entrada(session, user_id=paulo.id, tipo="aviso", expressao="orçamentos parados")
    session.commit()

    assert contar_por_tipo(session, paulo.id) == {"movel": 2, "aviso": 1}
