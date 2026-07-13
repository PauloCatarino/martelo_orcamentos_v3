"""Persistence for locally materialized costing-line operations."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.orcamento_item_custeio_linha_operacao import (
    OrcamentoItemCusteioLinhaOperacao,
)


class OrcamentoItemCusteioLinhaOperacaoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self, linha_id: int) -> list[OrcamentoItemCusteioLinhaOperacao]:
        return list(
            self.session.scalars(
                select(OrcamentoItemCusteioLinhaOperacao)
                .where(OrcamentoItemCusteioLinhaOperacao.linha_id == linha_id)
                .order_by(
                    OrcamentoItemCusteioLinhaOperacao.ordem.asc(),
                    OrcamentoItemCusteioLinhaOperacao.id.asc(),
                )
            )
        )

    def list_active(self, linha_id: int) -> list[OrcamentoItemCusteioLinhaOperacao]:
        return [row for row in self.list_all(linha_id) if row.ativo]

    def has_any(self, linha_id: int) -> bool:
        statement = (
            select(OrcamentoItemCusteioLinhaOperacao.id)
            .where(OrcamentoItemCusteioLinhaOperacao.linha_id == linha_id)
            .limit(1)
        )
        return self.session.scalar(statement) is not None

    def get_by_id(self, id: int) -> OrcamentoItemCusteioLinhaOperacao | None:
        return self.session.get(OrcamentoItemCusteioLinhaOperacao, id)

    def create(self, **fields) -> OrcamentoItemCusteioLinhaOperacao:
        row = OrcamentoItemCusteioLinhaOperacao(**fields)
        self.session.add(row)
        self.session.flush()
        return row

    def update(self, id: int, **fields) -> OrcamentoItemCusteioLinhaOperacao:
        row = self.get_by_id(id)
        if row is None:
            raise ValueError("Operação local não encontrada.")
        for field, value in fields.items():
            setattr(row, field, value)
        self.session.flush()
        return row

    def deactivate(self, id: int) -> bool:
        row = self.get_by_id(id)
        if row is None:
            return False
        row.ativo = False
        self.session.flush()
        return True

    def delete_by_linha(self, linha_id: int) -> int:
        result = self.session.execute(
            delete(OrcamentoItemCusteioLinhaOperacao).where(
                OrcamentoItemCusteioLinhaOperacao.linha_id == linha_id
            )
        )
        self.session.flush()
        return int(result.rowcount or 0)
