"""Basic production-time calculations from a piece's operations (phase 8R).

Times are stored in MINUTES (decimal). Each operation's ``tempo_base`` is the
per-unit time: for orlagem it is multiplied by the linear metres of edging
(``ml_orla_total``); for the other stages it is multiplied by the piece quantity
(``qt_total``). ``tempo_setup`` is summed into the setup bucket. No costs are
computed here.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.medidas import normalizar_numero

AVISO_TEMPO_OPERACAO_SEM_DADOS = (
    "Tempos de produção não calculados: tempos das operações em falta."
)

_BUCKETS = ("corte", "orlagem", "cnc", "montagem", "manual", "setup")

# Keyword (in tipo_operacao / codigo) -> time bucket. First match wins.
_REGRAS_BUCKET = (
    ("corte", ("CORTE",)),
    ("orlagem", ("ORLAGEM", "ORLA")),
    ("cnc", ("CNC",)),
    ("montagem", ("MONTAGEM",)),
    ("setup", ("SETUP",)),
    ("manual", ("MANUAL", "FURACAO", "RASGO", "COLAGEM", "EMBALAMENTO")),
)


def classificar_operacao(tipo_operacao, codigo) -> str | None:
    """Return the time bucket of an operation (or None when it has no time)."""
    texto = f"{tipo_operacao or ''} {codigo or ''}".upper()
    for bucket, palavras in _REGRAS_BUCKET:
        if any(palavra in texto for palavra in palavras):
            return bucket
    return None


def calcular_tempos_producao(
    operacoes,
    qt_total,
    ml_orla_total,
) -> tuple[dict[str, Decimal], bool]:
    """Return (tempos_por_bucket, faltam_dados) for one line's operations.

    ``operacoes`` is an iterable of objects with ``tipo_operacao``, ``codigo``,
    ``unidade_calculo``, ``tempo_base`` and ``tempo_setup``. ``faltam_dados`` is
    True when a time-relevant operation has no ``tempo_base`` (so the caller can
    add a diagnostic). Never raises.
    """
    qt = normalizar_numero(qt_total)
    if qt is None:
        qt = Decimal("1")
    ml = normalizar_numero(ml_orla_total) or Decimal("0")

    tempos = {bucket: Decimal("0") for bucket in _BUCKETS}
    faltam = False

    for operacao in operacoes:
        bucket = classificar_operacao(
            getattr(operacao, "tipo_operacao", None), getattr(operacao, "codigo", None)
        )
        if bucket is None:
            continue

        setup = normalizar_numero(getattr(operacao, "tempo_setup", None))
        if setup is not None:
            tempos["setup"] += setup
        if bucket == "setup":
            continue

        base = normalizar_numero(getattr(operacao, "tempo_base", None))

        if bucket == "orlagem":
            # No edging -> no time and no diagnostic (the piece may have no orla).
            if ml <= 0:
                continue
            if base is None:
                faltam = True
                continue
            tempos["orlagem"] += base * ml
            continue

        if base is None:
            faltam = True
            continue
        tempos[bucket] += base * qt

    return tempos, faltam
