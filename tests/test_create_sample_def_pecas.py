"""Tests for the sample piece definition seed script."""

from __future__ import annotations

from decimal import Decimal

from app.domain.componente_types import FERRAGEM, PECA
from app.domain.peca_types import COMPOSTA, SIMPLES
from scripts.create_sample_def_pecas import (
    GAVETA_COMPONENTES,
    GAVETA_PECA,
    REGRA_QUANTIDADE_FIXA,
    SIMPLE_PECAS,
    SampleDefPecasResult,
)


def test_sample_def_pecas_constants_import() -> None:
    codigos = {seed.codigo for seed in SIMPLE_PECAS}

    assert "LATERAL" in codigos
    assert "TAMPO" in codigos
    assert "FUNDO" in codigos
    assert "FRENTE_GAVETA" in codigos
    assert all(seed.tipo_peca == SIMPLES for seed in SIMPLE_PECAS)
    assert GAVETA_PECA.codigo == "GAVETA"
    assert GAVETA_PECA.nome == "Gaveta"
    assert GAVETA_PECA.tipo_peca == COMPOSTA


def test_sample_gaveta_componentes_constants_import() -> None:
    componentes_peca = [seed for seed in GAVETA_COMPONENTES if seed.tipo_componente == PECA]
    componentes_ferragem = [seed for seed in GAVETA_COMPONENTES if seed.tipo_componente == FERRAGEM]

    assert len(componentes_peca) == 4
    assert len(componentes_ferragem) == 2
    assert componentes_peca[0].def_peca_codigo == "LADO_GAVETA"
    assert componentes_peca[0].quantidade == Decimal("2")
    assert {seed.referencia_componente for seed in componentes_ferragem} == {"CORREDICA", "PUXADOR"}
    assert all(seed.regra_quantidade == REGRA_QUANTIDADE_FIXA for seed in GAVETA_COMPONENTES)


def test_sample_def_pecas_result_dataclass() -> None:
    result = SampleDefPecasResult(
        pecas_criadas=1,
        pecas_reutilizadas=10,
        componentes_criados=2,
        componentes_reutilizados=4,
    )

    assert result.pecas_criadas == 1
    assert result.pecas_reutilizadas == 10
    assert result.componentes_criados == 2
    assert result.componentes_reutilizados == 4
