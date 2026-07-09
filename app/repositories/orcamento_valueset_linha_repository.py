"""Repository for budget version ValueSet lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select
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
    ref_le: str | None
    descricao_no_orcamento: str | None
    preco_tabela: Decimal | None
    margem_percentagem: Decimal | None
    desconto_percentagem: Decimal | None
    preco_liquido: Decimal | None
    unidade: str | None
    desperdicio_percentagem: Decimal | None
    tipo_materia_prima: str | None
    familia_materia_prima: str | None
    coresp_orla_0_4: str | None
    coresp_orla_1_0: str | None
    comp_mp: Decimal | None
    larg_mp: Decimal | None
    esp_mp: Decimal | None
    origem_dados: str | None
    origem_modelo_id: int | None
    origem_modelo_codigo: str | None
    editado_localmente: bool
    ativo: bool
    observacoes: str | None
    prioridade: int | None = None
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
        """Get the winning active option for one budget version and key.

        The active line with the lowest prioridade wins (NULL last, then id).
        """
        statement = (
            select(OrcamentoValuesetLinha)
            .where(
                OrcamentoValuesetLinha.orcamento_versao_id == orcamento_versao_id,
                OrcamentoValuesetLinha.chave == chave,
                OrcamentoValuesetLinha.ativo.is_(True),
            )
            .order_by(
                OrcamentoValuesetLinha.prioridade.is_(None),
                OrcamentoValuesetLinha.prioridade.asc(),
                OrcamentoValuesetLinha.id.asc(),
            )
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

    def delete_by_orcamento_versao(self, orcamento_versao_id: int) -> int:
        """Delete all ValueSet lines of one budget version."""
        result = self.session.execute(
            delete(OrcamentoValuesetLinha).where(
                OrcamentoValuesetLinha.orcamento_versao_id == orcamento_versao_id
            ).execution_options(synchronize_session=False)
        )
        self.session.flush()
        return int(result.rowcount or 0)

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
            prioridade=linha.prioridade,
            ordem=linha.ordem,
            descricao=linha.descricao,
            materia_prima_id=linha.materia_prima_id,
            ref_materia_prima=linha.ref_materia_prima,
            descricao_materia_prima=linha.descricao_materia_prima,
            valor_texto=linha.valor_texto,
            origem=linha.origem,
            ref_le=linha.ref_le,
            descricao_no_orcamento=linha.descricao_no_orcamento,
            preco_tabela=linha.preco_tabela,
            margem_percentagem=linha.margem_percentagem,
            desconto_percentagem=linha.desconto_percentagem,
            preco_liquido=linha.preco_liquido,
            unidade=linha.unidade,
            desperdicio_percentagem=linha.desperdicio_percentagem,
            tipo_materia_prima=linha.tipo_materia_prima,
            familia_materia_prima=linha.familia_materia_prima,
            coresp_orla_0_4=linha.coresp_orla_0_4,
            coresp_orla_1_0=linha.coresp_orla_1_0,
            comp_mp=linha.comp_mp,
            larg_mp=linha.larg_mp,
            esp_mp=linha.esp_mp,
            origem_dados=linha.origem_dados,
            origem_modelo_id=linha.origem_modelo_id,
            origem_modelo_codigo=linha.origem_modelo_codigo,
            editado_localmente=linha.editado_localmente,
            ativo=linha.ativo,
            observacoes=linha.observacoes,
            created_at=linha.created_at,
            updated_at=linha.updated_at,
        )
