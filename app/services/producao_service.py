"""Read-only service helpers for production processes."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.producao import Producao

CAMPOS_EDITAVEIS_PRODUCAO = (
    "estado",
    "responsavel",
    "ref_cliente",
    "obra",
    "localizacao",
    "data_inicio",
    "data_entrega",
    "tipo_pasta",
    "descricao_artigos",
    "materias_usados",
    "descricao_producao",
    "notas1",
    "notas2",
    "notas3",
)

_CAMPOS_PESQUISA = (
    "codigo_processo",
    "num_enc_phc",
    "nome_cliente",
    "nome_cliente_simplex",
    "ref_cliente",
    "obra",
    "localizacao",
    "num_orcamento",
    "responsavel",
    "descricao_producao",
)


class ProducaoService:
    """Application service for production workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def listar_processos(self) -> list[Producao]:
        """List production processes ordered for the production page."""
        statement = select(Producao).order_by(
            Producao.ano.desc(),
            Producao.codigo_processo.asc(),
        )
        return list(self.session.scalars(statement).all())

    def obter_processo(self, proc_id: int) -> Producao | None:
        """Return one production process by id."""
        return self.session.get(Producao, proc_id)

    def atualizar_processo(
        self,
        proc_id: int,
        data: dict,
        *,
        updated_by_id: int | None,
    ) -> Producao:
        """Update only editable production fields and commit the change."""
        processo = self.obter_processo(proc_id)
        if processo is None:
            raise ValueError("Processo de producao nao encontrado.")

        for campo, valor in campos_editaveis(data).items():
            setattr(processo, campo, valor)
        processo.updated_by_id = updated_by_id

        self.session.commit()
        self.session.refresh(processo)
        return processo


def campos_editaveis(data: dict) -> dict:
    """Return only fields that are editable in the production detail form."""
    return {
        campo: data[campo]
        for campo in CAMPOS_EDITAVEIS_PRODUCAO
        if campo in data
    }


def filtrar_processos(
    todos,
    *,
    texto="",
    estado=None,
    cliente=None,
    responsavel=None,
) -> list[Producao]:
    """Filter production processes in memory, case-insensitively."""
    termos = [
        termo
        for termo in re.split(r"[\s%]+", (texto or "").strip().lower())
        if termo
    ]
    estado_norm = _normalizar_filtro(estado)
    cliente_norm = _normalizar_filtro(cliente)
    responsavel_norm = _normalizar_filtro(responsavel)

    resultado = []
    for processo in todos or []:
        if estado_norm and _texto(getattr(processo, "estado", None)) != estado_norm:
            continue
        if (
            cliente_norm
            and _texto(getattr(processo, "nome_cliente", None)) != cliente_norm
        ):
            continue
        if (
            responsavel_norm
            and _texto(getattr(processo, "responsavel", None)) != responsavel_norm
        ):
            continue

        haystack = " ".join(
            _texto(getattr(processo, campo, None)) for campo in _CAMPOS_PESQUISA
        )
        if all(termo in haystack for termo in termos):
            resultado.append(processo)

    return resultado


def _normalizar_filtro(valor) -> str | None:
    texto = _texto(valor)
    if not texto or texto == "todos":
        return None
    return texto


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip().lower()
