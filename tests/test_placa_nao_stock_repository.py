"""Tests for the board Não-Stock repository (phase 8W.2)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.consumos import chave_placa
from app.repositories.orcamento_versao_placa_nao_stock_repository import (
    OrcamentoVersaoPlacaNaoStockRepository,
)


def test_set_e_chaves_ativas(session) -> None:
    repo = OrcamentoVersaoPlacaNaoStockRepository(session)

    repo.set_estado(1, "LE01", "AGL 19mm", Decimal("19"), True)
    session.commit()

    assert repo.chaves_ativas(1) == {chave_placa("LE01", "AGL 19mm", Decimal("19"))}
    # esp matches regardless of trailing zeros (canonical key).
    assert chave_placa("LE01", "AGL 19mm", Decimal("19.0000")) in repo.chaves_ativas(1)


def test_unset_remove_a_chave(session) -> None:
    repo = OrcamentoVersaoPlacaNaoStockRepository(session)
    repo.set_estado(1, "LE01", "AGL", Decimal("19"), True)
    session.commit()
    assert repo.chaves_ativas(1)

    repo.set_estado(1, "LE01", "AGL", Decimal("19"), False)
    session.commit()

    assert repo.chaves_ativas(1) == set()
    assert repo.list_by_versao(1) == []


def test_isolado_por_versao(session) -> None:
    repo = OrcamentoVersaoPlacaNaoStockRepository(session)
    repo.set_estado(1, "LE01", "AGL", Decimal("19"), True)
    session.commit()

    assert repo.chaves_ativas(2) == set()


def test_desativar_nao_stock_preserva_suplemento_ativo(session) -> None:
    repo = OrcamentoVersaoPlacaNaoStockRepository(session)
    repo.set_estado(1, "LE01", "AGL", Decimal("19"), True)
    repo.set_suplemento(
        1,
        "LE01",
        "AGL",
        Decimal("19"),
        ativo=True,
        suplemento_ref_le="PLC0120",
        valor_base=Decimal("70"),
        valor_local=Decimal("75"),
        editado_localmente=True,
    )

    repo.set_estado(1, "LE01", "AGL", Decimal("19"), False)
    session.commit()

    rows = repo.list_by_versao(1)
    assert len(rows) == 1
    assert rows[0].nao_stock is False
    assert rows[0].suplemento_ativo is True
    assert rows[0].suplemento_valor_local == Decimal("75")
