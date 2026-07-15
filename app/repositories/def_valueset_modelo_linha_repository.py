"""Repository for reusable ValueSet model lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefValuesetModeloLinha


@dataclass(frozen=True)
class DefValuesetModeloLinhaResumo:
    """Read model for one reusable ValueSet model line."""

    id: int
    def_valueset_modelo_id: int
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
    editado_localmente: bool
    ativo: bool
    observacoes: str | None
    prioridade: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    preco_orla_0_4_m2: Decimal | None = None
    preco_orla_1_0_m2: Decimal | None = None


class DefValuesetModeloLinhaRepository:
    """Repository for DefValuesetModeloLinha operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DefValuesetModeloLinhaResumo]:
        """List all reusable ValueSet model lines."""
        statement = select(DefValuesetModeloLinha).order_by(DefValuesetModeloLinha.id.asc())
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_active(self) -> list[DefValuesetModeloLinhaResumo]:
        """List active reusable ValueSet model lines."""
        statement = (
            select(DefValuesetModeloLinha)
            .where(DefValuesetModeloLinha.ativo.is_(True))
            .order_by(DefValuesetModeloLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_by_modelo(self, modelo_id: int) -> list[DefValuesetModeloLinhaResumo]:
        """List lines of one reusable ValueSet model."""
        statement = (
            select(DefValuesetModeloLinha)
            .where(DefValuesetModeloLinha.def_valueset_modelo_id == modelo_id)
            .order_by(
                DefValuesetModeloLinha.chave.asc(),
                DefValuesetModeloLinha.ordem.asc(),
                DefValuesetModeloLinha.id.asc(),
            )
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_by_modelo_chave(
        self, modelo_id: int, chave: str
    ) -> list[DefValuesetModeloLinhaResumo]:
        """List all options for one model and key, ordered by ordem."""
        statement = (
            select(DefValuesetModeloLinha)
            .where(
                DefValuesetModeloLinha.def_valueset_modelo_id == modelo_id,
                DefValuesetModeloLinha.chave == chave,
            )
            .order_by(DefValuesetModeloLinha.ordem.asc(), DefValuesetModeloLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def get_by_id(self, id: int) -> DefValuesetModeloLinhaResumo | None:
        """Get one reusable ValueSet model line by id."""
        linha = self.session.get(DefValuesetModeloLinha, id)
        if linha is None:
            return None

        return self._to_resumo(linha)

    def get_by_modelo_chave(
        self, modelo_id: int, chave: str
    ) -> DefValuesetModeloLinhaResumo | None:
        """Get the first line for one model and key."""
        statement = (
            select(DefValuesetModeloLinha)
            .where(
                DefValuesetModeloLinha.def_valueset_modelo_id == modelo_id,
                DefValuesetModeloLinha.chave == chave,
            )
            .order_by(DefValuesetModeloLinha.ordem.asc(), DefValuesetModeloLinha.id.asc())
        )
        linha = self.session.execute(statement).scalars().first()
        if linha is None:
            return None

        return self._to_resumo(linha)

    def get_by_modelo_chave_opcao(
        self, modelo_id: int, chave: str, codigo_opcao: str
    ) -> DefValuesetModeloLinhaResumo | None:
        """Get one line by model, key and option code."""
        statement = select(DefValuesetModeloLinha).where(
            DefValuesetModeloLinha.def_valueset_modelo_id == modelo_id,
            DefValuesetModeloLinha.chave == chave,
            DefValuesetModeloLinha.codigo_opcao == codigo_opcao,
        )
        linha = self.session.execute(statement).scalars().first()
        if linha is None:
            return None

        return self._to_resumo(linha)

    def get_default_by_modelo_chave(
        self, modelo_id: int, chave: str
    ) -> DefValuesetModeloLinhaResumo | None:
        """Get the winning active option for one model and key.

        The active line with the lowest prioridade wins (NULL last, then id).
        """
        statement = (
            select(DefValuesetModeloLinha)
            .where(
                DefValuesetModeloLinha.def_valueset_modelo_id == modelo_id,
                DefValuesetModeloLinha.chave == chave,
                DefValuesetModeloLinha.ativo.is_(True),
            )
            .order_by(
                DefValuesetModeloLinha.prioridade.is_(None),
                DefValuesetModeloLinha.prioridade.asc(),
                DefValuesetModeloLinha.id.asc(),
            )
        )
        linha = self.session.execute(statement).scalars().first()
        if linha is None:
            return None

        return self._to_resumo(linha)

    def create(self, **fields) -> DefValuesetModeloLinhaResumo:
        """Create one reusable ValueSet model line."""
        linha = DefValuesetModeloLinha(**fields)
        self.session.add(linha)
        self.session.flush()

        return self._to_resumo(linha)

    def update(self, *, id: int, **fields) -> DefValuesetModeloLinhaResumo:
        """Update one reusable ValueSet model line."""
        linha = self.session.get(DefValuesetModeloLinha, id)
        if linha is None:
            raise ValueError("def_valueset_modelo_linha not found")

        for name, value in fields.items():
            setattr(linha, name, value)
        self.session.flush()

        return self._to_resumo(linha)

    def deactivate(self, id: int) -> bool:
        """Deactivate one reusable ValueSet model line."""
        linha = self.session.get(DefValuesetModeloLinha, id)
        if linha is None:
            return False

        linha.ativo = False
        self.session.flush()

        return True

    def activate(self, id: int) -> bool:
        """Reactivate one reusable ValueSet model line."""
        linha = self.session.get(DefValuesetModeloLinha, id)
        if linha is None:
            return False

        linha.ativo = True
        self.session.flush()

        return True

    def set_padrao(self, id: int, padrao: bool) -> bool:
        """Set the default flag on one line."""
        linha = self.session.get(DefValuesetModeloLinha, id)
        if linha is None:
            return False

        linha.padrao = padrao
        self.session.flush()

        return True

    def clear_padrao_for_chave(
        self, modelo_id: int, chave: str, exclude_id: int | None = None
    ) -> None:
        """Clear the default flag on the other options of one model and key."""
        statement = select(DefValuesetModeloLinha).where(
            DefValuesetModeloLinha.def_valueset_modelo_id == modelo_id,
            DefValuesetModeloLinha.chave == chave,
            DefValuesetModeloLinha.padrao.is_(True),
        )
        for linha in self.session.execute(statement).scalars().all():
            if exclude_id is not None and linha.id == exclude_id:
                continue
            linha.padrao = False
        self.session.flush()

    def _to_resumo(self, linha: DefValuesetModeloLinha) -> DefValuesetModeloLinhaResumo:
        """Convert an ORM line to the read model."""
        return DefValuesetModeloLinhaResumo(
            id=linha.id,
            def_valueset_modelo_id=linha.def_valueset_modelo_id,
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
            preco_orla_0_4_m2=linha.preco_orla_0_4_m2,
            preco_orla_1_0_m2=linha.preco_orla_1_0_m2,
            comp_mp=linha.comp_mp,
            larg_mp=linha.larg_mp,
            esp_mp=linha.esp_mp,
            origem_dados=linha.origem_dados,
            editado_localmente=linha.editado_localmente,
            ativo=linha.ativo,
            observacoes=linha.observacoes,
            created_at=linha.created_at,
            updated_at=linha.updated_at,
        )
