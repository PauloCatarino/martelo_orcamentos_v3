from __future__ import annotations

from app.domain.tempo_atividade import (
    formatar_tempo_ativo,
    incremento_tempo_ativo,
)


def test_conta_intervalo_com_contexto_app_ativa_e_atividade_recente() -> None:
    assert incremento_tempo_ativo(
        agora=110,
        ultimo_tick=100,
        ultima_atividade=105,
        contexto_ativo=True,
        aplicacao_ativa=True,
    ) == 10


def test_nao_conta_fora_do_orcamento_em_background_ou_inativo() -> None:
    base = dict(agora=110, ultimo_tick=100, ultima_atividade=105)
    assert incremento_tempo_ativo(
        **base, contexto_ativo=False, aplicacao_ativa=True
    ) == 0
    assert incremento_tempo_ativo(
        **base, contexto_ativo=True, aplicacao_ativa=False
    ) == 0
    assert incremento_tempo_ativo(
        agora=300,
        ultimo_tick=290,
        ultima_atividade=100,
        contexto_ativo=True,
        aplicacao_ativa=True,
    ) == 0


def test_intervalo_e_limitado_depois_de_suspensao_do_pc() -> None:
    assert incremento_tempo_ativo(
        agora=10_000,
        ultimo_tick=100,
        ultima_atividade=9_999,
        contexto_ativo=True,
        aplicacao_ativa=True,
    ) == 20


def test_formata_tempo_ativo_aproximado() -> None:
    assert formatar_tempo_ativo(0) == "0 min"
    assert formatar_tempo_ativo(89) == "1 min"
    assert formatar_tempo_ativo(3600) == "1 h"
    assert formatar_tempo_ativo(3930) == "1 h 06 min"
