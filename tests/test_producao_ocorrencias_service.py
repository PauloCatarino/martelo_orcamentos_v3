"""Tests for the per-obra occurrence log (diary)."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.models import Producao, ProducaoOcorrencia, User
from app.services.producao_ocorrencias_service import (
    MAX_TEXTO,
    contagem_por_obra,
    contar_ocorrencias,
    eliminar_ocorrencia,
    formatar_data,
    listar_ocorrencias,
    registar_ocorrencia,
)


@pytest.fixture()
def obra(session):
    processo = Producao(
        codigo_processo="26.1134_01_01_JF_VIVA",
        ano="2026",
        num_enc_phc="1134",
        versao_obra="01",
        versao_plano="01",
        estado="Desenho",
    )
    session.add(processo)
    session.commit()
    return processo


@pytest.fixture()
def utilizadores(session):
    paulo = User(
        username="paulo",
        nome="Paulo Catarino",
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


def test_registar_guarda_quem_e_quando(session, obra, utilizadores) -> None:
    paulo, _ana = utilizadores

    registar_ocorrencia(
        session,
        producao_id=obra.id,
        texto="  Faltou uma dobradiça no roupeiro do quarto 2.  ",
        user_id=paulo.id,
        autor=paulo.nome,
    )
    session.commit()

    registos = listar_ocorrencias(session, obra.id)
    assert len(registos) == 1
    assert registos[0].texto == "Faltou uma dobradiça no roupeiro do quarto 2."
    assert registos[0].autor == "Paulo Catarino"
    assert registos[0].user_id == paulo.id
    assert registos[0].created_at is not None


def test_texto_vazio_e_recusado(session, obra) -> None:
    with pytest.raises(ValueError, match="Escreva o que aconteceu"):
        registar_ocorrencia(session, producao_id=obra.id, texto="   ")


def test_texto_demasiado_longo_e_recusado(session, obra) -> None:
    with pytest.raises(ValueError, match="demasiado longo"):
        registar_ocorrencia(
            session, producao_id=obra.id, texto="x" * (MAX_TEXTO + 1)
        )


def test_o_diario_e_uma_lista_do_mais_recente_para_o_mais_antigo(
    session, obra, utilizadores
) -> None:
    paulo, _ana = utilizadores
    primeiro = registar_ocorrencia(
        session, producao_id=obra.id, texto="Primeiro", user_id=paulo.id
    )
    segundo = registar_ocorrencia(
        session, producao_id=obra.id, texto="Segundo", user_id=paulo.id
    )
    session.commit()

    # Mesmo com a mesma data, o id desempata: o último escrito vem primeiro.
    assert [o.id for o in listar_ocorrencias(session, obra.id)] == [
        segundo.id,
        primeiro.id,
    ]


def test_so_o_autor_pode_eliminar(session, obra, utilizadores) -> None:
    paulo, ana = utilizadores
    registo = registar_ocorrencia(
        session, producao_id=obra.id, texto="do Paulo", user_id=paulo.id
    )
    session.commit()

    with pytest.raises(ValueError, match="Só quem escreveu"):
        eliminar_ocorrencia(session, registo.id, user_id=ana.id)

    eliminar_ocorrencia(session, registo.id, user_id=paulo.id)
    session.commit()
    assert listar_ocorrencias(session, obra.id) == []


def test_administrador_pode_eliminar_o_de_qualquer_um(
    session, obra, utilizadores
) -> None:
    paulo, ana = utilizadores
    registo = registar_ocorrencia(
        session, producao_id=obra.id, texto="do Paulo", user_id=paulo.id
    )
    session.commit()

    eliminar_ocorrencia(session, registo.id, user_id=ana.id, is_admin=True)
    session.commit()
    assert listar_ocorrencias(session, obra.id) == []


def test_eliminar_registo_inexistente(session) -> None:
    with pytest.raises(ValueError, match="não encontrado"):
        eliminar_ocorrencia(session, 999, user_id=1, is_admin=True)


def test_contagens(session, obra, utilizadores) -> None:
    paulo, _ana = utilizadores
    outra = Producao(
        codigo_processo="26.1135_01_01_X",
        ano="2026",
        num_enc_phc="1135",
        versao_obra="01",
        versao_plano="01",
    )
    session.add(outra)
    session.flush()

    registar_ocorrencia(session, producao_id=obra.id, texto="a", user_id=paulo.id)
    registar_ocorrencia(session, producao_id=obra.id, texto="b", user_id=paulo.id)
    registar_ocorrencia(session, producao_id=outra.id, texto="c", user_id=paulo.id)
    session.commit()

    assert contar_ocorrencias(session, obra.id) == 2
    assert contar_ocorrencias(session, outra.id) == 1
    assert contagem_por_obra(session) == {obra.id: 2, outra.id: 1}
    assert contagem_por_obra(session, [obra.id]) == {obra.id: 2}
    assert contagem_por_obra(session, []) == {}


def test_o_diario_desaparece_com_a_obra_e_sobrevive_ao_utilizador() -> None:
    """Regras das chaves estrangeiras, verificadas no próprio modelo.

    Em SQLite (usado nos testes) as FKs não são aplicadas por omissão, por
    isso testa-se a declaração e não o efeito — em MySQL é o motor que a faz
    cumprir.
    """
    tabela = ProducaoOcorrencia.__table__

    obra_fk = next(
        fk for fk in tabela.foreign_keys if fk.column.table.name == "producao"
    )
    user_fk = next(
        fk for fk in tabela.foreign_keys if fk.column.table.name == "users"
    )

    # Sem obra, o diário não faz sentido.
    assert obra_fk.ondelete == "CASCADE"
    # Mas tem de sobreviver à saída de quem escreveu — daí o campo `autor`.
    assert user_fk.ondelete == "SET NULL"
    assert tabela.c.user_id.nullable is True
    assert tabela.c.autor is not None


def test_formatar_data() -> None:
    assert formatar_data(datetime(2026, 7, 23, 18, 11)) == "23-07-2026 18:11"
    assert formatar_data(None) == ""
