"""Create sample piece definitions for validating the piece catalog."""

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
from app.domain.componente_types import FERRAGEM, PECA  # noqa: E402
from app.domain.peca_types import COMPOSTA, SIMPLES  # noqa: E402
from app.models import DefPeca, DefPecaComponente  # noqa: E402


REGRA_QUANTIDADE_FIXA = "FIXA"


@dataclass(frozen=True)
class DefPecaSeed:
    """Definition data for one sample piece."""

    codigo: str
    nome: str
    tipo_peca: str = SIMPLES


@dataclass(frozen=True)
class ComponenteSeed:
    """Definition data for one sample composite piece component."""

    tipo_componente: str
    ordem: int
    quantidade: Decimal
    regra_quantidade: str = REGRA_QUANTIDADE_FIXA
    def_peca_codigo: str | None = None
    referencia_componente: str | None = None
    descricao: str | None = None


@dataclass(frozen=True)
class EntityResult:
    """Result for one seeded entity."""

    status: str
    entity: object


@dataclass(frozen=True)
class SampleDefPecasResult:
    """Result of the sample piece definition seed."""

    pecas_criadas: int
    pecas_reutilizadas: int
    componentes_criados: int
    componentes_reutilizados: int


SIMPLE_PECAS: tuple[DefPecaSeed, ...] = (
    DefPecaSeed(codigo="LATERAL", nome="Lateral"),
    DefPecaSeed(codigo="TAMPO", nome="Tampo"),
    DefPecaSeed(codigo="FUNDO", nome="Fundo"),
    DefPecaSeed(codigo="COSTA", nome="Costa"),
    DefPecaSeed(codigo="PORTA", nome="Porta"),
    DefPecaSeed(codigo="PRATELEIRA", nome="Prateleira"),
    DefPecaSeed(codigo="LADO_GAVETA", nome="Lado Gaveta"),
    DefPecaSeed(codigo="TRASEIRA_GAVETA", nome="Traseira Gaveta"),
    DefPecaSeed(codigo="FUNDO_GAVETA", nome="Fundo Gaveta"),
    DefPecaSeed(codigo="FRENTE_GAVETA", nome="Frente Gaveta"),
)

GAVETA_PECA = DefPecaSeed(codigo="GAVETA", nome="Gaveta", tipo_peca=COMPOSTA)

GAVETA_COMPONENTES: tuple[ComponenteSeed, ...] = (
    ComponenteSeed(
        tipo_componente=PECA,
        def_peca_codigo="LADO_GAVETA",
        ordem=1,
        quantidade=Decimal("2"),
    ),
    ComponenteSeed(
        tipo_componente=PECA,
        def_peca_codigo="TRASEIRA_GAVETA",
        ordem=2,
        quantidade=Decimal("1"),
    ),
    ComponenteSeed(
        tipo_componente=PECA,
        def_peca_codigo="FUNDO_GAVETA",
        ordem=3,
        quantidade=Decimal("1"),
    ),
    ComponenteSeed(
        tipo_componente=PECA,
        def_peca_codigo="FRENTE_GAVETA",
        ordem=4,
        quantidade=Decimal("1"),
    ),
    ComponenteSeed(
        tipo_componente=FERRAGEM,
        referencia_componente="CORREDICA",
        descricao="CORREDICA",
        ordem=5,
        quantidade=Decimal("1"),
    ),
    ComponenteSeed(
        tipo_componente=FERRAGEM,
        referencia_componente="PUXADOR",
        descricao="PUXADOR",
        ordem=6,
        quantidade=Decimal("1"),
    ),
)


def get_def_peca_by_codigo(session: Session, codigo: str) -> DefPeca | None:
    """Find one piece definition by code."""
    return session.execute(select(DefPeca).where(DefPeca.codigo == codigo)).scalar_one_or_none()


def get_or_create_def_peca(session: Session, seed: DefPecaSeed) -> EntityResult:
    """Create or reuse one sample piece definition."""
    peca = get_def_peca_by_codigo(session, seed.codigo)

    if peca is not None:
        return EntityResult(status="reutilizada", entity=peca)

    peca = DefPeca(
        codigo=seed.codigo,
        nome=seed.nome,
        tipo_peca=seed.tipo_peca,
        ativo=True,
    )
    session.add(peca)
    session.flush()

    return EntityResult(status="criada", entity=peca)


