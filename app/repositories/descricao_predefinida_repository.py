"""Repository for user predefined descriptions (phase P6a)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DescricaoPredefinida

_TIPOS_VALIDOS = {"-", "*"}


def normalizar_tipo(tipo: str | None) -> str:
    valor = (tipo or "").strip()[:1]
    return valor if valor in _TIPOS_VALIDOS else "-"


@dataclass(frozen=True)
class DescricaoPredefinidaResumo:
    id: int
    texto: str
    tipo: str
    ordem: int


class DescricaoPredefinidaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_user(
        self, user_id: int, termos: Iterable[str] | None = None
    ) -> list[DescricaoPredefinidaResumo]:
        if not user_id:
            return []
        stmt = (
            select(DescricaoPredefinida)
            .where(DescricaoPredefinida.user_id == user_id)
            .order_by(DescricaoPredefinida.ordem.asc(), DescricaoPredefinida.id.asc())
        )
        for termo in [t.strip() for t in (termos or []) if t and t.strip()]:
            stmt = stmt.where(DescricaoPredefinida.texto.ilike(f"%{termo}%"))
        rows = self.session.execute(stmt).scalars().all()
        return [self._to_resumo(r) for r in rows]

    def criar(self, user_id: int, texto: str, tipo: str) -> DescricaoPredefinidaResumo:
        max_ordem = self.session.execute(
            select(func.max(DescricaoPredefinida.ordem)).where(
                DescricaoPredefinida.user_id == user_id
            )
        ).scalar() or 0
        row = DescricaoPredefinida(
            user_id=user_id, texto=texto, tipo=normalizar_tipo(tipo), ordem=max_ordem + 1
        )
        self.session.add(row)
        self.session.flush()
        return self._to_resumo(row)

    def atualizar(
        self, id: int, user_id: int, texto: str, tipo: str
    ) -> DescricaoPredefinidaResumo:
        row = self.session.get(DescricaoPredefinida, id)
        if row is None or row.user_id != user_id:
            raise ValueError("Descrição não encontrada.")
        row.texto = texto
        row.tipo = normalizar_tipo(tipo)
        self.session.flush()
        return self._to_resumo(row)

    def eliminar(self, user_id: int, ids: Sequence[int]) -> int:
        if not ids:
            return 0
        rows = (
            self.session.execute(
                select(DescricaoPredefinida).where(
                    DescricaoPredefinida.user_id == user_id,
                    DescricaoPredefinida.id.in_(list(ids)),
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            self.session.delete(row)
        if rows:
            self.session.flush()
            self._reordenar(user_id)
        return len(rows)

    def mover(self, id: int, user_id: int, direcao: str) -> bool:
        if direcao not in {"up", "down"}:
            return False
        row = self.session.get(DescricaoPredefinida, id)
        if row is None or row.user_id != user_id:
            return False
        if direcao == "up":
            stmt = (
                select(DescricaoPredefinida)
                .where(
                    DescricaoPredefinida.user_id == user_id,
                    DescricaoPredefinida.ordem < row.ordem,
                )
                .order_by(DescricaoPredefinida.ordem.desc())
                .limit(1)
            )
        else:
            stmt = (
                select(DescricaoPredefinida)
                .where(
                    DescricaoPredefinida.user_id == user_id,
                    DescricaoPredefinida.ordem > row.ordem,
                )
                .order_by(DescricaoPredefinida.ordem.asc())
                .limit(1)
            )
        vizinho = self.session.execute(stmt).scalar_one_or_none()
        if vizinho is None:
            return False
        row.ordem, vizinho.ordem = vizinho.ordem, row.ordem
        self.session.flush()
        return True

    def _reordenar(self, user_id: int) -> None:
        rows = (
            self.session.execute(
                select(DescricaoPredefinida)
                .where(DescricaoPredefinida.user_id == user_id)
                .order_by(DescricaoPredefinida.ordem.asc(), DescricaoPredefinida.id.asc())
            )
            .scalars()
            .all()
        )
        for idx, row in enumerate(rows, start=1):
            if row.ordem != idx:
                row.ordem = idx
        self.session.flush()

    def _to_resumo(self, row: DescricaoPredefinida) -> DescricaoPredefinidaResumo:
        return DescricaoPredefinidaResumo(
            id=row.id, texto=row.texto, tipo=row.tipo or "-", ordem=row.ordem
        )
