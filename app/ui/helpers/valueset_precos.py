"""UI helpers for explicit ValueSet price checks."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.valueset_precos import DivergenciaPreco, detetar_divergencias
from app.repositories.def_materia_prima_repository import DefMateriaPrimaResumo
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.services.def_valueset_modelo_linha_service import DefValuesetModeloLinhaService


def detetar_divergencias_valueset(session: Session, linhas) -> list[DivergenciaPreco]:
    """Detect price differences for UI-triggered ValueSet checks."""
    return detetar_divergencias(linhas, criar_resolver_materia(session))


def criar_resolver_materia(session: Session):
    """Return a cached resolver by material id first, then Ref LE."""
    service = DefMateriaPrimaService(session)
    cache_id: dict[int, DefMateriaPrimaResumo | None] = {}
    cache_ref: dict[str, DefMateriaPrimaResumo | None] = {}

    def resolver(
        materia_prima_id: int | None, ref_le: str | None
    ) -> DefMateriaPrimaResumo | None:
        if materia_prima_id is not None:
            if materia_prima_id not in cache_id:
                cache_id[materia_prima_id] = service.obter_por_id(materia_prima_id)
            return cache_id[materia_prima_id]

        ref_normalizada = (ref_le or "").strip()
        if not ref_normalizada:
            return None

        if ref_normalizada not in cache_ref:
            cache_ref[ref_normalizada] = service.obter_por_ref_le(ref_normalizada)
        return cache_ref[ref_normalizada]

    return resolver


def atualizacoes_de_divergencias(
    divergencias: list[DivergenciaPreco],
) -> list[tuple[int, Decimal | None, Decimal | None]]:
    """Build service update tuples from selected price differences."""
    return [
        (
            divergencia.linha_id,
            divergencia.preco_tabela_atual,
            divergencia.preco_liquido_novo,
        )
        for divergencia in divergencias
    ]


def atualizar_modelo_origem_por_divergencias(
    session: Session, modelo_id: int, divergencias: list[DivergenciaPreco]
) -> int:
    """Update matching ValueSet model lines by key and option code."""
    service = DefValuesetModeloLinhaService(session)
    linhas_modelo = service.listar_linhas_do_modelo(modelo_id)
    linhas_por_chave_opcao = {
        (linha.chave, linha.codigo_opcao): linha for linha in linhas_modelo
    }

    atualizacoes: list[tuple[int, Decimal | None, Decimal | None]] = []
    for divergencia in divergencias:
        linha_modelo = linhas_por_chave_opcao.get(
            (divergencia.chave, divergencia.codigo_opcao)
        )
        if linha_modelo is None:
            continue
        atualizacoes.append(
            (
                linha_modelo.id,
                divergencia.preco_tabela_atual,
                divergencia.preco_liquido_novo,
            )
        )

    if not atualizacoes:
        return 0

    return service.atualizar_precos_linhas(atualizacoes)
