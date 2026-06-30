"""Testes do domínio do estado de produção (PD1)."""

from __future__ import annotations

import pytest

from app.domain.estado_producao import (
    estado_producao_encomenda,
    interpretar_ok,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("N", None),
        ("", None),
        (None, None),
        ("abc", None),
        ("0", 0.0),
        ("60", 60.0),
        ("100", 100.0),
        ("SIM", 100.0),
        ("S", 100.0),
        ("1", 100.0),
        ("TRUE", 100.0),
    ],
)
def test_interpretar_ok(valor, esperado) -> None:
    assert interpretar_ok(valor) == esperado if esperado is not None else (
        interpretar_ok(valor) is None
    )


def test_media_por_setor() -> None:
    linhas = [
        {"bd_preparacao_placas_ok": "100"},
        {"bd_preparacao_placas_ok": "60"},
        {"bd_preparacao_placas_ok": "0"},
    ]

    estado = estado_producao_encomenda(linhas)

    # Só o setor "Preparação" existe.
    assert [s.nome for s in estado.setores] == ["Preparação"]
    # (100 + 60 + 0) / 3 = 53.333 -> 53.3 (1 casa).
    assert estado.setores[0].media_pct == 53.3
    assert estado.setores[0].concluido is False


def test_existencia_corte_depende_da_quantidade() -> None:
    sem_corte = estado_producao_encomenda(
        [{"bd_operacoes_corte_quantidade": 0, "bd_corte_ok": "100"}]
    )
    assert [s.nome for s in sem_corte.setores] == []

    com_corte = estado_producao_encomenda(
        [{"bd_operacoes_corte_quantidade": 5, "bd_corte_ok": "100"}]
    )
    assert [s.nome for s in com_corte.setores] == ["Corte"]
    assert com_corte.setores[0].media_pct == 100.0
    assert com_corte.setores[0].concluido is True


def _linha_6_setores(stock, prep, corte, orla, cnc, montagem) -> dict:
    """Uma linha onde existem 6 setores (Embalagem/Expedição ausentes)."""
    return {
        "bd_stock_ok": stock,
        "bd_preparacao_placas_ok": prep,
        "bd_operacoes_corte_quantidade": 5,
        "bd_corte_ok": corte,
        "bd_operacoes_orla_quantidade": 3,
        "bd_orla_ok": orla,
        "bd_operacoes_cnc_quantidade": 2,
        "bd_cnc_ok": cnc,
        "tem_montagem_ativa": 1,
        "bd_montagem_ok": montagem,
        "bd_tempo_embalamento_minutos": 0,   # Embalagem não existe
        "bd_expedicao_ok": "N",              # Expedição não existe
    }


def test_global_dois_de_seis_concluidos() -> None:
    linha = _linha_6_setores("100", "100", "0", "0", "0", "0")

    estado = estado_producao_encomenda([linha])

    assert estado.total_setores == 6
    assert estado.concluidos == 2
    assert estado.etiqueta == "🔄 33.3% (2/6)"


def test_global_todos_concluidos() -> None:
    linha = _linha_6_setores("100", "100", "100", "100", "100", "100")

    estado = estado_producao_encomenda([linha])

    assert estado.total_setores == 6
    assert estado.concluidos == 6
    assert estado.global_pct == 100.0
    assert estado.etiqueta == "✅ 100% (6/6)"


def test_global_nenhum_concluido() -> None:
    linha = _linha_6_setores("0", "0", "0", "0", "0", "0")

    estado = estado_producao_encomenda([linha])

    assert estado.total_setores == 6
    assert estado.concluidos == 0
    assert estado.etiqueta == "⏳ 0% (0/6)"


def test_sem_linhas_etiqueta_traco() -> None:
    estado = estado_producao_encomenda([])

    assert estado.total_setores == 0
    assert estado.global_pct == 0.0
    assert estado.etiqueta == "—"
