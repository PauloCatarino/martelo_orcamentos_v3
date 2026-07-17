"""Per-item summary of the Simplificado costing for the reports page.

For every item of a budget version in the SIMPLIFICADO mode it explains how
the final value was reached: total piece count, the tier applied, the split
between thin (<=19 mm) and thick (>19 mm) pieces, the cutting/edging costs
already stored on the lines and the per-item urgency / no-Excel options.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.custeio_linha_types import PECA
from app.domain.custeio_simplificado import (
    MODALIDADE_CUSTEIO_SIMPLIFICADO,
    escolher_escalao_simplificado,
    espessura_e_grossa,
    normalizar_modalidade_custeio,
    rotulo_escalao,
)
from app.domain.medidas import normalizar_numero
from app.models.orcamento_item import OrcamentoItem
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.custeio_simplificado_tarifas_service import (
    CusteioSimplificadoTarifasService,
)


@dataclass(frozen=True)
class ResumoItemSimplificado:
    """How one Simplificado item reached its production value."""

    item_nome: str
    codigo: str | None
    quantidade_item: Decimal
    total_pecas: Decimal
    pecas_finas: Decimal          # esp <= 19 mm (tier tariffs)
    pecas_grossas: Decimal        # esp > 19 mm (flat tariff)
    escalao: str                  # e.g. "5–14"
    custo_corte: Decimal
    custo_orlagem: Decimal
    urgente: bool
    custo_urgencia: Decimal
    sem_excel: bool
    custo_sem_excel: Decimal

    @property
    def total_simplificado(self) -> Decimal:
        return self.custo_corte + self.custo_orlagem + self.custo_urgencia + self.custo_sem_excel


class RelatorioSimplificadoService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.linhas = OrcamentoItemCusteioLinhaRepository(session)

    def listar_da_versao(self, orcamento_versao_id: int) -> list[ResumoItemSimplificado]:
        """Summaries of the version's SIMPLIFICADO items (ordered as the items)."""
        items = self.session.execute(
            select(OrcamentoItem)
            .where(OrcamentoItem.orcamento_versao_id == orcamento_versao_id)
            .order_by(OrcamentoItem.ordem)
        ).scalars().all()

        escaloes = CusteioSimplificadoTarifasService(self.session).obter()
        resumos: list[ResumoItemSimplificado] = []
        for item in items:
            if normalizar_modalidade_custeio(item.modalidade_custeio) != MODALIDADE_CUSTEIO_SIMPLIFICADO:
                continue
            total = Decimal("0")
            grossas = Decimal("0")
            custo_corte = Decimal("0")
            custo_orlagem = Decimal("0")
            for linha in self.linhas.list_active_by_orcamento_item(item.id):
                if linha.tipo_linha != PECA:
                    continue
                quantidade = normalizar_numero(linha.quantidade) or Decimal("0")
                total += quantidade
                if espessura_e_grossa(linha.esp_real):
                    grossas += quantidade
                custo_corte += linha.custo_corte or Decimal("0")
                custo_orlagem += linha.custo_orlagem or Decimal("0")
            tarifa = escolher_escalao_simplificado(total, escaloes)
            resumos.append(ResumoItemSimplificado(
                item_nome=item.item,
                codigo=item.codigo,
                quantidade_item=item.quantidade,
                total_pecas=total,
                pecas_finas=total - grossas,
                pecas_grossas=grossas,
                escalao=rotulo_escalao(tarifa),
                custo_corte=custo_corte,
                custo_orlagem=custo_orlagem,
                urgente=bool(item.simplificado_urgente),
                custo_urgencia=item.custo_simplificado_urgencia or Decimal("0"),
                sem_excel=bool(item.simplificado_sem_excel),
                custo_sem_excel=item.custo_simplificado_sem_excel or Decimal("0"),
            ))
        return resumos
