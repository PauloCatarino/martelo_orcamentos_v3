from decimal import Decimal
import pytest
from app.services import tempos_lista_material_service as t
from app.services.analise_lista_material_service import calculate_cost


def header(key, version='01', **extra):
    return {'bd_key': key, 'bd_versao': version, **{v[1]: 'N' for v in t.SECTORS.values()}, **extra}


def event(id, key, minutes, stage='corte', **extra):
    return {'id': id, 'bd_key': key, 'tempo_gasto_minutos': minutes, 'operacao': stage, 'maquina': 'HPP300', **extra}


def test_queries_select_only_model_scoped_and_special_separate():
    for order in ('0722', '_0058', '-058', 'A013'):
        queries = t.queries(2026, order, '01')
        for q in queries:
            t.st.assert_select_only(q)
            assert 'TRY_CONVERT(int,ce.bd_modelo)=1' in q
            assert 'bd_versao=' not in q
        assert 'WHERE EXISTS' in queries[1]
        assert ('CadernoEncargos_ ce' in queries[0]) == (order != '0722')
    with pytest.raises(ValueError):
        t.queries(2026, "1' OR 1=1", '01')


def test_versions_sum_without_rounding_or_multiplying_events():
    result = t.summarize([header('v1'), header('v2','02')],
                         [event(1,'v1','60,5'),event(2,'v2','59.5'),event(3,'other',900)],2026,'0722','01')
    cutting = next(s for s in result['sectors'] if s['sector']=='corte')
    assert cutting['hours'] == '2.0'
    assert len(result['events']) == 2
    assert result['versions'] == ['01','02']
    assert result['lines'][0]['quantity'] == '2.0'


def test_all_eight_sectors_aliases_invalid_not_zero():
    history = [event(i,'v1',60,stage) for i,stage in enumerate(t.SECTORS)]
    history += [event(9,'v1','oops','orla'), event(10,'v1',-1,'cnc'),event(11,'v1',60,'CADERNO ENCARGOS')]
    result = t.summarize([header('v1')],history,2026,'722','01')
    assert len(result['sectors']) == 8
    assert all(Decimal(s['hours'])==1 for s in result['sectors'])
    assert len([l for l in result['lines'] if l['quantity'] is None]) == 2
    assert len(result['events']) == 10


def test_not_applicable_and_no_history_distinguished():
    result = t.summarize([header('v1',bd_corte_ok='100',bd_montagem_ok='0',bd_existe_montagem='0')],[],2026,'722','01')
    assert len(result['lines']) == 1
    assert result['lines'][0]['sector'] == 'corte'
    assert next(s for s in result['sectors'] if s['sector']=='montagem')['state'] == 'Não aplicável'
    missing = t.summarize([],[],2026,'722','01')
    assert len(missing['lines']) == 8
    assert all(s['state']=='Obra/modelo não encontrado' for s in missing['sectors'])


def test_duplicate_join_keys_fail_closed_but_identical_sessions_count():
    with pytest.raises(ValueError):
        t.summarize([header('v1'),header('v1')],[],2026,'722','01')
    with pytest.raises(ValueError):
        t.summarize([header('v1')],[event(1,'v1',60),event(1,'v1',60)],2026,'722','01')
    result=t.summarize([header('v1')],[event(1,'v1',60),event(2,'v1',60)],2026,'722','01')
    assert result['lines'][0]['quantity']=='2'


def test_machine_price_exact_only_snapshot_and_unknown_rate():
    line={'kind':'Produção','quantity':'2','unit':'h','machine':'HPP300'}
    machine={'id':1,'codigo':'HPP300','nome':'Serra','custo_hora':Decimal('40')}
    snapshot=t.match_machine(line,[machine])
    machine['custo_hora']=Decimal('60')
    assert calculate_cost(line,snapshot)[0] == Decimal('80')
    assert calculate_cost(line,t.machine_price(machine))[0] == Decimal('120')
    assert t.match_machine({**line,'machine':'HPP301'},[machine]) is None
    machine['custo_hora']=None
    assert calculate_cost(line,t.machine_price(machine))[0] is None


def test_estimates_sum_known_versions_not_missing_as_zero():
    result=t.summarize([header('v1',bd_tempo_corte_minutos=60),header('v2','02',bd_tempo_corte_minutos=120)],[],2026,'722','01')
    assert next(s for s in result['sectors'] if s['sector']=='corte')['estimated']=='3'
    assert next(s for s in result['sectors'] if s['sector']=='stock')['estimated'] is None
