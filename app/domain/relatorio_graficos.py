"""Modelos de dados (puros) para os gráficos de barras dos relatórios (fase 8W.3a).

Sem Qt nem matplotlib aqui — apenas transforma as dataclasses de consumo já
calculadas (:mod:`app.domain.consumos`) em modelos simples de gráfico que o
widget dos dashboards desenha. Mantido puro para ser testável sem GUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

_ZERO = Decimal("0")

# Comprimento máximo de uma etiqueta construída a partir da descrição (mantém o
# eixo X legível quando falta a referência).
_MAX_ETIQUETA = 18


@dataclass(frozen=True)
class SerieBarras:
    """Uma série de dados (com nome) de um gráfico de barras."""

    nome: str
    valores: list


@dataclass(frozen=True)
class GraficoBarras:
    """Modelo de um gráfico de barras: título, etiquetas X, séries e unidade Y."""

    titulo: str
    etiquetas: list
    series: list
    unidade: str


@dataclass(frozen=True)
class FatiaPizza:
    """Uma fatia (categoria) do gráfico de pizza da distribuição de custos."""

    nome: str
    euros: Decimal
    pct: Decimal


@dataclass(frozen=True)
class GraficoPizza:
    """Modelo de um gráfico de pizza: título, fatias e total de venda."""

    titulo: str
    fatias: list
    total_venda: Decimal


def _truncar(texto: str | None) -> str:
    """Corta uma descrição para um comprimento de etiqueta legível."""
    limpo = (texto or "").strip()
    if len(limpo) <= _MAX_ETIQUETA:
        return limpo
    return limpo[: _MAX_ETIQUETA - 1] + "…"


def _etiqueta_ref(ref, descricao) -> str:
    """Etiqueta = referência quando existe, senão a descrição truncada."""
    ref_limpa = (ref or "").strip()
    if ref_limpa:
        return ref_limpa
    return _truncar(descricao)


def dados_placas(placas) -> GraficoBarras:
    """Placas: duas séries (custo teórico %desp. vs. custo no orçamento), em €."""
    etiquetas = [_etiqueta_ref(p.ref_le, p.descricao_no_orcamento) for p in placas]
    series = (
        [
            SerieBarras("Teórico (% desp.)", [p.custo_mp_total for p in placas]),
            SerieBarras("No orçamento", [p.custo_no_orcamento for p in placas]),
        ]
        if placas
        else []
    )
    return GraficoBarras(
        titulo="Placas — custo",
        etiquetas=etiquetas,
        series=series,
        unidade="€",
    )


def dados_orlas(orlas) -> GraficoBarras:
    """Orlas: uma série de metros lineares, em ml."""
    etiquetas = [(o.ref_orla or "").strip() for o in orlas]
    series = [SerieBarras("ML", [o.ml_total for o in orlas])] if orlas else []
    return GraficoBarras(
        titulo="Orlas — metros lineares",
        etiquetas=etiquetas,
        series=series,
        unidade="ml",
    )


def dados_ferragens(ferragens) -> GraficoBarras:
    """Ferragens: uma série de custo total, em €."""
    etiquetas = [
        _etiqueta_ref(f.ref_le, f.descricao_no_orcamento) for f in ferragens
    ]
    series = (
        [SerieBarras("Custo", [f.custo_total for f in ferragens])]
        if ferragens
        else []
    )
    return GraficoBarras(
        titulo="Ferragens — custo",
        etiquetas=etiquetas,
        series=series,
        unidade="€",
    )


def dados_maquinas(maquinas) -> GraficoBarras:
    """Máquinas / MO: uma série de custo, em €; só centros com custo_total > 0."""
    com_custo = [m for m in maquinas if m.custo_total > _ZERO]
    etiquetas = [m.centro for m in com_custo]
    series = (
        [SerieBarras("Custo", [m.custo_total for m in com_custo])]
        if com_custo
        else []
    )
    return GraficoBarras(
        titulo="Máquinas / MO — custo",
        etiquetas=etiquetas,
        series=series,
        unidade="€",
    )


def dados_distribuicao(distribuicao) -> GraficoPizza:
    """Distribuição de custos: uma fatia por categoria com euros > 0.

    Ignora categorias a 0 ou negativas (ex.: margem negativa não desenha fatia),
    mantém a ordem das categorias e leva o total de venda para o título.
    """
    fatias = [
        FatiaPizza(c.nome, c.euros, c.pct)
        for c in distribuicao.categorias
        if c.euros > _ZERO
    ]
    return GraficoPizza(
        titulo="Distribuição de custos",
        fatias=fatias,
        total_venda=distribuicao.total_venda,
    )
