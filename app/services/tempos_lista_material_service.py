"""Tempos Streamlit: SELECT apenas; versão Martelo = modelo Streamlit.

Soma os lançamentos de todas as versões desse modelo, sem multiplicar o
histórico por joins. Não infere duração de máquina a partir de percentagens.
"""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import re
import unicodedata

from sqlalchemy import select
from app.models.def_maquina import DefMaquina
from app.services import streamlit_sql_service as st
from app.services.analise_lista_material_service import number, cost_line

SECTORS = {
    'stock': ('Stock', 'bd_stock_ok', None),
    'preparacao': ('Preparação', 'bd_preparacao_placas_ok', None),
    'corte': ('Corte', 'bd_corte_ok', 'bd_tempo_corte_minutos'),
    'orlagem': ('Orlagem', 'bd_orla_ok', 'bd_tempo_orla_minutos'),
    'cnc': ('CNC', 'bd_cnc_ok', 'bd_tempo_cnc_minutos'),
    'montagem': ('Montagem', 'bd_montagem_ok', 'bd_tempo_montagem_minutos'),
    'embalagem': ('Embalagem', 'bd_embalagem_ok', 'bd_tempo_embalamento_minutos'),
    'expedicao': ('Expedição', 'bd_expedicao_ok', 'bd_tempo_expedicao_minutos'),
}


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value or '').strip().lower())
                   if not unicodedata.combining(c))


def sector(value):
    value = norm(value)
    return {'orla': 'orlagem', 'embalamento': 'embalagem'}.get(value, value)


def queries(year, order, model):
    """Validate inputs before SQL interpolation; keep special orders separate."""
    order = str(order).strip().upper()
    if not re.fullmatch(r'(?:_|A|-)?\d+', order):
        raise ValueError('Número de encomenda inválido para consulta de tempos.')
    year, model = int(year), int(model)
    if not 2000 <= year <= 2100 or model < 1:
        raise ValueError('Ano/modelo inválido.')
    special = order[0] in '_-A'
    suffix = '_' if special else ''
    raw = "LTRIM(RTRIM(ce.bd_n_encomenda))"
    if special:
        prefixes = "('A')" if order[0] == 'A' else "('_','-')"
        predicate = f"LEFT({raw},1) IN {prefixes} AND TRY_CONVERT(bigint,SUBSTRING({raw},2,40))={int(order[1:])}"
    else:
        predicate = f"TRY_CONVERT(bigint,{raw})={int(order)} AND LEFT({raw},1) NOT IN ('_','-','A')"
    where = f"TRY_CONVERT(int,ce.bd_ano)={year} AND TRY_CONVERT(int,ce.bd_modelo)={model} AND {predicate}"
    fields = ['ce.bd_key', 'ce.bd_modelo', 'ce.bd_versao', 'ce.bd_existe_montagem', 'tp.bd_producao_serie']
    fields += [f'tp.{v}' for _, state, estimate in SECTORS.values() for v in (state, estimate) if v]
    headers = f"SELECT {','.join(fields)} FROM dbo.CadernoEncargos{suffix} ce LEFT JOIN dbo.TemposProducao{suffix} tp ON tp.bd_key=ce.bd_key WHERE {where}"
    history = (f"SELECT h.id,h.bd_key,h.operacao,h.maquina,h.responsavel,h.tempo_gasto_minutos,"
               f"h.percentagem_feita,CONVERT(varchar(23),h.data_registo,121) AS data_registo,h.bd_plano_corte "
               f"FROM dbo.TemposProducaoHistorico{suffix} h WHERE EXISTS (SELECT 1 FROM dbo.CadernoEncargos{suffix} ce "
               f"WHERE ce.bd_key=h.bd_key AND {where}) ORDER BY h.data_registo,h.id")
    for query in (headers, history):
        st.assert_select_only(query)
    return headers, history


def fetch(connection, year, order, model):
    headers, history = queries(year, order, model)
    return summarize(st.run_select(connection, headers), st.run_select(connection, history), year, order, model)


