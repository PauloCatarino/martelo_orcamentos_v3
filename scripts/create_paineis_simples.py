"""Create the "Paineis Simples" catalog pieces (cut + edging only).

Seeds the generic panels used by simpler costings: physical pieces with no
associated operations and no components, so their cost is material + automatic
cut and edging derived from the orla code.

This seed is idempotent: it creates the ValueSet key, the default model line
and each panel only when missing, and reuses existing records without
modifying them. Nothing is deleted.
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
from app.domain.peca_natureza_types import MATERIAL, NEUTRA  # noqa: E402
from app.domain.peca_types import SIMPLES  # noqa: E402
from app.models import (  # noqa: E402
    DefPeca,
    DefValuesetChave,
    DefValuesetModelo,
    DefValuesetModeloLinha,
)


CHAVE_MATERIAL_PECAS_SIMPLIFICADAS = "MATERIAL_PECAS_SIMPLIFICADAS"
NOME_CHAVE_MATERIAL_PECAS_SIMPLIFICADAS = "Material Peças Simplificadas"
GRUPO_PAINEIS_SIMPLES = "PAINEIS SIMPLES"

MODELO_DEFAULT_CODIGO = "ROUPEIRO_STANDARD"
LINHA_MODELO_DEFAULT = ("AGL_19_STANDARD", "Aglomerado 19mm standard")
LINHA_MODELO_DEFAULT_ORDEM = 9


@dataclass(frozen=True)
class PainelSeed:
    """Definition data for one simple panel (orla code C1-C2-L1-L2)."""

    codigo: str
    nome: str
    codigo_orlas: str


PAINEIS_SIMPLES: tuple[PainelSeed, ...] = (
    PainelSeed("PAINEL_0000", "Painel[0000]", "0000"),
    PainelSeed("PAINEL_2200", "Painel[2200]", "2200"),
    PainelSeed("PAINEL_2000", "Painel[2000]", "2000"),
    PainelSeed("PAINEL_2020", "Painel[2020]", "2020"),
    PainelSeed("PAINEL_2220", "Painel[2220]", "2220"),
    PainelSeed("PAINEL_2022", "Painel[2022]", "2022"),
    PainelSeed("PAINEL_2222", "Painel[2222]", "2222"),
)


@dataclass(frozen=True)
class PaineisSimplesResult:
    """Summary of the simple panels seed."""

    chave_criada: bool
    linha_modelo_criada: bool
    modelo_default_em_falta: bool
    paineis_criados: int
    paineis_reutilizados: int


def ensure_chave_material(session: Session) -> bool:
    """Create the panels material ValueSet key when missing. True if created."""
    existing = session.execute(
        select(DefValuesetChave).where(
            DefValuesetChave.codigo == CHAVE_MATERIAL_PECAS_SIMPLIFICADAS
        )
    ).scalar_one_or_none()
    if existing is not None:
        print(f"Chave {CHAVE_MATERIAL_PECAS_SIMPLIFICADAS} ja existe, mantida")
        return False

    ordem_maxima = session.execute(
        select(func.max(DefValuesetChave.ordem)).where(
            DefValuesetChave.grupo == "MATERIAIS"
        )
    ).scalar_one()
    chave = DefValuesetChave(
        codigo=CHAVE_MATERIAL_PECAS_SIMPLIFICADAS,
        nome=NOME_CHAVE_MATERIAL_PECAS_SIMPLIFICADAS,
        descricao="Material dos painéis simples (corte + orlagem).",
        tipo="MATERIAL",
        grupo="MATERIAIS",
        sistema=True,
        ativo=True,
        ordem=(ordem_maxima or 0) + 1,
    )
    session.add(chave)
    session.flush()
    print(f"Chave {CHAVE_MATERIAL_PECAS_SIMPLIFICADAS} criada")
    return True


def ensure_linha_modelo_default(session: Session) -> tuple[bool, bool]:
    """Add the panels material line to the default model when it exists.

    Returns ``(linha_criada, modelo_em_falta)``.
    """
    modelo = session.execute(
        select(DefValuesetModelo).where(
            DefValuesetModelo.codigo == MODELO_DEFAULT_CODIGO
        )
    ).scalar_one_or_none()
    if modelo is None:
        print(
            f"Modelo {MODELO_DEFAULT_CODIGO} nao existe nesta base; linha de "
            "material dos paineis nao foi criada."
        )
        return False, True

    codigo_opcao, nome_opcao = LINHA_MODELO_DEFAULT
    existing = session.execute(
        select(DefValuesetModeloLinha).where(
            DefValuesetModeloLinha.def_valueset_modelo_id == modelo.id,
            DefValuesetModeloLinha.chave == CHAVE_MATERIAL_PECAS_SIMPLIFICADAS,
        )
    ).scalar_one_or_none()
    if existing is not None:
        print(
            f"Linha {MODELO_DEFAULT_CODIGO} {CHAVE_MATERIAL_PECAS_SIMPLIFICADAS} "
            "ja existe, mantida"
        )
        return False, False

    linha = DefValuesetModeloLinha(
        def_valueset_modelo_id=modelo.id,
        chave=CHAVE_MATERIAL_PECAS_SIMPLIFICADAS,
        codigo_opcao=codigo_opcao,
        nome_opcao=nome_opcao,
        padrao=True,
        ordem=LINHA_MODELO_DEFAULT_ORDEM,
        materia_prima_id=None,
        ref_materia_prima=None,
        descricao_materia_prima=None,
        valor_texto=nome_opcao,
        ativo=True,
    )
    session.add(linha)
    session.flush()
    print(
        f"Linha {MODELO_DEFAULT_CODIGO} {CHAVE_MATERIAL_PECAS_SIMPLIFICADAS}/"
        f"{codigo_opcao} criada"
    )
    return True, False


def ensure_paineis_simples(session: Session) -> tuple[int, int]:
    """Create the simple panels when missing. Returns (criados, reutilizados)."""
    criados = 0
    reutilizados = 0

    for seed in PAINEIS_SIMPLES:
        existing = session.execute(
            select(DefPeca).where(DefPeca.codigo == seed.codigo)
        ).scalar_one_or_none()
        if existing is not None:
            reutilizados += 1
            print(f"Painel {seed.codigo} ja existe, mantido")
            continue

        orla_c1, orla_c2, orla_l1, orla_l2 = (
            normalize_orla_type(digito) for digito in seed.codigo_orlas
        )
        painel = DefPeca(
            codigo=seed.codigo,
            nome=seed.nome,
            descricao="Painel simples: material + corte + orlagem.",
            grupo=GRUPO_PAINEIS_SIMPLES,
            tipo_peca=SIMPLES,
            natureza=MATERIAL,
            orientacao=NEUTRA,
            funcao=None,
            orla_c1=orla_c1,
            orla_c2=orla_c2,
            orla_l1=orla_l1,
            orla_l2=orla_l2,
            chave_valueset_material=CHAVE_MATERIAL_PECAS_SIMPLIFICADAS,
            permite_acabamento=False,
            sem_material=False,
            ativo=True,
        )
        session.add(painel)
        session.flush()
        criados += 1
        print(f"Painel {seed.codigo} criado (grupo {GRUPO_PAINEIS_SIMPLES})")

    return criados, reutilizados


def seed_paineis_simples(session: Session) -> PaineisSimplesResult:
    """Create or reuse the key, default model line and panels (idempotent)."""
    chave_criada = ensure_chave_material(session)
    linha_criada, modelo_em_falta = ensure_linha_modelo_default(session)
    criados, reutilizados = ensure_paineis_simples(session)

    session.commit()

    return PaineisSimplesResult(
        chave_criada=chave_criada,
        linha_modelo_criada=linha_criada,
        modelo_default_em_falta=modelo_em_falta,
        paineis_criados=criados,
        paineis_reutilizados=reutilizados,
    )


def print_summary(result: PaineisSimplesResult) -> None:
    """Print the final user-facing summary."""
    print("Resumo final")
    print(f"Chave criada: {'sim' if result.chave_criada else 'nao (ja existia)'}")
    if result.modelo_default_em_falta:
        print("Linha no modelo default: modelo nao existe nesta base")
    else:
        print(
            "Linha no modelo default: "
            f"{'criada' if result.linha_modelo_criada else 'ja existia'}"
        )
    print(f"Paineis criados: {result.paineis_criados}")
    print(f"Paineis mantidos (ja existiam): {result.paineis_reutilizados}")
    print(
        "Nota: nos modelos ValueSet em uso real, adicione uma linha com a chave "
        f"{CHAVE_MATERIAL_PECAS_SIMPLIFICADAS} e o material pretendido para os "
        "paineis custearem."
    )


def main() -> int:
    """Create or reuse the simple panels in the configured database."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = seed_paineis_simples(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
