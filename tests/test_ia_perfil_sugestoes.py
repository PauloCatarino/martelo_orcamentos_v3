"""Tests for the ready-made lines that get people started on the AI profile."""

from __future__ import annotations

import pytest

from app.domain.assistente_intencao import (
    Intencao,
    palavra_a_ensinar,
    sugestao_recrutamento,
)
from app.domain.pesquisa_texto import raiz
from app.models import User
from app.services.ia_perfil_service import (
    TIPOS_ENTRADA,
    acrescentar_sugestoes,
    criar_entrada,
    listar_entradas,
    sugestoes_do_tipo,
    sugestoes_em_falta,
)


@pytest.fixture()
def paulo(session):
    utilizador = User(
        username="paulo",
        nome="Paulo Catarino",
        email="paulo@exemplo.pt",
        password_hash="x",
        role="user",
    )
    session.add(utilizador)
    session.commit()
    return utilizador


def test_todos_os_quadros_chegam_com_sugestoes() -> None:
    """Uma folha em branco é o que trava quem nunca ensinou o assistente."""
    sem_sugestoes = [tipo.chave for tipo in TIPOS_ENTRADA if not tipo.sugestoes]

    assert sem_sugestoes == []


def test_as_sugestoes_sao_pares_de_texto() -> None:
    for tipo in TIPOS_ENTRADA:
        for sugestao in tipo.sugestoes:
            assert len(sugestao) == 2
            expressao, significado = sugestao
            assert expressao.strip()
            assert isinstance(significado, str)


def test_quadro_desconhecido_nao_tem_sugestoes() -> None:
    assert sugestoes_do_tipo("nao_existe") == ()
    assert sugestoes_do_tipo("") == ()


def test_perfil_vazio_ve_todas_as_sugestoes(session, paulo) -> None:
    pendentes = sugestoes_em_falta(session, paulo.id, "instrucao_ocorrencias")

    assert pendentes == list(sugestoes_do_tipo("instrucao_ocorrencias"))


def test_uma_sugestao_ja_escrita_desaparece_da_lista(session, paulo) -> None:
    primeira = sugestoes_do_tipo("instrucao_ocorrencias")[0]
    criar_entrada(
        session,
        user_id=paulo.id,
        tipo="instrucao_ocorrencias",
        expressao=primeira[0],
        significado="",
    )
    session.commit()

    pendentes = sugestoes_em_falta(session, paulo.id, "instrucao_ocorrencias")

    assert primeira not in pendentes
    assert len(pendentes) == len(sugestoes_do_tipo("instrucao_ocorrencias")) - 1


def test_a_comparacao_ignora_acentos_e_maiusculas(session, paulo) -> None:
    criar_entrada(
        session,
        user_id=paulo.id,
        tipo="instrucao_ocorrencias",
        expressao="INCLUIR SEMPRE AS FOTOS",
        significado="",
    )
    session.commit()

    pendentes = sugestoes_em_falta(session, paulo.id, "instrucao_ocorrencias")

    assert all(e != "Incluir sempre as fotos" for e, _s in pendentes)


def test_acrescentar_todas_escreve_o_quadro_de_uma_vez(session, paulo) -> None:
    criadas = acrescentar_sugestoes(session, paulo.id, "instrucao_ocorrencias")
    session.commit()

    entradas = listar_entradas(session, paulo.id, "instrucao_ocorrencias")

    assert criadas == len(sugestoes_do_tipo("instrucao_ocorrencias"))
    assert len(entradas) == criadas
    assert sugestoes_em_falta(session, paulo.id, "instrucao_ocorrencias") == []


def test_acrescentar_duas_vezes_nao_duplica(session, paulo) -> None:
    acrescentar_sugestoes(session, paulo.id, "instrucao_ocorrencias")
    session.commit()

    assert acrescentar_sugestoes(session, paulo.id, "instrucao_ocorrencias") == 0


def test_o_perfil_de_uma_pessoa_nao_conta_para_a_outra(session, paulo) -> None:
    ana = User(
        username="ana", nome="Ana", email="ana@exemplo.pt", password_hash="x", role="user"
    )
    session.add(ana)
    session.commit()
    acrescentar_sugestoes(session, paulo.id, "instrucao_ocorrencias")
    session.commit()

    assert sugestoes_em_falta(session, ana.id, "instrucao_ocorrencias") == list(
        sugestoes_do_tipo("instrucao_ocorrencias")
    )


# ---- palavra que a pesquisa não conheceu ---------------------------------
def test_a_palavra_desconhecida_e_devolvida_a_parte() -> None:
    """Para o perfil a levar já escrita, em vez de a pessoa a repetir à mão."""
    intencao = Intencao(desconhecidas=("gavetao",))

    assert palavra_a_ensinar(intencao, 0) == "gavetao"
    assert "gavetao" in sugestao_recrutamento(intencao, 0)


def test_nao_ha_palavra_a_ensinar_quando_a_pesquisa_encontrou_obras() -> None:
    intencao = Intencao(desconhecidas=("gavetao",))

    assert palavra_a_ensinar(intencao, 3) == ""
    assert sugestao_recrutamento(intencao, 3) == ""


def test_palavra_que_existe_nas_obras_nao_e_para_ensinar() -> None:
    """Se a palavra existe mesmo, só não teve resultados — não falta ensiná-la."""
    intencao = Intencao(desconhecidas=("roupeiros",))

    assert palavra_a_ensinar(intencao, 0, vocabulario=[raiz("roupeiro")]) == ""


def test_sem_palavras_desconhecidas_nao_ha_nada_a_ensinar() -> None:
    assert palavra_a_ensinar(Intencao(), 0) == ""
