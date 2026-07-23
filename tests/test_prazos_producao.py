"""Tests for the delivery-date warning rules."""

from __future__ import annotations

from datetime import date

from app.domain.prazos_producao import (
    ATRASADO,
    FECHADO,
    NORMAL,
    PROXIMO,
    SEM_DATA,
    estado_prazo,
)


HOJE = date(2026, 7, 22)


def test_entrega_passada_fica_atrasada() -> None:
    situacao = estado_prazo("15-07-2026", "Desenho", hoje=HOJE)

    assert situacao.situacao == ATRASADO
    assert situacao.dias == -7
    assert situacao.atrasada is True
    assert situacao.tem_alerta is True
    assert "7 dias" in situacao.descricao()


def test_entrega_dentro_de_uma_semana_fica_proxima() -> None:
    situacao = estado_prazo("27-07-2026", "Producao", hoje=HOJE)

    assert situacao.situacao == PROXIMO
    assert situacao.dias == 5
    assert situacao.atrasada is False
    assert situacao.tem_alerta is True


def test_entrega_hoje_conta_como_proxima() -> None:
    situacao = estado_prazo("22-07-2026", "Desenho", hoje=HOJE)

    assert situacao.situacao == PROXIMO
    assert situacao.dias == 0
    assert situacao.descricao() == "Entrega é hoje"


def test_entrega_longe_nao_tem_alerta() -> None:
    situacao = estado_prazo("30-09-2026", "Desenho", hoje=HOJE)

    assert situacao.situacao == NORMAL
    assert situacao.tem_alerta is False


def test_obra_arquivada_nunca_tem_alerta() -> None:
    """Foi o pedido do Paulo: numa obra fechada a data já é histórico."""
    situacao = estado_prazo("01-01-2020", "Arquivado", hoje=HOJE)

    assert situacao.situacao == FECHADO
    assert situacao.atrasada is False
    assert situacao.tem_alerta is False


def test_obra_finalizada_tambem_nao_tem_alerta() -> None:
    assert estado_prazo("01-01-2020", "Finalizado", hoje=HOJE).situacao == FECHADO


def test_estado_com_acentos_ou_maiusculas_e_reconhecido() -> None:
    assert estado_prazo("01-01-2020", "ARQUIVADO", hoje=HOJE).situacao == FECHADO
    assert estado_prazo("01-01-2020", " arquivado ", hoje=HOJE).situacao == FECHADO


def test_sem_data_de_entrega() -> None:
    assert estado_prazo(None, "Desenho", hoje=HOJE).situacao == SEM_DATA
    assert estado_prazo("", "Desenho", hoje=HOJE).situacao == SEM_DATA
    assert estado_prazo("data marada", "Desenho", hoje=HOJE).situacao == SEM_DATA


def test_aceita_objeto_date() -> None:
    situacao = estado_prazo(date(2026, 7, 25), "Desenho", hoje=HOJE)

    assert situacao.situacao == PROXIMO
    assert situacao.dias == 3
