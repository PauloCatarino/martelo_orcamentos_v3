"""Melhorias pedidas pelos utilizadores nos menus dos Orçamentos.

Cobre: encomendas PHC legíveis, botão «Abrir Pasta» nos relatórios, Enter a
saltar de campo no Editar Item e as descrições pré-definidas legíveis.
"""

from __future__ import annotations

import inspect
import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit

from app.ui import tema


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


# ---- 1. Encomendas PHC visíveis ------------------------------------------


def test_lista_de_encomendas_usa_o_estilo_das_listas(_app) -> None:
    from app.ui.dialogs.editar_orcamento_dialog import EditarOrcamentoDialog

    dialog = EditarOrcamentoDialog()

    assert dialog.encomendas_list.styleSheet() == tema.ESTILO_LISTAS
    assert dialog.encomendas_list.alternatingRowColors() is True
    assert dialog.encomendas_list.minimumHeight() >= 96


def test_encomenda_principal_a_negrito_e_a_adicional_com_marcador(_app) -> None:
    from app.ui.dialogs.editar_orcamento_dialog import EditarOrcamentoDialog

    dialog = EditarOrcamentoDialog()
    dialog._inserir_encomenda("1499", True)
    dialog._inserir_encomenda("1500", False)

    principal = dialog.encomendas_list.item(0)
    adicional = dialog.encomendas_list.item(1)
    assert principal.text().startswith("★")
    assert principal.font().bold() is True
    assert adicional.text().startswith("•")
    assert adicional.font().bold() is False


def test_estilo_das_listas_pinta_a_selecao_como_as_tabelas() -> None:
    # Sem estas duas regras o Windows escreve texto branco sobre o realce claro
    # do sistema, e a linha selecionada fica ilegível.
    assert f"background-color: {tema.CASTANHO_ESCURO}" in tema.ESTILO_LISTAS
    assert "QListWidget::item:selected" in tema.ESTILO_LISTAS
    assert "color: #FFFFFF" in tema.ESTILO_LISTAS


# ---- 2. Abrir Pasta nos relatórios ----------------------------------------


def test_relatorios_tem_botao_abrir_pasta() -> None:
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

    fonte = inspect.getsource(OrcamentoRelatoriosPage)
    assert 'QPushButton("Abrir Pasta")' in fonte
    assert "barra.addWidget(self.abrir_pasta_button)" in fonte


def test_abrir_pasta_nao_cria_a_pasta_sem_perguntar() -> None:
    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

    fonte = inspect.getsource(
        OrcamentoRelatoriosPage._abrir_pasta_orcamento
    )
    assert "criar=False" in fonte
    assert "QMessageBox.question" in fonte
    assert "QDesktopServices.openUrl" in fonte


# ---- 3. Enter salta de campo no Editar Item --------------------------------


def _enter(dialog, modificador=Qt.KeyboardModifier.NoModifier) -> None:
    """Carregar no Enter pela cadeia real de eventos, no widget com o foco.

    Sem rodar o ciclo de eventos (nada de ``qWaitForWindowExposed``): a correr
    a suite inteira no Windows, isso deixa correr o que ficou por limpar de
    testes anteriores e mata o processo. E ``keyClick`` com ``None`` também
    aborta, daí o ``assert`` em vez do widget cru.
    """
    foco = dialog.focusWidget()
    assert foco is not None, "o diálogo ficou sem campo em foco"
    QTest.keyClick(foco, Qt.Key.Key_Return, modificador)


def test_enter_percorre_os_campos_em_vez_de_gravar(_app) -> None:
    from app.ui.dialogs.novo_item_dialog import NovoItemDialog

    dialog = NovoItemDialog()
    dialog.show()
    dialog.altura_input.setFocus()

    for esperado in (
        dialog.largura_input,
        dialog.profundidade_input,
        dialog.quantidade_input,
        dialog.unidade_input,
        dialog.preco_unitario_input,
        dialog.preco_manual_check,
    ):
        _enter(dialog)
        assert dialog.focusWidget() is esperado

    # E a janela nunca se fechou pelo caminho.
    assert dialog.isVisible() is True
    assert dialog.result() == 0
    dialog.close()


def test_enter_na_descricao_escreve_linha_nova_e_ctrl_enter_sai(_app) -> None:
    from app.ui.dialogs.novo_item_dialog import NovoItemDialog

    dialog = NovoItemDialog()
    dialog.show()
    dialog.descricao_input.setFocus()

    _enter(dialog)
    # O foco não sai da descrição: lá dentro o Enter é para mudar de linha.
    assert dialog.focusWidget() is dialog.descricao_input
    assert dialog.descricao_input.toPlainText() == "\n"

    _enter(dialog, Qt.KeyboardModifier.ControlModifier)
    assert dialog.focusWidget() is not dialog.descricao_input
    dialog.close()


def test_botao_das_descricoes_nao_prende_o_enter(_app) -> None:
    from app.ui.dialogs.novo_item_dialog import NovoItemDialog

    dialog = NovoItemDialog()
    dialog.show()
    dialog.descricoes_button.setFocus()

    _enter(dialog)

    assert dialog.descricoes_button.autoDefault() is False
    assert dialog.focusWidget() is dialog.altura_input
    dialog.close()


def test_enter_nos_botoes_do_fundo_continua_a_gravar(_app) -> None:
    from PySide6.QtWidgets import QDialog, QDialogButtonBox

    from app.ui.dialogs.novo_item_dialog import NovoItemDialog

    dialog = NovoItemDialog()
    dialog.show()
    dialog.item_input.setText("RP_01")
    dialog.button_box.button(QDialogButtonBox.StandardButton.Save).setFocus()

    _enter(dialog)

    assert dialog.result() == QDialog.DialogCode.Accepted


def test_enter_nos_campos_de_texto_nunca_fecha_a_janela(_app) -> None:
    from app.ui.dialogs.novo_item_dialog import NovoItemDialog

    dialog = NovoItemDialog()
    dialog.show()
    for campo in dialog.findChildren(QLineEdit):
        campo.setFocus()
        _enter(dialog)
        assert dialog.result() == 0
    dialog.close()


# ---- 4. Descrições pré-definidas legíveis ----------------------------------


def test_descricoes_predefinidas_mais_altas_e_com_linhas_juntas(_app) -> None:
    from app.ui.dialogs.descricoes_predefinidas_dialog import (
        DescricoesPredefinidasDialog,
    )

    dialog = DescricoesPredefinidasDialog(user_id=None)

    assert dialog.height() > 520
    assert dialog.lista.styleSheet() == tema.ESTILO_LISTAS
    assert dialog.lista.spacing() == 0
    assert "padding: 1px 4px" in tema.ESTILO_LISTAS
