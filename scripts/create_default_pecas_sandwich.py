"""Seed the reusable sandwich-panel definitions.

The parent panels are virtual composite pieces.  Their physical components
inherit COMP/LARG from the parent: every ``FACE_SANDWICH`` costs its HPL
material plus the ``REVESTIMENTO_SANDWICH`` operation, while the core is an
independent AGL material piece.  The two-face panel therefore produces two
coating costs, one per face, exactly as the costing expansion expects.

The seed is deliberately additive and idempotent: existing keys, model lines,
pieces, components and operation links are kept untouched.  It is safe to run
again after the CNC migration and after the default operation seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.domain.componente_types import PECA  # noqa: E402
from app.domain.metodo_calculo_types import REVESTIMENTO  # noqa: E402
from app.domain.peca_natureza_types import CONJUNTO, MATERIAL, NEUTRA  # noqa: E402
from app.domain.peca_types import COMPOSTA, SIMPLES  # noqa: E402
from app.domain.regra_operacao_types import POR_AREA_FACE  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    DefOperacao,
    DefPeca,
    DefPecaComponente,
    DefPecaOperacao,
    DefValuesetChave,
    DefValuesetModelo,
    DefValuesetModeloLinha,
)


GRUPO_PAINEIS_SANDWICH = "PAINEIS SANDWICH"
MODELO_DEFAULT_CODIGO = "ROUPEIRO_STANDARD"
OPERACAO_REVESTIMENTO_CODIGO = "REVESTIMENTO_SANDWICH"

CHAVE_MATERIAL_FACE = "MATERIAL_FACE_SANDWICH"
CHAVE_MATERIAL_NUCLEO = "MATERIAL_NUCLEO_SANDWICH"

_LINHAS_MATERIAL = (
    (CHAVE_MATERIAL_FACE, "Material face sandwich (HPL)", "HPL_08_STANDARD", "HPL 0,8mm standard", 40),
    (CHAVE_MATERIAL_NUCLEO, "Material núcleo sandwich", "AGL_NUCLEO_STANDARD", "Aglomerado núcleo sandwich", 41),
)


@dataclass(frozen=True)
class PecaSandwichSeed:
    codigo: str
    nome: str
    tipo_peca: str
    natureza: str
    sem_material: bool
    chave_valueset_material: str | None = None


@dataclass(frozen=True)
class ComponenteSandwichSeed:
    pai_codigo: str
    filho_codigo: str
    ordem: int
    descricao: str
    formula_comp: str
    formula_larg: str
    formula_esp: str


@dataclass(frozen=True)
class PecasSandwichResult:
    chaves_criadas: int
    chaves_reutilizadas: int
    linhas_modelo_criadas: int
    linhas_modelo_reutilizadas: int
    modelo_default_em_falta: bool
    pecas_criadas: int
    pecas_reutilizadas: int
    componentes_criados: int
    componentes_reutilizados: int
    operacao_revestimento_criada: bool
    operacao_revestimento_reutilizada: bool
    operacao_revestimento_em_falta: bool


PECAS_SANDWICH: tuple[PecaSandwichSeed, ...] = (
    PecaSandwichSeed(
        "FACE_SANDWICH",
        "Face sandwich HPL 0,8mm",
        SIMPLES,
        MATERIAL,
        False,
        CHAVE_MATERIAL_FACE,
    ),
    PecaSandwichSeed(
        "NUCLEO_SANDWICH",
        "Núcleo sandwich",
        SIMPLES,
        MATERIAL,
        False,
        CHAVE_MATERIAL_NUCLEO,
    ),
    PecaSandwichSeed(
        "PAINEL_SANDWICH_1F",
        "Painel sandwich — 1 face",
        COMPOSTA,
        CONJUNTO,
        True,
    ),
    PecaSandwichSeed(
        "PAINEL_SANDWICH_2F",
        "Painel sandwich — 2 faces",
        COMPOSTA,
        CONJUNTO,
        True,
    ),
)


COMPONENTES_SANDWICH: tuple[ComponenteSandwichSeed, ...] = (
    ComponenteSandwichSeed(
        "PAINEL_SANDWICH_1F", "FACE_SANDWICH", 1, "Face revestida", "PAI_COMP", "PAI_LARG", "0.8"
    ),
    ComponenteSandwichSeed(
        "PAINEL_SANDWICH_1F", "NUCLEO_SANDWICH", 2, "Núcleo", "PAI_COMP", "PAI_LARG", "PAI_ESP-0.8"
    ),
    ComponenteSandwichSeed(
        "PAINEL_SANDWICH_2F", "FACE_SANDWICH", 1, "Face superior revestida", "PAI_COMP", "PAI_LARG", "0.8"
    ),
    ComponenteSandwichSeed(
        "PAINEL_SANDWICH_2F", "NUCLEO_SANDWICH", 2, "Núcleo", "PAI_COMP", "PAI_LARG", "PAI_ESP-1.6"
    ),
    ComponenteSandwichSeed(
        "PAINEL_SANDWICH_2F", "FACE_SANDWICH", 3, "Face inferior revestida", "PAI_COMP", "PAI_LARG", "0.8"
    ),
)


def _peca_por_codigo(session: Session, codigo: str) -> DefPeca | None:
    return session.execute(select(DefPeca).where(DefPeca.codigo == codigo)).scalar_one_or_none()


def _criar_chaves(session: Session) -> tuple[int, int]:
    criadas = reutilizadas = 0
    for codigo, nome, _opcao, _nome_opcao, _ordem in _LINHAS_MATERIAL:
        existing = session.execute(
            select(DefValuesetChave).where(DefValuesetChave.codigo == codigo)
        ).scalar_one_or_none()
        if existing is not None:
            reutilizadas += 1
            print(f"Chave {codigo} ja existe, mantida")
            continue
        ordem_maxima = session.execute(
            select(func.max(DefValuesetChave.ordem)).where(DefValuesetChave.grupo == "MATERIAIS")
        ).scalar_one()
        session.add(
            DefValuesetChave(
                codigo=codigo,
                nome=nome,
                descricao=f"Material da definição {GRUPO_PAINEIS_SANDWICH.lower()}.",
                tipo="MATERIAL",
                grupo="MATERIAIS",
                sistema=True,
                ativo=True,
                ordem=(ordem_maxima or 0) + 1,
            )
        )
        session.flush()
        criadas += 1
        print(f"Chave {codigo} criada")
    return criadas, reutilizadas


def _criar_linhas_modelo(session: Session) -> tuple[int, int, bool]:
    modelo = session.execute(
        select(DefValuesetModelo).where(DefValuesetModelo.codigo == MODELO_DEFAULT_CODIGO)
    ).scalar_one_or_none()
    if modelo is None:
        print(f"Modelo {MODELO_DEFAULT_CODIGO} nao existe; linhas de material nao criadas")
        return 0, 0, True

    criadas = reutilizadas = 0
    for chave, _nome, codigo_opcao, nome_opcao, ordem in _LINHAS_MATERIAL:
        existing = session.execute(
            select(DefValuesetModeloLinha).where(
                DefValuesetModeloLinha.def_valueset_modelo_id == modelo.id,
                DefValuesetModeloLinha.chave == chave,
            )
        ).scalar_one_or_none()
        if existing is not None:
            reutilizadas += 1
            print(f"Linha {MODELO_DEFAULT_CODIGO} {chave} ja existe, mantida")
            continue
        session.add(
            DefValuesetModeloLinha(
                def_valueset_modelo_id=modelo.id,
                chave=chave,
                codigo_opcao=codigo_opcao,
                nome_opcao=nome_opcao,
                padrao=True,
                ordem=ordem,
                materia_prima_id=None,
                ref_materia_prima=None,
                descricao_materia_prima=None,
                valor_texto=nome_opcao,
                ativo=True,
            )
        )
        session.flush()
        criadas += 1
        print(f"Linha {MODELO_DEFAULT_CODIGO} {chave}/{codigo_opcao} criada")
    return criadas, reutilizadas, False


def _criar_pecas(session: Session) -> tuple[int, int]:
    criadas = reutilizadas = 0
    for seed in PECAS_SANDWICH:
        existing = _peca_por_codigo(session, seed.codigo)
        if existing is not None:
            reutilizadas += 1
            print(f"Peça {seed.codigo} ja existe, mantida")
            continue
        session.add(
            DefPeca(
                codigo=seed.codigo,
                nome=seed.nome,
                descricao="Definição base para painel sandwich.",
                grupo=GRUPO_PAINEIS_SANDWICH,
                tipo_peca=seed.tipo_peca,
                natureza=seed.natureza,
                orientacao=NEUTRA,
                chave_valueset_material=seed.chave_valueset_material,
                permite_acabamento=False,
                sem_material=seed.sem_material,
                ativo=True,
            )
        )
        session.flush()
        criadas += 1
        print(f"Peça {seed.codigo} criada")
    return criadas, reutilizadas


def _criar_componentes(session: Session) -> tuple[int, int]:
    criados = reutilizados = 0
    for seed in COMPONENTES_SANDWICH:
        pai = _peca_por_codigo(session, seed.pai_codigo)
        filho = _peca_por_codigo(session, seed.filho_codigo)
        if pai is None or filho is None:
            raise ValueError(f"Peça sandwich em falta: {seed.pai_codigo} -> {seed.filho_codigo}")
        existing = session.execute(
            select(DefPecaComponente).where(
                DefPecaComponente.def_peca_pai_id == pai.id,
                DefPecaComponente.ordem == seed.ordem,
            )
        ).scalar_one_or_none()
        if existing is not None:
            reutilizados += 1
            print(f"Componente {seed.pai_codigo} ordem {seed.ordem} ja existe, mantido")
            continue
        session.add(
            DefPecaComponente(
                def_peca_pai_id=pai.id,
                tipo_componente=PECA,
                def_peca_componente_id=filho.id,
                descricao=seed.descricao,
                formula_comp=seed.formula_comp,
                formula_larg=seed.formula_larg,
                formula_esp=seed.formula_esp,
                ordem=seed.ordem,
                quantidade=Decimal("1"),
                regra_quantidade="FIXA",
                obrigatorio=True,
                ativo=True,
            )
        )
        session.flush()
        criados += 1
        print(f"Componente {seed.pai_codigo} -> {seed.filho_codigo} criado")
    return criados, reutilizados


def _criar_operacao_revestimento(session: Session) -> tuple[bool, bool, bool]:
    face = _peca_por_codigo(session, "FACE_SANDWICH")
    operacao = session.execute(
        select(DefOperacao).where(DefOperacao.codigo == OPERACAO_REVESTIMENTO_CODIGO)
    ).scalar_one_or_none()
    if face is None:
        raise ValueError("Peça FACE_SANDWICH em falta")
    if operacao is None:
        print(f"Operação {OPERACAO_REVESTIMENTO_CODIGO} nao encontrada; ligacao ignorada")
        return False, False, True
    existing = session.execute(
        select(DefPecaOperacao).where(
            DefPecaOperacao.def_peca_id == face.id,
            DefPecaOperacao.def_operacao_id == operacao.id,
            DefPecaOperacao.metodo_calculo == REVESTIMENTO,
        )
    ).scalar_one_or_none()
    if existing is not None:
        print("Ligação FACE_SANDWICH -> REVESTIMENTO_SANDWICH ja existe, mantida")
        return False, True, False
    session.add(
        DefPecaOperacao(
            def_peca_id=face.id,
            def_operacao_id=operacao.id,
            ordem=1,
            metodo_calculo=REVESTIMENTO,
            regra_calculo=POR_AREA_FACE,
            quantidade_base=Decimal("1"),
            obrigatorio=True,
            ativo=True,
        )
    )
    session.flush()
    print("Ligação FACE_SANDWICH -> REVESTIMENTO_SANDWICH criada")
    return True, False, False


def seed_pecas_sandwich(session: Session) -> PecasSandwichResult:
    """Create or reuse the sandwich catalog, with no destructive writes."""
    chaves_criadas, chaves_reutilizadas = _criar_chaves(session)
    linhas_criadas, linhas_reutilizadas, modelo_em_falta = _criar_linhas_modelo(session)
    pecas_criadas, pecas_reutilizadas = _criar_pecas(session)
    componentes_criados, componentes_reutilizados = _criar_componentes(session)
    op_criada, op_reutilizada, op_em_falta = _criar_operacao_revestimento(session)
    session.commit()
    return PecasSandwichResult(
        chaves_criadas,
        chaves_reutilizadas,
        linhas_criadas,
        linhas_reutilizadas,
        modelo_em_falta,
        pecas_criadas,
        pecas_reutilizadas,
        componentes_criados,
        componentes_reutilizados,
        op_criada,
        op_reutilizada,
        op_em_falta,
    )


def print_summary(result: PecasSandwichResult) -> None:
    print("Resumo final")
    print(f"Chaves criadas: {result.chaves_criadas}")
    print(f"Peças criadas: {result.pecas_criadas}")
    print(f"Componentes criados: {result.componentes_criados}")
    if result.operacao_revestimento_em_falta:
        print("Ligação de revestimento pendente: execute após o seed de operações")


def main() -> int:
    _ = settings.database_url
    with SessionLocal() as session:
        result = seed_pecas_sandwich(session)
    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
