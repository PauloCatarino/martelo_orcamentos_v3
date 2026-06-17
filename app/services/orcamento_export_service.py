"""Serviço de resolução das pastas da exportação de orçamentos (fase 8W.4.0).

Liga as regras puras de :mod:`app.domain.export_paths` aos caminhos
configurados (``SystemSettingService``) e aos dados do orçamento/cliente
(``OrcamentoService``), devolvendo a pasta de destino no disco.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.domain import export_paths
from app.services.orcamento_service import OrcamentoService
from app.services.system_setting_service import SystemSettingService


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
