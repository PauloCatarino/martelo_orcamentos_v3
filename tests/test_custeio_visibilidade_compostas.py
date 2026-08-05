"""A composta fechada não pode desaparecer ao inserir uma linha acima dela.

Relatado pelo Paulo (2026-08-05): inserindo uma linha de separação ACIMA de
uma peça composta FECHADA, a linha da composta sumia da tabela. Não era
apagada — apagando o separador, voltava; e sair e voltar ao menu também a
repunha. Com a composta ABERTA nunca acontecia.

A causa é o "escondido" do Qt ser propriedade do NÚMERO da linha e não do que
lá está: escondiam-se as descendentes e nunca se voltava a mostrar nada, por
isso uma marca antiga sobrevivia à tabela ser repovoada.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.domain.custeio_linha_types import FERRAGEM, PECA, PECA_COMPOSTA, SEPARADOR


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _linha(id_: int, tipo: str, pai: int | None = None):
    return SimpleNamespace(id=id_, tipo_linha=tipo, linha_pai_id=pai, custo_total=None)


def _pagina_com(_app, linhas, *, expandidas=()):
    """Uma página só com o que este método precisa (sem BD)."""
    from PySide6.QtWidgets import QTableWidget

    from app.domain.custeio_colapso import (
        descendentes_por_composta,
        ferragens_associadas_por_peca,
    )
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    pagina = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)
    pagina.table = QTableWidget(len(linhas), 1)
    pagina._custeio_by_row = dict(enumerate(linhas))
    pagina._descendentes_composta = descendentes_por_composta(linhas)
    pagina._ferragens_associadas_por_peca = ferragens_associadas_por_peca(linhas)
    pagina._compostas_expandidas = set(expandidas)
    return pagina


def _visiveis(pagina) -> list[int]:
    return [
        pagina._custeio_by_row[row].id
        for row in range(pagina.table.rowCount())
        if not pagina.table.isRowHidden(row)
    ]


# Uma gaveta composta (id 10) com dois filhos, e uma peça solta a seguir.
def _com_composta_fechada(_app):
    linhas = [
        _linha(1, PECA),
        _linha(10, PECA_COMPOSTA),
        _linha(11, PECA, pai=10),
        _linha(12, FERRAGEM, pai=10),
        _linha(2, PECA),
    ]
    return _pagina_com(_app, linhas)


def test_composta_fechada_esconde_so_os_filhos(_app) -> None:
    pagina = _com_composta_fechada(_app)

    pagina._aplicar_visibilidade_compostas()

    assert _visiveis(pagina) == [1, 10, 2]


def test_inserir_linha_acima_nao_faz_a_composta_desaparecer(_app) -> None:
    pagina = _com_composta_fechada(_app)
    pagina._aplicar_visibilidade_compostas()
    assert pagina.table.isRowHidden(2)  # o filho estava escondido

    # Agora entra um separador no topo: tudo desce uma linha e o cabeçalho da
    # composta cai num número que ANTES estava escondido.
    linhas = [
        _linha(1, PECA),
        _linha(99, SEPARADOR),
        _linha(10, PECA_COMPOSTA),
        _linha(11, PECA, pai=10),
        _linha(12, FERRAGEM, pai=10),
        _linha(2, PECA),
    ]
    pagina.table.setRowCount(len(linhas))
    pagina._custeio_by_row = dict(enumerate(linhas))

    pagina._aplicar_visibilidade_compostas()

    assert _visiveis(pagina) == [1, 99, 10, 2]


def test_o_separador_novo_tambem_nao_fica_escondido(_app) -> None:
    pagina = _com_composta_fechada(_app)
    pagina._aplicar_visibilidade_compostas()

    # O separador vai parar ao número onde estava um filho escondido.
    linhas = [
        _linha(1, PECA),
        _linha(10, PECA_COMPOSTA),
        _linha(99, SEPARADOR),
        _linha(11, PECA, pai=10),
        _linha(12, FERRAGEM, pai=10),
        _linha(2, PECA),
    ]
    pagina.table.setRowCount(len(linhas))
    pagina._custeio_by_row = dict(enumerate(linhas))

    pagina._aplicar_visibilidade_compostas()

    assert 99 in _visiveis(pagina)


def test_composta_aberta_mostra_tudo(_app) -> None:
    linhas = [
        _linha(10, PECA_COMPOSTA),
        _linha(11, PECA, pai=10),
        _linha(12, FERRAGEM, pai=10),
    ]
    pagina = _pagina_com(_app, linhas, expandidas={10})

    pagina._aplicar_visibilidade_compostas()

    assert _visiveis(pagina) == [10, 11, 12]


def test_fechar_depois_de_abrir_volta_a_esconder(_app) -> None:
    pagina = _com_composta_fechada(_app)
    pagina._compostas_expandidas = {10}
    pagina._aplicar_visibilidade_compostas()
    assert _visiveis(pagina) == [1, 10, 11, 12, 2]

    pagina._compostas_expandidas = set()
    pagina._aplicar_visibilidade_compostas()

    assert _visiveis(pagina) == [1, 10, 2]
