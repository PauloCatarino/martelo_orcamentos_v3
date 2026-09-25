"""Custo de produção: acrescentar linhas à mão (Matérias-Primas V3) e eliminar linhas.

Pedido do Paulo (25-09-2026): a obra gasta muitas vezes mais ferragens do que
as que vêm do IMOS — acrescenta-se a linha a partir das Matérias-Primas do V3 e
editam-se a quantidade e o preço; e poder eliminar linhas do custo.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest
from openpyxl import Workbook
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMessageBox

from app.services import analise_lista_material_service as svc
from app.ui.dialogs import analise_lista_material_dialog as ui
from app.ui.dialogs.acrescentar_linha_custo_dialog import AcrescentarLinhaCustoDialog

DOBRADICA = SimpleNamespace(
    id=60, ref_le='FF00060', ref_phc='FF00060', nome_imos='', descricao='DOBRADICA BLUM RETA 107º',
    unidade='UND', preco_liquido=Decimal('2.59'), familia_martelo='FERRAGENS', familia_original_excel='',
    tipo_martelo='', fornecedor='BLUM', referencia_fornecedor='75B1550', comprimento=None, largura=None,
    espessura=None, coresp_orla_0_4=None, coresp_orla_1_0=None)
CORREDICA = SimpleNamespace(**{**vars(DOBRADICA), 'id': 5, 'ref_le': 'FER0005', 'ref_phc': 'FER0005',
                               'descricao': 'CORRED. EXTR. TOTAL 450MM', 'preco_liquido': Decimal('6.105')})


def test_linha_manual_parte_da_materia_prima_e_guarda_o_preco_mudado():
    line, price = svc.linha_manual('Ferragens', CORREDICA, Decimal('4'), Decimal('6.105'), utilizador='paulo')
    assert line['manual'] and line['key'].startswith('manual:') and line['unit'] == 'un'
    assert line['added_by'] == 'paulo' and line['name'] == 'CORRED. EXTR. TOTAL 450MM'
    assert price['id'] == 5 and not price.get('preco_manual')
    assert svc.calculate_cost(line, price)[0] == Decimal('24.420')
    _, mudado = svc.linha_manual('Ferragens', CORREDICA, Decimal('4'), Decimal('5.5'))
    assert mudado['net'] == '5.5' and mudado['preco_manual'] and 'escrito à mão' in mudado['mapping_source']


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_dialogo_acrescentar_traz_o_preco_do_v3_e_pede_a_quantidade(app):
    dialog = AcrescentarLinhaCustoDialog([DOBRADICA, CORREDICA], categoria='SPP', utilizador='paulo')
    try:
        assert dialog.familia.currentText() == 'Ferragens'
        dialog.search.setText('corred')
        assert dialog.table.rowCount() == 1
        dialog.table.setCurrentCell(0, 0)
        assert dialog.preco.value() == pytest.approx(6.105)
        dialog._accept()
        assert dialog.line is None and 'quantidade' in dialog.status.text()   # 0 não entra
        dialog.quantidade.setValue(4)
        dialog._accept()
        assert dialog.line['kind'] == 'SPP' and Decimal(dialog.line['quantity']) == 4
    finally:
        dialog.close()


@pytest.fixture
def workbook(tmp_path):
    path = tmp_path / 'Lista_Material_1357_01_26_JF_VIVA.xlsx'
    w = Workbook()
    w.active.title = 'LISTAGEM_CUT_RITE'
    w.active.append(['Title'])
    w.active.append(['Material', 'Descricao', 'Qt', 'Esp', 'Comp', 'Larg', 'Orla ESQ'])
    w.active.append(['AGL_MLM_BRANCO_19MM', 'TETO', 2, 19, 1000, 500, 'PVC_0.4_BRANCO'])
    f = w.create_sheet('1_FERRAGENS')
    f.append(['Listagem Ferragem'])
    f.append(['Imagem\n', 'Ref PHC', None, 'Ref Fornecedor', 'Descrição 1', None, None, 'Qt.', 'UN', 'Artg.\n'])
    f.append([None, 'FF00060', None, '75B1550 BLUM', 'Dobradiça', None, None, 95, '\n', 'RP_A_03'])
    w.save(path)
    return path


def _dialog(session, workbook, monkeypatch):
    monkeypatch.setattr(ui, 'query_woodstore', lambda _: [])
    monkeypatch.setattr(ui.custo_ferragens, 'ler_precos_phc', lambda _s, refs: {})
    monkeypatch.setattr(ui.maps, 'load_catalog', lambda _s: [DOBRADICA, CORREDICA])
    return ui.AnaliseListaMaterialDialog(
        session, workbook_path=workbook, plan_name='1357_01_01_26_JF_VIVA', cutrite_folder=workbook.parent,
        user=SimpleNamespace(role='admin', username='paulo'), obra_info={'estado': 'Arquivado'})


def _acrescentar(dialog, monkeypatch, mp, quantidade):
    class Falso:
        def __init__(self, catalog, *, categoria, utilizador, parent):
            self.line, self.price = svc.linha_manual(categoria, mp, Decimal(quantidade), utilizador=utilizador)

        def exec(self):
            return ui.QDialog.DialogCode.Accepted
    monkeypatch.setattr(ui, 'AcrescentarLinhaCustoDialog', Falso)
    dialog._add_line()


def _editar(dialog, line, coluna, texto):
    dialog.cost_table.item(dialog._cost_row_of(line), coluna).setText(texto)
    for _ in range(3):   # a edição aplica-se depois do commit do editor
        QApplication.processEvents()


def test_acrescentar_editar_e_guardar_a_linha_da_obra(app, session, workbook, monkeypatch):
    dialog = _dialog(session, workbook, monkeypatch)
    try:
        dialog.category_filter.setCurrentText('Ferragens')
        _acrescentar(dialog, monkeypatch, CORREDICA, '4')
        linha = next(l for l in dialog.lines if l.get('manual'))
        assert linha['kind'] == 'Ferragens'
        row = dialog._cost_row_of(linha)
        assert dialog.cost_table.item(row, 9).text() == '24.42'
        assert 'acrescentada à mão por paulo' in dialog.cost_table.item(row, 10).text()
        # Só a quantidade e o preço da linha à mão se editam.
        assert dialog.cost_table.item(row, 5).flags() & ui.Qt.ItemFlag.ItemIsEditable
        assert not dialog.cost_table.item(row, 1).flags() & ui.Qt.ItemFlag.ItemIsEditable
        origem = next(l for l in dialog.lines if l['kind'] == 'Ferragens' and not l.get('manual'))
        assert not dialog.cost_table.item(dialog._cost_row_of(origem), 5).flags() & ui.Qt.ItemFlag.ItemIsEditable

        _editar(dialog, linha, 5, '6')
        assert linha['quantity'] == '6'
        _editar(dialog, linha, 8, '5,5')
        assert dialog.prices[linha['key']]['preco_manual']
        assert dialog.cost_table.item(dialog._cost_row_of(linha), 9).text() == '33.00'
        _editar(dialog, linha, 5, 'abc')
        assert linha['quantity'] == '6' and 'não é um número' in dialog.status.text()

        dialog._update_prices()                       # o V3 não mexe no preço escrito à mão
        assert dialog.prices[linha['key']]['net'] == '5.5'
        assert 'Acrescentadas à mão nesta obra (1)' in dialog._avisos_feitos_a_mao()[0]
        dialog._save()
        dialog._reload()                              # fica na análise desta obra
        guardada = next(l for l in dialog.lines if l.get('manual'))
        assert guardada['key'] == linha['key'] and guardada['quantity'] == '6'
        assert dialog.prices[guardada['key']]['net'] == '5.5'
    finally:
        dialog.close()


def test_eliminar_e_repor_linhas(app, session, workbook, monkeypatch):
    dialog = _dialog(session, workbook, monkeypatch)
    try:
        _acrescentar(dialog, monkeypatch, CORREDICA, '4')
        manual = next(l for l in dialog.lines if l.get('manual'))
        origem = next(l for l in dialog.lines if l['kind'] == 'Ferragens' and not l.get('manual'))
        monkeypatch.setattr(ui.QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.Yes)
        modelo = dialog.cost_table.selectionModel()
        for line in (manual, origem):      # como Ctrl+clique nas duas
            modelo.select(dialog.cost_table.model().index(dialog._cost_row_of(line), 0),
                          QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        dialog._remove_lines()
        assert manual not in dialog.lines and origem not in dialog.lines
        assert [l['key'] for l in dialog.removed_lines] == [origem['key']]   # a manual vai de vez
        assert dialog.restore_button.isEnabled() and '(1)' in dialog.restore_button.text()
        assert 'eliminada(s) nesta obra' in dialog.cost_summary.text()
        dialog._save()
        dialog._reload()
        assert all(l['key'] != origem['key'] for l in dialog.lines)
        assert not any(l.get('manual') for l in dialog.lines)
        dialog._restore_removed()
        assert any(l['key'] == origem['key'] for l in dialog.lines)
        assert not dialog.restore_button.isEnabled()
    finally:
        dialog.close()


def test_eliminar_pede_confirmacao(app, session, workbook, monkeypatch):
    dialog = _dialog(session, workbook, monkeypatch)
    try:
        origem = next(l for l in dialog.lines if l['kind'] == 'Ferragens')
        dialog.cost_table.selectRow(dialog._cost_row_of(origem))
        monkeypatch.setattr(ui.QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.No)
        dialog._remove_lines()
        assert origem in dialog.lines and not dialog.removed_lines
    finally:
        dialog.close()
