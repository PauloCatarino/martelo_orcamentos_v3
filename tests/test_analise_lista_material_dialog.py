from pathlib import Path
from types import SimpleNamespace

import pytest
from openpyxl import Workbook
from PySide6.QtWidgets import QApplication

from app.ui.dialogs import analise_lista_material_dialog as ui
from app.services.permission_service import (
    PERMISSAO_ANALISE_LISTA_MATERIAL, PERMISSAO_CUSTOS_LISTA_MATERIAL,
    PERMISSAO_CORRIGIR_LISTA_MATERIAL,
)


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def workbook(tmp_path):
    path = tmp_path / 'Lista_Material_0722_01_26_JF_VIVA.xlsx'
    w = Workbook()
    w.active.title = 'LISTAGEM_CUT_RITE'
    w.active.append(['Title'])
    w.active.append(['Material', 'Descricao', 'Qt', 'Esp'])
    w.active.append(['AGL_MLM_BRANCO_19M', 'TETO', 2, 19])
    w.save(path)
    return path


def test_no_stock_still_suggested_but_never_preselected(app, workbook, session, monkeypatch):
    monkeypatch.setattr(ui, 'query_woodstore', lambda _: [{'Codigo': 'AGL_MLM_BRANCO_19MM', 'Espessura': 19, 'Disponivel': 0}])
    user = SimpleNamespace(role='admin', username='Teste')
    dialog = ui.AnaliseListaMaterialDialog(session, workbook_path=workbook,
        plan_name='0722_01_01_26_JF_VIVA', cutrite_folder=workbook.parent, user=user)
    try:
        combo = dialog.choices['AGL_MLM_BRANCO_19M']
        assert combo.count() == 2
        assert combo.currentData() is None
        assert dialog.tabs.count() == 3
        assert dialog.analysis_ready
        dialog._save()
        assert len(list((workbook.parent / 'Analise_Lista_Material').glob('*.json'))) == 1
    finally:
        dialog.close()


def test_permissions_hide_costs_and_disable_corrections(app, workbook, session, monkeypatch):
    monkeypatch.setattr(ui, 'permissions_for_user', lambda *_: {PERMISSAO_ANALISE_LISTA_MATERIAL: True})
    monkeypatch.setattr(ui, 'query_woodstore', lambda _: [])
    dialog = ui.AnaliseListaMaterialDialog(session, workbook_path=workbook,
        plan_name='0722_01_01_26_JF_VIVA', cutrite_folder=workbook.parent,
        user=SimpleNamespace(username='Teste'))
    try:
        assert dialog.tabs.count() == 1
        assert not dialog.apply_button.isEnabled()
        assert 'Não foi possível validar' == dialog.material_table.item(0, 2).text()
    finally:
        dialog.close()


def test_hardware_import_prefers_embedded_sheet(app, workbook, session, monkeypatch):
    monkeypatch.setattr(ui, 'query_woodstore', lambda _: [])
    dialog=ui.AnaliseListaMaterialDialog(session,workbook_path=workbook,plan_name='0722_01_01_26_JF_VIVA',cutrite_folder=workbook.parent,user=SimpleNamespace(role='admin',username='Teste'))
    monkeypatch.setattr(ui.svc,'hardware_sheet_names',lambda _: ['5_Custo_Obra_Ferragens'])
    monkeypatch.setattr(ui.svc,'hardware_sources',lambda *_: pytest.fail('Não deve procurar fonte externa'))
    monkeypatch.setattr(dialog,'_reload',lambda: None)
    dialog._import_hardware()
    assert 'separador existente' in dialog.status.text()
    dialog.close()


def test_hardware_import_finds_archived_file(app, workbook, session, monkeypatch):
    monkeypatch.setattr(ui, 'query_woodstore', lambda _: [])
    dialog=ui.AnaliseListaMaterialDialog(session,workbook_path=workbook,plan_name='0722_01_01_26_JF_VIVA',cutrite_folder=workbook.parent,user=SimpleNamespace(role='admin',username='Teste'))
    source=workbook.parent/'5_Custo_Obra_Ferragens.xlsx'
    source.write_bytes(b'test')
    calls=[]
    monkeypatch.setattr(ui.svc,'import_hardware_cost',lambda p,s: calls.append((p,s)))
    monkeypatch.setattr(dialog,'_reload',lambda: None)
    dialog._import_hardware()
    assert calls==[(workbook,source)]
    dialog.close()


