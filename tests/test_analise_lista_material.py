import json
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from app.services import analise_lista_material_service as svc
from app.services.permission_service import (
    DEFAULT_USER_PERMISSIONS, PERMISSAO_ANALISE_LISTA_MATERIAL,
    PERMISSAO_CUSTOS_LISTA_MATERIAL, PERMISSAO_CORRIGIR_LISTA_MATERIAL,
)


def ptn(path, area='12.34', total=None):
    path.write_text('VER,V12.00.5.1,2.15\nFN1,' + path.stem + '\nSUM1,7.31,' + (total or area) +
                    '\nMAT1,AGL_BRANCO_12MM,descricao,12,0,,10,23,7.31,0,7,' + area + '\n', encoding='cp1252')
    return path


def test_plans_accumulate_only_same_version_and_flag_missing_result(tmp_path):
    ptn(tmp_path / '0418_01_01_26_JF_VIVA.ptn')
    ptn(tmp_path / '0418_01_03_26_JF_VIVA.ptn', '2.10')
    ptn(tmp_path / '0418_02_01_26_JF_VIVA.ptn', '99')
    (tmp_path / '0418_01_02_26_JF_VIVA.ctt').write_text('x')
    plans, warnings = svc.discover_plans(tmp_path, '0418_01_01_26_JF_VIVA')
    assert len(plans) == 2
    assert len(warnings) == 1 and '01_02' in warnings[0]
    assert svc.board_cost_lines(plans)[0]['quantity'] == '14.44'
    with pytest.raises(ValueError, match='duplicado'):
        svc.board_cost_lines(plans + plans[:1])
    with pytest.raises(ValueError, match='versões'):
        svc.board_cost_lines(plans + [svc.read_plan(tmp_path / '0418_02_01_26_JF_VIVA.ptn')])


def test_ptn_uses_whole_board_area_and_rejects_bad_summary(tmp_path):
    path = ptn(tmp_path / '0722_01_01_26_JF_VIVA.ptn')
    assert svc.read_plan(path)['total'] == '12.34'
    ptn(path, total='99')
    with pytest.raises(ValueError, match='reconciliados'):
        svc.read_plan(path)
    path.write_text('VER,V13,3\n')
    with pytest.raises(ValueError, match='Formato'):
        svc.read_plan(path)


def test_material_suggestions_consider_thickness_family_and_finish():
    catalog = [dict(Codigo=c, Espessura=e, Disponivel=0) for c, e in [
        ('AGL_MLM_BRANCO_B3768/SC_19MM', 19),
        ('AGL_MLM_BRANCO_B3768/SC_12MM', 12),
        ('MDF_MLM_BRANCO_B3768/SC_19MM', 19),
        ('AGL_MLM_BRANCO_B3768/ST10_19MM', 19),
    ]]
    # Repeated stock rows must not produce duplicate material choices.
    matches = svc.material_candidates('AGL_MLM_BRANCO_B3768/SC_19M', catalog + catalog[:1], 19)
    assert matches[0]['code'] == catalog[0]['Codigo']
    assert len(matches) == 2
    assert 'Confirmar decoração/acabamento' in matches[1]['reason']


@pytest.mark.parametrize('size,expected', [('1.0H22', '22'), ('0.4H22', '22'), ('15 x 0.4', '15'), ('', None)])
def test_edge_width(size, expected):
    assert svc.edge_width(size) == (Decimal(expected) if expected else None)


def test_cost_units_missing_prices_and_no_second_waste():
    line = svc.cost_line('Orlas', 'x', 'PVC', 100, 'ml', width='22')
    assert svc.calculate_cost(line, {'net': '10', 'unit': 'm²'})[0] == Decimal('22')
    assert svc.calculate_cost(line, {'net': '.20', 'unit': 'ml'})[0] == Decimal('20')
    assert svc.calculate_cost(line, {'net': None, 'unit': 'ml'})[0] is None
    assert svc.calculate_cost(line, None)[0] is None
    assert svc.calculate_cost(line, {'net': '1', 'unit': 'un'})[0] is None
    assert svc.calculate_cost(line, {'net': '0', 'unit': 'ml'}) == (Decimal(0), 'Preço líquido zero — confirmar')


def test_hardware_includes_hidden_hardware_but_not_imos_prices():
    rows = [('Nome iMos (Nome Uniao)', 'Ref PHC', 'Qt', 'Un', 'Na lista', '€ / un'),
            ('CAVILHA', 'FF00001', 30, 'un', 'fora', 99),
            ('TOTAL', '', 999, '', '', '')]
    result = svc.hardware_rows(rows)
    assert len(result) == 1
    assert result[0]['quantity'] == '30'
    assert '99' not in str(result)


def test_purchased_parts_without_imos_name_are_not_lost_and_reordering_keeps_key():
    header = ('Nome iMos (Nome Uniao)', 'Ref PHC', 'Qt', 'Un', 'Descricao')
    article = ('', '(?)', 2, 'un', 'Objeto Comprado PURCH')
    second = ('TULHA', '(?)', 1, '', 'Tulha')
    result = svc.hardware_rows([header, ('PURCHASED PARTS',), article, second])
    reverse = svc.hardware_rows([header, ('PURCHASED PARTS',), second, article])
    assert len(result) == 2
    assert result[0]['kind'] == 'Comprados'
    assert result[0]['key'] == reverse[1]['key']
    assert svc.calculate_cost(result[1], {'net': 2, 'unit': 'un'})[0] is None


