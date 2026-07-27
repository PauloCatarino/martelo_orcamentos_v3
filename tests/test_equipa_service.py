"""Tests for the team a ticket can be handed to."""

from __future__ import annotations

import pytest

from app.models import Producao
from app.services.equipa_service import (
    atualizar_membro,
    criar_membro,
    eliminar_membro,
    listar_membros,
    obter_por_nome,
    semear_de_producao,
)


def test_criar_e_listar_por_ordem(session) -> None:
    criar_membro(session, nome="Elsa Belo", email="elsa@lancaencanto.pt", ordem=2)
    criar_membro(session, nome="Adriano Silva", ordem=1)

    nomes = [membro.nome for membro in listar_membros(session)]

    assert nomes == ["Adriano Silva", "Elsa Belo"]


def test_nome_repetido_e_recusado(session) -> None:
    criar_membro(session, nome="Elsa Belo")

    with pytest.raises(ValueError, match="já está na equipa"):
        criar_membro(session, nome="elsa belo")


def test_nome_vazio_e_recusado(session) -> None:
    with pytest.raises(ValueError):
        criar_membro(session, nome="   ")


def test_desligar_alguem_tira_o_da_lista_sem_apagar(session) -> None:
    membro = criar_membro(session, nome="Dulce Faria")

    atualizar_membro(session, membro.id, ativo=False)

    assert listar_membros(session) == []
    assert len(listar_membros(session, incluir_inativos=True)) == 1


def test_atualizar_guarda_o_endereco_de_teams(session) -> None:
    membro = criar_membro(session, nome="Adriano Silva")

    atualizar_membro(session, membro.id, email="adriano@lancaencanto.pt")

    assert obter_por_nome(session, "ADRIANO SILVA").email == "adriano@lancaencanto.pt"


def test_nao_deixa_dois_com_o_mesmo_nome_ao_renomear(session) -> None:
    criar_membro(session, nome="Elsa Belo")
    outro = criar_membro(session, nome="Dulce Faria")

    with pytest.raises(ValueError, match="já está na equipa"):
        atualizar_membro(session, outro.id, nome="Elsa Belo")


def test_eliminar_pessoa_inexistente_avisa(session) -> None:
    with pytest.raises(ValueError, match="não encontrada"):
        eliminar_membro(session, 12345)


def test_importar_os_nomes_que_ja_sao_responsaveis_de_obras(session) -> None:
    session.add_all(
        [
            Producao(
                codigo_processo="26.1134_01_01_A",
                ano="2026",
                num_enc_phc="1134",
                versao_obra="01",
                versao_plano="01",
                estado="Desenho",
                responsavel="Elsa Belo",
            ),
            Producao(
                codigo_processo="26.1135_01_01_B",
                ano="2026",
                num_enc_phc="1135",
                versao_obra="01",
                versao_plano="01",
                estado="Desenho",
                responsavel="Elsa Belo",
            ),
            Producao(
                codigo_processo="26.1136_01_01_C",
                ano="2026",
                num_enc_phc="1136",
                versao_obra="01",
                versao_plano="01",
                estado="Desenho",
                responsavel="Dulce Faria",
            ),
        ]
    )
    session.commit()

    criados = semear_de_producao(session)

    assert criados == 2
    assert [m.nome for m in listar_membros(session)] == ["Dulce Faria", "Elsa Belo"]


def test_importar_duas_vezes_nao_duplica(session) -> None:
    session.add(
        Producao(
            codigo_processo="26.1134_01_01_A",
            ano="2026",
            num_enc_phc="1134",
            versao_obra="01",
            versao_plano="01",
            estado="Desenho",
            responsavel="Elsa Belo",
        )
    )
    session.commit()

    assert semear_de_producao(session) == 1
    assert semear_de_producao(session) == 0
