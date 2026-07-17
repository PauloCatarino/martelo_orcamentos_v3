"""Pure helpers for the budget list page."""

from __future__ import annotations

import re
from decimal import Decimal

_CAMPOS_PESQUISA = (
    "num_orcamento",
    "cliente_nome",
    "ref_cliente",
    "obra",
    "localizacao",
    "descricao",
    "estado",
    "utilizador",
    "enc_phc",
    "enc_phc_todos",
    "info_1",
    "info_2",
)


def resumo_lista(orcamentos):
    """Return (count, total_price), ignoring missing prices in the total."""
    total = Decimal("0")
    contagem = 0
    for orcamento in orcamentos or []:
        contagem += 1
        preco = getattr(orcamento, "preco_total", None)
        if preco is not None:
            total += preco

    return contagem, total


def filtrar_orcamentos(
    orcamentos,
    texto="",
    estado=None,
    cliente=None,
    utilizador=None,
):
    """Filter budget read models in memory, case-insensitively."""
    termos = [
        termo
        for termo in re.split(r"[\s%]+", (texto or "").strip().lower())
        if termo
    ]
    estado_norm = _normalizar_filtro(estado)
    cliente_norm = _normalizar_filtro(cliente)
    utilizador_norm = _normalizar_filtro(utilizador)

    resultado = []
    for orcamento in orcamentos or []:
        if estado_norm and _texto(getattr(orcamento, "estado", None)) != estado_norm:
            continue
        if (
            cliente_norm
            and _texto(getattr(orcamento, "cliente_nome", None)) != cliente_norm
        ):
            continue
        if (
            utilizador_norm
            and _texto(getattr(orcamento, "utilizador", None)) != utilizador_norm
        ):
            continue

        haystack = " ".join(
            _texto(getattr(orcamento, campo, None)) for campo in _CAMPOS_PESQUISA
        )
        if all(termo in haystack for termo in termos):
            resultado.append(orcamento)

    return resultado


def _normalizar_filtro(valor) -> str | None:
    texto = _texto(valor)
    if not texto or texto == "todos":
        return None
    return texto


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip().lower()
