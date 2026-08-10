"""Criar a chave ValueSet FERRAGEM_TULHA e a definição de peça TULHA.

Seed idempotente: cria apenas o que falta e nunca apaga registos. Se a peça
TULHA já existir, apenas corrige a sua chave de material para FERRAGEM_TULHA,
que é a ligação explicitamente definida por este seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import func, select, text
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


CHAVE_TULHA = "FERRAGEM_TULHA"
PECA_TULHA = "TULHA"
SUBFAMILIA_COZINHAS = "COZINHAS"


@dataclass(frozen=True)
class TulhaSeedResult:
    chave_criada: bool
    peca_criada: bool
    peca_reutilizada: bool
    chave_peca_corrigida: bool
    prefs_criadas: int


def _obter_peca(session: Session) -> DefPeca | None:
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == PECA_TULHA)
    ).scalar_one_or_none()


def _garantir_chave(session: Session) -> bool:
    existente = session.execute(
        select(DefValuesetChave).where(DefValuesetChave.codigo == CHAVE_TULHA)
    ).scalar_one_or_none()
    if existente is not None:
        return False

    ordem_maxima = session.execute(
        select(func.max(DefValuesetChave.ordem)).where(
            DefValuesetChave.grupo == GRUPO_FERRAGENS
        )
    ).scalar_one()
    session.add(
        DefValuesetChave(
            codigo=CHAVE_TULHA,
            nome="Tulha",
            descricao="Tulhas e cestos extraíveis para módulos de cozinha.",
            tipo="FERRAGEM",
            grupo=GRUPO_FERRAGENS,
            sistema=True,
            ativo=True,
            ordem=(ordem_maxima or 0) + 1,
        )
    )
    session.flush()
    return True


def _garantir_peca(session: Session) -> tuple[bool, bool, bool]:
    existente = _obter_peca(session)
    if existente is not None:
        corrigida = existente.chave_valueset_material != CHAVE_TULHA
        if corrigida:
            existente.chave_valueset_material = CHAVE_TULHA
            session.flush()
        return False, True, corrigida

    session.add(
        DefPeca(
            codigo=PECA_TULHA,
            nome="Tulha Gaveta",
            nome_biblioteca="Tulha Gaveta",
            descricao=(
                "Tulha de abertura tipo gaveta para módulo de cozinha, "
                "com corrediça."
            ),
            grupo=GRUPO_FERRAGENS,
            subgrupo=SUBFAMILIA_COZINHAS,
            tipo_peca=SIMPLES,
            natureza=NATUREZA_FERRAGEM,
            orientacao=NEUTRA,
            funcao=FUNCAO_FERRAGEM,
            usa_orlas=False,
            chave_valueset_material=CHAVE_TULHA,
            permite_acabamento=False,
            sem_material=False,
            ativo=True,
        )
    )
    session.flush()
    return True, False, False


def _adicionar_a_bibliotecas_personalizadas(session: Session) -> int:
    peca = _obter_peca(session)
    if peca is None:
        raise ValueError("A peça TULHA não foi criada.")

    users = session.execute(
        select(DefPecaUserPref.user_id).distinct()
    ).scalars().all()
    criadas = 0
    for user_id in users:
        existente = session.execute(
            select(DefPecaUserPref).where(
                DefPecaUserPref.user_id == user_id,
                DefPecaUserPref.def_peca_id == peca.id,
            )
        ).scalar_one_or_none()
        if existente is not None:
            continue
        session.add(
            DefPecaUserPref(
                user_id=user_id,
                def_peca_id=peca.id,
                favorito=False,
            )
        )
        criadas += 1
    session.flush()
    return criadas


def seed_tulha(session: Session) -> TulhaSeedResult:
    """Aplicar chave, peça e preferências numa única transação."""
    chave_criada = _garantir_chave(session)
    peca_criada, peca_reutilizada, corrigida = _garantir_peca(session)
    prefs_criadas = _adicionar_a_bibliotecas_personalizadas(session)
    session.commit()
    return TulhaSeedResult(
        chave_criada=chave_criada,
        peca_criada=peca_criada,
        peca_reutilizada=peca_reutilizada,
        chave_peca_corrigida=corrigida,
        prefs_criadas=prefs_criadas,
    )


def main() -> int:
    """Aplicar apenas na base de desenvolvimento configurada."""
    _ = settings.database_url
    with SessionLocal() as session:
        database_name = session.scalar(text("SELECT DATABASE()"))
        if database_name != "martelo_v3_dev":
            raise RuntimeError(
                "Seed TULHA recusado: a base configurada não é martelo_v3_dev."
            )
        result = seed_tulha(session)

    print("Resumo TULHA")
    print(f"Chave criada: {'sim' if result.chave_criada else 'não (já existia)'}")
    print(f"Peça criada: {'sim' if result.peca_criada else 'não (já existia)'}")
    print(f"Chave da peça corrigida: {'sim' if result.chave_peca_corrigida else 'não'}")
    print(f"Preferências de biblioteca criadas: {result.prefs_criadas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
