"""Persistence of simplified-costing tariffs in system settings."""

from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.custeio_simplificado import TARIFAS_SIMPLIFICADO_PADRAO, TarifaCusteioSimplificado
from app.services.system_setting_service import SystemSettingService


class CusteioSimplificadoTarifasService:
    CHAVE = "custeio_simplificado_tarifas_v1"

    def __init__(self, session: Session) -> None:
        self.settings = SystemSettingService(session)

    def obter(self) -> tuple[TarifaCusteioSimplificado, ...]:
        bruto = self.settings.obter_valor(self.CHAVE)
        if not bruto:
            return TARIFAS_SIMPLIFICADO_PADRAO
        try:
            dados = json.loads(bruto)
            tarifas = tuple(TarifaCusteioSimplificado(
                minimo_pecas=int(linha["minimo_pecas"]), corte_por_peca=Decimal(str(linha["corte_por_peca"])),
                pur_4_lados=Decimal(str(linha["pur_4_lados"])), laser_4_lados=Decimal(str(linha["laser_4_lados"])),
                urgencia_por_peca=Decimal(str(linha["urgencia_por_peca"])) if linha.get("urgencia_por_peca") is not None else None,
                urgencia_fixa=Decimal(str(linha["urgencia_fixa"])) if linha.get("urgencia_fixa") is not None else None,
                sem_excel_por_peca=Decimal(str(linha.get("sem_excel_por_peca", "0.10"))),
            ) for linha in dados)
            if [tarifa.minimo_pecas for tarifa in tarifas] != [1, 5, 15, 25]:
                raise ValueError("escaloes invalidos")
            return tarifas
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            return TARIFAS_SIMPLIFICADO_PADRAO

    def guardar(self, tarifas: tuple[TarifaCusteioSimplificado, ...]) -> None:
        if [tarifa.minimo_pecas for tarifa in tarifas] != [1, 5, 15, 25]:
            raise ValueError("Os escalões têm de ser 1, 5, 15 e 25 peças.")
        dados = [{
            "minimo_pecas": tarifa.minimo_pecas, "corte_por_peca": str(tarifa.corte_por_peca),
            "pur_4_lados": str(tarifa.pur_4_lados), "laser_4_lados": str(tarifa.laser_4_lados),
            "urgencia_por_peca": str(tarifa.urgencia_por_peca) if tarifa.urgencia_por_peca is not None else None,
            "urgencia_fixa": str(tarifa.urgencia_fixa) if tarifa.urgencia_fixa is not None else None,
            "sem_excel_por_peca": str(tarifa.sem_excel_por_peca),
        } for tarifa in tarifas]
        self.settings.guardar_valor(self.CHAVE, json.dumps(dados))
