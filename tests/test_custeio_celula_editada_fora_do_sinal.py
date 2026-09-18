"""A célula editada no custeio só é gravada DEPOIS de o Qt acabar de a escrever.

A 18-09-2026 o Martelo fechou-se sozinho (sem mensagem) a meio de um Enter
numa medida: o ``cellChanged`` gravava e redesenhava a linha ali mesmo, e o
``setItem`` destruía a célula que o Qt ainda tinha nas mãos. O registo de
crashes apontou ``_preencher_linha`` <- ``_on_cell_changed`` <- ``eventFilter``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

_app = QApplication.instance() or QApplication([])


def _pagina_falsa(carregando: bool):
    chamadas: list[tuple[int, int]] = []
    pagina = SimpleNamespace(
        _carregando_tabela=carregando,
        _on_cell_changed=lambda r, c: chamadas.append((r, c)),
    )
    return pagina, chamadas


def test_edicao_do_utilizador_e_tratada_so_depois_do_sinal() -> None:
    pagina, chamadas = _pagina_falsa(carregando=False)

    OrcamentoItemCusteioPage._on_cell_changed_sinal(pagina, 3, 7)
    assert chamadas == []  # nada dentro do sinal do Qt

    _app.processEvents()
    assert chamadas == [(3, 7)]


def test_mudancas_do_proprio_programa_continuam_ignoradas() -> None:
    pagina, chamadas = _pagina_falsa(carregando=True)

    OrcamentoItemCusteioPage._on_cell_changed_sinal(pagina, 3, 7)
    _app.processEvents()

    assert chamadas == []


def test_a_tabela_liga_o_sinal_ao_adiador() -> None:
    import inspect

    fonte = inspect.getsource(OrcamentoItemCusteioPage)
    assert "cellChanged.connect(self._on_cell_changed_sinal)" in fonte
    assert "cellChanged.connect(self._on_cell_changed)" not in fonte
