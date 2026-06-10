"""Idempotent seed of example machine tariffs and CNC area tiers (phase 8S.0).

Fills EXAMPLE, editable values only where they are still empty:
- CORTE / ORLAGEM: €/ML and setup/piece (STD and SERIE);
- CNC_VERTICAL: 5 area tiers (only created when the machine has none);
- MONTAGEM / MANUAL: custo_hora_serie = custo_hora * 0.85 (only when empty).

Re-running never duplicates tiers nor overwrites values the user already set.

Run:
    python -m scripts.seed_tarifas_maquinas
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import DefMaquina, DefMaquinaEscalaoArea

_D = Decimal

# €/ML and setup/piece tariffs (only empty fields are filled).
TARIFAS_ML: dict[str, dict[str, Decimal]] = {
    "CORTE": {
        "preco_ml_std": _D("0.45"),
        "preco_ml_serie": _D("0.35"),
        "custo_setup_peca_std": _D("0.15"),
        "custo_setup_peca_serie": _D("0.08"),
    },
    "ORLAGEM": {
        "preco_ml_std": _D("0.60"),
        "preco_ml_serie": _D("0.45"),
        "custo_setup_peca_std": _D("0.10"),
        "custo_setup_peca_serie": _D("0.05"),
    },
}

# CNC area tiers: (nivel, area_max_m2 [None = no limit], preco_std, preco_serie).
ESCALOES_CNC: dict[str, list[tuple[int, Decimal | None, Decimal, Decimal]]] = {
    "CNC_VERTICAL": [
        (1, _D("0.25"), _D("1.20"), _D("0.90")),
        (2, _D("0.50"), _D("1.80"), _D("1.35")),
        (3, _D("1.00"), _D("2.60"), _D("1.95")),
        (4, _D("2.00"), _D("3.80"), _D("2.85")),
        (5, None, _D("5.50"), _D("4.10")),
    ],
}

# Machines whose SERIE hourly rate is seeded from STD * factor (only when empty).
MAQUINAS_HORA = ("MONTAGEM", "MANUAL")
FATOR_HORA_SERIE = _D("0.85")


@dataclass
class SeedRelatorio:
    """Summary of what the idempotent seed changed."""

    campos_preenchidos: int = 0
    escaloes_criados: int = 0
    maquinas_em_falta: list[str] = field(default_factory=list)


def aplicar_tarifas(
    maquinas_por_codigo: dict[str, object],
    tem_escaloes: Callable[[int], bool],
    adicionar_escalao: Callable[[int, int, Decimal | None, Decimal, Decimal], None],
) -> SeedRelatorio:
    """Apply the example tariffs/tiers in memory (idempotent decision logic).

    ``maquinas_por_codigo`` maps a machine code to its (mutable) machine object;
    ``tem_escaloes(maquina_id)`` says whether tiers already exist; new tiers are
    created via ``adicionar_escalao``. Only empty fields are filled and tiers are
    only created when none exist, so re-running changes nothing.
    """
    relatorio = SeedRelatorio()

    def _maquina(codigo: str):
        maquina = maquinas_por_codigo.get(codigo)
        if maquina is None:
            relatorio.maquinas_em_falta.append(codigo)
        return maquina

    for codigo, valores in TARIFAS_ML.items():
        maquina = _maquina(codigo)
        if maquina is None:
            continue
        for campo, valor in valores.items():
            if getattr(maquina, campo) is None:
                setattr(maquina, campo, valor)
                relatorio.campos_preenchidos += 1

    for codigo in MAQUINAS_HORA:
        maquina = _maquina(codigo)
        if maquina is None:
            continue
        if maquina.custo_hora_serie is None and maquina.custo_hora is not None:
            maquina.custo_hora_serie = (maquina.custo_hora * FATOR_HORA_SERIE).quantize(
                _D("0.0001")
            )
            relatorio.campos_preenchidos += 1

    for codigo, escaloes in ESCALOES_CNC.items():
        maquina = _maquina(codigo)
        if maquina is None:
            continue
        if tem_escaloes(maquina.id):
            continue  # idempotent: tiers already exist -> do not duplicate
        for nivel, area_max, preco_std, preco_serie in escaloes:
            adicionar_escalao(maquina.id, nivel, area_max, preco_std, preco_serie)
            relatorio.escaloes_criados += 1

    return relatorio


def seed_tarifas_maquinas(session: Session) -> SeedRelatorio:
    """Fill example tariffs/tiers where empty. Idempotent (safe to re-run)."""
    codigos = list(TARIFAS_ML) + list(MAQUINAS_HORA) + list(ESCALOES_CNC)
    maquinas_por_codigo: dict[str, object] = {}
    for codigo in codigos:
        maquina = session.execute(
            select(DefMaquina).where(DefMaquina.codigo == codigo)
        ).scalars().first()
        if maquina is not None:
            maquinas_por_codigo[codigo] = maquina

    def tem_escaloes(maquina_id: int) -> bool:
        existente = session.execute(
            select(DefMaquinaEscalaoArea).where(
                DefMaquinaEscalaoArea.def_maquina_id == maquina_id
            )
        ).scalars().first()
        return existente is not None

    def adicionar_escalao(
        maquina_id: int,
        nivel: int,
        area_max: Decimal | None,
        preco_std: Decimal,
        preco_serie: Decimal,
    ) -> None:
        session.add(
            DefMaquinaEscalaoArea(
                def_maquina_id=maquina_id,
                nivel=nivel,
                area_max_m2=area_max,
                preco_peca_std=preco_std,
                preco_peca_serie=preco_serie,
                ativo=True,
            )
        )

    return aplicar_tarifas(maquinas_por_codigo, tem_escaloes, adicionar_escalao)


def main() -> None:
    with SessionLocal() as session:
        relatorio = seed_tarifas_maquinas(session)
        session.commit()

    print(
        f"Campos preenchidos: {relatorio.campos_preenchidos} | "
        f"Escalões criados: {relatorio.escaloes_criados}"
    )
    if relatorio.maquinas_em_falta:
        print("Máquinas não encontradas:", ", ".join(relatorio.maquinas_em_falta))


if __name__ == "__main__":
    main()
