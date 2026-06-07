"""Fill default ValueSet keys on existing piece definitions.

This script is idempotent: it sets the default ValueSet key (and finishing
keys) for known piece codes that do not have a material key yet. Existing
values are kept, unless the ``--force`` flag is passed. Missing pieces are
reported and skipped, nothing is deleted or duplicated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domain.valueset_types import (  # noqa: E402
    ACABAMENTO_FACE_INF,
    ACABAMENTO_FACE_SUP,
    MATERIAL_COSTAS,
    MATERIAL_FRENTES,
    MATERIAL_FUNDOS,
    MATERIAL_GAVETAS,
    MATERIAL_LATERAIS,
    MATERIAL_PORTAS,
    MATERIAL_PRATELEIRAS,
    MATERIAL_TAMPOS,
    normalize_valueset_key,
)
from app.models import DefPeca  # noqa: E402


@dataclass(frozen=True)
class DefPecaValuesetSeed:
    """Default ValueSet keys for one piece definition."""

    chave_valueset_material: str
    permite_acabamento: bool = False
    chave_valueset_acabamento_sup: str | None = None
    chave_valueset_acabamento_inf: str | None = None


@dataclass(frozen=True)
class UpdateValuesetKeysResult:
    """Summary of the ValueSet key update."""

    atualizadas: int
    ignoradas_existentes: int
    pecas_nao_encontradas: int


# Pieces with finishing share the same finishing keys.
_COM_ACABAMENTO_SUP = ACABAMENTO_FACE_SUP
_COM_ACABAMENTO_INF = ACABAMENTO_FACE_INF


# Piece code -> default ValueSet keys. Pieces that do not exist are skipped.
DEFAULT_DEF_PECA_VALUESET_KEYS: dict[str, DefPecaValuesetSeed] = {
    "COSTA": DefPecaValuesetSeed(MATERIAL_COSTAS),
    "LATERAL": DefPecaValuesetSeed(MATERIAL_LATERAIS),
    "TAMPO": DefPecaValuesetSeed(MATERIAL_TAMPOS),
    "FUNDO": DefPecaValuesetSeed(MATERIAL_FUNDOS),
    "PORTA": DefPecaValuesetSeed(
        MATERIAL_PORTAS, True, _COM_ACABAMENTO_SUP, _COM_ACABAMENTO_INF
    ),
    "PORTA_SIMPLES": DefPecaValuesetSeed(
        MATERIAL_PORTAS, True, _COM_ACABAMENTO_SUP, _COM_ACABAMENTO_INF
    ),
    "PRATELEIRA": DefPecaValuesetSeed(MATERIAL_PRATELEIRAS),
    "PRATELEIRA_AMOVIVEL": DefPecaValuesetSeed(MATERIAL_PRATELEIRAS),
    "FRENTE_GAVETA": DefPecaValuesetSeed(
        MATERIAL_FRENTES, True, _COM_ACABAMENTO_SUP, _COM_ACABAMENTO_INF
    ),
    "LADO_GAVETA": DefPecaValuesetSeed(MATERIAL_GAVETAS),
    "FUNDO_GAVETA": DefPecaValuesetSeed(MATERIAL_FUNDOS),
    "TRASEIRA_GAVETA": DefPecaValuesetSeed(MATERIAL_GAVETAS),
    "GAVETA": DefPecaValuesetSeed(MATERIAL_GAVETAS),
}


def _normalize_optional_key(chave: str | None) -> str | None:
    """Normalize an optional ValueSet key, keeping None as None."""
    if chave is None:
        return None

    return normalize_valueset_key(chave)


def update_def_peca_valueset_keys(
    session: Session, force: bool = False
) -> UpdateValuesetKeysResult:
    """Set default ValueSet keys for known pieces (idempotent)."""
    atualizadas = 0
    ignoradas_existentes = 0
    pecas_nao_encontradas = 0

    for codigo, seed in DEFAULT_DEF_PECA_VALUESET_KEYS.items():
        peca = session.execute(
            select(DefPeca).where(DefPeca.codigo == codigo)
        ).scalar_one_or_none()

        if peca is None:
            print(f"Peca {codigo} nao encontrada, ignorada")
            pecas_nao_encontradas += 1
            continue

        if peca.chave_valueset_material and not force:
            print(
                f"Peca {codigo} ja tem chave ({peca.chave_valueset_material}), mantida"
            )
            ignoradas_existentes += 1
            continue

        peca.chave_valueset_material = normalize_valueset_key(seed.chave_valueset_material)
        peca.permite_acabamento = seed.permite_acabamento
        peca.chave_valueset_acabamento_sup = _normalize_optional_key(
            seed.chave_valueset_acabamento_sup
        )
        peca.chave_valueset_acabamento_inf = _normalize_optional_key(
            seed.chave_valueset_acabamento_inf
        )
        session.flush()
        atualizadas += 1
        print(f"Peca {codigo} atualizada -> {peca.chave_valueset_material}")

    session.commit()

    return UpdateValuesetKeysResult(
        atualizadas=atualizadas,
        ignoradas_existentes=ignoradas_existentes,
        pecas_nao_encontradas=pecas_nao_encontradas,
    )


def print_summary(result: UpdateValuesetKeysResult) -> None:
    """Print the final user-facing summary."""
    print("Resumo final")
    print(f"Pecas atualizadas: {result.atualizadas}")
    print(f"Pecas mantidas (ja preenchidas): {result.ignoradas_existentes}")
    print(f"Pecas nao encontradas: {result.pecas_nao_encontradas}")


def main(argv: list[str] | None = None) -> int:
    """Update default ValueSet keys in the configured database."""
    args = list(sys.argv[1:] if argv is None else argv)
    force = "--force" in args

    _ = settings.database_url

    with SessionLocal() as session:
        result = update_def_peca_valueset_keys(session, force=force)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