def test_exact_mp_mapping_does_not_resolve_ambiguous_references():
    def mp(i):
        return SimpleNamespace(id=i, nome_imos='X', ref_phc='FF1', ref_le='FF1', descricao='x', unidade='un', preco_liquido=Decimal('2'))
    line = svc.cost_line('Ferragens', 'x', 'X', 1, 'un', ref_phc='FF1')
    assert svc.exact_price(line, [mp(1)])['net'] == '2'
    assert svc.exact_price(line, [mp(1), mp(2)]) is None


def test_snapshots_keep_price_history_and_version_separate(tmp_path):
    path = tmp_path / 'Lista_Material_0722_01_26_JF_VIVA.xlsx'
    path.write_text('book')
    old = svc.save_snapshot(path, {'version': '0722_01_26_JF_VIVA', 'prices': {'x': {'net': '2'}}})
    svc.save_snapshot(path, {'version': '0722_01_26_JF_VIVA', 'prices': {'x': {'net': '3'}}})
    assert '"2"' in old.read_text()
    assert svc.latest_snapshot(path, '0722_01_26_JF_VIVA')['prices']['x']['net'] == '3'
    assert svc.latest_snapshot(path, '0722_02_26_JF_VIVA') == {}


def test_original_and_stale_workbook_rejected_before_excel(tmp_path):
    path = tmp_path / 'ORIGINAL' / 'book.xlsx'
    path.parent.mkdir()
    path.write_text('x')
    with pytest.raises(ValueError, match='consulta'):
        svc.apply_material_codes(path, svc.fingerprint(path), {'A': 'B'}, 'Paulo')
    with pytest.raises(ValueError, match='consulta'):
        svc.save_snapshot(path, {})
    target = tmp_path / 'book.xlsx'
    target.write_text('new')
    with pytest.raises(ValueError, match='mudou'):
        svc.apply_material_codes(target, 'oldhash', {'A': 'B'}, 'Paulo')


def test_permissions_opt_in():
    for key in (PERMISSAO_ANALISE_LISTA_MATERIAL, PERMISSAO_CUSTOS_LISTA_MATERIAL, PERMISSAO_CORRIGIR_LISTA_MATERIAL):
        assert DEFAULT_USER_PERMISSIONS[key] is False


def test_read_workbook_retains_width_and_quantities(tmp_path):
    path = tmp_path / 'x.xlsx'
    w = Workbook()
    w.active.title = 'LISTAGEM_CUT_RITE'
    w.active.append(['Title'])
    w.active.append(['Material', 'Descricao', 'Qt', 'Esp'])
    w.active.append(['AGL_19MM', 'TETO', 2, 19])
    s = w.create_sheet('ResumoOrlas')
    s.append(['Material', 'Nome_Orlas', 'ML_QT', 'LARG X ESP'])
    s.append(['AGL_19MM', 'PVC_1.0_BRANCO', 100, '22 x 1.0'])
    w.save(path)
    assert svc.read_material_inputs(path)[0].quantity == 2
    lines, warnings = svc.workbook_cost_lines(path)
    assert lines[0]['width'] == '22'
    assert lines[0]['quantity'] == '100'
    assert len(warnings) == 1


def test_o_snapshot_mais_recente_nao_depende_do_relogio(tmp_path, monkeypatch):
    """Dois snapshots no mesmo tique do relógio: vale o segundo, sempre.

    O relógio do Windows anda aos saltos de cerca de um milissegundo, por isso
    duas gravações seguidas ficam com o mesmo carimbo no nome. Aqui o relógio
    é congelado de propósito, para o empate ser garantido em vez de sair uma
    vez em cada dez — e o que se exige é que a análise reabra com os preços
    novos, não com os antigos.
    """
    class _RelogioParado:
        @staticmethod
        def now():
            return datetime(2026, 9, 10, 22, 40, 7, 449717)

    monkeypatch.setattr(svc, 'datetime', _RelogioParado)
    path = tmp_path / 'Lista_Material_0722_01_26_JF_VIVA.xlsx'
    path.write_text('book')

    for preco in ('2', '3', '4'):
        svc.save_snapshot(path, {'version': '0722_01_26_JF_VIVA',
                                 'prices': {'x': {'net': preco}}})

    nomes = sorted(p.name for p in (path.parent / 'Analise_Lista_Material').glob('*.json'))
    assert len(nomes) == 3
    assert len({n.split('_')[3] for n in nomes}) == 3, "o contador tem de ser unico"
    assert svc.latest_snapshot(path, '0722_01_26_JF_VIVA')['prices']['x']['net'] == '4'


def test_um_snapshot_do_formato_antigo_nunca_ganha_ao_novo(tmp_path):
    """Quem já tem a pasta cheia não pode ver o histórico trocado."""
    path = tmp_path / 'Lista_Material_0722_01_26_JF_VIVA.xlsx'
    path.write_text('book')
    pasta = path.parent / 'Analise_Lista_Material'
    pasta.mkdir()
    antigo = pasta / '20260910_224007_449717_ff999999.json'
    antigo.write_text(json.dumps({'version': '0722_01_26_JF_VIVA',
                                 'workbook': path.name,
                                 'prices': {'x': {'net': '2'}}}), encoding='utf-8')

    svc.save_snapshot(path, {'version': '0722_01_26_JF_VIVA', 'prices': {'x': {'net': '3'}}})

    assert svc.latest_snapshot(path, '0722_01_26_JF_VIVA')['prices']['x']['net'] == '3'
