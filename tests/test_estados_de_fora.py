"""Quem manda em cada estado da obra, e o que isso impede.

O ``Desenho`` e a ``Producao`` são do utilizador: é ele que os marca no Martelo
enquanto trabalha. O ``Finalizado`` e o ``Arquivado`` são atribuídos por outras
pessoas da empresa, no PHC ou no Streamlit, e só de lá é que chegam cá.
"""

from __future__ import annotations

import pytest

from app.domain.producao_estados import (
    ESTADOS_DO_UTILIZADOR,
    ESTADOS_EXTERNOS,
    avanca_na_vida_da_obra,
    vem_de_fora,
)


def test_os_dois_grupos_nao_se_misturam() -> None:
    assert set(ESTADOS_DO_UTILIZADOR) & set(ESTADOS_EXTERNOS) == set()


@pytest.mark.parametrize(
    ("estado", "esperado"),
    [
        ("Finalizado", True),
        ("Arquivado", True),
        ("Desenho", False),
        ("Producao", False),
        ("Produção", False),  # com acento, como vem de obras antigas
        ("", False),
        (None, False),
    ],
)
def test_vem_de_fora(estado, esperado) -> None:
    assert vem_de_fora(estado) is esperado


@pytest.mark.parametrize(
    ("atual", "novo", "esperado"),
    [
        ("Desenho", "Producao", True),
        ("Desenho", "Arquivado", True),  # salta dois, mas anda para a frente
        ("Producao", "Finalizado", True),
        ("Finalizado", "Arquivado", True),
        # Recuar, nunca:
        ("Arquivado", "Producao", False),
        ("Arquivado", "Finalizado", False),
        ("Finalizado", "Desenho", False),
        ("Producao", "Desenho", False),
        # Ficar na mesma também não é mudança:
        ("Arquivado", "Arquivado", False),
        # Uma obra sem estado aceita qualquer um:
        ("", "Finalizado", True),
        (None, "Desenho", True),
        # Um estado que o Martelo não conhece nunca é destino:
        ("Desenho", "Standby", False),
        ("Desenho", "", False),
    ],
)
def test_avanca_na_vida_da_obra(atual, novo, esperado) -> None:
    assert avanca_na_vida_da_obra(atual, novo) is esperado


def test_acentos_nao_fazem_a_obra_recuar() -> None:
    """Em obras antigas o estado está gravado "Produção", com acento.

    Sem normalizar, "Produção" não era reconhecido, contava como estado
    desconhecido, e o PHC podia empurrar a obra de volta para Desenho.
    """
    assert avanca_na_vida_da_obra("Produção", "Desenho") is False
    assert avanca_na_vida_da_obra("Produção", "Finalizado") is True
