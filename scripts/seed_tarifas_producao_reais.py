"""Seed real production machine tariffs for Martelo V3.

Run after scripts.create_default_operacoes:
    python -m scripts.seed_tarifas_producao_reais
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
from app.models import DefMaquina, DefOperacao  # noqa: E402


_D = Decimal

TARIFA_FIELDS: tuple[str, ...] = (
    "custo_hora",
    "custo_hora_serie",
    "preco_ml_std",
    "preco_ml_serie",
    "preco_lado_curto_std",
    "preco_lado_curto_serie",
    "preco_lado_longo_std",
    "preco_lado_longo_serie",
    "limite_lado_mm",
    "custo_setup_peca_std",
    "custo_setup_peca_serie",
    "preco_furo_std",
    "preco_furo_serie",
    "preco_m2_face_std",
    "preco_m2_face_serie",
)


@dataclass(frozen=True)
class TarifaMaquinaReal:
    """Authoritative real tariff values for one machine."""

    codigo: str
    custo_hora: Decimal | None = None
    custo_hora_serie: Decimal | None = None
    preco_ml_std: Decimal | None = None
    preco_ml_serie: Decimal | None = None
    preco_lado_curto_std: Decimal | None = None
    preco_lado_curto_serie: Decimal | None = None
    preco_lado_longo_std: Decimal | None = None
    preco_lado_longo_serie: Decimal | None = None
    limite_lado_mm: Decimal | None = None
    custo_setup_peca_std: Decimal | None = None
    custo_setup_peca_serie: Decimal | None = None
    preco_furo_std: Decimal | None = None
    preco_furo_serie: Decimal | None = None
    preco_m2_face_std: Decimal | None = None
    preco_m2_face_serie: Decimal | None = None


@dataclass(frozen=True)
class SeedTarifasProducaoReaisResult:
    """Summary of the real production tariffs seed."""

    maquinas_atualizadas: int
    embalamento_criada: bool
    operacao_embalamento_reapontada: bool
    maquinas_nao_encontradas: tuple[str, ...]


TARIFAS_REAIS: tuple[TarifaMaquinaReal, ...] = (
    TarifaMaquinaReal(
        codigo="CORTE",
        preco_ml_std=_D("0.62"),
        preco_ml_serie=_D("0.41"),
        custo_setup_peca_std=_D("0.06"),
        custo_setup_peca_serie=_D("0.03"),
    ),
    TarifaMaquinaReal(
        codigo="ORLAGEM",
        preco_ml_std=None,
        preco_ml_serie=None,
        preco_lado_curto_std=_D("0.55"),
        preco_lado_curto_serie=_D("0.40"),
        preco_lado_longo_std=_D("1.10"),
        preco_lado_longo_serie=_D("0.80"),
        limite_lado_mm=_D("1500"),
        custo_setup_peca_std=_D("0.10"),
        custo_setup_peca_serie=_D("0.05"),
    ),
    TarifaMaquinaReal(
        codigo="CNC_ABD",
        custo_hora=_D("30"),
        custo_hora_serie=_D("30"),
        preco_furo_std=_D("0.10"),
        preco_furo_serie=_D("0.07"),
    ),
    TarifaMaquinaReal(
        codigo="CNC_VERTICAL",
        custo_hora=_D("60"),
        custo_hora_serie=_D("60"),
        preco_furo_std=_D("0.12"),
        preco_furo_serie=_D("0.09"),
    ),
    TarifaMaquinaReal(
        codigo="CNC_SANDWICH",
        custo_hora=_D("60"),
        custo_hora_serie=_D("60"),
        preco_furo_std=_D("0.10"),
        preco_furo_serie=_D("0.06"),
    ),
    TarifaMaquinaReal(
        codigo="CNC_5_EIXOS",
        custo_hora=_D("90"),
        custo_hora_serie=_D("90"),
        preco_furo_std=_D("0.15"),
        preco_furo_serie=_D("0.11"),
    ),
    TarifaMaquinaReal(
        codigo="REVESTIMENTO_SANDWICH",
        preco_m2_face_std=_D("3.25"),
        preco_m2_face_serie=_D("3.25"),
    ),
    TarifaMaquinaReal(
        codigo="MANUAL",
        custo_hora=_D("20"),
        custo_hora_serie=_D("20"),
    ),
    TarifaMaquinaReal(
        codigo="MONTAGEM",
        custo_hora=_D("60"),
        custo_hora_serie=_D("60"),
    ),
    TarifaMaquinaReal(
        codigo="EMBALAMENTO",
        custo_hora=_D("30"),
        custo_hora_serie=_D("30"),
    ),
)


def get_maquina_by_codigo(session: Session, codigo: str) -> DefMaquina | None:
    """Find one machine by code."""
    return session.execute(
        select(DefMaquina).where(DefMaquina.codigo == codigo)
    ).scalar_one_or_none()


def get_operacao_by_codigo(session: Session, codigo: str) -> DefOperacao | None:
    """Find one operation by code."""
    return session.execute(
        select(DefOperacao).where(DefOperacao.codigo == codigo)
    ).scalar_one_or_none()


def ensure_maquina_embalamento(session: Session) -> tuple[DefMaquina, bool]:
    """Ensure the EMBALAMENTO machine exists and is visible for manual insertion."""
    maquina = get_maquina_by_codigo(session, "EMBALAMENTO")
    if maquina is not None:
        maquina.nome = "Embalamento"
        maquina.tipo = "MONTAGEM"
        maquina.ativo = True
        session.flush()
        return maquina, False

    maquina = DefMaquina(
        codigo="EMBALAMENTO",
        nome="Embalamento",
        tipo="MONTAGEM",
        ativo=True,
    )
    session.add(maquina)
    session.flush()

    return maquina, True


def aplicar_tarifa_real(maquina: DefMaquina, tarifa: TarifaMaquinaReal) -> None:
    """Write the authoritative real tariff values to one machine."""
    for field in TARIFA_FIELDS:
        setattr(maquina, field, getattr(tarifa, field))


def seed_tarifas_producao_reais(session: Session) -> SeedTarifasProducaoReaisResult:
    """Write the real production tariffs. Idempotent and authoritative."""
    maquina_embalamento, embalamento_criada = ensure_maquina_embalamento(session)
    maquinas_atualizadas = 0
    maquinas_nao_encontradas: list[str] = []

    for tarifa in TARIFAS_REAIS:
        if tarifa.codigo == "EMBALAMENTO":
            maquina = maquina_embalamento
        else:
            maquina = get_maquina_by_codigo(session, tarifa.codigo)

        if maquina is None:
            maquinas_nao_encontradas.append(tarifa.codigo)
            continue

        aplicar_tarifa_real(maquina, tarifa)
        maquinas_atualizadas += 1

    operacao_embalamento_reapontada = False
    operacao_embalamento = get_operacao_by_codigo(session, "EMBALAMENTO")
    if (
        operacao_embalamento is not None
        and operacao_embalamento.maquina_id != maquina_embalamento.id
    ):
        operacao_embalamento.maquina_id = maquina_embalamento.id
        operacao_embalamento_reapontada = True

    session.commit()

    return SeedTarifasProducaoReaisResult(
        maquinas_atualizadas=maquinas_atualizadas,
        embalamento_criada=embalamento_criada,
        operacao_embalamento_reapontada=operacao_embalamento_reapontada,
        maquinas_nao_encontradas=tuple(maquinas_nao_encontradas),
    )


def print_summary(result: SeedTarifasProducaoReaisResult) -> None:
    """Print the final user-facing seed summary."""
    print("Resumo final")
    print(f"Maquinas atualizadas: {result.maquinas_atualizadas}")
    print(f"EMBALAMENTO criada: {'sim' if result.embalamento_criada else 'nao'}")
    print(
        "Operacao EMBALAMENTO re-apontada: "
        f"{'sim' if result.operacao_embalamento_reapontada else 'nao'}"
    )
    if result.maquinas_nao_encontradas:
        print("Maquinas nao encontradas: " + ", ".join(result.maquinas_nao_encontradas))
    else:
        print("Maquinas nao encontradas: nenhuma")


def main() -> int:
    """Seed real production machine tariffs in the configured database."""
    _ = settings.database_url

    with SessionLocal() as session:
        result = seed_tarifas_producao_reais(session)

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
