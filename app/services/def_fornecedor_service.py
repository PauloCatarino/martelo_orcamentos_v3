"""Service for supplier workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.def_fornecedor_repository import (
    DefFornecedorRepository,
    DefFornecedorResumo,
)


@dataclass(frozen=True)
class FornecedorData:
    """Input data for creating or editing a supplier."""

    nome: str
    email: str | None = None
    email_cc: str | None = None
    pessoa_contacto: str | None = None
    telefone: str | None = None
    observacoes: str | None = None
    ativo: bool = True


class DefFornecedorService:
    """Application service for supplier workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefFornecedorRepository(session)

    def listar_fornecedores(
        self, incluir_inativos: bool = True
    ) -> list[DefFornecedorResumo]:
        """List suppliers, with how many raw materials each one supplies."""
        return self.repository.list_all(incluir_inativos)

    def obter_por_id(self, id: int) -> DefFornecedorResumo | None:
        """Get one supplier by id."""
        return self.repository.get_by_id(id)

    def criar_fornecedor(self, data: FornecedorData) -> DefFornecedorResumo:
        """Create a supplier."""
        nome = self._normalizar_nome(data.nome)
        self._validar_nome_unico(nome, excluir_id=None)

        resultado = self.repository.create_fornecedor(
            nome=nome,
            email=self._texto(data.email),
            email_cc=self._texto(data.email_cc),
            pessoa_contacto=self._texto(data.pessoa_contacto),
            telefone=self._texto(data.telefone),
            observacoes=self._texto(data.observacoes),
            ativo=data.ativo,
        )
        self.session.commit()

        return resultado

    def editar_fornecedor(self, id: int, data: FornecedorData) -> DefFornecedorResumo:
        """Edit a supplier."""
        nome = self._normalizar_nome(data.nome)
        self._validar_nome_unico(nome, excluir_id=id)

        resultado = self.repository.update_fornecedor(
            id=id,
            nome=nome,
            email=self._texto(data.email),
            email_cc=self._texto(data.email_cc),
            pessoa_contacto=self._texto(data.pessoa_contacto),
            telefone=self._texto(data.telefone),
            observacoes=self._texto(data.observacoes),
            ativo=data.ativo,
        )
        self.session.commit()

        return resultado

    def fornecedores_sem_email(self) -> list[DefFornecedorResumo]:
        """Suppliers that supply something but a quem não se consegue escrever."""
        return [
            fornecedor
            for fornecedor in self.repository.list_all(incluir_inativos=False)
            if fornecedor.materias_primas and not fornecedor.tem_email
        ]

    def _normalizar_nome(self, nome: str | None) -> str:
        normalizado = (nome or "").strip()
        if not normalizado:
            raise ValueError("O nome do fornecedor é obrigatório.")

        return normalizado

    def _validar_nome_unico(self, nome: str, excluir_id: int | None) -> None:
        existente = self.repository.get_by_nome(nome)
        if existente is not None and existente.id != excluir_id:
            raise ValueError(f"Já existe um fornecedor com o nome «{nome}».")

    def _texto(self, valor: str | None) -> str | None:
        texto = (valor or "").strip()
        return texto or None
