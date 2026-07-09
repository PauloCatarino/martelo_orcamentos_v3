from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.domain.valueset_precos import (
    calcular_preco_liquido,
    detetar_divergencias,
)


def _linha(**kwargs):
    base = {
        "id": 1,
        "chave": "MATERIAL_FRENTES",
        "codigo_opcao": "MDF",
        "nome_opcao": "MDF",
        "materia_prima_id": None,
        "ref_le": "MP001",
        "preco_tabela": Decimal("10"),
        "margem_percentagem": Decimal("10"),
        "desconto_percentagem": Decimal("5"),
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_calcular_preco_liquido() -> None:
    assert calcular_preco_liquido(
        Decimal("10"), Decimal("10"), Decimal("5")
    ) == Decimal("10.450")


def test_detetar_divergencias_respeita_tolerancia() -> None:
    materias = {
        "MP001": SimpleNamespace(preco_tabela=Decimal("10.04")),
        "MP002": SimpleNamespace(preco_tabela=Decimal("10.06")),
    }

    divergencias = detetar_divergencias(
        [
            _linha(id=1, ref_le="MP001"),
            _linha(id=2, ref_le="MP002"),
        ],
        lambda _materia_id, ref_le: materias.get(ref_le),
    )

    assert [divergencia.linha_id for divergencia in divergencias] == [2]
    assert divergencias[0].preco_tabela_atual == Decimal("10.06")


def test_detetar_divergencias_ignora_linha_sem_ref_ou_materia() -> None:
    divergencias = detetar_divergencias(
        [_linha(ref_le=None, materia_prima_id=None)],
        lambda _materia_id, _ref_le: SimpleNamespace(preco_tabela=Decimal("12")),
    )

    assert divergencias == []


def test_detetar_divergencias_recalcula_preservando_margem_desconto() -> None:
    divergencias = detetar_divergencias(
        [
            _linha(
                preco_tabela=Decimal("10"),
                margem_percentagem=Decimal("20"),
                desconto_percentagem=Decimal("10"),
            )
        ],
        lambda _materia_id, _ref_le: SimpleNamespace(preco_tabela=Decimal("12")),
    )

    assert len(divergencias) == 1
    assert divergencias[0].margem_percentagem == Decimal("20")
    assert divergencias[0].desconto_percentagem == Decimal("10")
    assert divergencias[0].preco_liquido_novo == Decimal("12.96")
