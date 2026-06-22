"""Audit log das alteracoes da versao do orcamento (R2.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.session import app_session
from app.models.orcamento_versao_evento import OrcamentoVersaoEvento
from app.models.user import User


@dataclass(frozen=True)
class EventoResumo:
    created_at: datetime
    utilizador: str
    tipo: str
    descricao: str


class OrcamentoHistoricoService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def registar(self, orcamento_versao_id: int, tipo: str, descricao: str) -> None:
        """Regista um evento (NAO faz commit - usa a transacao do chamador)."""
        user = app_session.current_user
        self.session.add(
            OrcamentoVersaoEvento(
                orcamento_versao_id=orcamento_versao_id,
                tipo=tipo,
                descricao=descricao,
                user_id=user.id if user is not None else None,
            )
        )

    def listar(self, orcamento_versao_id: int) -> list[EventoResumo]:
        """Eventos da versao, mais recente primeiro."""
        stmt = (
            select(OrcamentoVersaoEvento, User.nome)
            .outerjoin(User, OrcamentoVersaoEvento.user_id == User.id)
            .where(OrcamentoVersaoEvento.orcamento_versao_id == orcamento_versao_id)
            .order_by(
                OrcamentoVersaoEvento.created_at.desc(),
                OrcamentoVersaoEvento.id.desc(),
            )
        )
        return [
            EventoResumo(
                created_at=ev.created_at,
                utilizador=nome or "\u2014",
                tipo=ev.tipo,
                descricao=ev.descricao,
            )
            for ev, nome in self.session.execute(stmt).all()
        ]
