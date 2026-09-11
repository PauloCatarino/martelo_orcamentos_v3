"""Repair only the rod associations of the two shelf assemblies.

The caller owns the transaction. Existing quote snapshots and ValueSets are
never updated. The working VARAO+SUPORTES assembly supplies the configuration.
"""
from sqlalchemy import select

from app.models.def_peca import DefPeca
from app.models.def_peca_componente import DefPecaComponente
from app.models.def_regra_quantidade import DefRegraQuantidade

CONJUNTOS = (
    "PRAT_AMOV[2111]+SUP_PRAT+VARAO+SUP_VARAO",
    "PRAT_FIXA[2000]+VARAO+SUP_VARAO",
)
REGRAS = {
    "VARAO": "VARAO_SPP",
    "SUPORTE_CENTRAL_VARAO": "SUPORTE_VARAO_CENTRAL",
    "SUPORTE_LATERAL_VARAO": "SUPORTE_TERMINAL_VARAO",
}
CAMPOS = (
    "tipo_componente", "def_peca_componente_id", "descricao", "quantidade",
    "regra_quantidade", "def_regra_quantidade_id", "formula_comp", "formula_larg",
    "formula_esp", "zona_aplicacao", "dimensao_referencia", "numero_topos",
    "modo_quantidade", "prioridade_valueset", "obrigatorio", "ativo",
)


def corrigir(session):
    pecas = {}
    for codigo in (*CONJUNTOS, "VARAO+SUPORTES", *REGRAS):
        pecas[codigo] = session.scalars(select(DefPeca).where(DefPeca.codigo == codigo)).one()
    fontes = {}
    for codigo, regra_codigo in REGRAS.items():
        fonte = session.scalars(select(DefPecaComponente).where(
            DefPecaComponente.def_peca_pai_id == pecas["VARAO+SUPORTES"].id,
            DefPecaComponente.def_peca_componente_id == pecas[codigo].id,
            DefPecaComponente.ativo.is_(True),
        )).one()
        regra = session.get(DefRegraQuantidade, fonte.def_regra_quantidade_id)
        if regra is None or not regra.ativo or regra.codigo != regra_codigo:
            raise ValueError(f"Regra de referência inválida: {codigo}")
        fontes[codigo] = fonte

    alteracoes = []
    for codigo_pai in CONJUNTOS:
        rows = list(session.scalars(select(DefPecaComponente).where(
            DefPecaComponente.def_peca_pai_id == pecas[codigo_pai].id)))
        ordem = max((r.ordem for r in rows), default=0)
        for codigo, fonte in fontes.items():
            existentes = [r for r in rows if r.def_peca_componente_id == pecas[codigo].id]
            if len(existentes) > 1:
                raise ValueError(f"Associados duplicados em {codigo_pai}: {codigo}")
            novo = not existentes
            if novo:
                ordem += 1
                row = DefPecaComponente(def_peca_pai_id=pecas[codigo_pai].id, ordem=ordem)
                session.add(row)
            else:
                row = existentes[0]
            campos = {c: getattr(fonte, c) for c in CAMPOS
                      if novo or getattr(row, c) != getattr(fonte, c)}
            if campos:
                for campo, valor in campos.items():
                    setattr(row, campo, valor)
                alteracoes.append((codigo_pai, codigo, "criado" if novo else "corrigido"))
    session.flush()
    return alteracoes
