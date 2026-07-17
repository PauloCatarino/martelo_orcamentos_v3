"""Persistence of simplified-costing tariffs in system settings."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.domain.custeio_simplificado import (
    TARIFA_ESPESSURA_GROSSA_PADRAO,
    TARIFAS_SIMPLIFICADO_PADRAO,
    TarifaCusteioSimplificado,
    TarifaEspessuraGrossa,
)
from app.services.system_setting_service import SystemSettingService


def _decimal(valor) -> Decimal:
    return Decimal(str(valor))


def parse_tarifas_simplificado(bruto: str | None) -> tuple[tuple[TarifaCusteioSimplificado, ...], TarifaEspessuraGrossa]:
    """Parse the stored JSON into (tiers, thick-board tariff).

    Accepts the current dict format ``{"escaloes": [...], "espessura_grossa":
    {...}}`` and the original list-only format, where the per-item urgency is
    recovered from ``urgencia_fixa`` (>=25) or ``urgencia_por_peca`` (1-24).
    Any invalid payload falls back to the defaults.
    """
    if not bruto:
        return TARIFAS_SIMPLIFICADO_PADRAO, TARIFA_ESPESSURA_GROSSA_PADRAO
    try:
        dados = json.loads(bruto)
        if isinstance(dados, dict):
            linhas = dados["escaloes"]
            grossa_bruto = dados.get("espessura_grossa") or {}
            grossa = TarifaEspessuraGrossa(
                corte_por_peca=_decimal(grossa_bruto.get("corte_por_peca", TARIFA_ESPESSURA_GROSSA_PADRAO.corte_por_peca)),
                orlagem_por_lado=_decimal(grossa_bruto.get("orlagem_por_lado", TARIFA_ESPESSURA_GROSSA_PADRAO.orlagem_por_lado)),
            )
        else:
            linhas = dados
            grossa = TARIFA_ESPESSURA_GROSSA_PADRAO
        tarifas = []
        for linha in linhas:
            if "urgencia_item" in linha:
                urgencia = _decimal(linha["urgencia_item"] or "0")
            else:
                # Old format: the fixed value (>=25) or the per-piece value
                # (1-24) becomes the once-per-item urgency.
                urgencia = _decimal(linha.get("urgencia_fixa") or linha.get("urgencia_por_peca") or "0")
            tarifas.append(TarifaCusteioSimplificado(
                minimo_pecas=int(linha["minimo_pecas"]),
                corte_por_peca=_decimal(linha["corte_por_peca"]),
                pur_4_lados=_decimal(linha["pur_4_lados"]),
                laser_4_lados=_decimal(linha["laser_4_lados"]),
                urgencia_item=urgencia,
                sem_excel_por_peca=_decimal(linha.get("sem_excel_por_peca", "0.10")),
            ))
        if [tarifa.minimo_pecas for tarifa in tarifas] != [1, 5, 15, 25]:
            raise ValueError("escaloes invalidos")
        return tuple(tarifas), grossa
    except (TypeError, ValueError, KeyError, InvalidOperation, json.JSONDecodeError):
        return TARIFAS_SIMPLIFICADO_PADRAO, TARIFA_ESPESSURA_GROSSA_PADRAO


class CusteioSimplificadoTarifasService:
    CHAVE = "custeio_simplificado_tarifas_v1"

    def __init__(self, session: Session) -> None:
        self.settings = SystemSettingService(session)

    def obter_completo(self) -> tuple[tuple[TarifaCusteioSimplificado, ...], TarifaEspessuraGrossa]:
        return parse_tarifas_simplificado(self.settings.obter_valor(self.CHAVE))

    def obter(self) -> tuple[TarifaCusteioSimplificado, ...]:
        return self.obter_completo()[0]

    def obter_espessura_grossa(self) -> TarifaEspessuraGrossa:
        return self.obter_completo()[1]

    def guardar(
        self,
        tarifas: tuple[TarifaCusteioSimplificado, ...],
        grossa: TarifaEspessuraGrossa | None = None,
    ) -> None:
        if [tarifa.minimo_pecas for tarifa in tarifas] != [1, 5, 15, 25]:
            raise ValueError("Os escalões têm de ser 1, 5, 15 e 25 peças.")
        if grossa is None:
            grossa = self.obter_espessura_grossa()
        dados = {
            "escaloes": [{
                "minimo_pecas": tarifa.minimo_pecas, "corte_por_peca": str(tarifa.corte_por_peca),
                "pur_4_lados": str(tarifa.pur_4_lados), "laser_4_lados": str(tarifa.laser_4_lados),
                "urgencia_item": str(tarifa.urgencia_item),
                "sem_excel_por_peca": str(tarifa.sem_excel_por_peca),
            } for tarifa in tarifas],
            "espessura_grossa": {
                "corte_por_peca": str(grossa.corte_por_peca),
                "orlagem_por_lado": str(grossa.orlagem_por_lado),
            },
        }
        self.settings.guardar_valor(self.CHAVE, json.dumps(dados))
