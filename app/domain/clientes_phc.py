"""Pure mapping of PHC dbo.CL rows to Martelo customer data (phase 10.5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.export_paths import simplificar_cliente


@dataclass(frozen=True)
class DadosClientePHC:
    """Normalized data for one PHC customer (from dbo.CL)."""

    num_cliente_phc: str
    nome: str
    nome_simplex: str
    morada: str | None
    email: str | None
    pagina_web: str | None
    telefone: str | None
    telemovel: str | None
    info_1: str | None


def normalizar_linha_phc(row: dict[str, Any]) -> DadosClientePHC | None:
    """Map one dbo.CL row to DadosClientePHC, or None when NO/NOME are missing."""
    num = _texto(row.get("Num_PHC"))
    nome = _texto(row.get("Nome"))
    if not num or not nome:
        return None

    return DadosClientePHC(
        num_cliente_phc=num,
        nome=nome,
        nome_simplex=simplificar_cliente(_ou_none(row.get("Simplex")), nome),
        morada=_ou_none(row.get("Morada")),
        email=_ou_none(row.get("Email")),
        pagina_web=_ou_none(row.get("WEB")),
        telefone=_ou_none(row.get("Telefone")),
        telemovel=_ou_none(row.get("Telemovel")),
        info_1=_ou_none(row.get("Info_1")),
    )


def _texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def _ou_none(valor: Any) -> str | None:
    texto = _texto(valor)
    return texto or None
