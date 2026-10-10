"""Copiar das tabelas só de leitura (pedido do Paulo na Pesquisa IA, 10-10-2026)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from app.ui.helpers import tabela_copiavel as copia


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _tabela(app) -> QTableWidget:
    tabela = QTableWidget(3, 3)
    tabela.setHorizontalHeaderLabels(["Ref", "Descrição", "Preço"])
    linhas = [
        ("FF00495", "DOBRADIÇA 90º C/ FECHO SUAVE X91", "1,04 €"),
        ("FF00555", "CALÇO X91 H0 C/ PARAFUSO\tEURO", "0,15 €"),
        ("FF04073", "CALCO X91 H2 3D\nS/ PARAFUSO", "0,17 €"),
    ]
    for linha, valores in enumerate(linhas):
        for coluna, valor in enumerate(valores):
            tabela.setItem(linha, coluna, QTableWidgetItem(valor))
    copia.tornar_copiavel(tabela)
    return tabela


def _selecionar(tabela: QTableWidget, *celulas) -> None:
    tabela.clearSelection()
    modelo = tabela.selectionModel()
    for linha, coluna in celulas:
        modelo.select(
            tabela.model().index(linha, coluna), QItemSelectionModel.SelectionFlag.Select
        )


def test_seleciona_celula_a_celula(app):
    tabela = _tabela(app)
    assert tabela.selectionBehavior() == QTableWidget.SelectionBehavior.SelectItems
    assert tabela.selectionMode() == QTableWidget.SelectionMode.ExtendedSelection


def test_uma_celula_sai_como_texto_simples(app):
    tabela = _tabela(app)
    _selecionar(tabela, (0, 1))
    assert copia.texto_da_selecao(tabela) == "DOBRADIÇA 90º C/ FECHO SUAVE X91"


def test_varias_celulas_saem_prontas_para_o_excel(app):
    tabela = _tabela(app)
    _selecionar(tabela, (0, 0), (0, 2), (1, 0), (1, 2))
    assert copia.texto_da_selecao(tabela) == "FF00495\t1,04 €\nFF00555\t0,15 €"


def test_selecao_salteada_fica_em_retangulo_com_brancos(app):
    tabela = _tabela(app)
    _selecionar(tabela, (0, 0), (2, 1))
    assert copia.texto_da_selecao(tabela) == "FF00495\t\n\tCALCO X91 H2 3D S/ PARAFUSO"


def test_tabulacoes_e_mudancas_de_linha_nao_partem_as_colunas(app):
    tabela = _tabela(app)
    _selecionar(tabela, (1, 1), (2, 1))
    assert copia.texto_da_selecao(tabela) == (
        "CALÇO X91 H0 C/ PARAFUSO EURO\nCALCO X91 H2 3D S/ PARAFUSO"
    )


def test_colunas_escondidas_ficam_de_fora(app):
    tabela = _tabela(app)
    tabela.setColumnHidden(1, True)
    _selecionar(tabela, (0, 0), (0, 1), (0, 2))
    assert copia.texto_da_selecao(tabela) == "FF00495\t1,04 €"


def test_ctrl_c_copia_a_selecao_e_nao_so_a_celula_atual(app):
    tabela = _tabela(app)
    tabela.show()
    tabela.setFocus()
    tabela.setCurrentCell(0, 0)
    _selecionar(tabela, (0, 0), (0, 1))
    app.clipboard().setText("antes")
    QTest.keyClick(tabela, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    assert app.clipboard().text() == "FF00495\tDOBRADIÇA 90º C/ FECHO SUAVE X91"
    tabela.hide()


def test_copiar_linha_inteira_e_tabela_com_titulos(app):
    tabela = _tabela(app)
    _selecionar(tabela, (2, 2))
    assert copia.copiar_linhas_selecionadas(tabela)
    assert app.clipboard().text() == "FF04073\tCALCO X91 H2 3D S/ PARAFUSO\t0,17 €"
    assert copia.copiar_tabela(tabela)
    linhas = app.clipboard().text().split("\n")
    assert linhas[0] == "Ref\tDescrição\tPreço"
    assert len(linhas) == 4


def test_tabela_vazia_nao_mexe_na_area_de_transferencia(app):
    tabela = QTableWidget(0, 2)
    copia.tornar_copiavel(tabela)
    app.clipboard().setText("fica")
    assert not copia.copiar_selecao(tabela)
    assert app.clipboard().text() == "fica"


def test_visor_mostra_o_texto_completo_da_celula_atual(app):
    tabela = _tabela(app)
    visor = copia.VisorCelula()
    visor.acompanhar(tabela)
    assert visor.isReadOnly()
    tabela.setCurrentCell(0, 1)
    assert visor.text() == "DOBRADIÇA 90º C/ FECHO SUAVE X91"
    # Só uma parte, como quem arrasta o rato sobre «FECHO SUAVE».
    visor.setSelection(visor.text().index("FECHO"), len("FECHO SUAVE"))
    visor.copy()
    assert app.clipboard().text() == "FECHO SUAVE"
    tabela.setRowCount(0)
    assert visor.text() == ""
