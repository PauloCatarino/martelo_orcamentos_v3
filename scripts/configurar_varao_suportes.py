"""Montar os associados do conjunto VARAO+SUPORTES.

O conjunto passa a trazer, com as regras de quantidade ja existentes:

* o **varao**, ao comprimento do modulo (COMP = LM), 1 unidade (VARAO_SPP);
* o **suporte central**, que so entra quando o varao passa dos 1100 mm
  (SUPORTE_VARAO_CENTRAL);
* os **suportes laterais/terminais**, 2 por varao (SUPORTE_TERMINAL_VARAO).

As regras leem as medidas da peça de referencia do bloco, que aqui e o proprio
varao (e o unico com medida). As quantidades gravadas nos associados sao so o
valor de arranque: no custeio, o "Atualizar" volta a aplicar as regras.

O seed e idempotente: cria apenas os associados em falta (pelo codigo da peça
componente) e nunca apaga nem altera os que ja existem.
"""

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
from app.domain.associado_types import COMP, GERAL, TOTAL  # noqa: E402
from app.domain.componente_types import PECA  # noqa: E402
from app.domain.regra_quantidade_types import FIXA  # noqa: E402
from app.models import (  # noqa: E402
    DefPeca,
    DefPecaComponente,
    DefRegraQuantidade,
)


CODIGO_CONJUNTO = "VARAO+SUPORTES"


@dataclass(frozen=True)
class AssociadoSeed:
    """Um associado do conjunto: peça componente + regra de quantidade."""

    codigo_peca: str
    descricao: str
    ordem: int
    quantidade: Decimal
    codigo_regra: str
    formula_comp: str | None = None


ASSOCIADOS: tuple[AssociadoSeed, ...] = (
    AssociadoSeed(
        codigo_peca="VARAO",
        descricao="Varao ao comprimento do modulo",
        ordem=1,
        quantidade=Decimal("1.000"),
        codigo_regra="VARAO_SPP",
        formula_comp="LM",
    ),
    AssociadoSeed(
        codigo_peca="SUPORTE_CENTRAL_VARAO",
        descricao="Suporte central (so quando o varao passa dos 1100 mm)",
        ordem=2,
        quantidade=Decimal("1.000"),
        codigo_regra="SUPORTE_VARAO_CENTRAL",
    ),
    AssociadoSeed(
        codigo_peca="SUPORTE_LATERAL_VARAO",
        descricao="Suportes laterais/terminais (2 por varao)",
        ordem=3,
        quantidade=Decimal("2.000"),
        codigo_regra="SUPORTE_TERMINAL_VARAO",
    ),
)


@dataclass(frozen=True)
class VaraoSuportesResult:
    """Resumo da configuracao do conjunto."""

    associados_criados: int
    associados_reutilizados: int


def get_peca(session: Session, codigo: str) -> DefPeca | None:
    """Devolver uma peca do catalogo pelo codigo."""
    return session.execute(
        select(DefPeca).where(DefPeca.codigo == codigo)
    ).scalar_one_or_none()


def get_peca_obrigatoria(session: Session, codigo: str) -> DefPeca:
    """Devolver uma peca do catalogo, com erro claro quando falta."""
    peca = get_peca(session, codigo)
    if peca is None:
        raise ValueError(f"Peca {codigo} nao existe nesta base de dados")
    return peca


def get_regra_id(session: Session, codigo: str) -> int:
    """Devolver o id de uma regra de quantidade, com erro claro quando falta."""
    regra = session.execute(
        select(DefRegraQuantidade).where(DefRegraQuantidade.codigo == codigo)
    ).scalar_one_or_none()
    if regra is None:
        raise ValueError(
            f"Regra de quantidade {codigo} nao existe nesta base de dados"
        )
    return regra.id


def criar_associados(session: Session) -> tuple[int, int]:
    """Criar os associados em falta. Devolve (criados, reutilizados)."""
    conjunto = get_peca_obrigatoria(session, CODIGO_CONJUNTO)

    criados = 0
    reutilizados = 0

    for seed in ASSOCIADOS:
        componente = get_peca_obrigatoria(session, seed.codigo_peca)
        existente = session.execute(
            select(DefPecaComponente).where(
                DefPecaComponente.def_peca_pai_id == conjunto.id,
                DefPecaComponente.def_peca_componente_id == componente.id,
            )
        ).scalar_one_or_none()
        if existente is not None:
            reutilizados += 1
            print(f"Associado {seed.codigo_peca} ja existe, mantido")
            continue

        session.add(
            DefPecaComponente(
                def_peca_pai_id=conjunto.id,
                tipo_componente=PECA,
                def_peca_componente_id=componente.id,
                descricao=seed.descricao,
                ordem=seed.ordem,
                quantidade=seed.quantidade,
                regra_quantidade=FIXA,
                def_regra_quantidade_id=get_regra_id(session, seed.codigo_regra),
                obrigatorio=True,
                ativo=True,
                zona_aplicacao=GERAL,
                dimensao_referencia=COMP,
                numero_topos=0,
                modo_quantidade=TOTAL,
                prioridade_valueset=1,
                formula_comp=seed.formula_comp,
            )
        )
        session.flush()
        criados += 1
        print(
            f"Associado {seed.codigo_peca} criado "
            f"(regra {seed.codigo_regra}, quantidade {seed.quantidade})"
        )

    return criados, reutilizados


def configurar_varao_suportes(session: Session) -> VaraoSuportesResult:
    """Montar os associados do conjunto VARAO+SUPORTES (idempotente)."""
    criados, reutilizados = criar_associados(session)

    session.commit()

    return VaraoSuportesResult(
        associados_criados=criados,
        associados_reutilizados=reutilizados,
    )


def print_summary(result: VaraoSuportesResult) -> None:
    """Escrever o resumo final para o utilizador."""
    print("Resumo final")
    print(f"Associados criados: {result.associados_criados}")
    print(f"Associados mantidos (ja existiam): {result.associados_reutilizados}")
    print(
        "Nota: as quantidades so' se ajustam depois do 'Atualizar' no custeio, "
        "que e' quando as regras correm."
    )


def main() -> int:
    """Configurar o conjunto na base de dados configurada."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = configurar_varao_suportes(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
