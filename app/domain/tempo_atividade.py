"""Regras puras para contabilizar tempo ativo de trabalho."""

from __future__ import annotations


LIMITE_INATIVIDADE_SEGUNDOS = 120.0
LIMITE_INTERVALO_SEGUNDOS = 20.0


def incremento_tempo_ativo(
    *,
    agora: float,
    ultimo_tick: float,
    ultima_atividade: float | None,
    contexto_ativo: bool,
    aplicacao_ativa: bool,
    limite_inatividade: float = LIMITE_INATIVIDADE_SEGUNDOS,
    limite_intervalo: float = LIMITE_INTERVALO_SEGUNDOS,
) -> float:
    """Return the countable portion since the prior timer tick.

    The interval cap prevents a suspended PC or a blocked event loop from
    turning hours into active work when the application resumes.
    """
    if not contexto_ativo or not aplicacao_ativa or ultima_atividade is None:
        return 0.0
    if agora < ultimo_tick or agora - ultima_atividade > limite_inatividade:
        return 0.0
    return max(0.0, min(agora - ultimo_tick, limite_intervalo))


def formatar_tempo_ativo(segundos) -> str:
    """Format accumulated seconds as an approximate human duration."""
    try:
        total_segundos = max(0, int(segundos or 0))
    except (TypeError, ValueError):
        total_segundos = 0

    minutos = (total_segundos + 30) // 60
    horas, resto = divmod(minutos, 60)
    if horas:
        return f"{horas} h {resto:02d} min" if resto else f"{horas} h"
    return f"{minutos} min"
