"""Custo de produção da Lista Material: separadores, horas × €/h do Martelo.

Pedido do Paulo (24-09-2026), obra de referência 1357_01_26_JF_VIVA:
- a tabela do custo separa placas | orlas | ferragens | purch | spp com uma
  linha vazia de outra cor, e a produção sai de lá (vive nos Tempos por setor);
- o quadro dos tempos leva SEMPRE o €/h das máquinas do Martelo, haja ou não
  horas no Streamlit; onde não houver, diz para o acrescentar nas Definições.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest
from openpyxl import Workbook
from PySide6.QtWidgets import QApplication

from app.models import DefMaquina
from app.services import analise_lista_material_service as svc
from app.services import custo_ferragens_service as custo
from app.services import tempos_lista_material_service as t
from app.services.def_maquina_service import (
    DefMaquinaService,
    chave_nome_streamlit,
    normalizar_nomes_streamlit,
)
from app.ui.dialogs import analise_lista_material_dialog as ui

# As máquinas da base real a 24-09-2026 (custo/hora STD).
CATALOGO = [
    {'id': 1, 'codigo': 'CORTE', 'nome': 'Corte', 'custo_hora': Decimal('80'), 'nomes_streamlit': None},
    {'id': 2, 'codigo': 'ORLAGEM', 'nome': 'Orlagem', 'custo_hora': Decimal('90'), 'nomes_streamlit': None},
    {'id': 6, 'codigo': 'CNC_ABD', 'nome': 'CNC ABD', 'custo_hora': Decimal('30'), 'nomes_streamlit': 'ABD'},
    {'id': 7, 'codigo': 'CNC_VERTICAL', 'nome': 'CNC Vertical', 'custo_hora': Decimal('60'),
     'nomes_streamlit': 'V310'},
    {'id': 4, 'codigo': 'MONTAGEM', 'nome': 'Montagem', 'custo_hora': Decimal('40'), 'nomes_streamlit': None},
    {'id': 10, 'codigo': 'EMBALAMENTO', 'nome': 'Embalamento', 'custo_hora': Decimal('30'), 'nomes_streamlit': None},
    {'id': 5, 'codigo': 'MANUAL', 'nome': 'Manual', 'custo_hora': Decimal('20'), 'nomes_streamlit': None},
]


def _linha(stage, machine='', horas='1'):
    return svc.cost_line('Produção', f'{stage}|{machine or "pendente"}', stage, horas, 'h',
                         sector=stage, machine=machine)


def test_nomes_do_streamlit_ignoram_espacos_maiusculas_e_repetidos():
    assert chave_nome_streamlit('HKL 300') == chave_nome_streamlit('hkl300') == chave_nome_streamlit('HKL-300')
    assert normalizar_nomes_streamlit(' HKL 300 ;hkl300,\nOrla  2, ') == 'HKL 300, Orla 2'
    assert normalizar_nomes_streamlit('  ') is None


@pytest.mark.parametrize('stage, machine, codigo, como', [
    ('cnc', 'ABD', 'CNC_ABD', 'pelo nome'),              # nome escrito na máquina
    ('cnc', 'v 310', 'CNC_VERTICAL', 'pelo nome'),       # espaços/maiúsculas não contam
    ('corte', 'HKL 300', 'CORTE', 'pelo setor'),         # sem nome: vale o setor
    ('orlagem', 'Orla 2', 'ORLAGEM', 'pelo setor'),
    ('embalagem', 'Embalagem', 'EMBALAMENTO', 'pelo nome'),  # Embalamento no V3 = Embalagem
    ('montagem', '', 'MONTAGEM', 'pelo setor'),
])
def test_linha_de_horas_encontra_a_maquina_do_martelo(stage, machine, codigo, como):
    maquina, porque = t.procurar_maquina(_linha(stage, machine), CATALOGO)
    assert maquina['codigo'] == codigo
    assert porque.startswith(como)
    preco = t.match_machine(_linha(stage, machine), CATALOGO)
    assert preco['machine_id'] == maquina['id'] and preco['unit'] == 'h'


def test_sem_maquina_ou_com_nome_repetido_diz_para_ir_as_definicoes():
    maquina, porque = t.procurar_maquina(_linha('cnc', 'H600'), CATALOGO)
    assert maquina is None
    assert '«H600»' in porque and t.MENU_MAQUINAS in porque
    assert t.procurar_maquina(_linha('stock'), CATALOGO)[0] is None
    repetido = CATALOGO + [{'id': 99, 'codigo': 'CNC_5', 'nome': 'CNC 5', 'custo_hora': 90, 'nomes_streamlit': 'abd'}]
    maquina, porque = t.procurar_maquina(_linha('cnc', 'ABD'), repetido)
    assert maquina is None and 'CNC_5' in porque and 'CNC_ABD' in porque
    texto, tem = t.descrever_tarifa(_linha('cnc', 'H600'), None)
    assert not tem and t.MENU_MAQUINAS in texto
    texto, tem = t.descrever_tarifa(_linha('corte'), {'ref': 'CORTE', 'description': 'Corte', 'net': None})
    assert not tem and 'sem custo/hora' in texto


def test_cada_setor_tem_sempre_uma_linha_pela_ordem_dos_setores():
    linhas = t.completar_setores([_linha('cnc', 'ABD'), _linha('corte', 'HKL 300')],
                                 [{'sector': 'montagem', 'state': 'Não aplicável'}])
    assert [l['sector'] for l in linhas] == list(t.ROTULOS)
    montagem = next(l for l in linhas if l['sector'] == 'montagem')
    assert montagem['quantity'] == '0' and 'não aplicável' in montagem['name']
    stock = next(l for l in linhas if l['sector'] == 'stock')
    assert stock['quantity'] is None and stock['key'] == 'stock|pendente'


def test_materiais_por_categoria_com_separadora_e_sem_producao():
    lines = [svc.cost_line(k, f'{k}:{i}', k, 1, 'un') for i, k in enumerate(
        ('SPP', 'Ferragens', 'Produção', 'Placas', 'Comprados', 'Orlas', 'Ferragens'))]
    rows = svc.linhas_por_categoria(lines)
    kinds = [r['kind'] if r else '|' for r in rows]
    assert kinds == ['Placas', '|', 'Orlas', '|', 'Ferragens', 'Ferragens', '|', 'Comprados', '|', 'SPP']
    assert svc.linhas_por_categoria([]) == []


def test_rigor_pede_o_euro_hora_das_linhas_com_horas():
    lines = [_linha('corte', 'HKL 300', '4'), _linha('cnc', 'H600', '1.17'), _linha('montagem', '', '0')]
    precos = {lines[0]['key']: t.machine_price(CATALOGO[0])}
    estado = custo.estado_do_custo('Arquivado', lines, precos, [], {})
    ponto = next(p for p in estado.pontos if 'Tarifas de produção' in p[1])
    assert ponto == (False, 'Tarifas de produção: 1 de 2 linhas com €/h do V3 — ver o separador Tempos por setor')


def test_memorizar_nome_streamlit_fica_numa_so_maquina(session):
    for codigo, nomes in (('CNC_ABD', None), ('CNC_VERTICAL', 'V310, H600')):
        session.add(DefMaquina(codigo=codigo, nome=codigo, custo_hora=Decimal('30'), nomes_streamlit=nomes))
    session.commit()
    abd = session.query(DefMaquina).filter_by(codigo='CNC_ABD').one()
    retirado = DefMaquinaService(session).memorizar_nome_streamlit(abd.id, ' h600 ')
    assert retirado == ['CNC_VERTICAL']
    assert abd.nomes_streamlit == 'h600'
    assert session.query(DefMaquina).filter_by(codigo='CNC_VERTICAL').one().nomes_streamlit == 'V310'
    # Repetir não duplica.
    assert DefMaquinaService(session).memorizar_nome_streamlit(abd.id, 'H600') == []
    assert abd.nomes_streamlit == 'h600'


# ---- Diálogo ------------------------------------------------------------------

@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


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
    for codigo, custo_hora, nomes in (('CORTE', 80, None), ('CNC_ABD', 30, 'ABD'), ('MONTAGEM', 40, None)):
        session.add(DefMaquina(codigo=codigo, nome=codigo.title(), custo_hora=Decimal(custo_hora),
                               nomes_streamlit=nomes, ativo=True))
    session.commit()
    monkeypatch.setattr(ui, 'query_woodstore', lambda _: [])
    monkeypatch.setattr(ui.custo_ferragens, 'ler_precos_phc', lambda _s, refs: {})
    return ui.AnaliseListaMaterialDialog(
        session, workbook_path=workbook, plan_name='1357_01_01_26_JF_VIVA', cutrite_folder=workbook.parent,
        user=SimpleNamespace(role='admin', username='paulo'), obra_info={'estado': 'Arquivado'})


def _consulta():
    header = {'bd_key': '2026_1357_01_01', 'bd_versao': '01', 'bd_corte_ok': '100', 'bd_cnc_ok': '100'}
    eventos = [
        {'id': 1, 'bd_key': '2026_1357_01_01', 'operacao': 'Corte', 'maquina': 'HKL 300', 'tempo_gasto_minutos': 240},
        {'id': 2, 'bd_key': '2026_1357_01_01', 'operacao': 'CNC', 'maquina': 'ABD', 'tempo_gasto_minutos': 75},
        {'id': 3, 'bd_key': '2026_1357_01_01', 'operacao': 'CNC', 'maquina': 'H600', 'tempo_gasto_minutos': 70},
    ]
    return t.summarize([header], eventos, 2026, '1357', '01')


def test_tabela_do_custo_separa_categorias_e_nao_tem_producao(app, session, workbook, monkeypatch):
    dialog = _dialog(session, workbook, monkeypatch)
    try:
        dialog._receive_times(_consulta())
        rows = dialog._cost_rows
        assert all(r is None or r['kind'] != 'Produção' for r in rows)
        kinds = [r['kind'] if r else '|' for r in rows]
        assert kinds == ['Orlas', '|', 'Ferragens']
        separadora = kinds.index('|')
        assert dialog.cost_table.rowHeight(separadora) == 8
        assert dialog.cost_table.verticalHeaderItem(separadora).text() == ''
        assert dialog.cost_table.verticalHeaderItem(2).text() == '2'
        assert dialog._line_at(separadora) is None
        # Com uma categoria no filtro, a separadora esconde-se.
        dialog.category_filter.setCurrentText('Ferragens')
        assert dialog.cost_table.isRowHidden(separadora)
        assert 'Produção (Tempos por setor): 357.50 €' in dialog.cost_summary.text()
        assert 'Produção' not in [dialog.category_filter.itemText(i) for i in range(dialog.category_filter.count())]
    finally:
        dialog.close()


def test_tempos_por_setor_tem_euro_hora_e_associar_memoriza(app, session, workbook, monkeypatch):
    dialog = _dialog(session, workbook, monkeypatch)
    try:
        # Sem consulta: desenho, Cut-Rite e os 8 setores já aparecem, com o €/h do Martelo.
        assert dialog.times_table.rowCount() == 10
        dialog._receive_times(_consulta())
        rows = {(l['sector'], l['machine']): i for i, l in enumerate(dialog._times_rows)}
        assert dialog.times_table.rowCount() == 11    # CNC tem duas máquinas
        corte = rows[('corte', 'HKL 300')]
        assert dialog.times_table.item(corte, 5).text() == '80.00'
        assert dialog.times_table.item(corte, 6).text() == '320.00'
        h600 = rows[('cnc', 'H600')]
        assert t.MENU_MAQUINAS in dialog.times_table.item(h600, 7).text()
        assert 'sem €/h' in dialog.times_summary.text()

        dialog.times_table.setCurrentCell(h600, 7)
        monkeypatch.setattr(ui.QInputDialog, 'getItem',
                            lambda *a, **k: (next(x for x in a[3] if x.startswith('CNC_ABD')), True))
        dialog._associate_machine()
        assert dialog.times_table.item(h600, 6).text() == f'{Decimal(70) / 60 * 30:.2f}'
        abd = session.query(DefMaquina).filter_by(codigo='CNC_ABD').one()
        assert abd.nomes_streamlit == 'ABD, H600'
        assert 'memorizado' in dialog.times_status.text()
    finally:
        dialog.close()


def test_maquina_dialog_guarda_nomes_streamlit_e_mostra_euro_hora_no_corte(app):
    from app.ui.dialogs.maquina_dialog import MaquinaDialog

    dialog = MaquinaDialog()
    try:
        dialog.codigo_input.setText('CORTE')
        dialog.nome_input.setText('Corte')
        dialog.tipo_input.setCurrentIndex(dialog.tipo_input.findData('CORTE'))
        dialog.nomes_streamlit_input.setText('HKL 300')
        assert dialog.get_data().nomes_streamlit == 'HKL 300'
        assert not dialog.hora_section.isHidden()
        assert dialog.nomes_streamlit_input.toolTip()
    finally:
        dialog.close()
