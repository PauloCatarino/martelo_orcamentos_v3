"""Pure helpers for ValueSet price synchronization."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


TOLERANCIA_PRECO = Decimal("0.05")


@dataclass(frozen=True)
class DivergenciaPreco:
    """Detected table-price difference between a ValueSet line and material catalog."""

    linha_id: int
    chave: str
    codigo_opcao: str | None
    nome_opcao: str | None
    ref_le: str | None
    preco_tabela_antigo: Decimal | None
    preco_tabela_atual: Decimal
    margem_percentagem: Decimal | None
    desconto_percentagem: Decimal | None
    preco_liquido_novo: Decimal


ResolverMateria = Callable[[int | None, str | None], Any | None]


def calcular_preco_liquido(
    preco_tabela: Decimal | None,
    margem_pct: Decimal | None,
    desconto_pct: Decimal | None,
) -> Decimal | None:
    """Calculate liquid price from table price, discount and margin percentages."""
    if preco_tabela is None:
        return None

    desconto_factor = Decimal("1") - (desconto_pct or Decimal("0")) / Decimal("100")
    margem_factor = Decimal("1") + (margem_pct or Decimal("0")) / Decimal("100")
    return preco_tabela * desconto_factor * margem_factor


def detetar_divergencias(
    linhas: Iterable[Any],
    resolver_materia: ResolverMateria,
    tolerancia: Decimal = TOLERANCIA_PRECO,
) -> list[DivergenciaPreco]:
    """Detect table-price differences between ValueSet lines and raw materials.

    The resolver receives ``(materia_prima_id, ref_le)`` and may return any
    object with a ``preco_tabela`` attribute. Lines without material id and
    without Ref LE are intentionally ignored.
    """
    divergencias: list[DivergenciaPreco] = []

    for linha in linhas:
        materia_prima_id = getattr(linha, "materia_prima_id", None)
        ref_le = _texto_ou_none(getattr(linha, "ref_le", None))
        if materia_prima_id is None and ref_le is None:
            continue

        materia = resolver_materia(materia_prima_id, ref_le)
        if materia is None:
            continue

        preco_atual = getattr(materia, "preco_tabela", None)
        if preco_atual is None:
            continue

        preco_antigo = getattr(linha, "preco_tabela", None)
        if (
            preco_antigo is not None
            and abs(preco_antigo - preco_atual) <= tolerancia
        ):
            continue

        margem = getattr(linha, "margem_percentagem", None)
        desconto = getattr(linha, "desconto_percentagem", None)
        preco_liquido_novo = calcular_preco_liquido(preco_atual, margem, desconto)
        if preco_liquido_novo is None:
            continue

        divergencias.append(
            DivergenciaPreco(
                linha_id=getattr(linha, "id"),
                chave=getattr(linha, "chave"),
                codigo_opcao=getattr(linha, "codigo_opcao", None),
                nome_opcao=getattr(linha, "nome_opcao", None),
                ref_le=ref_le,
                preco_tabela_antigo=preco_antigo,
                preco_tabela_atual=preco_atual,
                margem_percentagem=margem,
                desconto_percentagem=desconto,
                preco_liquido_novo=preco_liquido_novo,
            )
        )

    return divergencias


def _texto_ou_none(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None
