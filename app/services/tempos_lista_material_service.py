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
from app.services.def_maquina_service import chave_nome_streamlit, separar_nomes_streamlit

#: Onde se definem as máquinas e o custo/hora (o Martelo é a referência).
MENU_MAQUINAS = 'Configurações › Operações / Máquinas'

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

# Antes da produção (pedido do Paulo, 24-09-2026): o desenho da obra no iMos e o
# plano de corte no Cut-Rite com a Lista Material. Não são lançamentos: são um
# valor por modelo no CadernoEncargos, com a data em que ficaram concluídos.
# setor: (rótulo, «máquina» no quadro, coluna, divisor para horas, coluna da data)
PREPARACAO_CE = {
    'desenho': ('Preparação (Desenho)', 'Desenho', 'bd_desenho_horas', 1, 'bd_desenho_finalizado'),
    'plano_corte': ('Preparação (Cut-Rite)', 'Cut-Rite', 'bd_corte_minutos', 60, 'bd_corte_finalizado'),
}

#: Todos os setores do custo de produção, pela ordem do trabalho.
ROTULOS = {**{k: v[0] for k, v in PREPARACAO_CE.items()}, **{k: v[0] for k, v in SECTORS.items()}}


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
    fields += [f'ce.{v}' for _, _, column, _, done in PREPARACAO_CE.values() for v in (column, done)]
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
    lines, sectors = _preparacao_do_caderno(headers)
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
    lines = completar_setores(lines, sectors)
    return {'year': int(year), 'order': str(order), 'model': str(model),
            'queried_at': datetime.now().isoformat(timespec='seconds'),
            'versions': sorted(str(r.get('bd_versao') or '') for r in headers),
            'keys': sorted(by_key), 'sectors': sectors, 'events': events, 'lines': lines,
            'warnings': list(dict.fromkeys(warnings)), 'complete': False}


def _preparacao_do_caderno(headers):
    """Linhas e estados do desenho e do plano de corte (CadernoEncargos).

    Soma as versões do modelo, como os lançamentos. Um 0 sem data de fim é
    «por apurar»: no Streamlit o campo nasce a 0.
    """
    lines, sectors = [], []
    for stage, (label, machine, column, divisor, done_column) in PREPARACAO_CE.items():
        values = [number(r.get(column)) for r in headers]
        valid = [v for v in values if v is not None and v >= 0]
        hours = sum(valid, Decimal(0)) / divisor if valid else Decimal(0)
        done = bool(headers) and all(str(r.get(done_column) or '').strip() for r in headers)
        if not headers:
            state = 'Obra/modelo não encontrado'
        elif len(valid) != len(values):
            state = 'Valor inválido no Caderno de Encargos — confirmar'
        elif done:
            state = 'Concluído' if hours else 'Concluído sem horas — confirmar'
        else:
            state = 'Em curso / estado por confirmar'
        sectors.append({'sector': stage, 'name': label, 'hours': str(hours), 'estimated': None,
                        'state': state, 'invalid': len(values) - len(valid)})
        lines.append(cost_line('Produção', f'{stage}|{machine}', f'{label} — {machine}',
                               str(hours) if hours else None, 'h', sector=stage, machine=machine))
    return lines, sectors


def _linha_sem_horas(stage, na=False):
    if stage in PREPARACAO_CE:
        label, machine = PREPARACAO_CE[stage][:2]
        return cost_line('Produção', f'{stage}|{machine}', f'{label} — {machine}', None, 'h',
                         sector=stage, machine=machine)
    label = ROTULOS[stage]
    return cost_line('Produção', f'{stage}|pendente',
                     f'{label} — não aplicável' if na else f'{label} — horas por apurar',
                     '0' if na else None, 'h', sector=stage, machine='')


def completar_setores(lines, sectors=None):
    """Pelo menos uma linha por setor, pela ordem do trabalho.

    O quadro dos tempos no Excel tem de ter sempre o €/h de cada setor, haja
    ou não horas no Streamlit: o utilizador pode escrever as horas à mão.
    Setor «Não aplicável» sem horas fica a 0; os outros ficam por apurar.
    """
    estados = {s['sector']: s.get('state') for s in (sectors or [])}
    result = list(lines)
    for stage in ROTULOS:
        if not any(l.get('sector') == stage for l in result):
            result.append(_linha_sem_horas(stage, estados.get(stage) == 'Não aplicável'))
    ordem = list(ROTULOS)
    return sorted(result, key=lambda l: ordem.index(l['sector']) if l.get('sector') in ordem else len(ordem))


