"""Shared UI helpers for selecting and snapshotting edge-band references."""

from __future__ import annotations

from decimal import Decimal

from app.db.session import SessionLocal
from app.domain.materia_prima_snapshot import precos_orlas_m2
from app.repositories.def_materia_prima_repository import DefMateriaPrimaRepository


def obter_precos_orlas_m2(materia) -> tuple[Decimal | None, Decimal | None]:
    """Resolve a selected board's fine/thick orla prices in EUR/m²."""
    with SessionLocal() as session:
        repository = DefMateriaPrimaRepository(session)
        return precos_orlas_m2(materia, repository.get_by_ref_le)
