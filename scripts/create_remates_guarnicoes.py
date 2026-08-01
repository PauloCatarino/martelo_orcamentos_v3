"""Criar as peças do grupo REMATES/GUARNICOES e as suas chaves de material.

Os remates e guarnicoes sao tiras aplicadas no movel (remates verticais,
rodatetos, rodapes, enchimentos e guarnicoes). Cada familia tem a sua propria
chave de material no ValueSet.

Comecam so pelo remate vertical; as restantes familias entram aqui a medida que
forem definidas.

O seed e idempotente: cria apenas o que falta, nunca apaga nem altera registos
existentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domain.orla_types import normalize_orla_type  # noqa: E402
from app.domain.peca_funcao_types import REMATE  # noqa: E402
from app.domain.peca_natureza_types import MATERIAL, VERTICAL  # noqa: E402
from app.domain.peca_types import SIMPLES  # noqa: E402
from app.domain.regra_operacao_types import POR_ORLAS, POR_PECA  # noqa: E402
from app.models import (  # noqa: E402
    DefOperacao,
    DefPeca,
    DefPecaOperacao,
    DefPecaUserPref,
    DefValuesetChave,
)


GRUPO_REMATES_GUARNICOES = "REMATES/GUARNICOES"

CHAVE_REMATES_VERTICAIS = "MATERIAL_REMATES_VERTICAIS"


@dataclass(frozen=True)
class ChaveSeed:
    """Uma chave de material do ValueSet."""

    codigo: str
    nome: str
    descricao: str


@dataclass(frozen=True)
class PecaSeed:
    """Uma peca de remate/guarnicao (codigo de orlas C1-C2-L1-L2)."""

    codigo: str
    nome: str
    descricao: str
    chave_material: str
    orientacao: str
    funcao: str | None
    formula_comp: str | None
    formula_larg: str | None
    codigo_orlas: str


CHAVES: tuple[ChaveSeed, ...] = (
    ChaveSeed(
        CHAVE_REMATES_VERTICAIS,
        "Remates Verticais",
        "Material dos remates verticais.",
    ),
)

PECAS: tuple[PecaSeed, ...] = (
    PecaSeed(
        codigo="REMATE_VERTICAL_2220",
        nome="Remate Vertical[2220]",
        descricao="Remate vertical: material + corte + orlagem.",
        chave_material=CHAVE_REMATES_VERTICAIS,
        orientacao=VERTICAL,
        funcao=REMATE,
        # Altura do modulo por 100 mm de largura fixa.
        formula_comp="HM",
        formula_larg="100",
        codigo_orlas="2220",
    ),
)

# Sem unioes nem outros associados: o remate e so corte + orlagem.
OPERACOES: tuple[tuple[str, int, str], ...] = (
    ("CORTE_PAINEL", 1, POR_PECA),
    ("ORLAGEM_PECA", 2, POR_ORLAS),
)


@dataclass(frozen=True)
class RematesGuarnicoesResult:
    """Resumo do seed dos remates e guarnicoes."""

    chaves_criadas: int
    pecas_criadas: int
    pecas_reutilizadas: int
    operacoes_criadas: int
    prefs_criadas: int


def get_peca(session: Session, codigo: str) -> DefPeca | None:
    """Devolver uma peca do catalogo pelo codigo."""
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo)
    ).scalar_one_or_none()


def criar_chaves(session: Session) -> int:
    """Criar as chaves de material em falta. Devolve quantas criou."""
    criadas = 0
    for seed in CHAVES:
        existente = session.execute(
            select(DefValuesetChave).where(DefValuesetChave.codigo == seed.codigo)
        ).scalar_one_or_none()
        if existente is not None:
            print(f"Chave {seed.codigo} ja existe, mantida")
            continue

        ordem_maxima = session.execute(
            select(func.max(DefValuesetChave.ordem)).where(
                DefValuesetChave.grupo == "MATERIAIS"
            )
        ).scalar_one()
        session.add(
            DefValuesetChave(
                codigo=seed.codigo,
                nome=seed.nome,
                descricao=seed.descricao,
                tipo="MATERIAL",
                grupo="MATERIAIS",
                sistema=True,
                ativo=True,
                ordem=(ordem_maxima or 0) + 1,
            )
        )
        session.flush()
        criadas += 1
        print(f"Chave {seed.codigo} criada")

    return criadas


def get_operacao_id(session: Session, codigo: str) -> int:
    """Devolver o id de uma operacao pelo codigo (erro se nao existir)."""
    operacao = session.execute(
        select(DefOperacao).where(DefOperacao.codigo == codigo)
    ).scalar_one_or_none()
    if operacao is None:
        raise ValueError(f"Operacao {codigo} nao existe nesta base de dados")
    return operacao.id


def criar_operacoes(session: Session, peca: DefPeca) -> int:
    """Criar corte + orlagem numa peca acabada de criar. Devolve quantas criou."""
    for codigo_operacao, ordem, regra_calculo in OPERACOES:
        session.add(
            DefPecaOperacao(
                def_peca_id=peca.id,
                def_operacao_id=get_operacao_id(session, codigo_operacao),
                ordem=ordem,
                regra_calculo=regra_calculo,
                obrigatorio=True,
                ativo=True,
            )
        )
    session.flush()
    return len(OPERACOES)


def criar_pecas(session: Session) -> tuple[int, int, int]:
    """Criar as peças em falta. Devolve (criadas, reutilizadas, operacoes)."""
    criadas = 0
    reutilizadas = 0
    operacoes = 0

    for seed in PECAS:
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
            descricao=seed.descricao,
            grupo=GRUPO_REMATES_GUARNICOES,
            tipo_peca=SIMPLES,
            natureza=MATERIAL,
            orientacao=seed.orientacao,
            funcao=seed.funcao,
            formula_comp=seed.formula_comp,
            formula_larg=seed.formula_larg,
            orla_c1=orla_c1,
            orla_c2=orla_c2,
            orla_l1=orla_l1,
            orla_l2=orla_l2,
            chave_valueset_material=seed.chave_material,
            permite_acabamento=False,
            sem_material=False,
            ativo=True,
        )
        session.add(peca)
        session.flush()
        operacoes += criar_operacoes(session, peca)
        criadas += 1
        print(f"Peca {seed.codigo} criada ({seed.nome})")

    return criadas, reutilizadas, operacoes


def adicionar_as_bibliotecas(session: Session) -> int:
    """Mostrar as peças novas a quem tem biblioteca personalizada.

    Quem nunca personalizou a biblioteca ve todas as peças ativas. Quem
    personalizou so ve o que escolheu: sem isto, as peças novas ficariam
    invisiveis no custeio.
    """
    pecas_ids = [
        peca.id
        for peca in (get_peca(session, seed.codigo) for seed in PECAS)
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


def seed_remates_guarnicoes(session: Session) -> RematesGuarnicoesResult:
    """Criar chaves e peças de remates/guarnicoes em falta (idempotente)."""
    chaves_criadas = criar_chaves(session)
    criadas, reutilizadas, operacoes = criar_pecas(session)
    prefs = adicionar_as_bibliotecas(session)

    session.commit()

    return RematesGuarnicoesResult(
        chaves_criadas=chaves_criadas,
        pecas_criadas=criadas,
        pecas_reutilizadas=reutilizadas,
        operacoes_criadas=operacoes,
        prefs_criadas=prefs,
    )


def print_summary(result: RematesGuarnicoesResult) -> None:
    """Escrever o resumo final para o utilizador."""
    print("Resumo final")
    print(f"Chaves de material criadas: {result.chaves_criadas}")
    print(f"Pecas criadas: {result.pecas_criadas}")
    print(f"Pecas mantidas (ja existiam): {result.pecas_reutilizadas}")
    print(f"Operacoes associadas criadas: {result.operacoes_criadas}")
    print(f"Linhas de biblioteca de utilizador criadas: {result.prefs_criadas}")
    print(
        "Nota: nos modelos ValueSet em uso, acrescente uma linha com a chave "
        "Remates Verticais e o material pretendido, senao o remate fica sem "
        "material no custeio."
    )


def main() -> int:
    """Criar as peças de remates/guarnicoes na base de dados configurada."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = seed_remates_guarnicoes(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
