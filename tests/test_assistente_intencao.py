"""Testes do cérebro do IA Martelo (Fase 1): pergunta -> filtros."""

from __future__ import annotations

from app.domain.assistente_intencao import (
    Intencao,
    PerfilVocabulario,
    interpretar,
)


def test_pergunta_vazia_devolve_intencao_vazia() -> None:
    assert interpretar("   ") == Intencao()


def test_estado_por_expressao_padrao() -> None:
    assert interpretar("obras na máquina").estado == "Producao"
    # «obra fechada» = Arquivado; «finalizada» = Finalizado (distintos).
    assert interpretar("obras fechadas").estado == "Arquivado"
    assert interpretar("obras finalizadas").estado == "Finalizado"


def test_estado_do_perfil_tem_prioridade() -> None:
    perfil = PerfilVocabulario(estados={"a pintar": "Producao"})

    assert interpretar("o que está a pintar", perfil=perfil).estado == "Producao"


def test_atrasadas_liga_so_atrasadas() -> None:
    intencao = interpretar("mostra as obras atrasadas")

    assert intencao.so_atrasadas is True
    assert intencao.termos == ""


def test_cliente_por_nome_completo() -> None:
    intencao = interpretar(
        "obras do cliente Moviflor",
        clientes=["Moviflor", "Sonae"],
    )

    assert intencao.cliente == "Moviflor"
    assert intencao.responsavel is None


def test_cliente_por_alcunha_do_perfil() -> None:
    perfil = PerfilVocabulario(clientes={"a viva": "Vivadecor Lda"})

    intencao = interpretar(
        "o que temos da Viva", clientes=["Vivadecor Lda"], perfil=perfil
    )

    assert intencao.cliente == "Vivadecor Lda"


def test_responsavel_por_nome_e_alcunha() -> None:
    perfil = PerfilVocabulario(pessoas={"ze": "José Martins"})

    intencao = interpretar(
        "obras do Zé", responsaveis=["José Martins"], perfil=perfil
    )

    assert intencao.responsavel == "José Martins"
    assert intencao.cliente is None


def test_nome_que_serve_cliente_e_pessoa_gera_pergunta() -> None:
    intencao = interpretar(
        "obras da Silva",
        clientes=["Silva"],
        responsaveis=["Silva"],
    )

    assert intencao.cliente is None
    assert intencao.responsavel is None
    assert intencao.precisa_perguntar
    assert any("cliente ou a pessoa" in p for p in intencao.perguntas)


def test_pista_de_papel_resolve_ambiguidade() -> None:
    intencao = interpretar(
        "obras do cliente Silva",
        clientes=["Silva"],
        responsaveis=["Silva"],
    )

    assert intencao.cliente == "Silva"
    assert not intencao.precisa_perguntar


def test_palavra_ambigua_do_perfil_faz_perguntar() -> None:
    perfil = PerfilVocabulario(
        ambiguas={"central": "«central» é o cliente Central ou a zona central?"}
    )

    intencao = interpretar("obras da central", perfil=perfil)

    assert intencao.perguntas == (
        "«central» é o cliente Central ou a zona central?",
    )


def test_texto_livre_e_combinacao_de_filtros() -> None:
    perfil = PerfilVocabulario(pessoas={"ze": "José Martins"})

    intencao = interpretar(
        "roupeiros atrasados do Zé na máquina",
        responsaveis=["José Martins"],
        perfil=perfil,
    )

    assert intencao.estado == "Producao"
    assert intencao.responsavel == "José Martins"
    assert intencao.so_atrasadas is True
    assert intencao.termos == "roupeiros"


def test_desconhecidas_reune_o_texto_livre() -> None:
    intencao = interpretar("obras do palavrainventada")

    assert intencao.desconhecidas == ("palavrainventada",)


def test_minhas_obras_usa_o_utilizador_da_sessao() -> None:
    intencao = interpretar(
        "as minhas obras atrasadas", utilizador_sessao="Paulo"
    )

    assert intencao.responsavel == "Paulo"
    assert intencao.so_atrasadas is True
    assert intencao.termos == ""


def test_minhas_obras_sem_sessao_nao_inventa_responsavel() -> None:
    intencao = interpretar("as minhas obras")

    assert intencao.responsavel is None
    assert intencao.termos == ""


def test_nome_explicito_ganha_ao_possessivo() -> None:
    intencao = interpretar(
        "as minhas obras do Zé",
        responsaveis=["Zé"],
        utilizador_sessao="Paulo",
    )

    assert intencao.responsavel == "Zé"
