"""Service for temporary customers."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.export_paths import simplificar_cliente
from app.repositories.cliente_repository import ClienteListaResumo, ClienteRepository


@dataclass(frozen=True)
class DadosClienteTemporario:
    """Input data for creating/editing a temporary customer."""

    nome: str
    nome_simplex: str | None = None
    morada: str | None = None
    email: str | None = None
    pagina_web: str | None = None
    telefone: str | None = None
    telemovel: str | None = None
    num_cliente_phc: str | None = None
    info_1: str | None = None
    info_2: str | None = None


class ClienteEmUsoError(ValueError):
    """Raised when a temporary customer cannot be deleted because it is used."""

    def __init__(self, num_orcamentos: int) -> None:
        self.num_orcamentos = num_orcamentos
        super().__init__(
            f"Cliente associado a {num_orcamentos} orcamento(s); nao pode ser eliminado."
        )


class ClienteTemporarioService:
    """Create/edit/delete temporary customers."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ClienteRepository(session)

    def criar(self, data: DadosClienteTemporario) -> ClienteListaResumo:
        """Create a temporary customer."""
        campos = self._normalizar(data)
        resumo = self.repository.criar(**campos)
        self.session.commit()
        return resumo

    def editar(self, id: int, data: DadosClienteTemporario) -> ClienteListaResumo:
        """Edit a temporary customer."""
        campos = self._normalizar(data)
        resumo = self.repository.atualizar(id=id, **campos)
        self.session.commit()
        return resumo

    def eliminar(self, id: int) -> None:
        """Delete a temporary customer when it is not used by budgets."""
        num_orcamentos = self.repository.contar_orcamentos(id)
        if num_orcamentos > 0:
            raise ClienteEmUsoError(num_orcamentos)

        self.repository.eliminar(id)
        self.session.commit()

    @staticmethod
    def _normalizar(data: DadosClienteTemporario) -> dict:
        nome = (data.nome or "").strip()
        if not nome:
            raise ValueError("Indique o nome do cliente.")

        return {
            "nome": nome,
            "nome_simplex": simplificar_cliente(data.nome_simplex, nome),
            "morada": _limpo(data.morada),
            "email": _limpo(data.email),
            "pagina_web": _limpo(data.pagina_web),
            "telefone": _limpo(data.telefone),
            "telemovel": _limpo(data.telemovel),
            "num_cliente_phc": _limpo(data.num_cliente_phc),
            "info_1": _limpo(data.info_1),
            "info_2": _limpo(data.info_2),
        }


def _limpo(valor: str | None) -> str | None:
    texto = (valor or "").strip()
    return texto or None
