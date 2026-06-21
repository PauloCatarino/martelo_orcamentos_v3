"""Service for user predefined descriptions (phase P6a)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.repositories.descricao_predefinida_repository import (
    DescricaoPredefinidaRepository,
    DescricaoPredefinidaResumo,
)


class DescricaoPredefinidaService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DescricaoPredefinidaRepository(session)

    def listar(
        self, user_id: int, texto: str | None = None
    ) -> list[DescricaoPredefinidaResumo]:
        termos = (texto or "").split("%") if texto else None
        return self.repository.list_by_user(user_id, termos)

    def criar(self, user_id: int, texto: str, tipo: str) -> DescricaoPredefinidaResumo:
        if not user_id:
            raise ValueError("Utilizador inválido.")
        texto_limpo = (texto or "").strip()
        if not texto_limpo:
            raise ValueError("O texto da descrição não pode ser vazio.")
        resumo = self.repository.criar(user_id, texto_limpo, tipo)
        self.session.commit()
        return resumo

    def editar(
        self, id: int, user_id: int, texto: str, tipo: str
    ) -> DescricaoPredefinidaResumo:
        texto_limpo = (texto or "").strip()
        if not texto_limpo:
            raise ValueError("O texto da descrição não pode ser vazio.")
        resumo = self.repository.atualizar(id, user_id, texto_limpo, tipo)
        self.session.commit()
        return resumo

    def eliminar(self, user_id: int, ids: Sequence[int]) -> int:
        total = self.repository.eliminar(user_id, ids)
        self.session.commit()
        return total

    def mover(self, id: int, user_id: int, direcao: str) -> bool:
        moveu = self.repository.mover(id, user_id, direcao)
        if moveu:
            self.session.commit()
        return moveu
