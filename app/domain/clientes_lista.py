"""Pure helpers for the customers list page."""

from __future__ import annotations

import re

_CAMPOS_PESQUISA = (
    "nome",
    "nome_simplex",
    "morada",
    "email",
    "pagina_web",
    "telefone",
    "telemovel",
    "num_cliente_phc",
    "info_1",
    "info_2",
)


def filtrar_clientes(clientes, texto=""):
    """Filter customers by multiple case-insensitive terms."""
    termos = [
        termo
        for termo in re.split(r"[\s%]+", (texto or "").strip().lower())
        if termo
    ]
    if not termos:
        return list(clientes or [])

    resultado = []
    for cliente in clientes or []:
        haystack = " ".join(
            _texto(getattr(cliente, campo, None)) for campo in _CAMPOS_PESQUISA
        )
        if all(termo in haystack for termo in termos):
            resultado.append(cliente)

    return resultado


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip().lower()
