"""Serviço de resolução das pastas da exportação de orçamentos (fase 8W.4.0).

Liga as regras puras de :mod:`app.domain.export_paths` aos caminhos
configurados (``SystemSettingService``) e aos dados do orçamento/cliente
(``OrcamentoService``), devolvendo a pasta de destino no disco.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.domain import export_paths
from app.domain.relatorio_totais import calcular_totais_relatorio
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.repositories.orcamento_item_repository import OrcamentoItemRepository
from app.services.orcamento_excel_export import gerar_excel_orcamento
from app.services.orcamento_item_service import OrcamentoItemService
from app.services.orcamento_pdf_export import gerar_pdf_orcamento
from app.services.orcamento_service import OrcamentoService
from app.services.relatorio_consumos_service import RelatorioConsumosService
from app.services.resumo_custos_excel_export import (
    construir_linhas_geral,
    gerar_excel_resumo_custos,
)
from app.services.system_setting_service import SystemSettingService

_LOGO_MODELO = "LE_Logotipo.png"
_MODELO_RESUMO_CUSTOS = ("MODELO_Resumo_Custos.xlsx", "MODELO_Resumo_Custos_V2.xlsx")


class OrcamentoExportService:
    """Application service para as pastas de exportação de orçamentos."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.orcamento_service = OrcamentoService(session)
        self.settings_service = SystemSettingService(session)

    def pasta_modelos(self) -> Path | None:
        """Devolve a pasta de modelos (``Base_Dados_Orcamento``) ou None.

        None quando a chave ``pasta_base_dados_orcamento`` não está preenchida.
        """
        valor = self.settings_service.obter_valor("pasta_base_dados_orcamento")
        if not valor:
            return None

        return Path(valor)

    def resolver_pasta_versao(
        self, orcamento_versao_id: int, criar: bool = True
    ) -> Path | None:
        """Resolve (e opcionalmente cria) a pasta de destino de uma versão.

        Convenção: ``base / ano / {num}_{SIMPLEX} / versao2dig``. Reutiliza uma
        subpasta do ano que já comece por ``f"{num}_"``. Devolve None quando a
        pasta base não está configurada ou o orçamento/cliente não existe.
        """
        base = self.settings_service.obter_valor("pasta_base_orcamentos")
        if not base:
            return None

        orcamento = self.orcamento_service.get_orcamento_by_versao_id(orcamento_versao_id)
        cliente = self.orcamento_service.get_cliente_da_versao(orcamento_versao_id)
        if orcamento is None or cliente is None:
            return None

        ano_dir = Path(base) / str(orcamento.ano)
        if ano_dir.exists():
            existentes = [p.name for p in ano_dir.iterdir() if p.is_dir()]
        else:
            existentes = []

        nome = export_paths.escolher_nome_pasta(
            existentes,
            orcamento.num_orcamento,
            cliente.nome_simplex,
            cliente.nome,
        )
        destino = ano_dir / nome / export_paths.subpasta_versao(orcamento.numero_versao)

        if criar:
            destino.mkdir(parents=True, exist_ok=True)

        return destino

    def pasta_orcamento_atual(self, orcamento_versao_id: int) -> Path | None:
        """Existing budget parent folder (``{num}_*``), or None."""
        base = self.settings_service.obter_valor("pasta_base_orcamentos")
        if not base:
            return None

        orcamento = self.orcamento_service.get_orcamento_by_versao_id(
            orcamento_versao_id
        )
        if orcamento is None:
            return None

        ano_dir = Path(base) / str(orcamento.ano)
        return export_paths.encontrar_pasta_orcamento(
            ano_dir, orcamento.num_orcamento
        )

    def nome_pasta_orcamento_pretendido(
        self, orcamento_versao_id: int
    ) -> str | None:
        """Folder name matching the budget's current customer."""
        orcamento = self.orcamento_service.get_orcamento_by_versao_id(
            orcamento_versao_id
        )
        cliente = self.orcamento_service.get_cliente_da_versao(orcamento_versao_id)
        if orcamento is None or cliente is None:
            return None

        return export_paths.nome_pasta_orcamento(
            orcamento.num_orcamento,
            cliente.nome_simplex,
            cliente.nome,
        )

    def renomear_pasta_para_cliente(
        self, orcamento_versao_id: int
    ) -> tuple[Path, Path] | None:
        """Rename the budget parent folder to the current customer's SIMPLEX."""
        base = self.settings_service.obter_valor("pasta_base_orcamentos")
        if not base:
            return None

        orcamento = self.orcamento_service.get_orcamento_by_versao_id(
            orcamento_versao_id
        )
        cliente = self.orcamento_service.get_cliente_da_versao(orcamento_versao_id)
        if orcamento is None or cliente is None:
            return None

        ano_dir = Path(base) / str(orcamento.ano)
        return export_paths.renomear_pasta_orcamento(
            ano_dir,
            orcamento.num_orcamento,
            cliente.nome_simplex,
            cliente.nome,
        )

    def exportar_pdf_orcamento(self, orcamento_versao_id: int) -> Path:
        """Recalcula a versão e exporta o PDF do orçamento, devolvendo o ``Path``.

        O custeio é recalculado primeiro (o PDF lê os custos já gravados nas
        linhas) para o PDF estar sempre atual. Levanta ``ValueError`` quando a
        pasta base não está configurada ou faltam dados da versão.
        """
        RelatorioConsumosService(self.session).recalcular_versao(orcamento_versao_id)

        orcamento = self.orcamento_service.get_orcamento_by_versao_id(orcamento_versao_id)
        cliente = self.orcamento_service.get_cliente_da_versao(orcamento_versao_id)
        items = OrcamentoItemService(self.session).list_items_by_versao(orcamento_versao_id)
        if orcamento is None or cliente is None:
            raise ValueError("Orçamento ou cliente não encontrado para esta versão.")

        totais = calcular_totais_relatorio(items)

        pasta = self.resolver_pasta_versao(orcamento_versao_id, criar=True)
        if pasta is None:
            raise ValueError(
                "Defina a 'Pasta base dos Orcamentos' em Configurações → Caminhos."
            )

        logo = None
        modelos = self.pasta_modelos()
        if modelos is not None:
            candidato = modelos / _LOGO_MODELO
            if candidato.exists():
                logo = candidato

        output = pasta / (
            f"{orcamento.num_orcamento}_"
            f"{export_paths.subpasta_versao(orcamento.numero_versao)}.pdf"
        )
        gerar_pdf_orcamento(
            output,
            cliente=cliente,
            orcamento=orcamento,
            items=items,
            totais=totais,
            logo_path=logo,
        )

        return output

    def exportar_resumo_custos(self, orcamento_versao_id: int) -> Path:
        """Recalcula a versao e exporta o Excel interno de Resumo de Custos."""
        relatorio = RelatorioConsumosService(self.session)
        relatorio.recalcular_versao(orcamento_versao_id)

        orcamento = self.orcamento_service.get_orcamento_by_versao_id(
            orcamento_versao_id
        )
        if orcamento is None:
            raise ValueError("Orçamento não encontrado para esta versão.")

        resumo = relatorio.resumo_da_versao(orcamento_versao_id)
        itens = OrcamentoItemRepository(self.session).list_items_by_versao(
            orcamento_versao_id
        )
        item_qt = {item.id: (item.quantidade or Decimal("1")) for item in itens}
        linhas = OrcamentoItemCusteioLinhaRepository(
            self.session
        ).list_by_orcamento_versao(orcamento_versao_id)
        linhas_geral = construir_linhas_geral(
            [linha for linha in linhas if linha.ativo],
            item_qt,
        )

        modelos = self.pasta_modelos()
        if modelos is None:
            raise ValueError(
                "Defina a 'Pasta Base de Dados Orçamento' em Configurações → Caminhos."
            )

        modelo = next(
            (
                modelos / nome
                for nome in _MODELO_RESUMO_CUSTOS
                if (modelos / nome).exists()
            ),
            None,
        )
        if modelo is None:
            raise ValueError(
                "Modelo não encontrado: MODELO_Resumo_Custos.xlsx na pasta de modelos."
            )

        pasta = self.resolver_pasta_versao(orcamento_versao_id, criar=True)
        if pasta is None:
            raise ValueError(
                "Defina a 'Pasta base dos Orcamentos' em Configurações → Caminhos."
            )

        output = pasta / (
            f"Resumo_Custos_{orcamento.num_orcamento}_"
            f"{export_paths.subpasta_versao(orcamento.numero_versao)}.xlsx"
        )
        gerar_excel_resumo_custos(
            output,
            modelo,
            resumo=resumo,
            linhas_geral=linhas_geral,
        )

        return output

    def exportar_excel_orcamento(self, orcamento_versao_id: int) -> Path:
        """Recalcula a versão e exporta o Excel do orçamento, devolvendo o ``Path``.

        À semelhança de :meth:`exportar_pdf_orcamento`, mas grava ``.xlsx``.
        Levanta ``ValueError`` quando a pasta base não está configurada ou
        faltam dados da versão.
        """
        RelatorioConsumosService(self.session).recalcular_versao(orcamento_versao_id)

        orcamento = self.orcamento_service.get_orcamento_by_versao_id(orcamento_versao_id)
        cliente = self.orcamento_service.get_cliente_da_versao(orcamento_versao_id)
        items = OrcamentoItemService(self.session).list_items_by_versao(orcamento_versao_id)
        if orcamento is None or cliente is None:
            raise ValueError("Orçamento ou cliente não encontrado para esta versão.")

        totais = calcular_totais_relatorio(items)

        pasta = self.resolver_pasta_versao(orcamento_versao_id, criar=True)
        if pasta is None:
            raise ValueError(
                "Defina a 'Pasta base dos Orcamentos' em Configurações → Caminhos."
            )

        output = pasta / (
            f"{orcamento.num_orcamento}_"
            f"{export_paths.subpasta_versao(orcamento.numero_versao)}.xlsx"
        )
        gerar_excel_orcamento(
            output,
            cliente=cliente,
            orcamento=orcamento,
            items=items,
            totais=totais,
        )

        return output
