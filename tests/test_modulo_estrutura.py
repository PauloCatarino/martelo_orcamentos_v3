"""Tests for the top-level line resolution when saving a module (phase 8U.1)."""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.modulo_estrutura import selecionar_linhas_topo


def _l(id, *, ordem, nivel=0, linha_pai_id=None, ordem_visual=None):
    return SimpleNamespace(
        id=id,
        ordem=ordem,
        nivel=nivel,
        linha_pai_id=linha_pai_id,
        ordem_visual=ordem_visual,
    )


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


def test_ordem_visual_mantem_divisao_antes_das_pecas() -> None:
    """Uma divisão movida na grelha não pode ir para o fim do módulo."""
    linhas = [
        _l(10, ordem=None, ordem_visual=22),  # separador
        _l(30, ordem=None, ordem_visual=24),  # peça
        _l(40, ordem=None, ordem_visual=25),  # peça
        # ID maior, mas visualmente entre o separador e as peças.
        _l(50, ordem=None, ordem_visual=23),  # divisão independente
    ]

    topo = selecionar_linhas_topo(linhas, [10, 30, 40, 50])

    assert [linha.id for linha in topo] == [10, 50, 30, 40]


def test_sem_selecao_devolve_vazio() -> None:
    assert selecionar_linhas_topo([_l(1, ordem=1)], []) == []
