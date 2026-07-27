"""Separar o material das prateleiras fixas e das prateleiras amoviveis.

Ate agora os dois grupos partilhavam a chave ``MATERIAL_PRATELEIRAS``. Este
seed cria duas chaves proprias:

* ``MATERIAL_PRATELEIRAS_FIXAS``
* ``MATERIAL_PRATELEIRAS_AMOVIVEIS``

e, para nada deixar de custear, copia a linha ``MATERIAL_PRATELEIRAS`` para as
chaves novas em todo o lado onde ela ja existe: modelos ValueSet, ValueSets de
orçamentos e ValueSets de itens. No fim, aponta as peças de cada grupo para a
sua chave.

Nada e apagado: a chave antiga e as suas linhas ficam na base como estavam.
O seed e idempotente.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    DefPeca,
    DefValuesetChave,
    DefValuesetModeloLinha,
    OrcamentoItemValuesetLinha,
    OrcamentoValuesetLinha,
)


CHAVE_ORIGEM = "MATERIAL_PRATELEIRAS"

GRUPO_PRATELEIRAS_FIXAS = "PRATELEIRAS FIXAS"
GRUPO_PRATELEIRAS_AMOVIVEIS = "PRATELEIRAS AMOVIVEIS"


@dataclass(frozen=True)
class ChaveSeed:
    """Uma chave de material nova e o grupo de peças que a passa a usar."""

    codigo: str
    nome: str
    descricao: str
    grupo_pecas: str


CHAVES: tuple[ChaveSeed, ...] = (
    ChaveSeed(
        codigo="MATERIAL_PRATELEIRAS_FIXAS",
        nome="Material prateleiras fixas",
        descricao="Material das prateleiras fixas (coladas/aparafusadas ao movel).",
        grupo_pecas=GRUPO_PRATELEIRAS_FIXAS,
    ),
    ChaveSeed(
        codigo="MATERIAL_PRATELEIRAS_AMOVIVEIS",
        nome="Material prateleiras amoviveis",
        descricao="Material das prateleiras amoviveis (assentes em suportes).",
        grupo_pecas=GRUPO_PRATELEIRAS_AMOVIVEIS,
    ),
)

# Tabelas de linhas ValueSet onde a chave antiga pode existir, e a coluna que
# identifica o "dono" de cada conjunto de linhas.
TABELAS_LINHAS = (
    (DefValuesetModeloLinha, "def_valueset_modelo_id"),
    (OrcamentoValuesetLinha, "orcamento_versao_id"),
    (OrcamentoItemValuesetLinha, "orcamento_item_id"),
)


@dataclass(frozen=True)
class ChavesMaterialResult:
    """Resumo do seed das chaves de material das prateleiras."""

    chaves_criadas: int
    linhas_copiadas: dict[str, int]
    pecas_atualizadas: int


def ensure_chave(session: Session, seed: ChaveSeed) -> bool:
    """Criar a chave quando falta. Devolve True se a criou."""
    existente = session.execute(
        select(DefValuesetChave).where(DefValuesetChave.codigo == seed.codigo)
    ).scalar_one_or_none()
    if existente is not None:
        print(f"Chave {seed.codigo} ja existe, mantida")
        return False

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
    print(f"Chave {seed.codigo} criada")
    return True


def copiar_linha(linha, nova_chave: str):
    """Devolver uma copia de uma linha ValueSet com outra chave."""
    mapper = inspect(type(linha))
    valores = {
        coluna.key: getattr(linha, coluna.key)
        for coluna in mapper.column_attrs
        if coluna.key not in ("id", "created_at", "updated_at")
    }
    valores["chave"] = nova_chave
    return type(linha)(**valores)


def copiar_linhas_da_chave(session: Session, nova_chave: str) -> dict[str, int]:
    """Copiar as linhas da chave antiga para a chave nova em todas as tabelas."""
    copiadas: dict[str, int] = {}

    for modelo, coluna_dono in TABELAS_LINHAS:
        coluna = getattr(modelo, coluna_dono)
        origem = session.execute(
            select(modelo).where(modelo.chave == CHAVE_ORIGEM)
        ).scalars().all()

        donos_com_nova_chave = set(
            session.execute(
                select(coluna).where(modelo.chave == nova_chave)
            ).scalars().all()
        )

        criadas = 0
        for linha in origem:
            dono = getattr(linha, coluna_dono)
            if dono in donos_com_nova_chave:
                continue

            session.add(copiar_linha(linha, nova_chave))
            donos_com_nova_chave.add(dono)
            criadas += 1

        session.flush()
        copiadas[modelo.__tablename__] = criadas
        print(f"{modelo.__tablename__}: {criadas} linha(s) {nova_chave} criada(s)")

    return copiadas


def apontar_pecas_para_chave(session: Session, seed: ChaveSeed) -> int:
    """Passar as peças do grupo a usar a chave nova. Devolve quantas mudaram."""
    pecas = session.execute(
        select(DefPeca).where(
            DefPeca.grupo == seed.grupo_pecas,
            DefPeca.sem_material.is_(False),
        )
    ).scalars().all()

    atualizadas = 0
    for peca in pecas:
        if peca.chave_valueset_material == seed.codigo:
            continue

        anterior = peca.chave_valueset_material or "(sem chave)"
        peca.chave_valueset_material = seed.codigo
        atualizadas += 1
        print(f"Peca {peca.codigo}: {anterior} -> {seed.codigo}")

    session.flush()
    return atualizadas


def seed_chaves_material_prateleiras(session: Session) -> ChavesMaterialResult:
    """Criar as chaves, copiar as linhas e apontar as peças (idempotente)."""
    chaves_criadas = 0
    linhas_copiadas: dict[str, int] = {}
    pecas_atualizadas = 0

    for seed in CHAVES:
        if ensure_chave(session, seed):
            chaves_criadas += 1

        for tabela, criadas in copiar_linhas_da_chave(session, seed.codigo).items():
            linhas_copiadas[tabela] = linhas_copiadas.get(tabela, 0) + criadas

        pecas_atualizadas += apontar_pecas_para_chave(session, seed)

    session.commit()

    return ChavesMaterialResult(
        chaves_criadas=chaves_criadas,
        linhas_copiadas=linhas_copiadas,
        pecas_atualizadas=pecas_atualizadas,
    )


def print_summary(result: ChavesMaterialResult) -> None:
    """Escrever o resumo final para o utilizador."""
    print("Resumo final")
    print(f"Chaves criadas: {result.chaves_criadas}")
    for tabela, criadas in sorted(result.linhas_copiadas.items()):
        print(f"Linhas copiadas em {tabela}: {criadas}")
    print(f"Pecas apontadas para as chaves novas: {result.pecas_atualizadas}")


def main() -> int:
    """Criar as chaves de material das prateleiras na base configurada."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = seed_chaves_material_prateleiras(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
