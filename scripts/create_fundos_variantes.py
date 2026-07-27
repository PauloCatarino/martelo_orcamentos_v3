"""Criar as variantes em falta do grupo FUNDOS (peças e conjuntos +PES).

Segue exatamente o que ja estava criado a mao no catalogo:

* as peças simples copiam a configuracao do ``FUNDO_2000`` (material, formulas
  LM/PM, acabamentos, corte + orlagem + furacao CNC desativada), mudando apenas
  o codigo de orlas;
* os conjuntos ``+PES`` copiam o ``FUNDO+PES`` (fundo + pes com regra por
  dimensao + unioes por topo, cavilha em prioridade 1 e parafuso em prioridade
  2), trocando so o fundo que entra como componente.

O seed e idempotente: cria apenas o que falta, reutiliza o que ja existe e
nunca apaga nem altera registos existentes.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from app.domain.componente_types import FERRAGEM, PECA  # noqa: E402
from app.domain.orla_types import normalize_orla_type  # noqa: E402
from app.domain.peca_funcao_types import FUNDO  # noqa: E402
from app.domain.peca_natureza_types import CONJUNTO, MATERIAL, NEUTRA  # noqa: E402
from app.domain.peca_types import COMPOSTA, SIMPLES  # noqa: E402
from app.domain.regra_operacao_types import FIXA, POR_ORLAS, POR_PECA  # noqa: E402
from app.domain.regra_quantidade_types import (  # noqa: E402
    FIXA as QUANTIDADE_FIXA,
    POR_COMPRIMENTO_LARGURA,
)
from app.models import (  # noqa: E402
    DefOperacao,
    DefPeca,
    DefPecaComponente,
    DefPecaOperacao,
    DefPecaUserPref,
    DefRegraQuantidade,
)


GRUPO_FUNDOS = "FUNDOS"
CHAVE_MATERIAL_FUNDOS = "MATERIAL_FUNDOS"
CHAVE_ACABAMENTO_SUP = "ACABAMENTO_FACE_SUP"
CHAVE_ACABAMENTO_INF = "ACABAMENTO_FACE_INF"

CODIGO_PECA_UNIOES = "SISTEMAS_UNIAO"
REFERENCIA_FERRAGEM_PES = "PES"
REGRA_PES = "PES_NIVELADORES"
REGRA_UNIOES = "UNIAO_TOPOS_128"

METODO_ESCALAO_AREA = "ESCALAO_AREA"


@dataclass(frozen=True)
class OperacaoSeed:
    """Uma operacao associada a uma peca."""

    codigo_operacao: str
    ordem: int
    regra_calculo: str
    ativo: bool = True
    quantidade_base: Decimal | None = None
    tempo_setup_minutos: Decimal | None = None
    tempo_por_unidade_minutos: Decimal | None = None
    unidade_tempo: str | None = None
    metodo_calculo: str | None = None
    observacoes: str | None = None


@dataclass(frozen=True)
class FundoSimplesSeed:
    """Uma peca simples do grupo FUNDOS (codigo de orlas C1-C2-L1-L2)."""

    codigo: str
    nome: str
    codigo_orlas: str


@dataclass(frozen=True)
class FundoComPesSeed:
    """Um conjunto FUNDO+PES construido sobre uma peca simples ja existente."""

    codigo: str
    nome: str
    descricao: str
    codigo_fundo: str
    codigo_orlas: str


# Operacoes iguais as do FUNDO_2000: corte e orlagem ativos; a furacao em CNC
# fica associada mas desativada (foi assim que o catalogo foi montado).
OPERACOES_FUNDO_SIMPLES: tuple[OperacaoSeed, ...] = (
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

# Operacoes iguais as do FUNDO+PES.
OPERACOES_FUNDO_COM_PES: tuple[OperacaoSeed, ...] = (
    OperacaoSeed(
        codigo_operacao="CORTE_PAINEL",
        ordem=1,
        regra_calculo=FIXA,
        quantidade_base=Decimal("1.2000"),
        tempo_setup_minutos=Decimal("1.0000"),
        tempo_por_unidade_minutos=Decimal("0.8000"),
        unidade_tempo="UN",
    ),
    OperacaoSeed(
        codigo_operacao="CNC_ABD",
        ordem=2,
        regra_calculo=POR_PECA,
        ativo=False,
        quantidade_base=Decimal("0.8000"),
        tempo_setup_minutos=Decimal("0.6000"),
        tempo_por_unidade_minutos=Decimal("1.2000"),
        unidade_tempo="PECA",
        metodo_calculo=METODO_ESCALAO_AREA,
        observacoes="Furacao Cavilhas Horizontal Topos",
    ),
    OperacaoSeed(
        codigo_operacao="SETUP_MAQUINA",
        ordem=3,
        regra_calculo=FIXA,
        quantidade_base=Decimal("1.8000"),
        tempo_setup_minutos=Decimal("2.0000"),
        tempo_por_unidade_minutos=Decimal("1.6000"),
        unidade_tempo="PECA",
        observacoes="pes + embalamento ou aplicacao em moveis",
    ),
)

FUNDOS_SIMPLES: tuple[FundoSimplesSeed, ...] = (
    FundoSimplesSeed("FUNDO_2111", "Fundo[2111]", "2111"),
    FundoSimplesSeed("FUNDO_2200", "Fundo[2200]", "2200"),
    FundoSimplesSeed("FUNDO_2222", "Fundo[2222]", "2222"),
)

FUNDOS_COM_PES: tuple[FundoComPesSeed, ...] = (
    FundoComPesSeed(
        codigo="FUNDO_2111+PES",
        nome="FUNDO[2111]+PES",
        descricao="FUNDO 2111 + PES",
        codigo_fundo="FUNDO_2111",
        codigo_orlas="2111",
    ),
    FundoComPesSeed(
        codigo="FUNDO_2200+PES",
        nome="FUNDO[2200]+PES",
        descricao="FUNDO 2200 + PES",
        codigo_fundo="FUNDO_2200",
        codigo_orlas="2200",
    ),
    FundoComPesSeed(
        codigo="FUNDO_2222+PES",
        nome="FUNDO[2222]+PES",
        descricao="FUNDO 2222 + PES",
        codigo_fundo="FUNDO_2222",
        codigo_orlas="2222",
    ),
)


@dataclass(frozen=True)
class FundosVariantesResult:
    """Resumo do seed das variantes de fundos."""

    pecas_criadas: int
    pecas_reutilizadas: int
    operacoes_criadas: int
    componentes_criados: int
    prefs_criadas: int


def get_peca(session: Session, codigo: str) -> DefPeca | None:
    """Devolver uma peca do catalogo pelo codigo."""
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo)
    ).scalar_one_or_none()


def get_operacao_id(session: Session, codigo: str) -> int:
    """Devolver o id de uma operacao pelo codigo (erro se nao existir)."""
    operacao = session.execute(
        select(DefOperacao).where(DefOperacao.codigo == codigo)
    ).scalar_one_or_none()
    if operacao is None:
        raise ValueError(f"Operacao {codigo} nao existe nesta base de dados")
    return operacao.id


def get_regra_quantidade_id(session: Session, codigo: str) -> int | None:
    """Devolver o id de uma regra de quantidade pelo codigo (None se faltar)."""
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
    criadas = 0
    for seed in seeds:
        operacao = DefPecaOperacao(
            def_peca_id=peca.id,
            def_operacao_id=get_operacao_id(session, seed.codigo_operacao),
            ordem=seed.ordem,
            regra_calculo=seed.regra_calculo,
            quantidade_base=seed.quantidade_base,
            obrigatorio=True,
            ativo=seed.ativo,
            observacoes=seed.observacoes,
            tempo_setup_minutos=seed.tempo_setup_minutos,
            tempo_por_unidade_minutos=seed.tempo_por_unidade_minutos,
            unidade_tempo=seed.unidade_tempo,
            metodo_calculo=seed.metodo_calculo,
        )
        session.add(operacao)
        criadas += 1
    session.flush()
    return criadas


def criar_fundos_simples(session: Session) -> tuple[int, int, int]:
    """Criar as peças simples em falta. Devolve (criadas, reutilizadas, operacoes)."""
    criadas = 0
    reutilizadas = 0
    operacoes = 0

    for seed in FUNDOS_SIMPLES:
        existente = get_peca(session, seed.codigo)
        if existente is not None:
            reutilizadas += 1
            print(f"Peca {seed.codigo} ja existe, mantida")
            continue

        orla_c1, orla_c2, orla_l1, orla_l2 = (
            normalize_orla_type(digito) for digito in seed.codigo_orlas
        )
        peca = DefPeca(
            codigo=seed.codigo,
            nome=seed.nome,
            grupo=GRUPO_FUNDOS,
            tipo_peca=SIMPLES,
            natureza=MATERIAL,
            orientacao=NEUTRA,
            funcao=FUNDO,
            formula_comp="LM",
            formula_larg="PM",
            orla_c1=orla_c1,
            orla_c2=orla_c2,
            orla_l1=orla_l1,
            orla_l2=orla_l2,
            chave_valueset_material=CHAVE_MATERIAL_FUNDOS,
            permite_acabamento=False,
            chave_valueset_acabamento_sup=CHAVE_ACABAMENTO_SUP,
            chave_valueset_acabamento_inf=CHAVE_ACABAMENTO_INF,
            sem_material=False,
            ativo=True,
        )
        session.add(peca)
        session.flush()
        operacoes += criar_operacoes(session, peca, OPERACOES_FUNDO_SIMPLES)
        criadas += 1
        print(f"Peca {seed.codigo} criada ({seed.nome})")

    return criadas, reutilizadas, operacoes


def criar_componentes_com_pes(
    session: Session, conjunto: DefPeca, seed: FundoComPesSeed, fundo: DefPeca
) -> int:
    """Criar os componentes de um conjunto FUNDO+PES. Devolve quantos criou."""
    peca_unioes = get_peca(session, CODIGO_PECA_UNIOES)
    regra_pes_id = get_regra_quantidade_id(session, REGRA_PES)
    regra_unioes_id = get_regra_quantidade_id(session, REGRA_UNIOES)

    componentes = [
        DefPecaComponente(
            def_peca_pai_id=conjunto.id,
            tipo_componente=PECA,
            def_peca_componente_id=fundo.id,
            descricao=f"Fundo com Orla {seed.codigo_orlas}",
            ordem=1,
            quantidade=Decimal("1.000"),
            regra_quantidade=QUANTIDADE_FIXA,
            obrigatorio=True,
            ativo=True,
            zona_aplicacao=GERAL,
            dimensao_referencia=COMP,
            numero_topos=0,
            modo_quantidade=TOTAL,
            prioridade_valueset=1,
            formula_comp="LM",
            formula_larg="PM",
        ),
        DefPecaComponente(
            def_peca_pai_id=conjunto.id,
            tipo_componente=FERRAGEM,
            referencia_componente=REFERENCIA_FERRAGEM_PES,
            descricao="Pes com Regra aplicada Fundo",
            ordem=2,
            quantidade=Decimal("1.000"),
            regra_quantidade=POR_COMPRIMENTO_LARGURA,
            def_regra_quantidade_id=regra_pes_id,
            obrigatorio=True,
            ativo=True,
            zona_aplicacao=GERAL,
            dimensao_referencia=COMP,
            numero_topos=0,
            modo_quantidade=TOTAL,
            prioridade_valueset=1,
        ),
    ]

    if peca_unioes is None:
        print(
            f"Aviso: peca {CODIGO_PECA_UNIOES} nao existe; {seed.codigo} fica sem unioes"
        )
    else:
        for ordem, (descricao, prioridade) in enumerate(
            (("Unioes para Modulos Cavilha", 1), ("Unioes para Modulos Parafusos", 2)),
            start=3,
        ):
            componentes.append(
                DefPecaComponente(
                    def_peca_pai_id=conjunto.id,
                    tipo_componente=PECA,
                    def_peca_componente_id=peca_unioes.id,
                    descricao=descricao,
                    ordem=ordem,
                    quantidade=Decimal("1.000"),
                    regra_quantidade=QUANTIDADE_FIXA,
                    def_regra_quantidade_id=regra_unioes_id,
                    obrigatorio=True,
                    ativo=True,
                    zona_aplicacao=DOIS_TOPOS,
                    dimensao_referencia=MEDIDA_TOPO,
                    numero_topos=2,
                    modo_quantidade=POR_TOPO,
                    prioridade_valueset=prioridade,
                )
            )

    for componente in componentes:
        session.add(componente)
    session.flush()

    return len(componentes)


def criar_fundos_com_pes(session: Session) -> tuple[int, int, int, int]:
    """Criar os conjuntos +PES em falta.

    Devolve ``(criados, reutilizados, operacoes, componentes)``.
    """
    criados = 0
    reutilizados = 0
    operacoes = 0
    componentes = 0

    for seed in FUNDOS_COM_PES:
        existente = get_peca(session, seed.codigo)
        if existente is not None:
            reutilizados += 1
            print(f"Conjunto {seed.codigo} ja existe, mantido")
            continue

        fundo = get_peca(session, seed.codigo_fundo)
        if fundo is None:
            raise ValueError(
                f"Peca {seed.codigo_fundo} nao existe; nao e possivel criar {seed.codigo}"
            )

        conjunto = DefPeca(
            codigo=seed.codigo,
            nome=seed.nome,
            descricao=seed.descricao,
            grupo=GRUPO_FUNDOS,
            tipo_peca=COMPOSTA,
            natureza=CONJUNTO,
            orientacao=NEUTRA,
            funcao=FUNDO,
            permite_acabamento=False,
            sem_material=True,
            ativo=True,
        )
        session.add(conjunto)
        session.flush()

        operacoes += criar_operacoes(session, conjunto, OPERACOES_FUNDO_COM_PES)
        componentes += criar_componentes_com_pes(session, conjunto, seed, fundo)
        criados += 1
        print(f"Conjunto {seed.codigo} criado ({seed.nome})")

    return criados, reutilizados, operacoes, componentes


def adicionar_as_bibliotecas(session: Session) -> int:
    """Mostrar as novas peças a quem tem biblioteca personalizada.

    Quem nunca personalizou a biblioteca ve todas as peças ativas e nao precisa
    de nada. Quem personalizou so ve o que escolheu: sem esta linha, as peças
    novas ficariam invisiveis no custeio.
    """
    codigos = [seed.codigo for seed in FUNDOS_SIMPLES]
    codigos += [seed.codigo for seed in FUNDOS_COM_PES]

    pecas_ids = [
        peca.id
        for peca in (get_peca(session, codigo) for codigo in codigos)
        if peca is not None
    ]
    if not pecas_ids:
        return 0

    users_com_biblioteca = session.execute(
        select(DefPecaUserPref.user_id).distinct()
    ).scalars().all()

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


def seed_fundos_variantes(session: Session) -> FundosVariantesResult:
    """Criar as peças e conjuntos de fundos em falta (idempotente)."""
    simples_criadas, simples_reutilizadas, operacoes_simples = criar_fundos_simples(session)
    (
        conjuntos_criados,
        conjuntos_reutilizados,
        operacoes_conjuntos,
        componentes,
    ) = criar_fundos_com_pes(session)
    prefs = adicionar_as_bibliotecas(session)

    session.commit()

    return FundosVariantesResult(
        pecas_criadas=simples_criadas + conjuntos_criados,
        pecas_reutilizadas=simples_reutilizadas + conjuntos_reutilizados,
        operacoes_criadas=operacoes_simples + operacoes_conjuntos,
        componentes_criados=componentes,
        prefs_criadas=prefs,
    )


def print_summary(result: FundosVariantesResult) -> None:
    """Escrever o resumo final para o utilizador."""
    print("Resumo final")
    print(f"Pecas criadas: {result.pecas_criadas}")
    print(f"Pecas mantidas (ja existiam): {result.pecas_reutilizadas}")
    print(f"Operacoes associadas criadas: {result.operacoes_criadas}")
    print(f"Componentes criados: {result.componentes_criados}")
    print(f"Linhas de biblioteca de utilizador criadas: {result.prefs_criadas}")


def main() -> int:
    """Criar as variantes de fundos na base de dados configurada."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = seed_fundos_variantes(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