def summarize(headers, history, year, order, model):
    warnings = []
    by_key = {}
    for row in headers:
        key = row['bd_key']
        if key in by_key:
            raise ValueError('Cabeçalhos Streamlit duplicados; não é seguro somar tempos.')
        by_key[key] = row
    totals, grouped, invalid = defaultdict(Decimal), defaultdict(Decimal), defaultdict(int)
    events, seen = [], set()
    for row in history:
        if row['bd_key'] not in by_key:
            continue
        # Identical sessions are legitimate; only the database identity deduplicates.
        identity = row.get('id')
        if identity is not None:
            if identity in seen:
                raise ValueError('Lançamentos Streamlit duplicados; consulta por confirmar.')
            seen.add(identity)
        stage = sector(row.get('operacao'))
        if stage not in SECTORS:
            if stage != 'caderno encargos':
                warnings.append(f"Operação sem setor definido: {row.get('operacao')} (não imputada).")
            continue
        minutes = number(row.get('tempo_gasto_minutos'))
        if minutes is None or minutes < 0:
            invalid[stage] += 1
        else:
            totals[stage] += minutes
            if minutes > 0:
                grouped[(stage, str(row.get('maquina') or '').strip())] += minutes
        events.append({**row, 'setor': SECTORS[stage][0],
                       'horas': str(minutes / 60) if minutes is not None and minutes >= 0 else None})
    lines, sectors = [], []
    for stage, (label, state_column, estimate_column) in SECTORS.items():
        states = [str(r.get(state_column) if r.get(state_column) is not None else '').strip().upper() for r in headers]
        na = bool(states) and all(s == 'N' for s in states)
        if stage == 'montagem' and headers and all(str(r.get('bd_existe_montagem')).strip().lower() in ('0', 'false', 'n') for r in headers):
            na = True
        if invalid[stage]:
            state = 'Minutos inválidos — confirmar'
        elif na:
            state = 'Não aplicável' if not totals[stage] else 'Não aplicável com horas registadas — confirmar'
        elif not headers:
            state = 'Obra/modelo não encontrado'
        elif states and all(s in ('100', 'N') for s in states):
            state = 'Concluído' if totals[stage] else 'Concluído sem horas — confirmar'
        else:
            state = 'Em curso / estado por confirmar'
        estimates = [number(r.get(estimate_column)) for r in headers] if estimate_column else []
        estimated = sum(estimates, Decimal(0)) / 60 if estimates and all(x is not None and x >= 0 for x in estimates) else None
        hours = totals[stage] / 60
        sectors.append({'sector': stage, 'name': label, 'hours': str(hours),
                        'estimated': str(estimated) if estimated is not None else None,
                        'state': state, 'invalid': invalid[stage]})
        for (s, machine), minutes in grouped.items():
            if s == stage:
                lines.append(cost_line('Produção', f'{stage}|{machine}', f'{label} — {machine or "Máquina por identificar"}',
                                       str(minutes / 60), 'h', sector=stage, machine=machine))
        if invalid[stage] or (not totals[stage] and not na):
            lines.append(cost_line('Produção', f'{stage}|pendente', f'{label} — horas por apurar', None, 'h', sector=stage, machine=''))
    return {'year': int(year), 'order': str(order), 'model': str(model),
            'queried_at': datetime.now().isoformat(timespec='seconds'),
            'versions': sorted(str(r.get('bd_versao') or '') for r in headers),
            'keys': sorted(by_key), 'sectors': sectors, 'events': events, 'lines': lines,
            'warnings': list(dict.fromkeys(warnings)), 'complete': False}


def machines(session):
    columns = (DefMaquina.id, DefMaquina.codigo, DefMaquina.nome, DefMaquina.tipo, DefMaquina.custo_hora)
    return [dict(row._mapping) for row in session.execute(select(*columns).where(DefMaquina.ativo.is_(True)))]


def machine_price(machine):
    return {'id': machine['id'], 'machine_id': machine['id'], 'ref': machine['codigo'],
            'description': machine['nome'], 'unit': 'h',
            'net': str(machine['custo_hora']) if machine['custo_hora'] is not None else None,
            'date': datetime.now().isoformat(timespec='seconds'), 'mapping_source': 'Custo/hora máquina V3 (STD)'}


def match_machine(line, catalog):
    matches = [m for m in catalog if norm(line.get('machine')) and norm(line['machine']) in (norm(m['codigo']), norm(m['nome']))]
    return machine_price(matches[0]) if len(matches) == 1 else None
