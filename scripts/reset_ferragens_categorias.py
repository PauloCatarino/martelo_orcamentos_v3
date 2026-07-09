"""Reset old hardware piece variants and seed generic hardware categories.

Dry-run by default. Pass ``--aplicar`` to delete the old definitions and create
the new ValueSet keys, generic piece definitions, and base operation links.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domain.orla_types import SEM_ORLA  # noqa: E402
from app.domain.peca_types import SIMPLES  # noqa: E402
from app.domain.regra_operacao_types import POR_PECA  # noqa: E402
from app.models import (  # noqa: E402
    DefModuloLinha,
    DefOperacao,
    DefPeca,
    DefPecaComponente,
    DefPecaOperacao,
    DefValuesetChave,
    OrcamentoItemCusteioLinha,
)


@dataclass(frozen=True)
class ChaveSeed:
    """One ValueSet key required by the generic categories."""

    codigo: str
    nome: str
    tipo: str
    grupo: str


@dataclass(frozen=True)
class CategoriaPecaSeed:
    """One generic piece definition for a hardware/configurable category."""

    codigo: str
    nome: str
    grupo: str
    chave_valueset_material: str


@dataclass(frozen=True)
class OperacaoBaseSeed:
    """One base operation link for a generic piece definition."""

    peca_codigo: str
    operacao_codigo: str
    observacoes: str
    ordem: int = 1
    unidade_tempo: str | None = "PECA"


@dataclass(frozen=True)
class LimpezaPlano:
    """Rows that will be deleted in phase 1."""

    pecas: tuple[DefPeca, ...]
    pecas_protegidas: tuple[DefPeca, ...]
    codigos_nao_encontrados: tuple[str, ...]
    operacoes: tuple[DefPecaOperacao, ...]
    componentes: tuple[DefPecaComponente, ...]
    linhas_custeio_diretas: tuple[OrcamentoItemCusteioLinha, ...]
    linhas_custeio_dependentes: tuple[OrcamentoItemCusteioLinha, ...]
    linhas_modulo_diretas: tuple[DefModuloLinha, ...]
    linhas_modulo_dependentes: tuple[DefModuloLinha, ...]

    @property
    def linhas_custeio(self) -> tuple[OrcamentoItemCusteioLinha, ...]:
        return self.linhas_custeio_diretas + self.linhas_custeio_dependentes

    @property
    def linhas_modulo(self) -> tuple[DefModuloLinha, ...]:
        return self.linhas_modulo_diretas + self.linhas_modulo_dependentes


@dataclass(frozen=True)
class ResetFerragensResult:
    """Summary of the reset execution."""

    dry_run: bool
    pecas_removidas: int
    operacoes_removidas: int
    componentes_removidos: int
    linhas_custeio_removidas: int
    linhas_modulo_removidas: int
    chaves_criadas: int
    chaves_reutilizadas: int
    categorias_criadas: int
    categorias_reutilizadas: int
    ligacoes_criadas: int
    ligacoes_reutilizadas: int
    pecas_operacao_nao_encontradas: int
    operacoes_nao_encontradas: int


OLD_FERRAGEM_VARIANT_CODES: tuple[str, ...] = (
    "CORREDICA LIVRE_1",
    "CORREDICA LIVRE_2",
    "CORREDICA SILVER EXTRACAO TOTAL",
    "CORREDICA TANDEM EXTRACAO TOTAL",
    "CORREDICA VERTEX EXTRACAO TOTAL",
    "DOBRADICA_RETA",
    "DOBRADICA_LIVRE_1",
    "DOBRADICA_LIVRE_2",
    "DOBRADICA_ABERTURA_TOTAL",
    "DOBRADICA_CANTO_SEGO",
    "PES",
    "PES_AXILO",
    "PES_BOMBOCA",
    "PES_BONE",
    "PUXADOR APLICAR",
    "PUXADOR TIC-TAC",
    "VARAO",
    "SUPORTE_VARAO",
    "VARAO+SUPORTES",
    "PORTA+DOBRADICA",
)


NEW_VALUESET_CHAVES: tuple[ChaveSeed, ...] = (
    ChaveSeed(
        "FERRAGEM_SUPORTE_PRATELEIRA",
        "Suporte prateleira",
        "FERRAGEM",
        "FERRAGENS",
    ),
    ChaveSeed(
        "FERRAGEM_SUPORTE_PRATELEIRA_PAREDE",
        "Suporte prateleira parede",
        "FERRAGEM",
        "FERRAGENS",
    ),
    ChaveSeed("FERRAGEM_AVENTOS", "Aventos", "FERRAGEM", "FERRAGENS"),
    ChaveSeed(
        "FERRAGEM_SISTEMA_ELEVACAO",
        "Sistema eleva\u00e7\u00e3o",
        "FERRAGEM",
        "FERRAGENS",
    ),
    ChaveSeed("ILUMINACAO_CABO_LED", "Cabo LED", "ILUMINACAO", "ILUMINACAO"),
    ChaveSeed(
        "ILUMINACAO_CABO_TRANSFORMADOR",
        "Cabo transformador",
        "ILUMINACAO",
        "ILUMINACAO",
    ),
    ChaveSeed(
        "ILUMINACAO_DISTRIBUIDOR",
        "Distribuidor",
        "ILUMINACAO",
        "ILUMINACAO",
    ),
    ChaveSeed(
        "SISTEMA_CORRER_CALHA_U",
        "Calha U",
        "SISTEMA_CORRER",
        "SISTEMAS_CORRER",
    ),
    ChaveSeed(
        "SISTEMA_CORRER_CALHA_H",
        "Calha H",
        "SISTEMA_CORRER",
        "SISTEMAS_CORRER",
    ),
)


GENERIC_CATEGORIAS: tuple[CategoriaPecaSeed, ...] = (
    CategoriaPecaSeed("DOBRADICA", "Dobradi\u00e7a", "FERRAGENS", "FERRAGEM_DOBRADICA"),
    CategoriaPecaSeed("PUXADOR", "Puxador", "FERRAGENS", "FERRAGEM_PUXADOR"),
    CategoriaPecaSeed("CORREDICA", "Corredi\u00e7a", "FERRAGENS", "FERRAGEM_CORREDICA"),
    CategoriaPecaSeed(
        "SUPORTE_PRATELEIRA",
        "Suporte prateleira",
        "FERRAGENS",
        "FERRAGEM_SUPORTE_PRATELEIRA",
    ),
    CategoriaPecaSeed(
        "SUPORTE_PRATELEIRA_PAREDE",
        "Suporte prateleira parede",
        "FERRAGENS",
        "FERRAGEM_SUPORTE_PRATELEIRA_PAREDE",
    ),
    CategoriaPecaSeed(
        "SUPORTE_VARAO",
        "Suporte var\u00e3o",
        "FERRAGENS",
        "FERRAGEM_SUPORTE_VARAO",
    ),
    CategoriaPecaSeed("VARAO", "Var\u00e3o", "FERRAGENS", "FERRAGEM_VARAO"),
    CategoriaPecaSeed("PES", "P\u00e9s", "FERRAGENS", "FERRAGEM_PE_NIVELADOR"),
    CategoriaPecaSeed("AVENTOS", "Aventos", "FERRAGENS", "FERRAGEM_AVENTOS"),
    CategoriaPecaSeed(
        "SISTEMA_ELEVACAO",
        "Sistema eleva\u00e7\u00e3o",
        "FERRAGENS",
        "FERRAGEM_SISTEMA_ELEVACAO",
    ),
    CategoriaPecaSeed("LED", "LED", "ILUMINACAO", "ILUMINACAO_FITA_LED"),
    CategoriaPecaSeed("SENSOR_LED", "Sensor LED", "ILUMINACAO", "ILUMINACAO_SENSOR"),
    CategoriaPecaSeed(
        "TRANSFORMADOR",
        "Transformador",
        "ILUMINACAO",
        "ILUMINACAO_TRANSFORMADOR",
    ),
    CategoriaPecaSeed(
        "CABO_TRANSFORMADOR",
        "Cabo transformador",
        "ILUMINACAO",
        "ILUMINACAO_CABO_TRANSFORMADOR",
    ),
    CategoriaPecaSeed("CABO_LED", "Cabo LED", "ILUMINACAO", "ILUMINACAO_CABO_LED"),
    CategoriaPecaSeed(
        "DISTRIBUIDOR",
        "Distribuidor",
        "ILUMINACAO",
        "ILUMINACAO_DISTRIBUIDOR",
    ),
    CategoriaPecaSeed(
        "PUXADOR_PORTA_CORRER",
        "Puxador porta correr",
        "SISTEMAS_CORRER",
        "SISTEMA_CORRER_PUXADOR_WAVE",
    ),
    CategoriaPecaSeed(
        "RODAS_PORTA_CORRER_SUP",
        "Rodas porta correr sup",
        "SISTEMAS_CORRER",
        "SISTEMA_CORRER_RODIZIO_SUP",
    ),
    CategoriaPecaSeed(
        "RODAS_PORTA_CORRER_INF",
        "Rodas porta correr inf",
        "SISTEMAS_CORRER",
        "SISTEMA_CORRER_RODIZIO_INF",
    ),
    CategoriaPecaSeed(
        "CALHA_PORTA_CORRER_U",
        "Calha porta correr U",
        "SISTEMAS_CORRER",
        "SISTEMA_CORRER_CALHA_U",
    ),
    CategoriaPecaSeed(
        "CALHA_PORTA_CORRER_H",
        "Calha porta correr H",
        "SISTEMAS_CORRER",
        "SISTEMA_CORRER_CALHA_H",
    ),
    CategoriaPecaSeed(
        "CALHA_INF_SISTEMA_CORRER",
        "Calha inf sistema correr",
        "SISTEMAS_CORRER",
        "SISTEMA_CORRER_CALHA_INF",
    ),
    CategoriaPecaSeed(
        "CALHA_SUP_SISTEMA_CORRER",
        "Calha sup sistema correr",
        "SISTEMAS_CORRER",
        "SISTEMA_CORRER_CALHA_SUP",
    ),
)


OPERACOES_BASE: tuple[OperacaoBaseSeed, ...] = (
    OperacaoBaseSeed(
        "DOBRADICA",
        "CNC_VERTICAL",
        "Furo do copo da dobradi\u00e7a em CNC",
    ),
    OperacaoBaseSeed(
        "CORREDICA",
        "CNC_VERTICAL",
        "Fura\u00e7\u00e3o de fixa\u00e7\u00e3o da corredi\u00e7a",
    ),
    OperacaoBaseSeed("PUXADOR", "CNC_VERTICAL", "Fura\u00e7\u00e3o do puxador"),
    OperacaoBaseSeed("VARAO", "OPERACAO_MANUAL", "Corte do var\u00e3o \u00e0 medida"),
)


GENERIC_CATEGORIAS_BY_CODE = {seed.codigo: seed for seed in GENERIC_CATEGORIAS}
OLD_FERRAGEM_VARIANT_CODE_SET = set(OLD_FERRAGEM_VARIANT_CODES)


def _seed_matches_existing_generic(peca: DefPeca, seed: CategoriaPecaSeed) -> bool:
    """Return True when an existing row already is the desired generic category."""
    return (
        peca.codigo == seed.codigo
        and peca.nome == seed.nome
        and peca.grupo == seed.grupo
        and peca.tipo_peca == SIMPLES
        and peca.orla_c1 == SEM_ORLA
        and peca.orla_c2 == SEM_ORLA
        and peca.orla_l1 == SEM_ORLA
        and peca.orla_l2 == SEM_ORLA
        and peca.chave_valueset_material == seed.chave_valueset_material
        and not peca.permite_acabamento
        and not peca.sem_material
        and peca.ativo
    )


def _pecas_antigas_a_limpar(session: Session) -> tuple[
    tuple[DefPeca, ...],
    tuple[DefPeca, ...],
    tuple[str, ...],
]:
    """Find old piece rows by the explicit code list, protecting new generics."""
    pecas_por_codigo = {
        peca.codigo: peca
        for peca in session.execute(
            select(DefPeca)
            .where(DefPeca.codigo.in_(OLD_FERRAGEM_VARIANT_CODES))
            .order_by(DefPeca.codigo)
        ).scalars()
    }

    remover: list[DefPeca] = []
    protegidas: list[DefPeca] = []
    for codigo in OLD_FERRAGEM_VARIANT_CODES:
        peca = pecas_por_codigo.get(codigo)
        if peca is None:
            continue
        seed_generico = GENERIC_CATEGORIAS_BY_CODE.get(codigo)
        if seed_generico is not None and _seed_matches_existing_generic(peca, seed_generico):
            protegidas.append(peca)
            continue
        remover.append(peca)

    codigos_presentes = set(pecas_por_codigo)
    codigos_nao_encontrados = tuple(
        codigo for codigo in OLD_FERRAGEM_VARIANT_CODES if codigo not in codigos_presentes
    )
    return tuple(remover), tuple(protegidas), codigos_nao_encontrados


def _expandir_linhas_custeio(
    session: Session,
    linhas_diretas: tuple[OrcamentoItemCusteioLinha, ...],
) -> tuple[OrcamentoItemCusteioLinha, ...]:
    """Collect costing lines that depend on the direct rows through linha_pai_id."""
    vistos = {linha.id for linha in linhas_diretas}
    fronteira = set(vistos)
    dependentes: list[OrcamentoItemCusteioLinha] = []

    while fronteira:
        filhos = tuple(
            session.execute(
                select(OrcamentoItemCusteioLinha)
                .where(OrcamentoItemCusteioLinha.linha_pai_id.in_(fronteira))
                .order_by(OrcamentoItemCusteioLinha.id)
            ).scalars()
        )
        fronteira = set()
        for filho in filhos:
            if filho.id in vistos:
                continue
            vistos.add(filho.id)
            fronteira.add(filho.id)
            dependentes.append(filho)

    return tuple(dependentes)


def _expandir_linhas_modulo(
    session: Session,
    linhas_diretas: tuple[DefModuloLinha, ...],
) -> tuple[DefModuloLinha, ...]:
    """Collect module lines whose parent order points at a direct row."""
    if not linhas_diretas:
        return ()

    modulo_ids = {linha.def_modulo_id for linha in linhas_diretas}
    todas_linhas = tuple(
        session.execute(
            select(DefModuloLinha)
            .where(DefModuloLinha.def_modulo_id.in_(modulo_ids))
            .order_by(DefModuloLinha.def_modulo_id, DefModuloLinha.ordem)
        ).scalars()
    )
    por_pai: dict[tuple[int, int], list[DefModuloLinha]] = {}
    for linha in todas_linhas:
        if linha.linha_pai_ordem is None:
            continue
        por_pai.setdefault((linha.def_modulo_id, linha.linha_pai_ordem), []).append(linha)

    vistos = {linha.id for linha in linhas_diretas}
    fronteira = {(linha.def_modulo_id, linha.ordem) for linha in linhas_diretas}
    dependentes: list[DefModuloLinha] = []

    while fronteira:
        nova_fronteira: set[tuple[int, int]] = set()
        for chave_pai in fronteira:
            for filho in por_pai.get(chave_pai, []):
                if filho.id in vistos:
                    continue
                vistos.add(filho.id)
                nova_fronteira.add((filho.def_modulo_id, filho.ordem))
                dependentes.append(filho)
        fronteira = nova_fronteira

    return tuple(dependentes)


def construir_plano_limpeza(session: Session) -> LimpezaPlano:
    """Build the complete phase-1 deletion plan without mutating the database."""
    pecas, protegidas, codigos_nao_encontrados = _pecas_antigas_a_limpar(session)
    peca_ids = [peca.id for peca in pecas]

    if not peca_ids:
        return LimpezaPlano(
            pecas=(),
            pecas_protegidas=protegidas,
            codigos_nao_encontrados=codigos_nao_encontrados,
            operacoes=(),
            componentes=(),
            linhas_custeio_diretas=(),
            linhas_custeio_dependentes=(),
            linhas_modulo_diretas=(),
            linhas_modulo_dependentes=(),
        )

    operacoes = tuple(
        session.execute(
            select(DefPecaOperacao)
            .where(DefPecaOperacao.def_peca_id.in_(peca_ids))
            .order_by(DefPecaOperacao.def_peca_id, DefPecaOperacao.ordem)
        ).scalars()
    )
    componentes = tuple(
        session.execute(
            select(DefPecaComponente)
            .where(
                or_(
                    DefPecaComponente.def_peca_pai_id.in_(peca_ids),
                    DefPecaComponente.def_peca_componente_id.in_(peca_ids),
                )
            )
            .order_by(DefPecaComponente.def_peca_pai_id, DefPecaComponente.ordem)
        ).scalars()
    )
    linhas_custeio_diretas = tuple(
        session.execute(
            select(OrcamentoItemCusteioLinha)
            .where(OrcamentoItemCusteioLinha.def_peca_id.in_(peca_ids))
            .order_by(
                OrcamentoItemCusteioLinha.orcamento_item_id,
                OrcamentoItemCusteioLinha.ordem_visual,
                OrcamentoItemCusteioLinha.id,
            )
        ).scalars()
    )
    linhas_custeio_dependentes = _expandir_linhas_custeio(session, linhas_custeio_diretas)

    linhas_modulo_diretas = tuple(
        session.execute(
            select(DefModuloLinha)
            .where(DefModuloLinha.def_peca_id.in_(peca_ids))
            .order_by(DefModuloLinha.def_modulo_id, DefModuloLinha.ordem)
        ).scalars()
    )
    linhas_modulo_dependentes = _expandir_linhas_modulo(session, linhas_modulo_diretas)

    return LimpezaPlano(
        pecas=pecas,
        pecas_protegidas=protegidas,
        codigos_nao_encontrados=codigos_nao_encontrados,
        operacoes=operacoes,
        componentes=componentes,
        linhas_custeio_diretas=linhas_custeio_diretas,
        linhas_custeio_dependentes=linhas_custeio_dependentes,
        linhas_modulo_diretas=linhas_modulo_diretas,
        linhas_modulo_dependentes=linhas_modulo_dependentes,
    )


def _delete_by_ids(session: Session, model: type, ids: list[int]) -> int:
    """Delete rows from one model by primary key and return the affected count."""
    if not ids:
        return 0
    result = session.execute(delete(model).where(model.id.in_(ids)))
    return int(result.rowcount or 0)


def aplicar_limpeza(session: Session, plano: LimpezaPlano) -> tuple[int, int, int, int, int]:
    """Apply phase-1 deletions in dependency order."""
    linhas_custeio_ids = [linha.id for linha in plano.linhas_custeio]
    linhas_modulo_ids = [linha.id for linha in plano.linhas_modulo]
    operacao_ids = [operacao.id for operacao in plano.operacoes]
    componente_ids = [componente.id for componente in plano.componentes]
    peca_ids = [peca.id for peca in plano.pecas]

    linhas_custeio = _delete_by_ids(session, OrcamentoItemCusteioLinha, linhas_custeio_ids)
    linhas_modulo = _delete_by_ids(session, DefModuloLinha, linhas_modulo_ids)
    operacoes = _delete_by_ids(session, DefPecaOperacao, operacao_ids)
    componentes = _delete_by_ids(session, DefPecaComponente, componente_ids)
    pecas = _delete_by_ids(session, DefPeca, peca_ids)
    session.flush()

    return pecas, operacoes, componentes, linhas_custeio, linhas_modulo


def _proxima_ordem_grupo(session: Session, grupo: str) -> int:
    """Return the next display order for a ValueSet group."""
    ordem = session.execute(
        select(func.max(DefValuesetChave.ordem)).where(DefValuesetChave.grupo == grupo)
    ).scalar_one()
    return int(ordem or 0) + 1


def ensure_valueset_chaves(session: Session, aplicar: bool) -> tuple[int, int]:
    """Create missing ValueSet keys required by the generic categories."""
    criadas = 0
    reutilizadas = 0
    proxima_ordem_por_grupo: dict[str, int] = {}

    for seed in NEW_VALUESET_CHAVES:
        existing = session.execute(
            select(DefValuesetChave).where(DefValuesetChave.codigo == seed.codigo)
        ).scalar_one_or_none()
        if existing is not None:
            reutilizadas += 1
            print(f"Chave {seed.codigo} ja existe, mantida")
            continue

        criadas += 1
        print(f"Chave {seed.codigo} sera criada ({seed.tipo}/{seed.grupo})")
        if not aplicar:
            continue

        if seed.grupo not in proxima_ordem_por_grupo:
            proxima_ordem_por_grupo[seed.grupo] = _proxima_ordem_grupo(session, seed.grupo)
        ordem = proxima_ordem_por_grupo[seed.grupo]
        proxima_ordem_por_grupo[seed.grupo] += 1

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

    return criadas, reutilizadas


def _codigos_categorias_a_criar(
    session: Session,
    codigos_removidos: set[str],
) -> set[str]:
    """Return category codes that will not exist after phase 1 and need creation."""
    codigos: set[str] = set()
    for seed in GENERIC_CATEGORIAS:
        existing = _get_peca_by_codigo(session, seed.codigo)
        if existing is None or seed.codigo in codigos_removidos:
            codigos.add(seed.codigo)
    return codigos


def ensure_categorias(
    session: Session,
    aplicar: bool,
    codigos_removidos: set[str] | None = None,
) -> tuple[int, int]:
    """Create missing generic piece definitions."""
    criadas = 0
    reutilizadas = 0
    codigos_removidos = codigos_removidos or set()

    for seed in GENERIC_CATEGORIAS:
        existing = session.execute(
            select(DefPeca).where(DefPeca.codigo == seed.codigo)
        ).scalar_one_or_none()
        if existing is not None and seed.codigo not in codigos_removidos:
            reutilizadas += 1
            print(f"Peca {seed.codigo} ja existe, mantida")
            continue

        criadas += 1
        print(f"Peca {seed.codigo} sera criada ({seed.grupo}, chave {seed.chave_valueset_material})")
        if not aplicar:
            continue

        peca = DefPeca(
            codigo=seed.codigo,
            nome=seed.nome,
            descricao=None,
            grupo=seed.grupo,
            tipo_peca=SIMPLES,
            orla_c1=SEM_ORLA,
            orla_c2=SEM_ORLA,
            orla_l1=SEM_ORLA,
            orla_l2=SEM_ORLA,
            chave_valueset_material=seed.chave_valueset_material,
            permite_acabamento=False,
            chave_valueset_acabamento_sup=None,
            chave_valueset_acabamento_inf=None,
            sem_material=False,
            ativo=True,
        )
        session.add(peca)
        session.flush()

    return criadas, reutilizadas


def _get_peca_by_codigo(session: Session, codigo: str) -> DefPeca | None:
    return session.execute(select(DefPeca).where(DefPeca.codigo == codigo)).scalar_one_or_none()


def _get_operacao_by_codigo(session: Session, codigo: str) -> DefOperacao | None:
    return session.execute(
        select(DefOperacao).where(DefOperacao.codigo == codigo)
    ).scalar_one_or_none()


def _get_ligacao(
    session: Session,
    def_peca_id: int,
    def_operacao_id: int,
) -> DefPecaOperacao | None:
    return session.execute(
        select(DefPecaOperacao).where(
            DefPecaOperacao.def_peca_id == def_peca_id,
            DefPecaOperacao.def_operacao_id == def_operacao_id,
        )
    ).scalar_one_or_none()


def ensure_operacoes_base(
    session: Session,
    aplicar: bool,
    codigos_categorias_a_criar: set[str] | None = None,
) -> tuple[int, int, int, int]:
    """Create missing base operation links for selected generic categories."""
    criadas = 0
    reutilizadas = 0
    pecas_nao_encontradas = 0
    operacoes_nao_encontradas = 0
    codigos_categorias_a_criar = codigos_categorias_a_criar or set()

    for seed in OPERACOES_BASE:
        peca = _get_peca_by_codigo(session, seed.peca_codigo)
        peca_vai_existir = seed.peca_codigo in codigos_categorias_a_criar
        if peca is None and not peca_vai_existir:
            pecas_nao_encontradas += 1
            print(f"Peca {seed.peca_codigo} nao encontrada; ligacao ignorada")
            continue

        operacao = _get_operacao_by_codigo(session, seed.operacao_codigo)
        if operacao is None:
            operacoes_nao_encontradas += 1
            print(
                f"Operacao {seed.operacao_codigo} nao encontrada "
                f"(peca {seed.peca_codigo}); ligacao ignorada"
            )
            continue

        ligacao = None if peca_vai_existir or peca is None else _get_ligacao(session, peca.id, operacao.id)
        if ligacao is not None:
            reutilizadas += 1
            print(f"Ligacao {seed.peca_codigo} -> {seed.operacao_codigo} ja existe, mantida")
            continue

        criadas += 1
        print(f"Ligacao {seed.peca_codigo} -> {seed.operacao_codigo} sera criada")
        if not aplicar:
            continue

        if peca is None:
            peca = _get_peca_by_codigo(session, seed.peca_codigo)
            if peca is None:
                pecas_nao_encontradas += 1
                print(f"Peca {seed.peca_codigo} nao encontrada; ligacao ignorada")
                continue

        ligacao = DefPecaOperacao(
            def_peca_id=peca.id,
            def_operacao_id=operacao.id,
            ordem=seed.ordem,
            regra_calculo=POR_PECA,
            quantidade_base=None,
            tempo_setup_minutos=None,
            tempo_por_unidade_minutos=None,
            unidade_tempo=seed.unidade_tempo,
            obrigatorio=True,
            ativo=True,
            observacoes=seed.observacoes,
        )
        session.add(ligacao)
        session.flush()

    return criadas, reutilizadas, pecas_nao_encontradas, operacoes_nao_encontradas


def _codigo_peca(session: Session, def_peca_id: int | None) -> str:
    if def_peca_id is None:
        return "-"
    peca = session.get(DefPeca, def_peca_id)
    return peca.codigo if peca is not None else f"id={def_peca_id}"


def print_plano_limpeza(session: Session, plano: LimpezaPlano) -> None:
    """Print all rows covered by phase 1."""
    print("Fase 1 - limpeza das def_pecas antigas")
    print(f"Pecas a remover: {len(plano.pecas)}")
    for peca in plano.pecas:
        print(
            f"  - id={peca.id} codigo={peca.codigo} nome={peca.nome} "
            f"grupo={peca.grupo} chave={peca.chave_valueset_material}"
        )

    if plano.pecas_protegidas:
        print("Pecas protegidas (ja coincidem com as categorias genericas):")
        for peca in plano.pecas_protegidas:
            print(f"  - id={peca.id} codigo={peca.codigo} nome={peca.nome}")

    if plano.codigos_nao_encontrados:
        print("Codigos antigos nao encontrados:")
        for codigo in plano.codigos_nao_encontrados:
            print(f"  - {codigo}")

    print(f"def_peca_operacoes a remover: {len(plano.operacoes)}")
    for operacao in plano.operacoes:
        op = session.get(DefOperacao, operacao.def_operacao_id)
        print(
            f"  - id={operacao.id} peca={_codigo_peca(session, operacao.def_peca_id)} "
            f"operacao={op.codigo if op else operacao.def_operacao_id}"
        )

    print(f"def_peca_componentes a remover: {len(plano.componentes)}")
    for componente in plano.componentes:
        print(
            f"  - id={componente.id} pai={_codigo_peca(session, componente.def_peca_pai_id)} "
            f"componente={_codigo_peca(session, componente.def_peca_componente_id)} "
            f"referencia={componente.referencia_componente}"
        )

    print(f"orcamento_item_custeio_linhas diretas a remover: {len(plano.linhas_custeio_diretas)}")
    for linha in plano.linhas_custeio_diretas:
        print(
            f"  - id={linha.id} item={linha.orcamento_item_id} tipo={linha.tipo_linha} "
            f"codigo={linha.codigo} peca={_codigo_peca(session, linha.def_peca_id)} "
            f"pai={linha.linha_pai_id}"
        )

    print(f"orcamento_item_custeio_linhas dependentes a remover: {len(plano.linhas_custeio_dependentes)}")
    for linha in plano.linhas_custeio_dependentes:
        print(
            f"  - id={linha.id} item={linha.orcamento_item_id} tipo={linha.tipo_linha} "
            f"codigo={linha.codigo} peca={_codigo_peca(session, linha.def_peca_id)} "
            f"pai={linha.linha_pai_id}"
        )

    print(f"def_modulo_linhas diretas a remover: {len(plano.linhas_modulo_diretas)}")
    for linha in plano.linhas_modulo_diretas:
        print(
            f"  - id={linha.id} modulo={linha.def_modulo_id} ordem={linha.ordem} "
            f"tipo={linha.tipo_linha} codigo={linha.codigo} "
            f"peca={_codigo_peca(session, linha.def_peca_id)} pai_ordem={linha.linha_pai_ordem}"
        )

    print(f"def_modulo_linhas dependentes a remover: {len(plano.linhas_modulo_dependentes)}")
    for linha in plano.linhas_modulo_dependentes:
        print(
            f"  - id={linha.id} modulo={linha.def_modulo_id} ordem={linha.ordem} "
            f"tipo={linha.tipo_linha} codigo={linha.codigo} "
            f"peca={_codigo_peca(session, linha.def_peca_id)} pai_ordem={linha.linha_pai_ordem}"
        )


def reset_ferragens_categorias(session: Session, aplicar: bool = False) -> ResetFerragensResult:
    """Run all reset phases, mutating only when ``aplicar`` is True."""
    plano = construir_plano_limpeza(session)
    print_plano_limpeza(session, plano)
    codigos_removidos = {peca.codigo for peca in plano.pecas}
    codigos_categorias_a_criar = _codigos_categorias_a_criar(session, codigos_removidos)

    if aplicar:
        (
            pecas_removidas,
            operacoes_removidas,
            componentes_removidos,
            linhas_custeio_removidas,
            linhas_modulo_removidas,
        ) = aplicar_limpeza(session, plano)
    else:
        pecas_removidas = len(plano.pecas)
        operacoes_removidas = len(plano.operacoes)
        componentes_removidos = len(plano.componentes)
        linhas_custeio_removidas = len(plano.linhas_custeio)
        linhas_modulo_removidas = len(plano.linhas_modulo)

    print("Fase 2 - chaves ValueSet novas")
    chaves_criadas, chaves_reutilizadas = ensure_valueset_chaves(session, aplicar)

    print("Fase 3 - categorias genericas")
    categorias_criadas, categorias_reutilizadas = ensure_categorias(
        session,
        aplicar,
        codigos_removidos,
    )

    print("Fase 4 - operacoes base")
    (
        ligacoes_criadas,
        ligacoes_reutilizadas,
        pecas_operacao_nao_encontradas,
        operacoes_nao_encontradas,
    ) = ensure_operacoes_base(session, aplicar, codigos_categorias_a_criar)

    if aplicar:
        session.commit()
    else:
        session.rollback()

    return ResetFerragensResult(
        dry_run=not aplicar,
        pecas_removidas=pecas_removidas,
        operacoes_removidas=operacoes_removidas,
        componentes_removidos=componentes_removidos,
        linhas_custeio_removidas=linhas_custeio_removidas,
        linhas_modulo_removidas=linhas_modulo_removidas,
        chaves_criadas=chaves_criadas,
        chaves_reutilizadas=chaves_reutilizadas,
        categorias_criadas=categorias_criadas,
        categorias_reutilizadas=categorias_reutilizadas,
        ligacoes_criadas=ligacoes_criadas,
        ligacoes_reutilizadas=ligacoes_reutilizadas,
        pecas_operacao_nao_encontradas=pecas_operacao_nao_encontradas,
        operacoes_nao_encontradas=operacoes_nao_encontradas,
    )


def print_summary(result: ResetFerragensResult) -> None:
    """Print the final user-facing summary."""
    modo = "DRY-RUN" if result.dry_run else "APLICADO"
    print("Resumo final")
    print(f"Modo: {modo}")
    print(f"Pecas removidas: {result.pecas_removidas}")
    print(f"Operacoes removidas: {result.operacoes_removidas}")
    print(f"Componentes removidos: {result.componentes_removidos}")
    print(f"Linhas de custeio removidas: {result.linhas_custeio_removidas}")
    print(f"Linhas de modulos removidas: {result.linhas_modulo_removidas}")
    print(f"Chaves criadas: {result.chaves_criadas}")
    print(f"Chaves mantidas: {result.chaves_reutilizadas}")
    print(f"Categorias criadas: {result.categorias_criadas}")
    print(f"Categorias mantidas: {result.categorias_reutilizadas}")
    print(f"Ligacoes de operacao criadas: {result.ligacoes_criadas}")
    print(f"Ligacoes de operacao mantidas: {result.ligacoes_reutilizadas}")
    print(f"Pecas para operacao nao encontradas: {result.pecas_operacao_nao_encontradas}")
    print(f"Operacoes nao encontradas: {result.operacoes_nao_encontradas}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset old hardware variants and seed generic hardware categories."
    )
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Executa as remocoes/criacoes. Sem esta opcao faz apenas dry-run.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the reset against the configured database."""
    args = parse_args(argv)
    _ = settings.database_url

    print("RESET FERRAGENS CATEGORIAS")
    print(f"Modo: {'APLICAR' if args.aplicar else 'DRY-RUN'}")
    print("Sem --aplicar nada e gravado na base de dados.")

    with SessionLocal() as session:
        result = reset_ferragens_categorias(session, aplicar=args.aplicar)

    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