def machines(session):
    columns = (DefMaquina.id, DefMaquina.codigo, DefMaquina.nome, DefMaquina.tipo, DefMaquina.custo_hora,
               DefMaquina.nomes_streamlit)
    return [dict(row._mapping) for row in session.execute(select(*columns).where(DefMaquina.ativo.is_(True)))]


def machine_price(machine, origem='Custo/hora máquina V3 (STD)'):
    return {'id': machine['id'], 'machine_id': machine['id'], 'ref': machine['codigo'],
            'description': machine['nome'], 'unit': 'h',
            'net': str(machine['custo_hora']) if machine['custo_hora'] is not None else None,
            'date': datetime.now().isoformat(timespec='seconds'), 'mapping_source': origem}


def _chaves_da_maquina(machine):
    """Por onde uma máquina V3 é reconhecida: código, nome e «Nomes no Streamlit»."""
    nomes = [machine.get('codigo'), machine.get('nome'), *separar_nomes_streamlit(machine.get('nomes_streamlit'))]
    chaves = {chave_nome_streamlit(n) for n in nomes}
    # «Embalamento» no V3 é o setor «Embalagem» do Streamlit (idem «Orla»).
    chaves |= {chave_nome_streamlit(sector(n)) for n in nomes if n}
    return chaves - {''}


def procurar_maquina(line, catalog):
    """A máquina V3 de uma linha de horas: (máquina, como) ou (None, porquê).

    Primeiro pelo nome da máquina no Streamlit (HKL 300, ABD…), depois pelo
    setor (Corte, Montagem…). Um nome em duas máquinas não escolhe nenhuma.
    """
    tentativas = []
    machine = ' '.join(str(line.get('machine') or '').split())
    if machine:
        tentativas.append(('pelo nome', machine))
    if line.get('sector') in ROTULOS:
        tentativas.append(('pelo setor', ROTULOS[line['sector']]))
    for como, nome in tentativas:
        chave = chave_nome_streamlit(nome)
        found = [m for m in catalog if chave and chave in _chaves_da_maquina(m)]
        if len(found) == 1:
            return found[0], f'{como} «{nome}»'
        if len(found) > 1:
            codigos = ', '.join(sorted(str(m['codigo']) for m in found))
            return None, (f'«{nome}» serve várias máquinas V3 ({codigos}) — deixar o nome só numa, em '
                          f'{MENU_MAQUINAS}')
    alvo = machine or ROTULOS.get(line.get('sector'), 'esta linha')
    return None, (f'Sem máquina V3 para «{alvo}» — criar a máquina ou juntar «{alvo}» aos «Nomes no Streamlit» '
                  f'em {MENU_MAQUINAS}')


def match_machine(line, catalog):
    machine, como = procurar_maquina(line, catalog)
    return machine_price(machine, f'Custo/hora máquina V3 (STD), {como}') if machine else None


def descrever_tarifa(line, price, catalog=None, *, curto=False):
    """(texto, tem €/h) para a coluna «Máquina V3» do quadro dos tempos.

    ``curto``: sem o caminho do menu (no Excel está no cabeçalho da coluna).
    """
    onde = '' if curto else f' em {MENU_MAQUINAS}'
    if price:
        codigo = ' — '.join(str(price.get(k) or '') for k in ('ref', 'description') if price.get(k))
        if number(price.get('net')) is None:
            return (f'{codigo}: sem custo/hora — preencher{onde}', False)
        return (codigo, True)
    if catalog is not None and not curto:
        return (procurar_maquina(line, catalog)[1], False)
    alvo = line.get('machine') or ROTULOS.get(line.get('sector'), '')
    return (f'Sem €/h no Martelo — criar a máquina ou juntar «{alvo}» aos «Nomes no Streamlit»{onde}', False)
