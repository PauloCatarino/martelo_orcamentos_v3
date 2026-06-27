"""Aggregates for the Producao "Ponto Situacao" dashboard."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.services.producao_service import ProducaoService, filtrar_processos

ESTADOS_FECHADOS = ("Finalizado", "Arquivado")
_ESTADOS_FECHADOS_NORM = {"finalizado", "arquivado"}


def _parse_data(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class DashboardData:
    total: int
    por_estado: list
    por_responsavel: list
    por_cliente: list
    em_desenho: int
    em_producao: int
    finalizadas: int
    arquivadas: int
    atrasadas: int
    sem_preco: int
    valor_aberto: float
    hoje: date


def calcular_dashboard(
    session: Session,
    *,
    texto="",
    utilizador=None,
    cliente=None,
    estado=None,
    hoje=None,
) -> DashboardData:
    """Calculate read-only dashboard aggregates for production processes."""
    hoje = hoje or date.today()
    todos = ProducaoService(session).listar_processos()
    filtrados = filtrar_processos(
        todos,
        texto=texto,
        estado=estado,
        cliente=cliente,
        responsavel=utilizador,
    )

    por_estado, por_resp, por_cli = {}, {}, {}
    em_desenho = em_producao = finalizadas = arquivadas = atrasadas = sem_preco = 0
    valor_aberto = 0.0

    for processo in filtrados:
        est = (processo.estado or "").strip()
        est_label = est or "(sem estado)"
        est_norm = _normalizar_estado(est)
        por_estado[est_label] = por_estado.get(est_label, 0) + 1

        resp = (processo.responsavel or "").strip() or "(sem resp)"
        por_resp[resp] = por_resp.get(resp, 0) + 1

        cli = (processo.nome_cliente or "").strip() or "(sem cliente)"
        por_cli[cli] = por_cli.get(cli, 0) + 1

        if est_norm == "desenho":
            em_desenho += 1
        elif est_norm == "producao":
            em_producao += 1
        elif est_norm == "finalizado":
            finalizadas += 1
        elif est_norm == "arquivado":
            arquivadas += 1

        if est_norm not in _ESTADOS_FECHADOS_NORM:
            if processo.preco_total is None:
                sem_preco += 1
            else:
                valor_aberto += float(processo.preco_total)
            entrega = _parse_data(processo.data_entrega)
            if entrega is not None and entrega < hoje:
                atrasadas += 1

    return DashboardData(
        total=len(filtrados),
        por_estado=_ordenar(por_estado),
        por_responsavel=_ordenar(por_resp),
        por_cliente=_ordenar(por_cli),
        em_desenho=em_desenho,
        em_producao=em_producao,
        finalizadas=finalizadas,
        arquivadas=arquivadas,
        atrasadas=atrasadas,
        sem_preco=sem_preco,
        valor_aberto=round(valor_aberto, 2),
        hoje=hoje,
    )


def _ordenar(valores: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(valores.items(), key=lambda kv: (-kv[1], kv[0].casefold()))


def _normalizar_estado(estado: str | None) -> str:
    sem_acentos = unicodedata.normalize("NFKD", (estado or "").strip())
    return "".join(
        caractere
        for caractere in sem_acentos
        if not unicodedata.combining(caractere)
    ).lower()
