"""Diário da obra: registar e ler o que aconteceu, sem tocar na obra.

Deliberadamente simples: linhas acrescentadas, não editadas. Sem estados, sem
responsáveis, sem workflow — é um diário, não um módulo de assistências.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.producao_ocorrencia import ProducaoOcorrencia


#: Limite defensivo: um registo é uma nota, não um relatório.
MAX_TEXTO = 4000


def listar_ocorrencias(session: Session, producao_id: int) -> list[ProducaoOcorrencia]:
    """List one obra's diary, most recent first."""
    statement = (
        select(ProducaoOcorrencia)
        .where(ProducaoOcorrencia.producao_id == producao_id)
        .order_by(ProducaoOcorrencia.created_at.desc(), ProducaoOcorrencia.id.desc())
    )
    return list(session.scalars(statement).all())


def contar_ocorrencias(session: Session, producao_id: int) -> int:
    """How many lines this obra's diary has."""
    return int(
        session.scalar(
            select(func.count())
            .select_from(ProducaoOcorrencia)
            .where(ProducaoOcorrencia.producao_id == producao_id)
        )
        or 0
    )


def contagem_por_obra(session: Session, producao_ids=None) -> dict[int, int]:
    """Diary size for many obras at once (one query)."""
    statement = select(
        ProducaoOcorrencia.producao_id, func.count()
    ).group_by(ProducaoOcorrencia.producao_id)
    if producao_ids is not None:
        ids = list(producao_ids)
        if not ids:
            return {}
        statement = statement.where(ProducaoOcorrencia.producao_id.in_(ids))
    return {int(pid): int(total) for pid, total in session.execute(statement).all()}


def registar_ocorrencia(
    session: Session,
    *,
    producao_id: int,
    texto: str,
    user_id: int | None = None,
    autor: str | None = None,
) -> ProducaoOcorrencia:
    """Add one line to the obra's diary."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Escreva o que aconteceu antes de registar.")
    if len(texto) > MAX_TEXTO:
        raise ValueError(
            f"O registo é demasiado longo ({len(texto)} caracteres, "
            f"máximo {MAX_TEXTO})."
        )

    ocorrencia = ProducaoOcorrencia(
        producao_id=producao_id,
        user_id=user_id,
        autor=(autor or "").strip() or None,
        texto=texto,
    )
    session.add(ocorrencia)
    session.flush()
    return ocorrencia


def eliminar_ocorrencia(
    session: Session,
    ocorrencia_id: int,
    *,
    user_id: int | None,
    is_admin: bool = False,
) -> None:
    """Delete one line — só o próprio autor ou um administrador.

    Um diário onde qualquer pessoa apaga o que outra escreveu não serve para
    resolver discussões com clientes.
    """
    ocorrencia = session.get(ProducaoOcorrencia, ocorrencia_id)
    if ocorrencia is None:
        raise ValueError("Registo não encontrado.")
    if not is_admin and (user_id is None or ocorrencia.user_id != user_id):
        raise ValueError("Só quem escreveu o registo o pode eliminar.")

    session.delete(ocorrencia)
    session.flush()


def formatar_data(valor: datetime | None) -> str:
    """Return the diary date as ``dd-mm-aaaa HH:MM``."""
    if valor is None:
        return ""
    try:
        return valor.strftime("%d-%m-%Y %H:%M")
    except AttributeError:
        return ""
