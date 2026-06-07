"""Create the default (system) ValueSet keys.

This seed is idempotent: it creates a key only when its code does not exist
yet, and reuses existing keys without modifying them. Nothing is deleted.
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
from app.models import DefValuesetChave  # noqa: E402


@dataclass(frozen=True)
class ChaveSeed:
    """One default ValueSet key."""

    codigo: str
    nome: str
    tipo: str
    grupo: str


@dataclass(frozen=True)
class DefaultValuesetChavesResult:
    """Summary of the ValueSet keys seed."""

    criadas: int
    reutilizadas: int


# Base (system) ValueSet keys. All seeded with sistema=True and ativo=True.
DEFAULT_VALUESET_CHAVES: tuple[ChaveSeed, ...] = (
    # Materiais
    ChaveSeed("MATERIAL_CAIXOTE", "Material caixote", "MATERIAL", "MATERIAIS"),
    ChaveSeed("MATERIAL_LATERAIS", "Material laterais", "MATERIAL", "MATERIAIS"),
    ChaveSeed("MATERIAL_TAMPOS", "Material tampos", "MATERIAL", "MATERIAIS"),
    ChaveSeed("MATERIAL_PORTAS", "Material portas", "MATERIAL", "MATERIAIS"),
    ChaveSeed("MATERIAL_FRENTES", "Material frentes", "MATERIAL", "MATERIAIS"),
    ChaveSeed("MATERIAL_COSTAS", "Material costas", "MATERIAL", "MATERIAIS"),
    ChaveSeed("MATERIAL_FUNDOS", "Material fundos", "MATERIAL", "MATERIAIS"),
    ChaveSeed("MATERIAL_PRATELEIRAS", "Material prateleiras", "MATERIAL", "MATERIAIS"),
    ChaveSeed("MATERIAL_GAVETAS", "Material gavetas", "MATERIAL", "MATERIAIS"),
    ChaveSeed("MATERIAL_OUTROS", "Material outros", "MATERIAL", "MATERIAIS"),
    # Ferragens
    ChaveSeed("FERRAGEM_DOBRADICA", "Dobradiça", "FERRAGEM", "FERRAGENS"),
    ChaveSeed("FERRAGEM_CORREDICA", "Corrediça", "FERRAGEM", "FERRAGENS"),
    ChaveSeed("FERRAGEM_PUXADOR", "Puxador", "FERRAGEM", "FERRAGENS"),
    ChaveSeed("FERRAGEM_VARAO", "Varão", "FERRAGEM", "FERRAGENS"),
    ChaveSeed("FERRAGEM_SUPORTE_VARAO", "Suporte varão", "FERRAGEM", "FERRAGENS"),
    ChaveSeed("FERRAGEM_PE_NIVELADOR", "Pé nivelador", "FERRAGEM", "FERRAGENS"),
    ChaveSeed("FERRAGEM_OUTRA", "Ferragem outra", "FERRAGEM", "FERRAGENS"),
    # Sistemas de correr
    ChaveSeed("SISTEMA_CORRER", "Sistema correr", "SISTEMA_CORRER", "SISTEMAS_CORRER"),
    ChaveSeed("SISTEMA_CORRER_RODIZIO_SUP", "Rodízio superior", "SISTEMA_CORRER", "SISTEMAS_CORRER"),
    ChaveSeed("SISTEMA_CORRER_RODIZIO_INF", "Rodízio inferior", "SISTEMA_CORRER", "SISTEMAS_CORRER"),
    ChaveSeed("SISTEMA_CORRER_CALHA_SUP", "Calha superior", "SISTEMA_CORRER", "SISTEMAS_CORRER"),
    ChaveSeed("SISTEMA_CORRER_CALHA_INF", "Calha inferior", "SISTEMA_CORRER", "SISTEMAS_CORRER"),
    ChaveSeed("SISTEMA_CORRER_PUXADOR_WAVE", "Puxador Wave", "SISTEMA_CORRER", "SISTEMAS_CORRER"),
    ChaveSeed("SISTEMA_CORRER_OUTRO", "Sistema correr outro", "SISTEMA_CORRER", "SISTEMAS_CORRER"),
    # Iluminacao
    ChaveSeed("ILUMINACAO_CALHA_LED", "Calha LED", "ILUMINACAO", "ILUMINACAO"),
    ChaveSeed("ILUMINACAO_FITA_LED", "Fita LED", "ILUMINACAO", "ILUMINACAO"),
    ChaveSeed("ILUMINACAO_TRANSFORMADOR", "Transformador", "ILUMINACAO", "ILUMINACAO"),
    ChaveSeed("ILUMINACAO_SENSOR", "Sensor iluminação", "ILUMINACAO", "ILUMINACAO"),
    ChaveSeed("ILUMINACAO_OUTRO", "Iluminação outro", "ILUMINACAO", "ILUMINACAO"),
    # Orlas
    ChaveSeed("ORLA_FINA", "Orla fina", "ORLA", "ORLAS"),
    ChaveSeed("ORLA_GROSSA", "Orla grossa", "ORLA", "ORLAS"),
    # Acabamentos
    ChaveSeed("ACABAMENTO_FACE_SUP", "Acabamento face superior", "ACABAMENTO", "ACABAMENTOS"),
    ChaveSeed("ACABAMENTO_FACE_INF", "Acabamento face inferior", "ACABAMENTO", "ACABAMENTOS"),
    ChaveSeed("ACABAMENTO_OUTRO", "Acabamento outro", "ACABAMENTO", "ACABAMENTOS"),
    # Acessorios
    ChaveSeed("ACESSORIO_OUTRO", "Acessório outro", "ACESSORIO", "ACESSORIOS"),
)


def ensure_default_valueset_chaves(session: Session) -> DefaultValuesetChavesResult:
    """Create or reuse the default ValueSet keys (idempotent)."""
    criadas = 0
    reutilizadas = 0
    ordem_por_grupo: dict[str, int] = {}

    for seed in DEFAULT_VALUESET_CHAVES:
        ordem = ordem_por_grupo.get(seed.grupo, 0) + 1
        ordem_por_grupo[seed.grupo] = ordem

        existing = session.execute(
            select(DefValuesetChave).where(DefValuesetChave.codigo == seed.codigo)
        ).scalar_one_or_none()

        if existing is not None:
            reutilizadas += 1
            print(f"Chave {seed.codigo} ja existe, mantida")
            continue

        chave = DefValuesetChave(
            codigo=seed.codigo,
            nome=seed.nome,
            descricao=None,
            tipo=seed.tipo,
            grupo=seed.grupo,
            sistema=True,
            ativo=True,
            ordem=ordem,
        )
        session.add(chave)
        session.flush()
        criadas += 1
        print(f"Chave {seed.codigo} criada (grupo {seed.grupo}, ordem {ordem})")

    session.commit()

    return DefaultValuesetChavesResult(criadas=criadas, reutilizadas=reutilizadas)


def print_summary(result: DefaultValuesetChavesResult) -> None:
    """Print the final user-facing summary."""
    print("Resumo final")
    print(f"Chaves criadas: {result.criadas}")
    print(f"Chaves mantidas (ja existiam): {result.reutilizadas}")


def main() -> int:
    """Create or reuse the default ValueSet keys in the configured database."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = ensure_default_valueset_chaves(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
