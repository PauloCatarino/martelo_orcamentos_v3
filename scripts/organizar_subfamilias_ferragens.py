"""Arrumar as ferragens em sub-familias dentro do grupo FERRAGENS.

Segue a arrumacao que o catalogo ja tinha no V2. Alem de preencher a
sub-familia de cada ferragem, traz para dentro de FERRAGENS os grupos
ILUMINACAO e SISTEMAS_CORRER, que no V2 sao sub-familias e nao grupos de topo.

Nada e apagado nem renomeado: so' mudam o grupo e a sub-familia das peças
listadas aqui. O seed e idempotente e nunca escreve por cima de uma
sub-familia que ja esteja preenchida (o que o utilizador arrumar a mao fica
como esta).
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
from app.domain.peca_subgrupo_types import GRUPO_FERRAGENS  # noqa: E402
from app.models import DefPeca  # noqa: E402


# Ferragens que ja estao no grupo FERRAGENS: codigo -> sub-familia.
SUBFAMILIA_POR_CODIGO: dict[str, str] = {
    "DOBRADICA": "DOBRADICAS",
    "CORREDICA": "CORREDICAS GAVETAS",
    "PUXADOR": "PUXADORES",
    "PES": "PES",
    "NIVELADORES/PENDURAIS": "PES",
    "SUPORTE_PRATELEIRA": "SUPORTES PRATELEIRA",
    "SUPORTE_PRATELEIRA_PAREDE": "SUPORTES PRATELEIRA",
    "AVENTOS": "SISTEMAS ELEVATORIOS",
    "SISTEMA_ELEVACAO": "SISTEMAS ELEVATORIOS",
    "SISTEMAS_UNIAO": "UNIOES CANTO SPP",
    "VARAO": "ROUPEIROS",
    "VARAO+SUPORTES": "ROUPEIROS",
    "SUPORTE_VARAO": "ROUPEIROS",
    "SUPORTE_CENTRAL_VARAO": "ROUPEIROS",
    "SUPORTE_LATERAL_VARAO": "ROUPEIROS",
}

# Grupos de topo que passam a sub-familias dentro de FERRAGENS.
GRUPOS_QUE_VIRAM_SUBFAMILIA: dict[str, str] = {
    "ILUMINACAO": "ILUMINACAO",
    "SISTEMAS_CORRER": "SISTEMAS CORRER",
}


@dataclass(frozen=True)
class SubfamiliasResult:
    """Resumo da arrumacao das ferragens."""

    ferragens_arrumadas: int
    pecas_movidas_de_grupo: int
    ja_arrumadas: int
    codigos_em_falta: tuple[str, ...]


def arrumar_ferragens(session: Session) -> tuple[int, int, tuple[str, ...]]:
    """Preencher a sub-familia das ferragens. Devolve (arrumadas, ja_arrumadas, em_falta)."""
    arrumadas = 0
    ja_arrumadas = 0
    em_falta: list[str] = []

    for codigo, subfamilia in SUBFAMILIA_POR_CODIGO.items():
        peca = session.execute(
            select(DefPeca).where(DefPeca.codigo == codigo)
        ).scalar_one_or_none()
        if peca is None:
            em_falta.append(codigo)
            continue
        if peca.subgrupo:
            ja_arrumadas += 1
            print(f"Peca {codigo} ja tem sub-familia {peca.subgrupo}, mantida")
            continue

        peca.subgrupo = subfamilia
        session.flush()
        arrumadas += 1
        print(f"Peca {codigo} arrumada em {GRUPO_FERRAGENS} > {subfamilia}")

    return arrumadas, ja_arrumadas, tuple(em_falta)


def mover_grupos_para_ferragens(session: Session) -> tuple[int, int]:
    """Trazer ILUMINACAO e SISTEMAS_CORRER para dentro das ferragens.

    Devolve ``(movidas, ja_arrumadas)``.
    """
    movidas = 0
    ja_arrumadas = 0

    for grupo, subfamilia in GRUPOS_QUE_VIRAM_SUBFAMILIA.items():
        pecas = session.execute(
            select(DefPeca).where(DefPeca.grupo == grupo)
        ).scalars().all()
        for peca in pecas:
            if peca.subgrupo:
                ja_arrumadas += 1
                continue

            peca.grupo = GRUPO_FERRAGENS
            peca.subgrupo = subfamilia
            movidas += 1
            print(
                f"Peca {peca.codigo} movida de {grupo} para "
                f"{GRUPO_FERRAGENS} > {subfamilia}"
            )
        session.flush()

    return movidas, ja_arrumadas


def organizar_subfamilias(session: Session) -> SubfamiliasResult:
    """Arrumar as ferragens em sub-familias (idempotente)."""
    arrumadas, ja_arrumadas, em_falta = arrumar_ferragens(session)
    movidas, ja_movidas = mover_grupos_para_ferragens(session)

    session.commit()

    return SubfamiliasResult(
        ferragens_arrumadas=arrumadas,
        pecas_movidas_de_grupo=movidas,
        ja_arrumadas=ja_arrumadas + ja_movidas,
        codigos_em_falta=em_falta,
    )


def print_summary(result: SubfamiliasResult) -> None:
    """Escrever o resumo final para o utilizador."""
    print("Resumo final")
    print(f"Ferragens arrumadas em sub-familias: {result.ferragens_arrumadas}")
    print(f"Pecas trazidas para o grupo FERRAGENS: {result.pecas_movidas_de_grupo}")
    print(f"Pecas que ja estavam arrumadas: {result.ja_arrumadas}")
    if result.codigos_em_falta:
        print(
            "Codigos que nao existem nesta base (ignorados): "
            + ", ".join(result.codigos_em_falta)
        )


def main() -> int:
    """Arrumar as ferragens na base de dados configurada."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = organizar_subfamilias(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
