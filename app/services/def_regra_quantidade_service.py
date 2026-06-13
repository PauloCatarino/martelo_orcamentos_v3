"""Service for configurable quantity-rule workflows (phase 8T.5.0).

Stores and validates the rules. The expression is validated on save by
evaluating it against a sample context (COMP=2000, LARG=600, ESP=19, QT_PAI=1);
invalid expressions are rejected with a friendly message. Wiring to
components/costing comes later (8T.5.1).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.regras_quantidade_expr import (
    CONTEXTO_EXEMPLO,
    avaliar_regra_quantidade,
)
from app.repositories.def_regra_quantidade_repository import (
    DefRegraQuantidadeRepository,
    DefRegraQuantidadeResumo,
)


@dataclass(frozen=True)
class CriarRegraQuantidadeData:
    """Input data for creating a quantity rule."""

    codigo: str
    nome: str
    expressao: str
    descricao: str | None = None
    ativo: bool = True


@dataclass(frozen=True)
class EditarRegraQuantidadeData:
    """Input data for editing a quantity rule (code is fixed)."""

    nome: str
    expressao: str
    descricao: str | None = None


class DefRegraQuantidadeService:
    """Application service for DefRegraQuantidade workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefRegraQuantidadeRepository(session)

    def listar(self) -> list[DefRegraQuantidadeResumo]:
        """List every quantity rule."""
        return self.repository.list_all()

    def listar_ativas(self) -> list[DefRegraQuantidadeResumo]:
        """List the active quantity rules."""
        return self.repository.list_ativas()

    def obter(self, id: int) -> DefRegraQuantidadeResumo | None:
        """Get one rule by id."""
        return self.repository.get_by_id(id)

    def testar_expressao(
        self, expressao: str, contexto: dict | None = None
    ) -> tuple[int | None, str | None]:
        """Evaluate an expression (sample context by default) for the UI tester."""
        return avaliar_regra_quantidade(
            expressao, contexto if contexto is not None else CONTEXTO_EXEMPLO
        )

    def criar(self, data: CriarRegraQuantidadeData) -> DefRegraQuantidadeResumo:
        """Create a rule after validating its code and expression."""
        codigo = self._validar_codigo(data.codigo)
        nome = self._validar_nome(data.nome)
        expressao = self._validar_expressao(data.expressao)

        if self.repository.get_by_codigo(codigo) is not None:
            raise ValueError(f"Já existe uma regra com o código {codigo}.")

        result = self.repository.create_regra(
            codigo=codigo,
            nome=nome,
            expressao=expressao,
            descricao=self._normalizar_descricao(data.descricao),
            ativo=data.ativo,
        )
        self.session.commit()

        return result

    def editar(
        self, id: int, data: EditarRegraQuantidadeData
    ) -> DefRegraQuantidadeResumo:
        """Edit a rule's name/expression/description after validating them."""
        nome = self._validar_nome(data.nome)
        expressao = self._validar_expressao(data.expressao)

        result = self.repository.update_regra(
            id=id,
            nome=nome,
            expressao=expressao,
            descricao=self._normalizar_descricao(data.descricao),
        )
        self.session.commit()

        return result

    def definir_ativo(self, id: int, ativo: bool) -> DefRegraQuantidadeResumo:
        """Activate/deactivate one rule."""
        result = self.repository.set_ativo(id, ativo)
        self.session.commit()

        return result

    def _validar_codigo(self, codigo: str) -> str:
        """Normalize and require a non-empty code (uppercase, no spaces)."""
        normalizado = (codigo or "").strip().upper().replace(" ", "_")
        if not normalizado:
            raise ValueError("O código da regra é obrigatório.")

        return normalizado

    def _validar_nome(self, nome: str) -> str:
        """Require a non-empty name."""
        normalizado = (nome or "").strip()
        if not normalizado:
            raise ValueError("O nome da regra é obrigatório.")

        return normalizado

    def _validar_expressao(self, expressao: str) -> str:
        """Require a valid expression (tested against the sample context)."""
        normalizada = (expressao or "").strip()
        if not normalizada:
            raise ValueError("A expressão da regra é obrigatória.")

        _quantidade, motivo = avaliar_regra_quantidade(normalizada, CONTEXTO_EXEMPLO)
        if motivo is not None:
            raise ValueError(f"Expressão inválida: {motivo}")

        return normalizada

    @staticmethod
    def _normalizar_descricao(descricao: str | None) -> str | None:
        """Trim the description; empty becomes None."""
        if descricao is None:
            return None

        texto = descricao.strip()
        return texto or None
