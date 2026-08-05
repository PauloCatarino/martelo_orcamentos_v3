"""Um botão só para abrir e agrupar todas as peças compostas.

Pedido do Paulo (2026-08-05): clicar mostra tudo expandido; clicar outra vez
agrupa tudo. O texto do botão diz sempre o que o PRÓXIMO clique vai fazer.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.domain.custeio_linha_types import FERRAGEM, PECA, PECA_COMPOSTA
from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _linha(id_: int, tipo: str, pai: int | None = None):
    return SimpleNamespace(id=id_, tipo_linha=tipo, linha_pai_id=pai, custo_total=None)


# Duas compostas (10 e 30) e uma peça com ferragem automática (20).
LINHAS = [
    _linha(1, PECA),
    _linha(10, PECA_COMPOSTA),
    _linha(11, PECA, pai=10),
    _linha(12, FERRAGEM, pai=10),
    _linha(20, PECA),
    _linha(21, FERRAGEM, pai=20),
    _linha(30, PECA_COMPOSTA),
    _linha(31, PECA, pai=30),
]


def _pagina(_app, linhas=LINHAS, *, expandidas=()):
    from PySide6.QtWidgets import QPushButton, QTableWidget

    from app.domain.custeio_colapso import (
        descendentes_por_composta,
        ferragens_associadas_por_peca,
    )

    pagina = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)
    pagina.table = QTableWidget(len(linhas), 1)
    pagina._custeio_by_row = dict(enumerate(linhas))
    pagina._descendentes_composta = descendentes_por_composta(linhas)
    pagina._ferragens_associadas_por_peca = ferragens_associadas_por_peca(linhas)
    pagina._compostas_expandidas = set(expandidas)
    pagina._carregando_tabela = False
    pagina.expandir_tudo_button = QPushButton()
    pagina.status_label = QPushButton()  # basta ter setText
    return pagina


def _visiveis(pagina) -> list[int]:
    return [
        pagina._custeio_by_row[row].id
        for row in range(pagina.table.rowCount())
        if not pagina.table.isRowHidden(row)
    ]


def test_o_primeiro_clique_abre_tudo(_app) -> None:
    pagina = _pagina(_app)

    pagina.alternar_expandir_tudo()

    assert _visiveis(pagina) == [1, 10, 11, 12, 20, 21, 30, 31]


def test_o_segundo_clique_agrupa_tudo(_app) -> None:
    pagina = _pagina(_app)

    pagina.alternar_expandir_tudo()
    pagina.alternar_expandir_tudo()

    assert _visiveis(pagina) == [1, 10, 20, 30]


def test_o_texto_diz_o_que_o_proximo_clique_faz(_app) -> None:
    pagina = _pagina(_app)
    pagina._atualizar_botao_expandir_tudo()
    assert pagina.expandir_tudo_button.text() == OrcamentoItemCusteioPage._TEXTO_EXPANDIR_TUDO

    pagina.alternar_expandir_tudo()

    assert pagina.expandir_tudo_button.text() == OrcamentoItemCusteioPage._TEXTO_AGRUPAR_TUDO


def test_com_alguns_abertos_o_clique_abre_os_que_faltam(_app) -> None:
    # Meio abertos não é "tudo aberto": o clique tem de completar, não fechar.
    pagina = _pagina(_app, expandidas={10})

    pagina.alternar_expandir_tudo()

    assert _visiveis(pagina) == [1, 10, 11, 12, 20, 21, 30, 31]


def test_abrir_um_a_um_ate_ao_fim_muda_o_texto(_app) -> None:
    pagina = _pagina(_app)

    for comp_id in (10, 20, 30):
        pagina._toggle_composta(comp_id)

    # Chegou a tudo aberto pela seta de cada linha: o botão tem de acompanhar.
    assert pagina.expandir_tudo_button.text() == OrcamentoItemCusteioPage._TEXTO_AGRUPAR_TUDO


def test_sem_compostas_o_botao_fica_desligado(_app) -> None:
    pagina = _pagina(_app, [_linha(1, PECA), _linha(2, PECA)])

    pagina._atualizar_botao_expandir_tudo()

    assert not pagina.expandir_tudo_button.isEnabled()
    assert not pagina._tudo_expandido()


def test_sem_compostas_clicar_nao_rebenta(_app) -> None:
    pagina = _pagina(_app, [_linha(1, PECA)])

    pagina.alternar_expandir_tudo()  # não deve levantar

    assert _visiveis(pagina) == [1]
