"""Associações reutilizáveis de custos. Não são aliases do Woodstore.

Cada associação usa uma chave própria na tabela operacional de mapeamentos.
Guarda a identidade da matéria-prima, nunca o preço: cada obra fixa o seu preço.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import select, inspect
from sqlalchemy.exc import SQLAlchemyError
from app.models.lista_material_custo_mapeamento import ListaMaterialCustoMapeamento

from app.models.def_materia_prima import DefMateriaPrima
from app.models.system_setting import SystemSetting
from app.models.def_materia_prima_componente import DefMateriaPrimaComponente
from app.services import analise_lista_material_service as svc

PREFIX = 'lm_custo_mapa_'


def mapping_identity(line):
    identity = [line['kind'], line['name'].strip().upper(), svc.unit(line['unit'])]
    if line['kind'] == 'Orlas':
        identity += [str(line.get('board') or '').upper(), str(line.get('width') or ''), str(line.get('thickness') or '')]
    elif line['kind'] == 'Placas':
        identity += [str(line.get('thickness') or svc.nominal_thickness(svc.material_traits(line['name'])[1]) or '')]
    else:
        identity += [str(line.get('union_set') or '').upper(), str(line.get('ref_phc') or '').upper()]
    return identity


def mapping_key(line):
    return PREFIX + hashlib.sha256(json.dumps(mapping_identity(line), ensure_ascii=False).encode()).hexdigest()


def load_mappings(session):
    result = {row.chave: json.loads(row.valor) for row in session.scalars(
        select(SystemSetting).where(SystemSetting.chave.startswith(PREFIX, autoescape=True), SystemSetting.ativo.is_(True))) if row.valor}
    if inspect(session.get_bind()).has_table(ListaMaterialCustoMapeamento.__tablename__):
        result.update({row.chave: json.loads(row.valor) for row in session.scalars(select(ListaMaterialCustoMapeamento))})
    return result


def load_components(session):
    inspector = inspect(session.get_bind())
    table = DefMateriaPrimaComponente.__tablename__
    if not inspector.has_table(table) or 'nome_jogo_imos' not in {c['name'] for c in inspector.get_columns(table)}:
        raise RuntimeError('Configuração de componentes/jogos de uniões ainda não disponível nesta base V3.')
    return list(session.scalars(select(DefMateriaPrimaComponente).where(DefMateriaPrimaComponente.ativo.is_(True))))


def component_price(line, catalog, components):
    """Preços individuais de componentes; nunca aplica o preço do kit a cada filho."""
    if line['kind'] not in ('Ferragens', 'SPP', 'Comprados'):
        return None
    matches = []
    for c in components:
        if c.nome_jogo_imos and c.nome_jogo_imos != line.get('union_set'):
            continue
        if (c.nome_imos and c.nome_imos == line.get('union_name')) or (c.ref_phc and c.ref_phc == line.get('ref_phc')):
            matches.append(c)
    # Se existir um jogo explícito, os seus componentes prevalecem sobre aliases genéricos.
    specific = [c for c in matches if c.nome_jogo_imos and c.nome_jogo_imos == line.get('union_set')]
    matches = specific or matches
    linked_ids = {c.componente_materia_prima_id for c in matches if c.componente_materia_prima_id}
    if matches and len(linked_ids) == 1 and all(c.componente_materia_prima_id in linked_ids for c in matches):
        mp = next((mp for mp in catalog if mp.id in linked_ids), None)
        if mp:
            return {**svc.price_record(mp), 'mapping_source': 'Componente V3: jogo de uniões / nome da união'}
    if len(matches) == 1 and matches[0].preco_liquido is not None:
        c = matches[0]
        return {'id': None, 'component_id': c.id, 'ref': line.get('ref_phc') or '',
                'description': c.descricao or line['name'], 'unit': line['unit'], 'net': str(c.preco_liquido),
                'date': datetime.now().isoformat(timespec='seconds'), 'mapping_source': 'Preço líquido individual do componente V3'}
    return None


def save_mapping(session, line, mp, user_name):
    try:
        _save_mapping(session, line, mp, user_name)
    except SQLAlchemyError as exc:
        session.rollback()
        raise ValueError('Não foi possível memorizar a associação. O administrador deve aplicar a atualização 20260908_111 e as permissões da tabela de mapeamentos de custos. A associação não foi guardada.') from exc


def _save_mapping(session, line, mp, user_name):
    key = mapping_key(line)
    row = session.scalar(select(ListaMaterialCustoMapeamento).where(ListaMaterialCustoMapeamento.chave == key).with_for_update())
    legacy = None if row else session.scalar(select(SystemSetting).where(SystemSetting.chave == key))
    previous = row or legacy
    old = json.loads(previous.valor) if previous is not None and previous.valor else {}
    history = old.get('history', [])
    if old.get('mp_id') is not None and old['mp_id'] != mp.id:
        history = history + [{k: v for k, v in old.items() if k != 'history'}]
    payload = {'identity': mapping_identity(line), 'mp_id': mp.id, 'ref_le': mp.ref_le,
               'user': user_name, 'date': datetime.now().isoformat(timespec='seconds'), 'history': history}
    if row is None:
        row = ListaMaterialCustoMapeamento(chave=key)
        session.add(row)
    row.valor = json.dumps(payload, ensure_ascii=False)
    session.commit()


def load_catalog(session):
    # Só os campos usados aqui; não requer colunas de outras funcionalidades novas.
    names = ('id', 'ref_le', 'ref_phc', 'nome_imos', 'descricao', 'unidade', 'preco_liquido',
             'familia_martelo', 'familia_original_excel', 'tipo_martelo', 'fornecedor',
             'referencia_fornecedor', 'comprimento', 'largura', 'espessura', 'coresp_orla_0_4', 'coresp_orla_1_0')
    return [SimpleNamespace(**dict(zip(names, row))) for row in session.execute(
        select(*(getattr(DefMateriaPrima, name) for name in names)).where(DefMateriaPrima.ativo.is_(True)))]


def category(mp):
    family = str(getattr(mp, 'familia_martelo', '') or getattr(mp, 'familia_original_excel', '') or '').upper()
    ref = str(mp.ref_le or '').upper()
    if 'PLACA' in family or ref.startswith('PLC'):
        return 'Placas'
    if 'ORLA' in family or ref.startswith('ORL'):
        return 'Orlas'
    if 'FERRA' in family or ref.startswith('FER'):
        return 'Ferragens'
    return 'Outros'


def egger_references(line, references):
    if line['kind'] != 'Placas':
        return []
    name = line['name'].upper()
    def contained(token):
        return bool(token and re.search(r'(?<![A-Z0-9])' + re.escape(token.upper()) + r'(?![A-Z0-9])', name))
    return [r for r in references if 'EGGER' in (r.folha + ' ' + r.fornecedor).upper()
            and contained(r.referencia) and contained(r.st_acab)]


def numero_do_grupo(bruto):
    """O número do grupo de preço, venha ele como ``7`` ou como ``Grupo 7``.

    A folha do Egger escreve as duas formas conforme o separador, e desde que
    as referências passaram a vir da base (Fase 3) chega sempre a forma por
    extenso. A descrição da matéria-prima diz «AGL MLM EGGER GRUPO 7», e a
    procura é montada com este número: com o texto por extenso o padrão ficava
    ``GRUPO Grupo 7`` e **nenhuma placa era encontrada** — sem erro nenhum,
    apenas a associação automática a deixar de funcionar.
    """
    encontrado = re.search(r'\d+', str(bruto or ''))
    return encontrado.group(0) if encontrado else ''


def egger_candidates(line, catalog, references):
    refs = egger_references(line, references)
    family = svc.material_traits(line['name'])[2]
    typed = [r for r in refs if (family == 'AGL' and ('PART' in r.tipo.upper() or 'AGL' in r.tipo.upper()))
             or (family == 'MDF' and 'MDF' in r.tipo.upper())]
    if typed:
        refs = typed
    groups = {numero_do_grupo(r.grupo) for r in refs if numero_do_grupo(r.grupo)}
    if len(groups) != 1:
        return [], ''
    group = next(iter(groups))
    thickness = svc.nominal_thickness(line.get('thickness')) or svc.nominal_thickness(svc.material_traits(line['name'])[1])
    candidates = [mp for mp in catalog if category(mp) == 'Placas' and 'EGGER' in mp.descricao.upper()
                  and re.search(r'\bGRUPO\s*' + re.escape(group) + r'\b', mp.descricao, re.I)
                  and thickness is not None and svc.nominal_thickness(mp.espessura) == thickness
                  and family and family in mp.descricao.upper().split()]
    return candidates, f"EGGER {refs[0].referencia}/{refs[0].st_acab} — grupo {group}, {thickness} mm"


def resolve_price(line, catalog, mappings, references=(), components=()):
    mapped = mappings.get(mapping_key(line))
    if mapped:
        matches = [mp for mp in catalog if mp.id == mapped['mp_id']]
        if len(matches) == 1:
            return {**svc.price_record(matches[0]), 'mapping_source': 'Mapeamento guardado no V3'}
        return None
    exact = svc.exact_price(line, catalog)
    if exact:
        return {**exact, 'mapping_source': 'Referência PHC / nome IMOS'}
    component = component_price(line, catalog, components)
    if component:
        return component
    matches, reason = egger_candidates(line, catalog, references)
    if len(matches) == 1:
        return {**svc.price_record(matches[0]), 'mapping_source': reason}
    return None
