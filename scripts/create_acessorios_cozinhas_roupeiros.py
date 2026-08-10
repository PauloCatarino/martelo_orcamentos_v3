"""Criar acessórios de cozinhas/roupeiros e as respetivas chaves ValueSet.

As famílias genéricas ``Acessórios Cozinha`` e ``Acessórios Roupeiros``
permitem acrescentar artigos aos modelos ValueSet sem multiplicar categorias
antes de existir necessidade real. Baldes do lixo, cantos e porta-talheres
mantêm chaves próprias porque já são categorias identificadas.

O seed é idempotente: cria apenas o que falta. A única correção admitida num
registo existente é alinhar a chave de material de uma das seis peças deste
seed; isto permite aproveitar a definição ``ACESSORIOS_BALDE_LIXO`` já criada
no V3 com a chave provisória de grampas de rodapé. Nunca apaga registos.
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
from app.domain.peca_funcao_types import FERRAGEM as FUNCAO_FERRAGEM  # noqa: E402
from app.domain.peca_natureza_types import (  # noqa: E402
    FERRAGEM as NATUREZA_FERRAGEM,
    NEUTRA,
)
from app.domain.peca_subgrupo_types import GRUPO_FERRAGENS  # noqa: E402
from app.domain.peca_types import SIMPLES  # noqa: E402
from app.models import DefPeca, DefPecaUserPref, DefValuesetChave  # noqa: E402


SUBFAMILIA_COZINHAS = "COZINHAS"
SUBFAMILIA_ROUPEIROS = "ROUPEIROS"

CHAVE_BALDE_LIXO = "FERRAGEM_BALDE_LIXO"
CHAVE_CANTOS = "FERRAGEM_CANTOS"
CHAVE_PORTA_TALHERES = "FERRAGEM_PORTA_TALHERES"
CHAVE_ACESSORIOS_COZINHA = "FERRAGEM_ACESSORIOS_COZINHA"
CHAVE_ACESSORIOS_ROUPEIROS = "FERRAGEM_ACESSORIOS_ROUPEIROS"


@dataclass(frozen=True)
class ChaveSeed:
    """Uma categoria de ferragem comprada no ValueSet."""

    codigo: str
    nome: str
    descricao: str


@dataclass(frozen=True)
class PecaSeed:
    """Uma ferragem/acessório sem medidas nem operações de produção."""

    codigo: str
    nome: str
    descricao: str
    chave_material: str
    subfamilia: str


CHAVES: tuple[ChaveSeed, ...] = (
    ChaveSeed(
        CHAVE_BALDE_LIXO,
        "Balde Lixo",
        "Baldes e sistemas de separação de lixo para cozinhas.",
    ),
    ChaveSeed(
        CHAVE_CANTOS,
        "Cantos",
        "Ferragens e mecanismos para módulos de canto de cozinhas.",
    ),
    ChaveSeed(
        CHAVE_PORTA_TALHERES,
        "Porta Talheres",
        "Porta-talheres e divisórias interiores de gaveta para cozinhas.",
    ),
    ChaveSeed(
        CHAVE_ACESSORIOS_COZINHA,
        "Acessórios Cozinha",
        "Acessórios de cozinha ainda sem categoria ValueSet própria.",
    ),
    ChaveSeed(
        CHAVE_ACESSORIOS_ROUPEIROS,
        "Acessórios Roupeiros",
        "Acessórios de roupeiro ainda sem categoria ValueSet própria.",
    ),
)


PECAS: tuple[PecaSeed, ...] = (
    PecaSeed(
        "ACESSORIOS_BALDE_LIXO",
        "Balde Lixo",
        "Balde ou sistema de separação de lixo para cozinha.",
        CHAVE_BALDE_LIXO,
        SUBFAMILIA_COZINHAS,
    ),
    PecaSeed(
        "ACESSORIOS_PORTA_TALHERES",
        "Porta Talheres",
        "Porta-talheres ou divisória interior de gaveta de cozinha.",
        CHAVE_PORTA_TALHERES,
        SUBFAMILIA_COZINHAS,
    ),
    PecaSeed(
        "ACESSORIOS_CANTOS",
        "Cantos",
        "Ferragem ou mecanismo para módulo de canto de cozinha.",
        CHAVE_CANTOS,
        SUBFAMILIA_COZINHAS,
    ),
    PecaSeed(
        "ACESSORIOS_FUNDO_ALUMINIO",
        "Fundo Alumínio",
        "Fundo de alumínio para módulo de cozinha.",
        CHAVE_ACESSORIOS_COZINHA,
        SUBFAMILIA_COZINHAS,
    ),
    PecaSeed(
        "ACESSORIOS_GRELHA_VELUDO",
        "Grelha Veludo",
        "Grelha revestida a veludo para interior de roupeiro.",
        CHAVE_ACESSORIOS_ROUPEIROS,
        SUBFAMILIA_ROUPEIROS,
    ),
    PecaSeed(
        "ACESSORIOS_PORTA_CALCAS",
        "Porta Calças",
        "Acessório porta-calças para interior de roupeiro.",
        CHAVE_ACESSORIOS_ROUPEIROS,
        SUBFAMILIA_ROUPEIROS,
    ),
)


@dataclass(frozen=True)
class AcessoriosCozinhasRoupeirosResult:
    """Resumo das alterações feitas pelo seed."""

    chaves_criadas: int
    chaves_reutilizadas: int
    pecas_criadas: int
    pecas_reutilizadas: int
    pecas_corrigidas: int
    prefs_criadas: int


def _get_peca(session: Session, codigo: str) -> DefPeca | None:
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo)
    ).scalar_one_or_none()


def criar_chaves(session: Session) -> tuple[int, int]:
    """Criar as cinco chaves em falta, sem alterar chaves existentes."""
    criadas = 0
    reutilizadas = 0

    for seed in CHAVES:
        existente = session.execute(
            select(DefValuesetChave).where(DefValuesetChave.codigo == seed.codigo)
        ).scalar_one_or_none()
        if existente is not None:
            reutilizadas += 1
            print(f"Chave {seed.codigo} já existe, mantida")
            continue

        ordem_maxima = session.execute(
            select(func.max(DefValuesetChave.ordem)).where(
                DefValuesetChave.grupo == GRUPO_FERRAGENS
            )
        ).scalar_one()
        session.add(
            DefValuesetChave(
                codigo=seed.codigo,
                nome=seed.nome,
                descricao=seed.descricao,
                tipo="FERRAGEM",
                grupo=GRUPO_FERRAGENS,
                sistema=True,
                ativo=True,
                ordem=(ordem_maxima or 0) + 1,
            )
        )
        session.flush()
        criadas += 1
        print(f"Chave {seed.codigo} criada")

    return criadas, reutilizadas


def criar_pecas(session: Session) -> tuple[int, int, int]:
    """Criar as seis peças e corrigir apenas a sua ligação de material."""
    criadas = 0
    reutilizadas = 0
    corrigidas = 0

    for seed in PECAS:
        existente = _get_peca(session, seed.codigo)
        if existente is not None:
            reutilizadas += 1
            if existente.chave_valueset_material != seed.chave_material:
                anterior = existente.chave_valueset_material or "sem chave"
                existente.chave_valueset_material = seed.chave_material
                session.flush()
                corrigidas += 1
                print(
                    f"Peça {seed.codigo}: chave corrigida de {anterior} "
                    f"para {seed.chave_material}"
                )
            else:
                print(f"Peça {seed.codigo} já existe, mantida")
            continue

        session.add(
            DefPeca(
                codigo=seed.codigo,
                nome=seed.nome,
                descricao=seed.descricao,
                grupo=GRUPO_FERRAGENS,
                subgrupo=seed.subfamilia,
                tipo_peca=SIMPLES,
                natureza=NATUREZA_FERRAGEM,
                orientacao=NEUTRA,
                funcao=FUNCAO_FERRAGEM,
                usa_orlas=False,
                chave_valueset_material=seed.chave_material,
                permite_acabamento=False,
                sem_material=False,
                ativo=True,
            )
        )
        session.flush()
        criadas += 1
        print(
            f"Peça {seed.codigo} criada "
            f"({GRUPO_FERRAGENS} > {seed.subfamilia})"
        )

    return criadas, reutilizadas, corrigidas


def adicionar_as_bibliotecas(session: Session) -> int:
    """Mostrar as peças novas a quem já personalizou a biblioteca."""
    pecas_ids = [
        peca.id
        for peca in (_get_peca(session, seed.codigo) for seed in PECAS)
        if peca is not None
    ]
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
                DefPecaUserPref(
                    user_id=user_id,
                    def_peca_id=peca_id,
                    favorito=False,
                )
            )
            criadas += 1

    session.flush()
    return criadas


def seed_acessorios_cozinhas_roupeiros(
    session: Session,
) -> AcessoriosCozinhasRoupeirosResult:
    """Aplicar toda a configuração e confirmar numa única transação."""
    chaves_criadas, chaves_reutilizadas = criar_chaves(session)
    pecas_criadas, pecas_reutilizadas, pecas_corrigidas = criar_pecas(session)
    prefs_criadas = adicionar_as_bibliotecas(session)
    session.commit()

    return AcessoriosCozinhasRoupeirosResult(
        chaves_criadas=chaves_criadas,
        chaves_reutilizadas=chaves_reutilizadas,
        pecas_criadas=pecas_criadas,
        pecas_reutilizadas=pecas_reutilizadas,
        pecas_corrigidas=pecas_corrigidas,
        prefs_criadas=prefs_criadas,
    )


def print_summary(result: AcessoriosCozinhasRoupeirosResult) -> None:
    print("Resumo final")
    print(f"Chaves criadas: {result.chaves_criadas}")
    print(f"Chaves mantidas (já existiam): {result.chaves_reutilizadas}")
    print(f"Peças criadas: {result.pecas_criadas}")
    print(f"Peças mantidas (já existiam): {result.pecas_reutilizadas}")
    print(f"Ligações de material corrigidas: {result.pecas_corrigidas}")
    print(f"Linhas de biblioteca de utilizador criadas: {result.prefs_criadas}")
    print(
        "As opções/artigos destas chaves podem agora ser acrescentadas "
        "aos modelos ValueSet pelo utilizador."
    )


def main() -> int:
    """Aplicar a configuração na base V3 indicada pelo ambiente."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = seed_acessorios_cozinhas_roupeiros(session)

    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
