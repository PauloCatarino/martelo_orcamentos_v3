"""Repository for budget item ValueSet lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OrcamentoItemValuesetLinha


@dataclass(frozen=True)
class OrcamentoItemValuesetLinhaResumo:
    """Read model for one budget item ValueSet line."""

    id: int
    orcamento_item_id: int
    chave: str
    codigo_opcao: str | None
    nome_opcao: str | None
    padrao: bool
    ordem: int
    descricao: str | None
    materia_prima_id: int | None
    ref_materia_prima: str | None
    descricao_materia_prima: str | None
    valor_texto: str | None
    origem: str | None
    herdado_do_orcamento: bool
    editado_localmente: bool
    ativo: bool
    observacoes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrcamentoItemValuesetLinhaRepository:
    """Repository for OrcamentoItemValuesetLinha operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[OrcamentoItemValuesetLinhaResumo]:
        """List all budget item ValueSet lines."""
        statement = select(OrcamentoItemValuesetLinha).order_by(
            OrcamentoItemValuesetLinha.id.asc()
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_active(self) -> list[OrcamentoItemValuesetLinhaResumo]:
        """List active budget item ValueSet lines."""
        statement = (
            select(OrcamentoItemValuesetLinha)
            .where(OrcamentoItemValuesetLinha.ativo.is_(True))
            .order_by(OrcamentoItemValuesetLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_by_orcamento_item(
        self, orcamento_item_id: int
    ) -> list[OrcamentoItemValuesetLinhaResumo]:
        """List ValueSet lines of one budget item."""
        statement = (
            select(OrcamentoItemValuesetLinha)
            .where(OrcamentoItemValuesetLinha.orcamento_item_id == orcamento_item_id)
            .order_by(
                OrcamentoItemValuesetLinha.chave.asc(),
                OrcamentoItemValuesetLinha.ordem.asc(),
                OrcamentoItemValuesetLinha.id.asc(),
            )
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_by_item_chave(
        self, orcamento_item_id: int, chave: str
    ) -> list[OrcamentoItemValuesetLinhaResumo]:
        """List all options for one budget item and key, ordered by ordem."""
        statement = (
            select(OrcamentoItemValuesetLinha)
            .where(
                OrcamentoItemValuesetLinha.orcamento_item_id == orcamento_item_id,
                OrcamentoItemValuesetLinha.chave == chave,
            )
            .order_by(OrcamentoItemValuesetLinha.ordem.asc(), OrcamentoItemValuesetLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def get_by_id(self, id: int) -> OrcamentoItemValuesetLinhaResumo | None:
        """Get one budget item ValueSet line by id."""
        linha = self.session.get(OrcamentoItemValuesetLinha, id)
        if linha is None:
            return None

        return self._to_resumo(linha)

    def get_by_item_chave(
        self, orcamento_item_id: int, chave: str
    ) -> OrcamentoItemValuesetLinhaResumo | None:
        """Get the first line for one budget item and key."""
        statement = (
            select(OrcamentoItemValuesetLinha)
            .where(
                OrcamentoItemValuesetLinha.orcamento_item_id == orcamento_item_id,
                OrcamentoItemValuesetLinha.chave == chave,
            )
            .order_by(OrcamentoItemValuesetLinha.ordem.asc(), OrcamentoItemValuesetLinha.id.asc())
        )
        linha = self.session.execute(statement).scalars().first()
        if linha is None:
            return None

        return self._to_resumo(linha)

    def get_by_item_chave_opcao(
        self, orcamento_item_id: int, chave: str, codigo_opcao: str
    ) -> OrcamentoItemValuesetLinhaResumo | None:
        """Get one line by budget item, key and option code."""
        statement = select(OrcamentoItemValuesetLinha).where(
            OrcamentoItemValuesetLinha.orcamento_item_id == orcamento_item_id,
            OrcamentoItemValuesetLinha.chave == chave,
            OrcamentoItemValuesetLinha.codigo_opcao == codigo_opcao,
        )
        linha = self.session.execute(statement).scalars().first()
        if linha is None:
            return None

        return self._to_resumo(linha)

    def get_default_by_item_chave(
        self, orcamento_item_id: int, chave: str
    ) -> OrcamentoItemValuesetLinhaResumo | None:
        """Get the active default option for one budget item and key."""
        statement = (
            select(OrcamentoItemValuesetLinha)
            .where(
                OrcamentoItemValuesetLinha.orcamento_item_id == orcamento_item_id,
                OrcamentoItemValuesetLinha.chave == chave,
                OrcamentoItemValuesetLinha.padrao.is_(True),
                OrcamentoItemValuesetLinha.ativo.is_(True),
            )
            .order_by(OrcamentoItemValuesetLinha.ordem.asc(), OrcamentoItemValuesetLinha.id.asc())
        )
        linha = self.session.execute(statement).scalars().first()
        if linha is None:
            return None

        return self._to_resumo(linha)

    def create(self, **fields) -> OrcamentoItemValuesetLinhaResumo:
        """Create one budget item ValueSet line."""
        linha = OrcamentoItemValuesetLinha(**fields)
        self.session.add(linha)
        self.session.flush()

        return self._to_resumo(linha)

    def update(self, *, id: int, **fields) -> OrcamentoItemValuesetLinhaResumo:
        """Update one budget item ValueSet line."""
        linha = self.session.get(OrcamentoItemValuesetLinha, id)
        if linha is None:
            raise ValueError("orcamento_item_valueset_linha not found")

        for name, value in fields.items():
            setattr(linha, name, value)
        self.session.flush()

        return self._to_resumo(linha)

    def deactivate(self, id: int) -> bool:
        """Deactivate one budget item ValueSet line."""
        linha = self.session.get(OrcamentoItemValuesetLinha, id)
        if linha is None:
            return False

        linha.ativo = False
        self.session.flush()

        return True

    def activate(self, id: int) -> bool:
        """Reactivate one budget item ValueSet line."""
        linha = self.session.get(OrcamentoItemValuesetLinha, id)
        if linha is None:
            return False

        linha.ativo = True
        self.session.flush()

        return True

    def set_padrao(self, id: int, padrao: bool) -> bool:
        """Set the default flag on one line."""
        linha = self.session.get(OrcamentoItemValuesetLinha, id)
        if linha is None:
            return False

        linha.padrao = padrao
        self.session.flush()

        return True

    def clear_padrao_for_chave(
        self, orcamento_item_id: int, chave: str, exclude_id: int | None = None
    ) -> None:
        """Clear the default flag on the other options of one item and key."""
        statement = select(OrcamentoItemValuesetLinha).where(
            OrcamentoItemValuesetLinha.orcamento_item_id == orcamento_item_id,
            OrcamentoItemValuesetLinha.chave == chave,
            OrcamentoItemValuesetLinha.padrao.is_(True),
        )
        for linha in self.session.execute(statement).scalars().all():
            if exclude_id is not None and linha.id == exclude_id:
                continue
            linha.padrao = False
        self.session.flush()

    def _to_resumo(self, linha: OrcamentoItemValuesetLinha) -> OrcamentoItemValuesetLinhaResumo:
        """Convert an ORM line to the read model."""
        return OrcamentoItemValuesetLinhaResumo(
            id=linha.id,
            orcamento_item_id=linha.orcamento_item_id,
            chave=linha.chave,
            codigo_opcao=linha.codigo_opcao,
            nome_opcao=linha.nome_opcao,
            padrao=linha.padrao,
            ordem=linha.ordem,
            descricao=linha.descricao,
            materia_prima_id=linha.materia_prima_id,
            ref_materia_prima=linha.ref_materia_prima,
            descricao_materia_prima=linha.descricao_materia_prima,
            valor_texto=linha.valor_texto,
            origem=linha.origem,
            herdado_do_orcamento=linha.herdado_do_orcamento,
            editado_localmente=linha.editado_localmente,
            ativo=linha.ativo,
            observacoes=linha.observacoes,
            created_at=linha.created_at,
            updated_at=linha.updated_at,
        )
