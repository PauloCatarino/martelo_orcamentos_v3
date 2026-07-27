"""Criar as variantes em falta do grupo PRATELEIRAS AMOVIVEIS.

Parte do ``PRAT_AMOV[2111]`` que o Paulo montou a mao e acrescenta:

* as peças simples ``[2000]`` e ``[2222]`` (mesma configuracao, so mudam as
  orlas);
* o conjunto ``PRAT. AMOV. [2111] + SUPORTE PRATELEIRA``;
* o conjunto ``PRAT. AMOV. [2111] + SUPORTE PRATELEIRA + VARAO + SUPORTE VARAO``.

O suporte de prateleira sai da peca simples e passa a viver nestes conjuntos:
a peca simples fica so material + corte + orlagem. Essa limpeza esta na funcao
``remover_suporte_da_peca_simples`` e **so corre com o argumento
``--remover-suporte-simples``**, para nunca apagar nada sem ser pedido.

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
    TOTAL,
)
from app.domain.componente_types import PECA  # noqa: E402
from app.domain.orla_types import normalize_orla_type  # noqa: E402
from app.domain.peca_funcao_types import PRATELEIRA_AMOVIVEL  # noqa: E402
from app.domain.peca_natureza_types import (  # noqa: E402
    CONJUNTO,
    HORIZONTAL,
    MATERIAL,
    NEUTRA,
)
from app.domain.peca_types import COMPOSTA, SIMPLES  # noqa: E402
from app.domain.regra_operacao_types import POR_ORLAS, POR_PECA  # noqa: E402
from app.domain.regra_quantidade_types import FIXA as QUANTIDADE_FIXA  # noqa: E402
from app.models import (  # noqa: E402
    DefOperacao,
    DefPeca,
    DefPecaComponente,
    DefPecaOperacao,
    DefPecaUserPref,
    DefRegraQuantidade,
)


GRUPO_PRATELEIRAS_AMOVIVEIS = "PRATELEIRAS AMOVIVEIS"
CHAVE_MATERIAL_PRATELEIRAS = "MATERIAL_PRATELEIRAS"

CODIGO_PRAT_AMOV_2111 = "PRAT_AMOV[2111]"
CODIGO_SUPORTE_PRATELEIRA = "SUPORTE_PRATELEIRA"
CODIGO_VARAO = "VARAO"
CODIGO_SUPORTE_VARAO = "SUPORTE_VARAO"

REGRA_SUPORTE_PRATELEIRA = "SUPORTE_PRATELEIRA"
REGRA_VARAO = "VARAO_SPP"
REGRA_SUPORTE_TERMINAL_VARAO = "SUPORTE_TERMINAL_VARAO"


@dataclass(frozen=True)
class OperacaoSeed:
    """Uma operacao associada a uma peca."""

    codigo_operacao: str
    ordem: int
    regra_calculo: str
    ativo: bool = True


@dataclass(frozen=True)
class ComponenteSeed:
    """Um componente de um conjunto (sempre uma peca do catalogo)."""

    codigo_peca: str
    ordem: int
    descricao: str
    codigo_regra_quantidade: str | None = None
    zona_aplicacao: str = GERAL
    dimensao_referencia: str = COMP
    numero_topos: int = 0
    formula_comp: str | None = None
    formula_larg: str | None = None


@dataclass(frozen=True)
class PrateleiraSimplesSeed:
    """Uma prateleira amovivel simples (codigo de orlas C1-C2-L1-L2)."""

    codigo: str
    nome: str
    nome_biblioteca: str
    codigo_orlas: str


@dataclass(frozen=True)
class ConjuntoSeed:
    """Um conjunto de prateleira amovivel."""

    codigo: str
    nome: str
    nome_biblioteca: str
    descricao: str
    componentes: tuple[ComponenteSeed, ...] = field(default_factory=tuple)


# Operacoes iguais as do PRAT_AMOV[2111]: corte e orlagem.
OPERACOES_PRATELEIRA_SIMPLES: tuple[OperacaoSeed, ...] = (
    OperacaoSeed(codigo_operacao="CORTE_PAINEL", ordem=1, regra_calculo=POR_PECA),
    OperacaoSeed(codigo_operacao="ORLAGEM_PECA", ordem=2, regra_calculo=POR_ORLAS),
)

# O nome na biblioteca segue o estilo do PRAT_AMOV[2111] ja existente (nome na
# biblioteca igual ao codigo), para a arvore do custeio ficar coerente.
PRATELEIRAS_SIMPLES: tuple[PrateleiraSimplesSeed, ...] = (
    PrateleiraSimplesSeed(
        codigo="PRAT_AMOV[2000]",
        nome="Prateleira Amovivel[2000]",
        nome_biblioteca="PRAT_AMOV[2000]",
        codigo_orlas="2000",
    ),
    PrateleiraSimplesSeed(
        codigo="PRAT_AMOV[2222]",
        nome="Prateleira Amovivel[2222]",
        nome_biblioteca="PRAT_AMOV[2222]",
        codigo_orlas="2222",
    ),
)

# A prateleira entra com as formulas do modulo; o suporte usa a regra dos dois
# topos que ja estava na peca simples.
COMPONENTE_PRATELEIRA = ComponenteSeed(
    codigo_peca=CODIGO_PRAT_AMOV_2111,
    ordem=1,
    descricao="Prateleira amovivel [2111]",
    formula_comp="LM",
    formula_larg="PM",
)
COMPONENTE_SUPORTE_PRATELEIRA = ComponenteSeed(
    codigo_peca=CODIGO_SUPORTE_PRATELEIRA,
    ordem=2,
    descricao="Suportes de prateleira (2 topos)",
    codigo_regra_quantidade=REGRA_SUPORTE_PRATELEIRA,
    zona_aplicacao=DOIS_TOPOS,
    dimensao_referencia=MEDIDA_TOPO,
    numero_topos=2,
)

CONJUNTOS: tuple[ConjuntoSeed, ...] = (
    ConjuntoSeed(
        codigo="PRAT_AMOV[2111]+SUP_PRAT",
        nome="PRAT. AMOV. [2111] + SUPORTE PRATELEIRA",
        nome_biblioteca="PRAT_AMOV[2111]+SUP_PRAT",
        descricao="Prateleira amovivel 2111 + suportes de prateleira",
        componentes=(COMPONENTE_PRATELEIRA, COMPONENTE_SUPORTE_PRATELEIRA),
    ),
    ConjuntoSeed(
        codigo="PRAT_AMOV[2111]+SUP_PRAT+VARAO+SUP_VARAO",
        nome="PRAT. AMOV. [2111] + SUPORTE PRATELEIRA + VARAO + SUPORTE VARAO",
        nome_biblioteca="PRAT_AMOV[2111]+SUP_PRAT+VARAO+SUP_VARAO",
        descricao=(
            "Prateleira amovivel 2111 + suportes de prateleira + varao com terminais"
        ),
        componentes=(
            COMPONENTE_PRATELEIRA,
            COMPONENTE_SUPORTE_PRATELEIRA,
            ComponenteSeed(
                codigo_peca=CODIGO_VARAO,
                ordem=3,
                descricao="Varao ao comprimento do modulo",
                codigo_regra_quantidade=REGRA_VARAO,
                formula_comp="LM",
            ),
            ComponenteSeed(
                codigo_peca=CODIGO_SUPORTE_VARAO,
                ordem=4,
                descricao="Terminais de varao (2 por varao)",
                codigo_regra_quantidade=REGRA_SUPORTE_TERMINAL_VARAO,
            ),
        ),
    ),
)


@dataclass(frozen=True)
class PrateleirasResult:
    """Resumo do seed das prateleiras amoviveis."""

    pecas_criadas: int
    pecas_reutilizadas: int
    operacoes_criadas: int
    componentes_criados: int
    prefs_criadas: int
    suporte_removido: bool


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
            )
        )
    session.flush()
    return len(seeds)


def criar_prateleiras_simples(session: Session) -> tuple[int, int, int]:
    """Criar as peças simples em falta. Devolve (criadas, reutilizadas, operacoes)."""
    criadas = 0
    reutilizadas = 0
    operacoes = 0

    for seed in PRATELEIRAS_SIMPLES:
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
            nome_biblioteca=seed.nome_biblioteca,
            descricao="Prateleira amovivel",
            grupo=GRUPO_PRATELEIRAS_AMOVIVEIS,
            tipo_peca=SIMPLES,
            natureza=MATERIAL,
            orientacao=HORIZONTAL,
            funcao=PRATELEIRA_AMOVIVEL,
            formula_comp="LM",
            formula_larg="PM",
            orla_c1=orla_c1,
            orla_c2=orla_c2,
            orla_l1=orla_l1,
            orla_l2=orla_l2,
            chave_valueset_material=CHAVE_MATERIAL_PRATELEIRAS,
            permite_acabamento=False,
            sem_material=False,
            ativo=True,
        )
        session.add(peca)
        session.flush()
        operacoes += criar_operacoes(session, peca, OPERACOES_PRATELEIRA_SIMPLES)
        criadas += 1
        print(f"Peca {seed.codigo} criada ({seed.nome_biblioteca})")

    return criadas, reutilizadas, operacoes


def criar_componentes(
    session: Session, conjunto: DefPeca, seeds: tuple[ComponenteSeed, ...]
) -> int:
    """Criar os componentes de um conjunto. Devolve quantos criou."""
    for seed in seeds:
        componente = get_peca_obrigatoria(session, seed.codigo_peca)
        session.add(
            DefPecaComponente(
                def_peca_pai_id=conjunto.id,
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
                modo_quantidade=TOTAL,
                prioridade_valueset=1,
                formula_comp=seed.formula_comp,
                formula_larg=seed.formula_larg,
            )
        )
    session.flush()
    return len(seeds)


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
            nome_biblioteca=seed.nome_biblioteca,
            descricao=seed.descricao,
            grupo=GRUPO_PRATELEIRAS_AMOVIVEIS,
            tipo_peca=COMPOSTA,
            natureza=CONJUNTO,
            orientacao=NEUTRA,
            funcao=PRATELEIRA_AMOVIVEL,
            permite_acabamento=False,
            sem_material=True,
            ativo=True,
        )
        session.add(conjunto)
        session.flush()

        componentes += criar_componentes(session, conjunto, seed.componentes)
        criados += 1
        print(f"Conjunto {seed.codigo} criado ({seed.nome_biblioteca})")

    return criados, reutilizados, componentes


def adicionar_as_bibliotecas(session: Session) -> int:
    """Mostrar as novas peças a quem tem biblioteca personalizada.

    Quem nunca personalizou a biblioteca ve todas as peças ativas; quem
    personalizou so ve o que escolheu e, sem isto, nao veria as peças novas.
    """
    codigos = [seed.codigo for seed in PRATELEIRAS_SIMPLES]
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


def remover_suporte_da_peca_simples(session: Session) -> bool:
    """Tirar o associado SUPORTE_PRATELEIRA da peca simples PRAT_AMOV[2111].

    O suporte passa a existir so nos conjuntos, para a peca simples poder ser
    usada sozinha (material + corte + orlagem). Apaga uma unica linha de
    associado, identificada por peca-pai e peca-componente; nao toca em
    orçamentos, que guardam as suas proprias linhas.
    """
    peca = get_peca(session, CODIGO_PRAT_AMOV_2111)
    suporte = get_peca(session, CODIGO_SUPORTE_PRATELEIRA)
    if peca is None or suporte is None:
        print("Peca simples ou suporte nao existem; nada a remover")
        return False

    componente = session.execute(
        select(DefPecaComponente).where(
            DefPecaComponente.def_peca_pai_id == peca.id,
            DefPecaComponente.def_peca_componente_id == suporte.id,
        )
    ).scalar_one_or_none()
    if componente is None:
        print(f"{CODIGO_PRAT_AMOV_2111} ja nao tem o associado {CODIGO_SUPORTE_PRATELEIRA}")
        return False

    session.delete(componente)
    session.flush()
    print(
        f"Associado {CODIGO_SUPORTE_PRATELEIRA} (linha {componente.id}) removido de "
        f"{CODIGO_PRAT_AMOV_2111}"
    )
    return True


def seed_prateleiras_amoviveis(
    session: Session, remover_suporte: bool = False
) -> PrateleirasResult:
    """Criar as peças e conjuntos de prateleiras amoviveis em falta."""
    simples_criadas, simples_reutilizadas, operacoes = criar_prateleiras_simples(session)
    conjuntos_criados, conjuntos_reutilizados, componentes = criar_conjuntos(session)
    prefs = adicionar_as_bibliotecas(session)
    suporte_removido = remover_suporte_da_peca_simples(session) if remover_suporte else False

    session.commit()

    return PrateleirasResult(
        pecas_criadas=simples_criadas + conjuntos_criados,
        pecas_reutilizadas=simples_reutilizadas + conjuntos_reutilizados,
        operacoes_criadas=operacoes,
        componentes_criados=componentes,
        prefs_criadas=prefs,
        suporte_removido=suporte_removido,
    )


def print_summary(result: PrateleirasResult) -> None:
    """Escrever o resumo final para o utilizador."""
    print("Resumo final")
    print(f"Pecas criadas: {result.pecas_criadas}")
    print(f"Pecas mantidas (ja existiam): {result.pecas_reutilizadas}")
    print(f"Operacoes associadas criadas: {result.operacoes_criadas}")
    print(f"Componentes criados: {result.componentes_criados}")
    print(f"Linhas de biblioteca de utilizador criadas: {result.prefs_criadas}")
    print(
        "Suporte retirado da peca simples: "
        f"{'sim' if result.suporte_removido else 'nao'}"
    )


def main(argv: list[str] | None = None) -> int:
    """Criar as variantes de prateleiras amoviveis na base configurada."""
    argumentos = sys.argv[1:] if argv is None else argv
    remover_suporte = "--remover-suporte-simples" in argumentos

    _ = settings.database_url

    with SessionLocal() as session:
        result = seed_prateleiras_amoviveis(session, remover_suporte=remover_suporte)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
