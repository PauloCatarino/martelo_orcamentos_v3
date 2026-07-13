"""Read-only aggregates shared by the Home and budget dashboards."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from app.repositories.orcamento_repository import OrcamentoResumo

_FECHADOS = {"concluido", "adjudicado", "sem interesse", "nao adjudicado", "cancelado"}


@dataclass(frozen=True)
class AvisoDashboard:
    nivel: str
    titulo: str
    detalhe: str
    orcamento_versao_id: int | None = None


@dataclass(frozen=True)
class DashboardOrcamentos:
    total: int
    em_curso: int
    adjudicados: int
    falta_orcamentar: int
    enviados: int
    valor_em_curso: Decimal
    valor_adjudicado: Decimal
    com_preco_manual: int
    sem_total: int
    recentes: tuple[OrcamentoResumo, ...]
    avisos: tuple[AvisoDashboard, ...]


def calcular_dashboard_orcamentos(
    orcamentos: list[OrcamentoResumo],
    *,
    limite_recentes: int = 6,
    limite_avisos: int = 8,
) -> DashboardOrcamentos:
    """Calculate stable UI aggregates without performing database access."""
    em_curso = adjudicados = falta = enviados = manuais = sem_total = 0
    valor_em_curso = Decimal("0")
    valor_adjudicado = Decimal("0")
    avisos: list[AvisoDashboard] = []

    for orcamento in orcamentos:
        estado = _normalizar(orcamento.estado)
        fechado = estado in _FECHADOS
        preco = orcamento.preco_total
        if not fechado:
            em_curso += 1
            if preco is not None:
                valor_em_curso += preco
        if estado == "adjudicado":
            adjudicados += 1
            if preco is not None:
                valor_adjudicado += preco
        if estado == "falta orcamentar":
            falta += 1
            avisos.append(_aviso(orcamento, "atenção", "Falta orçamentar"))
        if estado == "enviado":
            enviados += 1
        if orcamento.tem_preco_manual:
            manuais += 1
            avisos.append(_aviso(orcamento, "informação", "Preço manual aplicado"))
        if preco is None:
            sem_total += 1
            avisos.append(_aviso(orcamento, "crítico", "Total ainda não calculado"))

    recentes = tuple(sorted(orcamentos, key=lambda item: item.created_at, reverse=True)[:limite_recentes])
    return DashboardOrcamentos(
        total=len(orcamentos),
        em_curso=em_curso,
        adjudicados=adjudicados,
        falta_orcamentar=falta,
        enviados=enviados,
        valor_em_curso=valor_em_curso,
        valor_adjudicado=valor_adjudicado,
        com_preco_manual=manuais,
        sem_total=sem_total,
        recentes=recentes,
        avisos=tuple(avisos[:limite_avisos]),
    )


def _aviso(orcamento: OrcamentoResumo, nivel: str, titulo: str) -> AvisoDashboard:
    cliente = orcamento.cliente_nome or "Sem cliente"
    obra = orcamento.obra or orcamento.descricao or "Sem descrição"
    return AvisoDashboard(
        nivel=nivel,
        titulo=titulo,
        detalhe=f"{orcamento.codigo_versao} · {cliente} · {obra}",
        orcamento_versao_id=orcamento.orcamento_versao_id,
    )


def _normalizar(valor: str | None) -> str:
    texto = unicodedata.normalize("NFKD", (valor or "").strip())
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold()