def get_componente_by_seed(
    session: Session,
    gaveta: DefPeca,
    seed: ComponenteSeed,
    def_peca_componente: DefPeca | None,
) -> DefPecaComponente | None:
    """Find one sample component by its stable identity."""
    statement = select(DefPecaComponente).where(
        DefPecaComponente.def_peca_pai_id == gaveta.id,
        DefPecaComponente.tipo_componente == seed.tipo_componente,
    )

    if seed.tipo_componente == PECA:
        statement = statement.where(
            DefPecaComponente.def_peca_componente_id == def_peca_componente.id
        )
    else:
        statement = statement.where(
            DefPecaComponente.referencia_componente == seed.referencia_componente
        )

    return session.execute(statement).scalar_one_or_none()


def get_or_create_gaveta_componente(
    session: Session,
    gaveta: DefPeca,
    seed: ComponenteSeed,
) -> EntityResult:
    """Create or reuse one component of the sample GAVETA composite piece."""
    def_peca_componente = None
    if seed.def_peca_codigo is not None:
        def_peca_componente = get_def_peca_by_codigo(session, seed.def_peca_codigo)
        if def_peca_componente is None:
            raise ValueError(f"DefPeca {seed.def_peca_codigo} nao encontrada")

    componente = get_componente_by_seed(session, gaveta, seed, def_peca_componente)
    if componente is not None:
        return EntityResult(status="reutilizado", entity=componente)

    componente = DefPecaComponente(
        def_peca_pai_id=gaveta.id,
        tipo_componente=seed.tipo_componente,
        def_peca_componente_id=def_peca_componente.id if def_peca_componente is not None else None,
        referencia_componente=seed.referencia_componente,
        descricao=seed.descricao,
        ordem=seed.ordem,
        quantidade=seed.quantidade,
        regra_quantidade=seed.regra_quantidade,
        obrigatorio=True,
        ativo=True,
    )
    session.add(componente)
    session.flush()

    return EntityResult(status="criado", entity=componente)


def ensure_sample_def_pecas(session: Session) -> SampleDefPecasResult:
    """Create or reuse sample piece definitions and GAVETA components."""
    pecas_criadas = 0
    pecas_reutilizadas = 0
    componentes_criados = 0
    componentes_reutilizados = 0

    for seed in SIMPLE_PECAS:
        result = get_or_create_def_peca(session, seed)
        print(f"Pe\u00e7a {seed.codigo} {result.status}")
        if result.status == "criada":
            pecas_criadas += 1
        else:
            pecas_reutilizadas += 1

    gaveta_result = get_or_create_def_peca(session, GAVETA_PECA)
    print(f"Pe\u00e7a {GAVETA_PECA.codigo} {gaveta_result.status}")
    if gaveta_result.status == "criada":
        pecas_criadas += 1
    else:
        pecas_reutilizadas += 1

    gaveta = gaveta_result.entity
    for seed in GAVETA_COMPONENTES:
        result = get_or_create_gaveta_componente(session, gaveta, seed)
        label = seed.def_peca_codigo or seed.referencia_componente or seed.tipo_componente
        print(f"Componente GAVETA -> {label} {result.status}")
        if result.status == "criado":
            componentes_criados += 1
        else:
            componentes_reutilizados += 1

    session.commit()

    return SampleDefPecasResult(
        pecas_criadas=pecas_criadas,
        pecas_reutilizadas=pecas_reutilizadas,
        componentes_criados=componentes_criados,
        componentes_reutilizados=componentes_reutilizados,
    )


def print_summary(result: SampleDefPecasResult) -> None:
    """Print the final user-facing seed summary."""
    print("Resumo final")
    print(f"Pe\u00e7as criadas: {result.pecas_criadas}")
    print(f"Pe\u00e7as reutilizadas: {result.pecas_reutilizadas}")
    print(f"Componentes criados: {result.componentes_criados}")
    print(f"Componentes reutilizados: {result.componentes_reutilizados}")


def main() -> int:
    """Create or reuse sample piece definitions in the configured database."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = ensure_sample_def_pecas(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
