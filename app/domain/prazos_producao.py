"""Delivery-date warning rules for the production list.

An obra que já está fechada (Arquivado/Finalizado) não tem alarme de prazo:
a data de entrega passa a ser histórico, não um aviso.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date

from app.domain.datas import normalizar_data


#: Dias de antecedência a partir dos quais a entrega é assinalada como próxima.
DIAS_AVISO_ENTREGA = 7

#: Estados em que a obra já está fechada — sem semáforo de prazo.
#: Decisão do Paulo (2026-07-23): «obra fechada» é Arquivado. Uma obra
#: Finalizada ainda pode estar por levantar ou por faturar, por isso o alerta
#: de prazo mantém-se.
ESTADOS_SEM_PRAZO: frozenset[str] = frozenset({"arquivado"})

SEM_DATA = "sem_data"
FECHADO = "fechado"
ATRASADO = "atrasado"
PROXIMO = "proximo"
NORMAL = "normal"


@dataclass(frozen=True)
class EstadoPrazo:
    """Delivery-date status for one production process."""

    situacao: str
    dias: int | None = None

    @property
    def tem_alerta(self) -> bool:
        return self.situacao in {ATRASADO, PROXIMO}

    @property
    def atrasada(self) -> bool:
        return self.situacao == ATRASADO

    def descricao(self) -> str:
        """Human-readable hint for the tooltip."""
        if self.situacao == ATRASADO:
            dias = abs(self.dias or 0)
            return f"Entrega em atraso há {dias} dia{'s' if dias != 1 else ''}"
        if self.situacao == PROXIMO:
            dias = self.dias or 0
            if dias == 0:
                return "Entrega é hoje"
            return f"Faltam {dias} dia{'s' if dias != 1 else ''} para a entrega"
        if self.situacao == NORMAL:
            return f"Faltam {self.dias} dias para a entrega"
        if self.situacao == FECHADO:
            return "Obra fechada — sem alerta de prazo"
        return ""


def estado_prazo(
    data_entrega: object,
    estado: object = None,
    *,
    hoje: date | None = None,
) -> EstadoPrazo:
    """Classify one delivery date, ignoring closed works."""
    if _estado_fechado(estado):
        return EstadoPrazo(FECHADO)

    entrega = _para_data(data_entrega)
    if entrega is None:
        return EstadoPrazo(SEM_DATA)

    dias = (entrega - (hoje or date.today())).days
    if dias < 0:
        return EstadoPrazo(ATRASADO, dias)
    if dias <= DIAS_AVISO_ENTREGA:
        return EstadoPrazo(PROXIMO, dias)
    return EstadoPrazo(NORMAL, dias)


def _estado_fechado(estado: object) -> bool:
    return _normalizar(estado) in ESTADOS_SEM_PRAZO


def _normalizar(valor: object) -> str:
    sem_acentos = unicodedata.normalize("NFKD", str(valor or "").strip())
    return "".join(
        caractere for caractere in sem_acentos if not unicodedata.combining(caractere)
    ).lower()


def _para_data(valor: object) -> date | None:
    if isinstance(valor, date):
        return valor

    texto = normalizar_data(valor)
    if not texto:
        return None
    try:
        dia, mes, ano = (int(parte) for parte in texto.split("-"))
        return date(ano, mes, dia)
    except (TypeError, ValueError):
        return None
