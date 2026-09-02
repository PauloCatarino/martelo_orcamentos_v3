"""Regra da verificação diária dos clientes do PHC (dias úteis, das 09h00)."""

from __future__ import annotations

from datetime import date, datetime

from app.domain.agenda_diaria_phc import (
    deve_verificar,
    escrever_data,
    ler_data,
)

# 2026-09-02 é uma quarta-feira; 2026-09-05 um sábado; 2026-09-06 um domingo.
QUARTA_9H = datetime(2026, 9, 2, 9, 0)


def test_verifica_num_dia_util_a_partir_das_nove() -> None:
    assert deve_verificar(QUARTA_9H, None) is True
    assert deve_verificar(datetime(2026, 9, 2, 14, 30), None) is True


def test_nao_verifica_antes_das_nove() -> None:
    assert deve_verificar(datetime(2026, 9, 2, 8, 59), None) is False


def test_nao_verifica_ao_fim_de_semana() -> None:
    assert deve_verificar(datetime(2026, 9, 5, 10, 0), None) is False
    assert deve_verificar(datetime(2026, 9, 6, 10, 0), None) is False


def test_so_uma_vez_por_dia() -> None:
    assert deve_verificar(QUARTA_9H, date(2026, 9, 2)) is False
    # A verificação de ontem não conta para hoje.
    assert deve_verificar(QUARTA_9H, date(2026, 9, 1)) is True


def test_data_guardada_e_lida_de_volta() -> None:
    assert ler_data(escrever_data(date(2026, 9, 2))) == date(2026, 9, 2)


def test_data_em_falta_ou_estragada_conta_como_nunca_verificado() -> None:
    assert ler_data(None) is None
    assert ler_data("") is None
    assert ler_data("ontem") is None
