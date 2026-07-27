"""People of the team a ticket can be handed to."""

from __future__ import annotations

from sqlalchemy import Boolean, BigInteger, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EquipaMembro(Base):
    """Someone who can be made responsible for a ticket.

    Não são as contas do V3 (``users``): quem monta, quem corta e quem prepara
    não entra no programa, mas tem de receber o ticket no chat. O ``email`` é o
    endereço do Microsoft Teams — é ele que abre a conversa certa.
    """

    __tablename__ = "equipa_membros"
    __table_args__ = (UniqueConstraint("nome", name="uq_equipa_membros_nome"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
