"""Repository for budget version ValueSet lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OrcamentoValuesetLinha


@dataclass(frozen=True)
class OrcamentoValuesetLinhaResumo:
    """Read model for one budget version ValueSet line."""

    id: int
    orcamento_versao_id: int
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
    editado_localmente: bool
    ativo: bool
    observacoes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrcamentoValuesetLinhaRepository:
    """Repository for OrcamentoValuesetLinha operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[OrcamentoValuesetLinhaResumo]:
        """List all budget version ValueSet lines."""
        statement = select(OrcamentoValuesetLinha).order_by(OrcamentoValuesetLinha.id.asc())
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_active(self) -> list[OrcamentoValuesetLinhaResumo]:
        """List active budget version ValueSet lines."""
        statement = (
            select(OrcamentoValuesetLinha)
            .where(OrcamentoValuesetLinha.ativo.is_(True))
            .order_by(OrcamentoValuesetLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_by_orcamento_versao(
        self, orcamento_versao_id: int
    ) -> list[OrcamentoValuesetLinhaResumo]:
        """List ValueSet lines of one budget version."""
        statement = (
            select(OrcamentoValuesetLinha)
            .where(OrcamentoValuesetLinha.orcamento_versao_id == orcamento_versao_id)
            .order_by(
                OrcamentoValuesetLinha.chave.asc(),
                OrcamentoValuesetLinha.ordem.asc(),
                OrcamentoValuesetLinha.id.asc(),
            )
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_by_versao_chave(
        self, orcamento_versao_id: int, chave: str
    ) -> list[OrcamentoValuesetLinhaResumo]:
        """List all options for one budget version and key, ordered by ordem."""
        statement = (
            select(OrcamentoValuesetLinha)
            .where(
                OrcamentoValuesetLinha.orcamento_versao_id == orcamento_versao_id,
                OrcamentoValuesetLinha.chave == chave,
            )
            .order_by(OrcamentoValuesetLinha.ordem.asc(), OrcamentoValuesetLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def get_by_id(self, id: int) -> OrcamentoValuesetLinhaResumo | None:
        """Get one budget version ValueSet line by id."""
        linha = self.session.get(OrcamentoValuesetLinha, id)
        if linha is None:
            return None

        return self._to_resumo(linha)

    def get_by_versao_chave(
        self, orcamento_versao_id: int, chave: str
    ) -> OrcamentoValuesetLinhaResumo | None:
        """Get the first line for one budget version and key."""
        statement = (
            select(OrcamentoValuesetLinha)
            .where(
                OrcamentoValuesetLinha.orcamento_versao_id == orcamento_versao_id,
                OrcamentoValuesetLinha.chave == chave,
            )
            .order_by(OrcamentoValuesetLinha.ordem.asc(), OrcamentoValuesetLinha.id.asc())
        )
        linha = self.session.execute(statement).scalars().first()
        if linha is None:
            return None

        return self._to_resumo(linha)

    def get_by_versao_chave_opcao(
        self, orcamento_versao_id: int, chave: str, codigo_opcao: str
    ) -> OrcamentoValuesetLinhaResumo | None:
        """Get one line by budget version, key and option code."""
        statement = select(OrcamentoValuesetLinha).where(
            OrcamentoValuesetLinha.orcamento_versao_id == orcamento_versao_id,
            OrcamentoValuesetLinha.chave == chave,
            OrcamentoValuesetLinha.codigo_opcao == codigo_opcao,
        )
        linha = self.session.execute(statement).scalars().first()
        if linha is None:
            return None

        return self._to_resumo(linha)

    def get_default_by_versao_chave(
        self, orcamento_versao_id: int, chave: str
    ) -> OrcamentoValuesetLinhaResumo | None:
        """Get the active default option for one budget version and key."""
        statement = (
            select(OrcamentoValuesetLinha)
            .where(
                OrcamentoValuesetLinha.orcamento_versao_id == orcamento_versao_id,
                OrcamentoValuesetLinha.chave == chave,
                OrcamentoValuesetLinha.padrao.is_(True),
                OrcamentoValuesetLinha.ativo.is_(True),
            )
            .order_by(OrcamentoValuesetLinha.ordem.asc(), OrcamentoValuesetLinha.id.asc())
        )
        linha = self.session.execute(statement).scalars().first()
        if linha is None:
            return None

        return self._to_resumo(linha)

    def create(self, **fields) -> OrcamentoValuesetLinhaResumo:
        """Create one budget version ValueSet line."""
        linha = OrcamentoValuesetLinha(**fields)
        self.session.add(linha)
        self.session.flush()

        return self._to_resumo(linha)

    def update(self, *, id: int, **fields) -> OrcamentoValuesetLinhaResumo:
        """Update one budget version ValueSet line."""
        linha = self.session.get(OrcamentoValuesetLinha, id)
        if linha is None:
            raise ValueError("orcamento_valueset_linha not found")

        for name, value in fields.items():
            setattr(linha, name, value)
        self.session.flush()

        return self._to_resumo(linha)

    def deactivate(self, id: int) -> bool:
        """Deactivate one budget version ValueSet line."""
        linha = self.session.get(OrcamentoValuesetLinha, id)
        if linha is None:
            return False

        linha.ativo = False
        self.session.flush()

        return True

    def activate(self, id: int) -> bool:
        """Reactivate one budget version ValueSet line."""
        linha = self.session.get(OrcamentoValuesetLinha, id)
        if linha is None:
            return False

        linha.ativo = True
        self.session.flush()

        return True

    def set_padrao(self, id: int, padrao: bool) -> bool:
        """Set the default flag on one line."""
        linha = self.session.get(OrcamentoValuesetLinha, id)
        if linha is None:
            return False

        linha.padrao = padrao
        self.session.flush()

        return True

    def clear_padrao_for_chave(
        self, orcamento_versao_id: int, chave: str, exclude_id: int | None = None
    ) -> None:
        """Clear the default flag on the other options of one version and key."""
        statement = select(OrcamentoValuesetLinha).where(
            OrcamentoValuesetLinha.orcamento_versao_id == orcamento_versao_id,
            OrcamentoValuesetLinha.chave == chave,
            OrcamentoValuesetLinha.padrao.is_(True),
        )
        for linha in self.session.execute(statement).scalars().all():
            if exclude_id is not None and linha.id == exclude_id:
                continue
            linha.padrao = False
        self.session.flush()

    def _to_resumo(self, linha: OrcamentoValuesetLinha) -> OrcamentoValuesetLinhaResumo:
        """Convert an ORM line to the read model."""
        return OrcamentoValuesetLinhaResumo(
            id=linha.id,
            orcamento_versao_id=linha.orcamento_versao_id,
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
            editado_localmente=linha.editado_localmente,
            ativo=linha.ativo,
            observacoes=linha.observacoes,
            created_at=linha.created_at,
            updated_at=linha.updated_at,
        )
