"""Basic production-time calculations from a piece's operations (phase 8R).

Times are stored in MINUTES (decimal). Each operation's ``tempo_base`` is the
per-unit time: for orlagem it is multiplied by the linear metres of edging
(``ml_orla_total``); for the other stages it is multiplied by the piece quantity
(``qt_total``). ``tempo_setup`` is summed into the setup bucket. No costs are
computed here.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.custo_producao import calcular_tempo_operacao
from app.domain.medidas import normalizar_numero
from app.domain.regra_operacao_types import POR_ORLAS

AVISO_TEMPO_OPERACAO_SEM_DADOS = (
    "Tempos de produção não calculados: tempos das operações em falta."
)

_BUCKETS = ("corte", "orlagem", "cnc", "montagem", "manual", "setup")
_UNIDADES_TEMPO_ML = ("ML", "M", "MTL")

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


# --- Times from the piece↔operation link (phase 8R.1) -------------------------
# Informative production times read from DefPecaOperacao (the same source the
# production COST uses), so assembly/manual minutes match the minutes behind
# custo_montagem_manual. These times never change any cost.


def _tempo_por_orlas(unidade_tempo, bucket, regra_calculo) -> bool:
    """True when an operation's time follows the line's edging metres (ML).

    Applies to ML-timed edging operations (bucket 'orlagem') or operations
    carrying the 'Por orlas' rule. Assembly/manual operations are excluded so
    their time stays exactly the minutes behind custo_montagem_manual.
    """
    if (unidade_tempo or "").strip().upper() not in _UNIDADES_TEMPO_ML:
        return False
    if bucket in ("montagem", "manual"):
        return False
    if bucket == "orlagem":
        return True
    return (regra_calculo or "").strip().upper() == POR_ORLAS


def minutos_operacao_ligacao(
    *,
    bucket,
    unidade_tempo,
    quantidade_base,
    tempo_setup_minutos,
    tempo_por_unidade_minutos,
    regra_calculo,
    area_m2,
    qt_total,
    ml_orla_total,
) -> tuple[Decimal | None, Decimal | None]:
    """Return (setup_min, variavel_min) of one piece↔operation link.

    Reuses ``calcular_tempo_operacao`` for the general units (PECA/FURO/UN, M2,
    HORA, OPERACAO/LOTE), so assembly/manual times stay identical to the minutes
    behind ``custo_montagem_manual``. For ML edging / 'Por orlas' operations the
    variable quantity is the line's total edging metres (mirroring the orlagem
    cost). Returns (None, None) when no time is configured (caller ignores it,
    no warning). Never raises.
    """
    if _tempo_por_orlas(unidade_tempo, bucket, regra_calculo):
        ml = normalizar_numero(ml_orla_total) or Decimal("0")
        if ml <= 0:
            return None, None  # no edging -> no orlagem time (as in the cost)
        setup = normalizar_numero(tempo_setup_minutos)
        por_unidade = normalizar_numero(tempo_por_unidade_minutos)
        if setup is None and por_unidade is None:
            return None, None
        return (setup or Decimal("0")), ml * (por_unidade or Decimal("0"))

    return calcular_tempo_operacao(
        unidade_tempo,
        quantidade_base,
        tempo_setup_minutos,
        tempo_por_unidade_minutos,
        area_m2,
        qt_total,
    )


def calcular_tempos_producao_ligacoes(
    pares_operacao_ligacao,
    area_m2,
    qt_total,
    ml_orla_total,
) -> dict[str, Decimal]:
    """Sum the production times (minutes) by bucket from a piece's operations.

    ``pares_operacao_ligacao`` is an iterable of (operacao, ligacao): the
    operation supplies tipo_operacao/codigo (the time bucket) and the link
    supplies the time configuration (unidade_tempo / quantidade_base /
    tempo_setup_minutos / tempo_por_unidade_minutos / regra_calculo). Every
    operation's setup feeds the 'setup' bucket; its variable minutes feed its
    own bucket. Never raises.
    """
    tempos = {bucket: Decimal("0") for bucket in _BUCKETS}

    for operacao, ligacao in pares_operacao_ligacao:
        bucket = classificar_operacao(
            getattr(operacao, "tipo_operacao", None),
            getattr(operacao, "codigo", None),
        )
        if bucket is None:
            continue

        setup_min, variavel_min = minutos_operacao_ligacao(
            bucket=bucket,
            unidade_tempo=getattr(ligacao, "unidade_tempo", None),
            quantidade_base=getattr(ligacao, "quantidade_base", None),
            tempo_setup_minutos=getattr(ligacao, "tempo_setup_minutos", None),
            tempo_por_unidade_minutos=getattr(
                ligacao, "tempo_por_unidade_minutos", None
            ),
            regra_calculo=getattr(ligacao, "regra_calculo", None),
            area_m2=area_m2,
            qt_total=qt_total,
            ml_orla_total=ml_orla_total,
        )
        if setup_min is None and variavel_min is None:
            continue

        if setup_min is not None:
            tempos["setup"] += setup_min
        if bucket != "setup" and variavel_min is not None:
            tempos[bucket] += variavel_min

    return tempos
