"""O «Atualizar Custeio» do ValueSet só redesenha o custeio DEPOIS do clique.

A 28-09-2026 o Martelo fechou-se sozinho (sem mensagem) no 260954_02, item
RP_08: o botão «Atualizar Custeio» sem linha selecionada abria o quadro das
diferenças e redesenhava a tabela do custeio ainda dentro do clique. O registo
de crashes apontou ``_montar_combo_material`` (``setCellWidget``) <- ``carregar``
<- ``rever_diferencas_valueset`` <- ``atualizar_custeio_da_linha``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import inspect
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

_app = QApplication.instance() or QApplication([])


def _pagina_falsa():
    chamadas: list[bool] = []
    pagina = SimpleNamespace(
        rever_diferencas_valueset=lambda *, forcar=False: chamadas.append(forcar),
    )
    return pagina, chamadas


def test_pedido_do_botao_e_tratado_so_depois_do_clique() -> None:
    pagina, chamadas = _pagina_falsa()

    OrcamentoItemCusteioPage._on_pedido_rever_diferencas(pagina)
    assert chamadas == []  # nada dentro do clique do botão

    _app.processEvents()
    # O botão abre sempre o quadro, mesmo que o utilizador já o tenha dispensado.
    assert chamadas == [True]


def test_o_sinal_do_valueset_liga_ao_adiador() -> None:
    fonte = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    ligacao = " ".join(fonte.split())  # indiferente às quebras de linha
    assert "pedido_rever_diferencas.connect( self._on_pedido_rever_diferencas )" in ligacao
    assert "lambda: self.rever_diferencas_valueset(forcar=True)" not in fonte