def test_layout_saved_per_user_and_precision_display_only(app, workbook, session, monkeypatch):
    monkeypatch.setattr(ui, 'query_woodstore', lambda _: [])
    args=dict(workbook_path=workbook,plan_name='0722_01_01_26_JF_VIVA',cutrite_folder=workbook.parent)
    d=ui.AnaliseListaMaterialDialog(session,**args,user=SimpleNamespace(id=77,role='admin',username='Teste'))
    d.cost_table.setColumnWidth(1, 517)
    d._render_costs()
    assert d.cost_table.columnWidth(1)==517
    assert d._decimal('2.216666666666')=='2.22'
    assert d._decimal('0')=='0.00'
    d.accept()
    reopened=ui.AnaliseListaMaterialDialog(session,**args,user=SimpleNamespace(id=77,role='admin',username='Teste'))
    assert reopened.cost_table.columnWidth(1)==517
    other=ui.AnaliseListaMaterialDialog(session,**args,user=SimpleNamespace(id=78,role='admin',username='Outro'))
    assert other.cost_table.columnWidth(1)!=517
    reopened.accept();other.accept()


def test_wrong_work_version_rejected(app, workbook, session):
    with pytest.raises(ValueError, match='versão'):
        ui.AnaliseListaMaterialDialog(session, workbook_path=workbook,
            plan_name='0722_02_01_26_JF_VIVA', cutrite_folder=workbook.parent,
            user=SimpleNamespace(role='admin', username='Teste'))


def test_streamlit_hours_saved_and_reloaded_without_network(app, workbook, session, monkeypatch):
    monkeypatch.setattr(ui, 'query_woodstore', lambda _: [])
    monkeypatch.setattr(ui.times, 'machines', lambda _: [{'id': 1, 'codigo': 'HPP300', 'nome': 'Serra', 'custo_hora': 40}])
    args = dict(workbook_path=workbook, plan_name='0722_01_01_26_JF_VIVA',
                cutrite_folder=workbook.parent, user=SimpleNamespace(role='admin', username='Teste'))
    dialog = ui.AnaliseListaMaterialDialog(session, **args)
    data = ui.times.summarize([{'bd_key':'2026_0722_01_01','bd_versao':'01'}],
        [{'id':1,'bd_key':'2026_0722_01_01','operacao':'corte','maquina':'HPP300','tempo_gasto_minutos':90}],2026,'0722','01')
    dialog._receive_times(data)
    assert dialog.times_table.rowCount()==8
    line=next(l for l in dialog.lines if l.get('machine')=='HPP300')
    assert ui.svc.calculate_cost(line,dialog.prices[line['key']])[0]==60
    dialog._save()
    dialog.close()
    reopened=ui.AnaliseListaMaterialDialog(session, **args)
    assert reopened.production['queried_at']==data['queried_at']
    assert reopened.prices[line['key']]['net']=='40'
    reopened._times_failed('Falha de consulta')
    assert reopened.production['last_query_error']=='Falha de consulta'
    assert reopened.events_table.rowCount()==1
    reopened.close()


def test_dialogo_abre_sem_a_base_dos_catalogos(app, workbook, session, monkeypatch):
    """Sem a base martelo_catalogos, o diálogo abre a avisar — não rebenta.

    As referências passaram a vir da base (Fase 3). Se ela não existir ou não
    estiver acessível, o erro subia até ao QMessageBox e o diálogo abria com um
    aviso modal por cima; num teste sem ninguém para carregar em OK, ficava lá
    para sempre. A degradação tem de ser a mesma de quando faltava o Excel: uma
    linha de aviso e a associação manual à mão.
    """
    monkeypatch.setattr(ui, 'query_woodstore', lambda _: [])
    dialog = ui.AnaliseListaMaterialDialog(
        session, workbook_path=workbook, plan_name='0722_01_01_26_JF_VIVA',
        cutrite_folder=workbook.parent,
        user=SimpleNamespace(role='admin', username='Teste'),
    )
    assert dialog.references == []
    assert any('Catálogo dos fornecedores indisponível' in aviso
               for aviso in dialog.warnings)
