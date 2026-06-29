"""Testes do otimizador (puro) do plano de corte (C3.1)."""

from __future__ import annotations

import importlib.util

import pytest

from app.domain.plano_corte import (
    PecaCorte,
    _empacotar_ingenuo,
    empacotar,
)

_TEM_RECTPACK = importlib.util.find_spec("rectpack") is not None

# Placa "standard" 2750 x 1830 mm (referência das placas do V2).
PLACA_COMP = 2750.0
PLACA_LARG = 1830.0


def test_varias_pecas_pequenas_cabem_numa_so_placa() -> None:
    pecas = [PecaCorte(i, f"P{i}", 400.0, 300.0) for i in range(1, 9)]

    resultado = empacotar(pecas, PLACA_COMP, PLACA_LARG)

    assert len(resultado.placas) == 1
    assert resultado.nao_alocadas == []
    # Todas as 8 peças ficaram colocadas.
    total_colocadas = sum(len(placa.pecas) for placa in resultado.placas)
    assert total_colocadas == 8


def test_peca_maior_que_a_placa_fica_nao_alocada() -> None:
    pecas = [
        PecaCorte(1, "OK", 400.0, 300.0),
        PecaCorte(2, "GIGANTE", 3000.0, 2000.0),
    ]

    resultado = empacotar(pecas, PLACA_COMP, PLACA_LARG)

    ids_nao_alocadas = {peca.id for peca in resultado.nao_alocadas}
    assert ids_nao_alocadas == {2}
    # A peça OK foi colocada.
    descs = [pc.desc for placa in resultado.placas for pc in placa.pecas]
    assert descs == ["OK"]


def test_aproveitamento_e_areas_caso_conhecido() -> None:
    # Placa 1000x1000 (1,0 m²); 1 peça 500x500 (0,25 m²) -> 25% sem kerf.
    pecas = [PecaCorte(1, "Q", 500.0, 500.0)]

    resultado = empacotar(pecas, 1000.0, 1000.0, kerf=0.0)

    assert len(resultado.placas) == 1
    assert resultado.area_pecas_m2 == 0.25
    assert resultado.area_placas_m2 == 1.0
    assert resultado.aproveitamento_pct == 25.0
    # Dimensões reais (sem kerf) guardadas na peça colocada.
    colocada = resultado.placas[0].pecas[0]
    assert (colocada.comp, colocada.larg) == (500.0, 500.0)


def test_sem_rotacao_peca_que_so_cabe_rodada_fica_nao_alocada() -> None:
    # Placa 1000 (comp) x 500 (larg). Peça 400x800: só cabe rodada.
    peca = PecaCorte(1, "RODA", 400.0, 800.0)

    com_rot = empacotar([peca], 1000.0, 500.0, rotacao=True)
    sem_rot = empacotar([peca], 1000.0, 500.0, rotacao=False)

    assert com_rot.nao_alocadas == []
    assert len(com_rot.placas) == 1
    assert [p.id for p in sem_rot.nao_alocadas] == [1]
    assert sem_rot.placas == []


def test_pecas_com_dimensao_nao_positiva_sao_ignoradas() -> None:
    pecas = [
        PecaCorte(1, "OK", 400.0, 300.0),
        PecaCorte(2, "ZERO", 0.0, 300.0),
        PecaCorte(3, "NEG", 400.0, -10.0),
    ]

    resultado = empacotar(pecas, PLACA_COMP, PLACA_LARG)

    # As peças inválidas não aparecem nem nas placas nem em nao_alocadas.
    assert resultado.nao_alocadas == []
    descs = [pc.desc for placa in resultado.placas for pc in placa.pecas]
    assert descs == ["OK"]


@pytest.mark.skipif(not _TEM_RECTPACK, reason="rectpack não instalado")
def test_rectpack_usa_menos_ou_igual_placas_que_fallback() -> None:
    pecas = [PecaCorte(i, f"P{i}", 400.0, 300.0) for i in range(1, 9)]

    otimizado = empacotar(pecas, PLACA_COMP, PLACA_LARG)
    ingenuo = _empacotar_ingenuo(
        pecas, PLACA_COMP, PLACA_LARG, kerf=3.0, rotacao=True
    )

    assert len(ingenuo.placas) == 8  # 1 peça por placa
    assert len(otimizado.placas) <= len(ingenuo.placas)
    assert len(otimizado.placas) == 1
