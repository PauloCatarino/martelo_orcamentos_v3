"""Estado real de produção por setor (PD1) — domínio puro.

Traduz os dados do Streamlit (``CadernoEncargos[_]`` / ``TemposProducao[_]``) no
estado de produção de uma encomenda: percentagem por setor e estado global. Sem
DB, sem Qt e sem SQL — só regras + ``dataclasses`` — para ser testável.

Cada setor tem um campo ``_ok`` cujo TEXTO é a percentagem (ex.: ``"60"`` -> 60%;
``"SIM"``/``"1"`` -> 100%; ``""``/``"N"``/None -> o setor não existe nessa linha).
Uma encomenda pode ter várias linhas (``bd_key``); o estado é a agregação delas.
"""

from __future__ import annotations

from dataclasses import dataclass

# Valores de texto que significam 100% (booleano "feito"); "1" conta como 100%,
# não como 1%. "100" é tratado pela via numérica.
_VERDADEIRO = {"SIM", "S", "Y", "YES", "TRUE", "1"}

# Tolerância para considerar uma média como 100% (evita ruído de vírgula flutuante).
_TOLERANCIA_100 = 99.999


def interpretar_ok(valor) -> float | None:
    """Interpreta o texto de um campo ``_ok`` como percentagem (0..100) ou None.

    None/""/"N" -> None (setor não existe nessa linha); texto não numérico -> None;
    "SIM"/"S"/"Y"/"YES"/"TRUE"/"1" -> 100; senão o número (ex.: "60" -> 60.0).
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if texto == "":
        return None
    maiusc = texto.upper()
    if maiusc == "N":
        return None
    if maiusc in _VERDADEIRO:
        return 100.0
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return None


def _num(valor) -> float:
    """Converte para float de forma tolerante (""/"02h:08m"/None -> 0.0)."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if texto == "":
        return 0.0
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return 0.0


@dataclass(frozen=True)
class SetorEstado:
    """Estado de um setor existente: média de % e se está concluído (100%)."""

    nome: str
    media_pct: float
    concluido: bool


@dataclass(frozen=True)
class EstadoProducao:
    """Estado de produção agregado de uma encomenda."""

    setores: list[SetorEstado]      # só os existentes, por ordem
    total_setores: int              # Z
    concluidos: int                 # Y
    global_pct: float
    etiqueta: str


# Setores por ordem: (nome, campo _ok, condição de existência por linha).
_SETORES = (
    (
        "Stock",
        "bd_stock_ok",
        lambda linha: interpretar_ok(linha.get("bd_stock_ok")) is not None,
    ),
    (
        "Preparação",
        "bd_preparacao_placas_ok",
        lambda linha: interpretar_ok(linha.get("bd_preparacao_placas_ok")) is not None,
    ),
    (
        "Corte",
        "bd_corte_ok",
        lambda linha: _num(linha.get("bd_operacoes_corte_quantidade")) > 0,
    ),
    (
        "Orlagem",
        "bd_orla_ok",
        lambda linha: _num(linha.get("bd_operacoes_orla_quantidade")) > 0,
    ),
    (
        "CNC",
        "bd_cnc_ok",
        lambda linha: _num(linha.get("bd_operacoes_cnc_quantidade")) > 0,
    ),
    (
        "Montagem",
        "bd_montagem_ok",
        lambda linha: _num(linha.get("tem_montagem_ativa")) == 1,
    ),
    (
        "Embalagem",
        "bd_embalagem_ok",
        lambda linha: _num(linha.get("bd_tempo_embalamento_minutos")) > 0,
    ),
    (
        "Expedição",
        "bd_expedicao_ok",
        lambda linha: interpretar_ok(linha.get("bd_expedicao_ok")) is not None,
    ),
)


def _etiqueta(pct: float, concluidos: int, total: int) -> str:
    if total == 0:
        return "—"
    if pct >= 100:
        return f"✅ 100% ({concluidos}/{total})"
    if pct == 0:
        return f"⏳ 0% (0/{total})"
    return f"🔄 {pct:.1f}% ({concluidos}/{total})"


def estado_producao_encomenda(linhas: list[dict]) -> EstadoProducao:
    """Calcula o estado de produção a partir das linhas (bd_key) da encomenda."""
    linhas = linhas or []

    setores: list[SetorEstado] = []
    for nome, ok_key, existe_na_linha in _SETORES:
        existe = False
        valores: list[float] = []
        for linha in linhas:
            if not existe_na_linha(linha):
                continue
            existe = True
            ok = interpretar_ok(linha.get(ok_key))
            if ok is not None:
                valores.append(ok)
        if not existe:
            continue
        media = sum(valores) / len(valores) if valores else 0.0
        setores.append(
            SetorEstado(
                nome=nome,
                media_pct=round(media, 1),
                concluido=media >= _TOLERANCIA_100,
            )
        )

    total = len(setores)
    concluidos = sum(1 for setor in setores if setor.concluido)
    global_pct = round(concluidos / total * 100, 1) if total else 0.0

    return EstadoProducao(
        setores=setores,
        total_setores=total,
        concluidos=concluidos,
        global_pct=global_pct,
        etiqueta=_etiqueta(global_pct, concluidos, total),
    )
