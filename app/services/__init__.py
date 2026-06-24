"""Service layer package."""

from app.services.cliente_phc_sync_service import (
    ClientePhcSyncService,
    ResumoSincronizacaoPHC,
)
from app.services.cliente_temporario_service import (
    ClienteEmUsoError,
    ClienteTemporarioService,
    DadosClienteTemporario,
)
from app.services.def_maquina_service import CriarDefMaquinaData, DefMaquinaService, EditarDefMaquinaData
from app.services.def_margem_padrao_service import (
    CriarMargemPadraoData,
    DefMargemPadraoService,
    EditarMargemPadraoData,
)
from app.services.def_operacao_service import (
    CriarDefOperacaoData,
    DefOperacaoService,
    EditarDefOperacaoData,
)
from app.services.def_peca_service import CriarDefPecaData, DefPecaService, EditarDefPecaData
from app.services.def_peca_componente_service import (
    CriarDefPecaComponenteData,
    DefPecaComponenteService,
    EditarDefPecaComponenteData,
)
from app.services.descricao_predefinida_service import DescricaoPredefinidaService
from app.services.orcamento_item_modulo_service import (
    CriarOrcamentoItemModuloSimplesData,
    EditarOrcamentoItemModuloSimplesData,
    OrcamentoItemModuloService,
)
from app.services.orcamento_item_service import (
    CriarOrcamentoItemSimplesData,
    EditarOrcamentoItemSimplesData,
    OrcamentoItemService,
)
from app.services.orcamento_service import CriarOrcamentoSimplesData, OrcamentoService
from app.services.placas_referencias_service import LinhaReferencia, listar_referencias
from app.services.producao_pastas_service import (
    PRODUCAO_BASE_PATH_DEFAULT,
    PRODUCAO_BASE_PATH_KEY,
    arvore_pastas_processo,
    caminho_versao,
    criar_pasta_versao,
    resolver_base_dir,
    segmentos_pasta,
    sugerir_proxima_versao_obra,
    sugerir_proxima_versao_plano,
)
from app.services.producao_service import (
    criar_nova_versao,
    gerar_nome_enc_imos_ix,
    gerar_nome_plano_cut_rite,
    listar_versoes_processo,
    preparar_nova_versao,
)
from app.services.relatorio_consumos_service import RelatorioConsumosService
from app.services.system_setting_service import SystemSettingService

__all__ = [
    "ClienteEmUsoError",
    "ClientePhcSyncService",
    "ClienteTemporarioService",
    "CriarDefMaquinaData",
    "CriarDefOperacaoData",
    "CriarDefPecaData",
    "CriarMargemPadraoData",
    "CriarDefPecaComponenteData",
    "CriarOrcamentoItemModuloSimplesData",
    "CriarOrcamentoItemSimplesData",
    "CriarOrcamentoSimplesData",
    "DadosClienteTemporario",
    "DefMaquinaService",
    "DefMargemPadraoService",
    "DefOperacaoService",
    "DefPecaComponenteService",
    "DefPecaService",
    "DescricaoPredefinidaService",
    "EditarDefMaquinaData",
    "EditarDefOperacaoData",
    "EditarMargemPadraoData",
    "EditarDefPecaComponenteData",
    "EditarDefPecaData",
    "EditarOrcamentoItemModuloSimplesData",
    "EditarOrcamentoItemSimplesData",
    "LinhaReferencia",
    "listar_referencias",
    "OrcamentoItemModuloService",
    "OrcamentoItemService",
    "OrcamentoService",
    "PRODUCAO_BASE_PATH_DEFAULT",
    "PRODUCAO_BASE_PATH_KEY",
    "RelatorioConsumosService",
    "ResumoSincronizacaoPHC",
    "SystemSettingService",
    "arvore_pastas_processo",
    "caminho_versao",
    "criar_nova_versao",
    "criar_pasta_versao",
    "gerar_nome_enc_imos_ix",
    "gerar_nome_plano_cut_rite",
    "listar_versoes_processo",
    "preparar_nova_versao",
    "resolver_base_dir",
    "segmentos_pasta",
    "sugerir_proxima_versao_obra",
    "sugerir_proxima_versao_plano",
]
