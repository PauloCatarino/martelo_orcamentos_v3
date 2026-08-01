"""Criar as peças do grupo PAINEIS ACABAMENTO e as suas chaves de material.

Os paineis de acabamento sao peças vistas que se aplicam por fora do movel
(tampo, lateral, fundo, costa e painel de acabamento). Cada uma tem a sua
propria chave de material no ValueSet, para o utilizador poder escolher um
material diferente do material estrutural do mesmo sitio.

O que o seed faz:

* cria as 5 chaves de material (``MATERIAL_..._ACABAMENTO``);
* renomeia o ``TAMPO_2222`` que ja existia para ``TAMPO_ACABAMENTO_2222`` e
  aponta-o para a chave nova;
* cria as 4 peças em falta (lateral, fundo, costa e painel), copiando o molde
  do tampo: orlas 2222, corte + orlagem, e as formulas dimensionais da peça
  estrutural equivalente;
* acrescenta as peças novas as bibliotecas de quem personalizou a sua.

As peças ficam **sem** chaves de acabamento sup/inf: por defeito nao levam
acabamento nenhum e e no custeio, linha a linha, que o utilizador define em que
faces aplica (``Editar Dados do Acabamento``).

O seed e idempotente: cria apenas o que falta e nunca apaga nada.
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
from app.domain.peca_funcao_types import COSTA, FUNDO, LATERAL, TETO  # noqa: E402
from app.domain.peca_natureza_types import (  # noqa: E402
    HORIZONTAL,
    MATERIAL,
    NEUTRA,
    VERTICAL,
)
from app.domain.peca_types import SIMPLES  # noqa: E402
from app.domain.regra_operacao_types import POR_ORLAS, POR_PECA  # noqa: E402
from app.models import (  # noqa: E402
    DefOperacao,
    DefPeca,
    DefPecaOperacao,
    DefPecaUserPref,
    DefValuesetChave,
)


GRUPO_PAINEIS_ACABAMENTO = "PAINEIS ACABAMENTO"

# O tampo de acabamento ja existia com este codigo, criado a mao.
CODIGO_TAMPO_ANTIGO = "TAMPO_2222"


@dataclass(frozen=True)
class ChaveSeed:
    """Uma chave de material do ValueSet."""

    codigo: str
    nome: str
    descricao: str


@dataclass(frozen=True)
class PecaSeed:
    """Uma peça de acabamento (codigo de orlas C1-C2-L1-L2)."""

    codigo: str
    nome: str
    descricao: str
    chave_material: str
    orientacao: str
    funcao: str | None
    formula_comp: str | None
    formula_larg: str | None
    codigo_orlas: str = "2222"


CHAVE_TAMPO = "MATERIAL_TAMPO_ACABAMENTO"
CHAVE_LATERAL = "MATERIAL_LATERAL_ACABAMENTO"
CHAVE_FUNDO = "MATERIAL_FUNDO_ACABAMENTO"
CHAVE_COSTA = "MATERIAL_COSTA_ACABAMENTO"
CHAVE_PAINEL = "MATERIAL_PAINEL_ACABAMENTO"

CHAVES: tuple[ChaveSeed, ...] = (
    ChaveSeed(CHAVE_TAMPO, "Material Tampo Acabamento", "Material dos tampos de acabamento."),
    ChaveSeed(
        CHAVE_LATERAL,
        "Material Lateral Acabamento",
        "Material das laterais de acabamento.",
    ),
    ChaveSeed(CHAVE_FUNDO, "Material Fundo Acabamento", "Material dos fundos de acabamento."),
    ChaveSeed(CHAVE_COSTA, "Material Costa Acabamento", "Material das costas de acabamento."),
    ChaveSeed(
        CHAVE_PAINEL,
        "Material Painel Acabamento",
        "Material dos paineis de acabamento genericos.",
    ),
)

# O tampo ja existe na base do Paulo; fica aqui para o seed o poder criar numa
# base nova (beta) e para o renomear/apontar a chave nova onde ja existia.
TAMPO = PecaSeed(
    codigo="TAMPO_ACABAMENTO_2222",
    nome="Tampo Acabamento[2222]",
    descricao="Tampo de acabamento: material + corte + orlagem.",
    chave_material=CHAVE_TAMPO,
    orientacao=HORIZONTAL,
    funcao=TETO,
    formula_comp=None,
    formula_larg=None,
)

PECAS: tuple[PecaSeed, ...] = (
    TAMPO,
    PecaSeed(
        codigo="LATERAL_ACABAMENTO_2222",
        nome="Lateral Acabamento[2222]",
        descricao="Lateral de acabamento: material + corte + orlagem.",
        chave_material=CHAVE_LATERAL,
        orientacao=VERTICAL,
        funcao=LATERAL,
        formula_comp="HM",
        formula_larg="LM",
    ),
    PecaSeed(
        codigo="FUNDO_ACABAMENTO_2222",
        nome="Fundo Acabamento[2222]",
        descricao="Fundo de acabamento: material + corte + orlagem.",
        chave_material=CHAVE_FUNDO,
        orientacao=HORIZONTAL,
        funcao=FUNDO,
        formula_comp="LM",
        formula_larg="PM",
    ),
    PecaSeed(
        codigo="COSTA_ACABAMENTO_2222",
        nome="Costa Acabamento[2222]",
        descricao="Costa de acabamento: material + corte + orlagem.",
        chave_material=CHAVE_COSTA,
        orientacao=VERTICAL,
        funcao=COSTA,
        formula_comp="HM",
        formula_larg="LM",
    ),
    PecaSeed(
        codigo="PAINEL_ACABAMENTO_2222",
        nome="Painel Acabamento[2222]",
        descricao="Painel de acabamento: material + corte + orlagem.",
        chave_material=CHAVE_PAINEL,
        orientacao=NEUTRA,
        funcao=None,
        formula_comp=None,
        formula_larg=None,
    ),
)

# As mesmas operacoes que o tampo de acabamento ja tinha configurado a mao.
OPERACOES: tuple[tuple[str, int, str], ...] = (
    ("CORTE_PAINEL", 1, POR_PECA),
    ("ORLAGEM_PECA", 2, POR_ORLAS),
)


@dataclass(frozen=True)
class PaineisAcabamentoResult:
    """Resumo do seed dos paineis de acabamento."""

    chaves_criadas: int
    tampo_renomeado: bool
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


def renomear_tampo_existente(session: Session) -> bool:
    """Passar o TAMPO_2222 antigo para o codigo e a chave de acabamento.

    So mexe quando o codigo novo ainda nao existe: assim o seed pode correr
    varias vezes sem duplicar nem voltar a escrever por cima.
    """
    if get_peca(session, TAMPO.codigo) is not None:
        return False

    antigo = get_peca(session, CODIGO_TAMPO_ANTIGO)
    if antigo is None:
        return False

    antigo.codigo = TAMPO.codigo
    antigo.nome = TAMPO.nome
    antigo.grupo = GRUPO_PAINEIS_ACABAMENTO
    antigo.chave_valueset_material = TAMPO.chave_material
    session.flush()
    print(
        f"Peca {CODIGO_TAMPO_ANTIGO} renomeada para {TAMPO.codigo} "
        f"(chave {TAMPO.chave_material})"
    )
    return True


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
            grupo=GRUPO_PAINEIS_ACABAMENTO,
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
            # Aceita acabamento, mas sem chaves: nada e aplicado por defeito;
            # e o utilizador que escolhe as faces no custeio.
            permite_acabamento=True,
            chave_valueset_acabamento_sup=None,
            chave_valueset_acabamento_inf=None,
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


def seed_paineis_acabamento(session: Session) -> PaineisAcabamentoResult:
    """Criar chaves e peças de acabamento em falta (idempotente)."""
    chaves_criadas = criar_chaves(session)
    tampo_renomeado = renomear_tampo_existente(session)
    criadas, reutilizadas, operacoes = criar_pecas(session)
    prefs = adicionar_as_bibliotecas(session)

    session.commit()

    return PaineisAcabamentoResult(
        chaves_criadas=chaves_criadas,
        tampo_renomeado=tampo_renomeado,
        pecas_criadas=criadas,
        pecas_reutilizadas=reutilizadas,
        operacoes_criadas=operacoes,
        prefs_criadas=prefs,
    )


def print_summary(result: PaineisAcabamentoResult) -> None:
    """Escrever o resumo final para o utilizador."""
    print("Resumo final")
    print(f"Chaves de material criadas: {result.chaves_criadas}")
    print(
        "Tampo antigo renomeado: "
        f"{'sim' if result.tampo_renomeado else 'nao (ja estava tratado)'}"
    )
    print(f"Pecas criadas: {result.pecas_criadas}")
    print(f"Pecas mantidas (ja existiam): {result.pecas_reutilizadas}")
    print(f"Operacoes associadas criadas: {result.operacoes_criadas}")
    print(f"Linhas de biblioteca de utilizador criadas: {result.prefs_criadas}")
    print(
        "Nota: nos modelos ValueSet em uso, acrescente uma linha para cada chave "
        "nova (Material Tampo/Lateral/Fundo/Costa/Painel Acabamento) com o "
        "material pretendido, senao as peças ficam sem material no custeio."
    )


def main() -> int:
    """Criar as peças de acabamento na base de dados configurada."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = seed_paineis_acabamento(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
