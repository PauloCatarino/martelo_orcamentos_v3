from decimal import Decimal
from types import SimpleNamespace as NS
from sqlalchemy import event
from app.models.system_setting import SystemSetting
import json

import pytest

from app.models.def_materia_prima import DefMateriaPrima
from app.services import analise_lista_material_service as svc
from app.services import analise_custo_mapeamento_service as maps
from app.services.placas_referencias_service import LinhaReferencia


def test_global_mapping_reused_with_current_price_and_keeps_history(session):
    a = DefMateriaPrima(descricao='AGL LINHO', ref_le='PLC1', unidade='M2', preco_liquido=Decimal('5'))
    b = DefMateriaPrima(descricao='AGL LINHO NOVO', ref_le='PLC2', unidade='M2', preco_liquido=Decimal('7'))
    session.add_all([a,b]); session.commit()
    line = svc.cost_line('Placas', 'obra1', 'AGL_LINHO_19MM', 10, 'm2', thickness='19')
    maps.save_mapping(session,line,a,'Paulo')
    frozen = svc.price_record(a)
    a.preco_liquido = Decimal('6'); session.commit()
    other = {**line,'key':'obra2','quantity':'42'}
    price = maps.resolve_price(other,[a,b],maps.load_mappings(session))
    assert Decimal(price['net']) == 6
    assert Decimal(frozen['net']) == 5
    maps.save_mapping(session,line,b,'Paulo')
    mapping = maps.load_mappings(session)[maps.mapping_key(line)]
    assert mapping['mp_id'] == b.id
    assert mapping['history'][0]['mp_id'] == a.id


def test_mapping_does_not_write_or_lock_protected_settings(session):
    mp=DefMateriaPrima(descricao='Linho 10',ref_le='PLC10',unidade='M2')
    session.add(mp);session.commit()
    line=svc.cost_line('Placas','x','AGL_MLM_LINHO_CANCUN_10MM',1,'m2',thickness='10')
    key=maps.mapping_key(line)
    original=json.dumps({'mp_id':999,'history':[]})
    session.add(SystemSetting(chave=key,valor=original));session.commit()
    def guard(conn,cursor,statement,parameters,context,executemany):
        upper=statement.upper()
        if 'SYSTEM_SETTINGS' in upper:
            assert upper.lstrip().startswith('SELECT')
            assert 'FOR UPDATE' not in upper
    engine=session.get_bind()
    event.listen(engine,'before_cursor_execute',guard)
    try:
        maps.save_mapping(session,line,mp,'Paulo')
        saved=maps.load_mappings(session)[key]
        assert saved['mp_id']==mp.id
        assert saved['history'][0]['mp_id']==999
        assert session.query(SystemSetting).filter_by(chave=key).one().valor==original
    finally:
        event.remove(engine,'before_cursor_execute',guard)


def test_hardware_sources_prioritize_job_and_exclude_other_versions(tmp_path):
    job=tmp_path/'job';job.mkdir()
    output=tmp_path/'imos';output.mkdir()
    path=job/'Lista_Material_0722_01_26_JF_VIVA.xlsm'
    correct=output/'0722_01_26_JF_VIVA_5_Custo_Obra_Ferragens_V1.xlsx';correct.write_bytes(b'x')
    (output/'1523_01_26_JF_VIVA_5_Custo_Obra_Ferragens_V1.xlsx').write_bytes(b'x')
    assert svc.hardware_sources(path,'0722_01_26_JF_VIVA',output)==[correct]
    local=job/'5_Custo_Obra_Ferragens.xlsx';local.write_bytes(b'x')
    assert svc.hardware_sources(path,'0722_01_26_JF_VIVA',output)==[local]


def test_mapping_distinguishes_edge_width_and_union_set():
    a = svc.cost_line('Orlas','a','PVC_1.0_BRANCO',10,'ml',board='AGL_BRANCO_19MM',width='22')
    assert maps.mapping_key(a) != maps.mapping_key({**a,'width':'33'})
    a = svc.cost_line('Ferragens','a','DOBRADICA',2,'un',union_set='JOGO_1')
    assert maps.mapping_key(a) != maps.mapping_key({**a,'union_set':'JOGO_2'})


