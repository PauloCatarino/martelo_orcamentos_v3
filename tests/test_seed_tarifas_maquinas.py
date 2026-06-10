"""Tests for the idempotent machine-tariffs seed (phase 8S.0)."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from scripts.seed_tarifas_maquinas import aplicar_tarifas


def _maquina(id, **kwargs):
    base = {
        "id": id,
        "custo_hora": None,
        "custo_hora_serie": None,
        "preco_ml_std": None,
        "preco_ml_serie": None,
        "custo_setup_peca_std": None,
        "custo_setup_peca_serie": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _cenario():
    maquinas = {
        "CORTE": _maquina(1),
        "ORLAGEM": _maquina(2),
        "CNC_VERTICAL": _maquina(3),
        "MONTAGEM": _maquina(4, custo_hora=Decimal("20")),
        "MANUAL": _maquina(5, custo_hora=Decimal("15")),
    }
    escaloes_ids: set[int] = set()
    adicionados: list[tuple] = []

    def tem_escaloes(maquina_id: int) -> bool:
        return maquina_id in escaloes_ids

    def adicionar(maquina_id, nivel, area, std, serie) -> None:
        adicionados.append((maquina_id, nivel, area, std, serie))
        escaloes_ids.add(maquina_id)

    return maquinas, tem_escaloes, adicionar, adicionados


def test_seed_preenche_valores_de_exemplo() -> None:
    maquinas, tem_escaloes, adicionar, adicionados = _cenario()

    relatorio = aplicar_tarifas(maquinas, tem_escaloes, adicionar)

    # CORTE(4) + ORLAGEM(4) + MONTAGEM serie(1) + MANUAL serie(1) = 10.
    assert relatorio.campos_preenchidos == 10
    assert relatorio.escaloes_criados == 5  # CNC tiers
    assert maquinas["CORTE"].preco_ml_std == Decimal("0.45")
    assert maquinas["CORTE"].custo_setup_peca_serie == Decimal("0.08")
    assert maquinas["ORLAGEM"].preco_ml_std == Decimal("0.60")
    assert maquinas["MONTAGEM"].custo_hora_serie == Decimal("17")  # 20 * 0.85
    assert maquinas["MANUAL"].custo_hora_serie == Decimal("12.75")  # 15 * 0.85
    assert len(adicionados) == 5
    # last CNC tier has no area limit
    assert adicionados[-1][2] is None


def test_seed_idempotente_segunda_corrida_nao_altera() -> None:
    maquinas, tem_escaloes, adicionar, adicionados = _cenario()

    aplicar_tarifas(maquinas, tem_escaloes, adicionar)
    relatorio2 = aplicar_tarifas(maquinas, tem_escaloes, adicionar)

    assert relatorio2.campos_preenchidos == 0  # nothing re-written
    assert relatorio2.escaloes_criados == 0  # tiers not duplicated
    assert len(adicionados) == 5


def test_seed_nao_reescreve_valores_do_utilizador() -> None:
    maquinas, tem_escaloes, adicionar, _ = _cenario()
    maquinas["CORTE"].preco_ml_std = Decimal("0.99")  # user-set value

    aplicar_tarifas(maquinas, tem_escaloes, adicionar)

    assert maquinas["CORTE"].preco_ml_std == Decimal("0.99")  # preserved


def test_seed_reporta_maquinas_em_falta() -> None:
    maquinas = {"CORTE": _maquina(1)}  # others missing
    relatorio = aplicar_tarifas(maquinas, lambda _id: False, lambda *a: None)

    assert "ORLAGEM" in relatorio.maquinas_em_falta
    assert "CNC_VERTICAL" in relatorio.maquinas_em_falta
