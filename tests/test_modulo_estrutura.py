"""Tests for the top-level line resolution when saving a module (phase 8U.1)."""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.modulo_estrutura import selecionar_linhas_topo


def _l(id, *, ordem, nivel=0, linha_pai_id=None):
    return SimpleNamespace(id=id, ordem=ordem, nivel=nivel, linha_pai_id=linha_pai_id)


def test_topo_inclui_divisao_simples_e_cabecalho_composto() -> None:
    linhas = [
        _l(1, ordem=1),  # independent division
        _l(2, ordem=2),  # simple piece
        _l(3, ordem=3),  # composite header
        _l(4, ordem=4, nivel=1, linha_pai_id=3),  # composite child
        _l(5, ordem=5),  # standalone hardware
    ]

    topo = selecionar_linhas_topo(linhas, [1, 2, 3, 4, 5])

    # The child (4) is represented by its header (3); no duplicates.
    assert [linha.id for linha in topo] == [1, 2, 3, 5]


def test_selecionar_so_o_filho_inclui_o_cabecalho() -> None:
    linhas = [
        _l(3, ordem=3),  # composite header
        _l(4, ordem=4, nivel=1, linha_pai_id=3),  # composite child
    ]

    topo = selecionar_linhas_topo(linhas, [4])

    assert [linha.id for linha in topo] == [3]


def test_filhos_em_dois_niveis_resolvem_ate_ao_topo() -> None:
    linhas = [
        _l(1, ordem=1),  # header
        _l(2, ordem=2, nivel=1, linha_pai_id=1),  # child
        _l(3, ordem=3, nivel=2, linha_pai_id=2),  # grandchild
    ]

    topo = selecionar_linhas_topo(linhas, [3])

    assert [linha.id for linha in topo] == [1]


def test_ordena_por_ordem_da_tabela() -> None:
    linhas = [
        _l(1, ordem=3),
        _l(2, ordem=1),
        _l(3, ordem=2),
    ]

    topo = selecionar_linhas_topo(linhas, [1, 2, 3])

    assert [linha.id for linha in topo] == [2, 3, 1]


def test_sem_selecao_devolve_vazio() -> None:
    assert selecionar_linhas_topo([_l(1, ordem=1)], []) == []
