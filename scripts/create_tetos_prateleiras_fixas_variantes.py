"""Criar as variantes em falta dos grupos TETOS e PRATELEIRAS FIXAS.

Parte do ``TETO_2000`` e da ``PRATELEIRA FIXA 2000`` que o Paulo montou a mao:

* tetos ``[0000]``, ``[2100]``, ``[2111]``, ``[2200]`` e ``[2222]``;
* prateleiras fixas ``[0000]``, ``[2111]`` e ``[2222]``;
* conjunto ``PRAT. FIXA [2000] + VARAO + SUPORTE VARAO``.

Sao todas peças horizontais e todas levam os sistemas de uniao nos dois topos
(cavilha em prioridade 1, parafuso em prioridade 2), como o ``TETO_2000``.

O seed e idempotente: cria apenas o que falta e reutiliza o que ja existe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domain.associado_types import (  # noqa: E402
    COMP,
    DOIS_TOPOS,
    GERAL,
    MEDIDA_TOPO,
    POR_TOPO,
    TOTAL,
)
from app.domain.componente_types import PECA  # noqa: E402
from app.domain.orla_types import normalize_orla_type  # noqa: E402
from app.domain.peca_funcao_types import PRATELEIRA_FIXA, TETO  # noqa: E402
from app.domain.peca_natureza_types import (  # noqa: E402
    CONJUNTO,
    HORIZONTAL,
    MATERIAL,
    NEUTRA,
)
from app.domain.peca_types import COMPOSTA, SIMPLES  # noqa: E402
from app.domain.regra_operacao_types import FIXA, POR_ORLAS, POR_PECA  # noqa: E402
from app.domain.regra_quantidade_types import FIXA as QUANTIDADE_FIXA  # noqa: E402
from app.models import (  # noqa: E402
    DefOperacao,
    DefPeca,
    DefPecaComponente,
    DefPecaOperacao,
    DefPecaUserPref,
    DefRegraQuantidade,
)


GRUPO_TETOS = "TETOS"
GRUPO_PRATELEIRAS_FIXAS = "PRATELEIRAS FIXAS"

CHAVE_MATERIAL_TETOS = "MATERIAL_TETOS"
CHAVE_MATERIAL_PRATELEIRAS_FIXAS = "MATERIAL_PRATELEIRAS_FIXAS"

CODIGO_PRAT_FIXA_2000 = "PRATELEIRA FIXA 2000"
CODIGO_PECA_UNIOES = "SISTEMAS_UNIAO"
CODIGO_VARAO = "VARAO"
CODIGO_SUPORTE_VARAO = "SUPORTE_VARAO"

REGRA_UNIOES = "UNIAO_TOPOS_128"
REGRA_VARAO = "VARAO_SPP"
REGRA_SUPORTE_TERMINAL_VARAO = "SUPORTE_TERMINAL_VARAO"

METODO_ESCALAO_AREA = "ESCALAO_AREA"

# Formulas das peças horizontais (tetos, fundos, prateleiras): o comprimento e
# a largura do modulo e a largura e a profundidade.
FORMULA_COMP_HORIZONTAL = "LM"
FORMULA_LARG_HORIZONTAL = "PM"


@dataclass(frozen=True)
class OperacaoSeed:
    """Uma operacao associada a uma peca."""

    codigo_operacao: str
    ordem: int
    regra_calculo: str
    ativo: bool = True
    unidade_tempo: str | None = None
    metodo_calculo: str | None = None
    observacoes: str | None = None


@dataclass(frozen=True)
class ComponenteSeed:
    """Um componente/associado (sempre uma peca do catalogo)."""

    codigo_peca: str
    ordem: int
    descricao: str
    codigo_regra_quantidade: str | None = None
    zona_aplicacao: str = GERAL
    dimensao_referencia: str = COMP
    numero_topos: int = 0
    modo_quantidade: str = TOTAL
    prioridade_valueset: int = 1
    formula_comp: str | None = None
    formula_larg: str | None = None


@dataclass(frozen=True)
class PecaSimplesSeed:
    """Uma peca simples horizontal (codigo de orlas C1-C2-L1-L2)."""

    codigo: str
    nome: str
    codigo_orlas: str
    grupo: str
    funcao: str
    formula_comp: str
    formula_larg: str
    chave_valueset_material: str
    operacoes: tuple[OperacaoSeed, ...]


@dataclass(frozen=True)
class ConjuntoSeed:
    """Um conjunto construido sobre peças ja existentes."""

    codigo: str
    nome: str
    descricao: str
    grupo: str
    funcao: str
    componentes: tuple[ComponenteSeed, ...] = field(default_factory=tuple)


# Uniões nos dois topos: cavilha (prioridade 1) e parafuso (prioridade 2), como
# no TETO_2000. A prioridade escolhe a variante no ValueSet do orçamento.
UNIOES: tuple[ComponenteSeed, ...] = (
    ComponenteSeed(
        codigo_peca=CODIGO_PECA_UNIOES,
        ordem=1,
        descricao="Unioes para Modulos Cavilha",
        codigo_regra_quantidade=REGRA_UNIOES,
        zona_aplicacao=DOIS_TOPOS,
        dimensao_referencia=MEDIDA_TOPO,
        numero_topos=2,
        modo_quantidade=POR_TOPO,
        prioridade_valueset=1,
    ),
    ComponenteSeed(
        codigo_peca=CODIGO_PECA_UNIOES,
        ordem=2,
        descricao="Unioes para Modulos Parafusos",
        codigo_regra_quantidade=REGRA_UNIOES,
        zona_aplicacao=DOIS_TOPOS,
        dimensao_referencia=MEDIDA_TOPO,
        numero_topos=2,
        modo_quantidade=POR_TOPO,
        prioridade_valueset=2,
    ),
)

# Operacoes iguais as do TETO_2000: corte e orlagem ativos, furacao CNC
# associada mas desativada.
OPERACOES_TETO: tuple[OperacaoSeed, ...] = (
    OperacaoSeed(codigo_operacao="CORTE_PAINEL", ordem=1, regra_calculo=POR_PECA),
    OperacaoSeed(codigo_operacao="ORLAGEM_PECA", ordem=2, regra_calculo=POR_ORLAS),
    OperacaoSeed(
        codigo_operacao="CNC_5_EIXOS",
        ordem=3,
        regra_calculo=FIXA,
        ativo=False,
        unidade_tempo="PECA",
        metodo_calculo=METODO_ESCALAO_AREA,
        observacoes="Furacao Cavilhas Horizontal Topos",
    ),
)

# Operacoes iguais as da PRATELEIRA FIXA 2000: corte e orlagem.
OPERACOES_PRATELEIRA_FIXA: tuple[OperacaoSeed, ...] = (
    OperacaoSeed(codigo_operacao="CORTE_PAINEL", ordem=1, regra_calculo=POR_PECA),
    OperacaoSeed(codigo_operacao="ORLAGEM_PECA", ordem=2, regra_calculo=POR_ORLAS),
)

TETOS: tuple[PecaSimplesSeed, ...] = tuple(
    PecaSimplesSeed(
        codigo=f"TETO_{orlas}",
        nome=f"Teto[{orlas}]",
        codigo_orlas=orlas,
        grupo=GRUPO_TETOS,
        funcao=TETO,
        # Peca horizontal: comprimento = largura do modulo e largura =
        # profundidade, como nos fundos e nas prateleiras.
        formula_comp=FORMULA_COMP_HORIZONTAL,
        formula_larg=FORMULA_LARG_HORIZONTAL,
        chave_valueset_material=CHAVE_MATERIAL_TETOS,
        operacoes=OPERACOES_TETO,
    )
    for orlas in ("0000", "2100", "2111", "2200", "2222")
)

PRATELEIRAS_FIXAS: tuple[PecaSimplesSeed, ...] = tuple(
    PecaSimplesSeed(
        codigo=f"PRAT_FIXA[{orlas}]",
        nome=f"Prateleira Fixa [{orlas}]",
        codigo_orlas=orlas,
        grupo=GRUPO_PRATELEIRAS_FIXAS,
        funcao=PRATELEIRA_FIXA,
        formula_comp=FORMULA_COMP_HORIZONTAL,
        formula_larg=FORMULA_LARG_HORIZONTAL,
        chave_valueset_material=CHAVE_MATERIAL_PRATELEIRAS_FIXAS,
        operacoes=OPERACOES_PRATELEIRA_FIXA,
    )
    for orlas in ("0000", "2111", "2222")
)

# A prateleira ja traz as suas uniões, por isso o conjunto so acrescenta o
# varao e os terminais.
CONJUNTOS: tuple[ConjuntoSeed, ...] = (
    ConjuntoSeed(
        codigo="PRAT_FIXA[2000]+VARAO+SUP_VARAO",
        nome="PRAT. FIXA [2000] + VARAO + SUPORTE VARAO",
        descricao="Prateleira fixa 2000 + varao com terminais",
        grupo=GRUPO_PRATELEIRAS_FIXAS,
        funcao=PRATELEIRA_FIXA,
        componentes=(
            ComponenteSeed(
                codigo_peca=CODIGO_PRAT_FIXA_2000,
                ordem=1,
                descricao="Prateleira fixa [2000]",
                formula_comp="LM",
                formula_larg="PM",
            ),
            ComponenteSeed(
                codigo_peca=CODIGO_VARAO,
                ordem=2,
                descricao="Varao ao comprimento do modulo",
                codigo_regra_quantidade=REGRA_VARAO,
                formula_comp="LM",
            ),
            ComponenteSeed(
                codigo_peca=CODIGO_SUPORTE_VARAO,
                ordem=3,
                descricao="Terminais de varao (2 por varao)",
                codigo_regra_quantidade=REGRA_SUPORTE_TERMINAL_VARAO,
            ),
        ),
    ),
)


@dataclass(frozen=True)
class TetosPrateleirasResult:
    """Resumo do seed dos tetos e prateleiras fixas."""

    pecas_criadas: int
    pecas_reutilizadas: int
    operacoes_criadas: int
    componentes_criados: int
    prefs_criadas: int
    formulas_corrigidas: int


def get_peca(session: Session, codigo: str) -> DefPeca | None:
    """Devolver uma peca do catalogo pelo codigo."""
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo)
    ).scalar_one_or_none()


def get_peca_obrigatoria(session: Session, codigo: str) -> DefPeca:
    """Devolver uma peca do catalogo, com erro claro se nao existir."""
    peca = get_peca(session, codigo)
    if peca is None:
        raise ValueError(f"Peca {codigo} nao existe nesta base de dados")
    return peca


def get_operacao_id(session: Session, codigo: str) -> int:
    """Devolver o id de uma operacao pelo codigo (erro se nao existir)."""
    operacao = session.execute(
        select(DefOperacao).where(DefOperacao.codigo == codigo)
    ).scalar_one_or_none()
    if operacao is None:
        raise ValueError(f"Operacao {codigo} nao existe nesta base de dados")
    return operacao.id


def get_regra_quantidade_id(session: Session, codigo: str | None) -> int | None:
    """Devolver o id de uma regra de quantidade pelo codigo (None se faltar)."""
    if codigo is None:
        return None

    regra = session.execute(
        select(DefRegraQuantidade).where(DefRegraQuantidade.codigo == codigo)
    ).scalar_one_or_none()
    if regra is None:
        print(f"Aviso: regra de quantidade {codigo} nao existe; componente fica sem regra")
        return None
    return regra.id


def criar_operacoes(
    session: Session, peca: DefPeca, seeds: tuple[OperacaoSeed, ...]
) -> int:
    """Criar as operacoes de uma peca acabada de criar. Devolve quantas criou."""
    for seed in seeds:
        session.add(
            DefPecaOperacao(
                def_peca_id=peca.id,
                def_operacao_id=get_operacao_id(session, seed.codigo_operacao),
                ordem=seed.ordem,
                regra_calculo=seed.regra_calculo,
                obrigatorio=True,
                ativo=seed.ativo,
                observacoes=seed.observacoes,
                unidade_tempo=seed.unidade_tempo,
                metodo_calculo=seed.metodo_calculo,
            )
        )
    session.flush()
    return len(seeds)


def criar_componentes(
    session: Session, pai: DefPeca, seeds: tuple[ComponenteSeed, ...]
) -> int:
    """Criar os associados/componentes de uma peca. Devolve quantos criou."""
    for seed in seeds:
        componente = get_peca_obrigatoria(session, seed.codigo_peca)
        session.add(
            DefPecaComponente(
                def_peca_pai_id=pai.id,
                tipo_componente=PECA,
                def_peca_componente_id=componente.id,
                descricao=seed.descricao,
                ordem=seed.ordem,
                quantidade=Decimal("1.000"),
                regra_quantidade=QUANTIDADE_FIXA,
                def_regra_quantidade_id=get_regra_quantidade_id(
                    session, seed.codigo_regra_quantidade
                ),
                obrigatorio=True,
                ativo=True,
                zona_aplicacao=seed.zona_aplicacao,
                dimensao_referencia=seed.dimensao_referencia,
                numero_topos=seed.numero_topos,
                modo_quantidade=seed.modo_quantidade,
                prioridade_valueset=seed.prioridade_valueset,
                formula_comp=seed.formula_comp,
                formula_larg=seed.formula_larg,
            )
        )
    session.flush()
    return len(seeds)


def criar_pecas_simples(
    session: Session, seeds: tuple[PecaSimplesSeed, ...]
) -> tuple[int, int, int, int]:
    """Criar as peças simples em falta.

    Devolve ``(criadas, reutilizadas, operacoes, componentes)``.
    """
    criadas = 0
    reutilizadas = 0
    operacoes = 0
    componentes = 0

    for seed in seeds:
        if get_peca(session, seed.codigo) is not None:
            reutilizadas += 1
            print(f"Peca {seed.codigo} ja existe, mantida")
            continue

        orla_c1, orla_c2, orla_l1, orla_l2 = (
            normalize_orla_type(digito) for digito in seed.codigo_orlas
        )
        peca = DefPeca(
            codigo=seed.codigo,
            nome=seed.nome,
            grupo=seed.grupo,
            tipo_peca=SIMPLES,
            natureza=MATERIAL,
            orientacao=HORIZONTAL,
            funcao=seed.funcao,
            formula_comp=seed.formula_comp,
            formula_larg=seed.formula_larg,
            orla_c1=orla_c1,
            orla_c2=orla_c2,
            orla_l1=orla_l1,
            orla_l2=orla_l2,
            chave_valueset_material=seed.chave_valueset_material,
            permite_acabamento=False,
            sem_material=False,
            ativo=True,
        )
        session.add(peca)
        session.flush()

        operacoes += criar_operacoes(session, peca, seed.operacoes)
        componentes += criar_componentes(session, peca, UNIOES)
        criadas += 1
        print(f"Peca {seed.codigo} criada ({seed.nome})")

    return criadas, reutilizadas, operacoes, componentes


def criar_conjuntos(session: Session) -> tuple[int, int, int]:
    """Criar os conjuntos em falta. Devolve (criados, reutilizados, componentes)."""
    criados = 0
    reutilizados = 0
    componentes = 0

    for seed in CONJUNTOS:
        if get_peca(session, seed.codigo) is not None:
            reutilizados += 1
            print(f"Conjunto {seed.codigo} ja existe, mantido")
            continue

        conjunto = DefPeca(
            codigo=seed.codigo,
            nome=seed.nome,
            descricao=seed.descricao,
            grupo=seed.grupo,
            tipo_peca=COMPOSTA,
            natureza=CONJUNTO,
            orientacao=NEUTRA,
            funcao=seed.funcao,
            permite_acabamento=False,
            sem_material=True,
            ativo=True,
        )
        session.add(conjunto)
        session.flush()

        componentes += criar_componentes(session, conjunto, seed.componentes)
        criados += 1
        print(f"Conjunto {seed.codigo} criado ({seed.nome})")

    return criados, reutilizados, componentes


def adicionar_as_bibliotecas(session: Session) -> int:
    """Mostrar as novas peças a quem tem biblioteca personalizada."""
    codigos = [seed.codigo for seed in TETOS + PRATELEIRAS_FIXAS]
    codigos += [seed.codigo for seed in CONJUNTOS]

    pecas_ids = [
        peca.id
        for peca in (get_peca(session, codigo) for codigo in codigos)
        if peca is not None
    ]
    if not pecas_ids:
        return 0

    users_com_biblioteca = (
        session.execute(select(DefPecaUserPref.user_id).distinct()).scalars().all()
    )

    criadas = 0
    for user_id in users_com_biblioteca:
        for peca_id in pecas_ids:
            existente = session.execute(
                select(DefPecaUserPref).where(
                    DefPecaUserPref.user_id == user_id,
                    DefPecaUserPref.def_peca_id == peca_id,
                )
            ).scalar_one_or_none()
            if existente is not None:
                continue

            session.add(
                DefPecaUserPref(user_id=user_id, def_peca_id=peca_id, favorito=False)
            )
            criadas += 1

    session.flush()
    return criadas


def corrigir_formulas_horizontais(session: Session) -> int:
    """Por os tetos com as formulas das peças horizontais (LM x PM).

    O ``TETO_2000`` tinha ficado com ``HM`` no comprimento, herdado do tempo em
    que a dimensao principal era tratada como altura. Devolve quantas peças
    mudaram.
    """
    pecas = session.execute(
        select(DefPeca).where(
            DefPeca.grupo == GRUPO_TETOS,
            DefPeca.tipo_peca == SIMPLES,
        )
    ).scalars().all()

    corrigidas = 0
    for peca in pecas:
        if (peca.formula_comp, peca.formula_larg) == (
            FORMULA_COMP_HORIZONTAL,
            FORMULA_LARG_HORIZONTAL,
        ):
            continue

        anterior = f"{peca.formula_comp or '-'} x {peca.formula_larg or '-'}"
        peca.formula_comp = FORMULA_COMP_HORIZONTAL
        peca.formula_larg = FORMULA_LARG_HORIZONTAL
        corrigidas += 1
        print(
            f"Peca {peca.codigo}: formulas {anterior} -> "
            f"{FORMULA_COMP_HORIZONTAL} x {FORMULA_LARG_HORIZONTAL}"
        )

    session.flush()
    return corrigidas


def seed_tetos_prateleiras_fixas(session: Session) -> TetosPrateleirasResult:
    """Criar tetos, prateleiras fixas e o conjunto do varao (idempotente)."""
    criadas = reutilizadas = operacoes = componentes = 0

    for seeds in (TETOS, PRATELEIRAS_FIXAS):
        parciais = criar_pecas_simples(session, seeds)
        criadas += parciais[0]
        reutilizadas += parciais[1]
        operacoes += parciais[2]
        componentes += parciais[3]

    conjuntos_criados, conjuntos_reutilizados, conjuntos_componentes = criar_conjuntos(
        session
    )
    prefs = adicionar_as_bibliotecas(session)
    formulas_corrigidas = corrigir_formulas_horizontais(session)

    session.commit()

    return TetosPrateleirasResult(
        pecas_criadas=criadas + conjuntos_criados,
        pecas_reutilizadas=reutilizadas + conjuntos_reutilizados,
        operacoes_criadas=operacoes,
        componentes_criados=componentes + conjuntos_componentes,
        prefs_criadas=prefs,
        formulas_corrigidas=formulas_corrigidas,
    )


def print_summary(result: TetosPrateleirasResult) -> None:
    """Escrever o resumo final para o utilizador."""
    print("Resumo final")
    print(f"Pecas criadas: {result.pecas_criadas}")
    print(f"Pecas mantidas (ja existiam): {result.pecas_reutilizadas}")
    print(f"Operacoes associadas criadas: {result.operacoes_criadas}")
    print(f"Componentes/associados criados: {result.componentes_criados}")
    print(f"Linhas de biblioteca de utilizador criadas: {result.prefs_criadas}")
    print(f"Tetos com formulas corrigidas para LM x PM: {result.formulas_corrigidas}")


def main() -> int:
    """Criar as variantes de tetos e prateleiras fixas na base configurada."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = seed_tetos_prateleiras_fixas(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