def test_egger_group_requires_exact_decor_finish_and_nominal_thickness():
    ref = LinhaReferencia('EGGER','H1365','ST12','Carvalho','7','Tableros partículas','EGGER',{})
    def mp(i, esp, group):
        return NS(id=i,ref_le=f'PLC{i}',ref_phc=None,nome_imos=None,descricao=f'AGL MLM EGGER GRUPO {group}',espessura=Decimal(esp),unidade='M2',preco_liquido=Decimal('8'))
    line = svc.cost_line('Placas','x','AGL_MLM_CARVALHO_H1365/ST12_19MM',10,'m2',thickness='19.2')
    catalog=[mp(1,'19','7'),mp(2,'8','7'),mp(3,'19','8')]
    assert maps.resolve_price(line,catalog,{},[ref])['id'] == 1
    assert maps.resolve_price({**line,'name':line['name'].replace('ST12','ST10')},catalog,{},[ref]) is None


def test_component_never_applies_parent_kit_price_to_each_child():
    line = svc.cost_line('Ferragens','x','DOB',2,'un',union_name='DOB',union_set='JOGO1',ref_phc='FF1')
    c = NS(id=10,nome_jogo_imos='JOGO1',nome_imos='DOB',ref_phc='FF1',componente_materia_prima_id=None,preco_liquido=None)
    assert maps.component_price(line,[],[c]) is None
    c.preco_liquido=Decimal('2');c.descricao='Dobradiça individual'
    assert maps.component_price(line,[],[c])['net'] == '2'
    assert maps.component_price({**line,'union_set':'JOGO2'},[],[c]) is None


def test_empty_edge_summary_calculates_existing_excel_rule():
    row=NS(material='AGL_BRANCO_19MM',quantity=Decimal(2),values={
        'Comp':1000.9,'Larg':500,'Esp':19.4,'Orla ESQ':'PVC_1.0_BRANCO','Orla DIR':'PVC_1.0_BRANCO'})
    lines,warnings=svc.calculated_edges([row])
    assert not warnings
    assert lines[0]['quantity']=='5'  # ceil(4 ml * 1.08), desperdício uma única vez
    assert lines[0]['width']=='22'
    assert lines[0]['thickness']=='1.0'
    assert svc.calculate_cost(lines[0],{'net':'10','unit':'m2'})[0] == Decimal('1.10')


def test_source_is_transferred_with_short_name_only_after_verification(tmp_path):
    job=tmp_path/'obra';job.mkdir()
    book=job/'Lista_Material_0722_01_26_JF_VIVA.xlsm';book.write_bytes(b'book')
    incoming=tmp_path/'0722_01_26_JF_VIVA_5_Custo_Obra_Ferragens_V1.xlsx';incoming.write_bytes(b'xlsx')
    destination=svc.archive_hardware_file(book,incoming)
    assert destination.name=='5_Custo_Obra_Ferragens.xlsx'
    assert destination.read_bytes()==b'xlsx'
    assert not incoming.exists()
    assert svc.archive_hardware_file(book,destination)==destination


def test_transfer_collision_preserves_both_sources(tmp_path):
    book=tmp_path/'Lista_Material_0722_01_26_JF_VIVA.xlsm';book.write_bytes(b'book')
    incoming=tmp_path/'0722_01_26_JF_VIVA_5_Custo_Obra_Ferragens_V1.xlsx';incoming.write_bytes(b'new')
    destination=tmp_path/svc.HARDWARE_FILENAME;destination.write_bytes(b'old')
    with pytest.raises(ValueError,match='preservados'):
        svc.archive_hardware_file(book,incoming)
    assert incoming.read_bytes()==b'new' and destination.read_bytes()==b'old'


def test_hardware_dimensions_and_games_are_not_lost():
    header=('Nome iMos (Nome Uniao)','Ref PHC','Qt','Un','Comp','Larg','Esp','Jogo de Unioes (iMos)')
    lines=svc.hardware_rows([header,('SPP',),('PERFIL','FF1',10,'ml','511-2438',45,21,'JOGO1'),('PERFIL','FF1',3,'ml',500,45,21,'JOGO2')])
    assert len(lines)==2
    assert lines[0]['length']=='511-2438'
    assert lines[0]['width']=='45' and lines[0]['thickness']=='21'
    assert lines[0]['union_set']=='JOGO1'
