"""SQLAlchemy models package."""

from app.models.cliente import Cliente
from app.models.equipa_membro import EquipaMembro
from app.models.ia_perfil import IaPerfilEntrada
from app.models.def_fornecedor import DefFornecedor
from app.models.def_maquina import DefMaquina
from app.models.def_margem_padrao import DefMargemPadrao
from app.models.def_maquina_escalao_area import DefMaquinaEscalaoArea
from app.models.def_materia_prima import DefMateriaPrima
from app.models.def_materia_prima_preco_historico import DefMateriaPrimaPrecoHistorico
from app.models.def_modulo import DefModulo
from app.models.def_modulo_categoria import DefModuloCategoria
from app.models.def_modulo_linha import DefModuloLinha
from app.models.def_operacao import DefOperacao
from app.models.def_peca import DefPeca
from app.models.def_peca_componente import DefPecaComponente
from app.models.def_peca_operacao import DefPecaOperacao
from app.models.def_peca_user_pref import DefPecaUserPref
from app.models.def_regra_quantidade import DefRegraQuantidade
from app.models.def_valueset_chave import DefValuesetChave
from app.models.def_valueset_modelo import DefValuesetModelo
from app.models.def_valueset_modelo_linha import DefValuesetModeloLinha
from app.models.def_valueset_modelo_linha_operacao import DefValuesetModeloLinhaOperacao
from app.models.descricao_predefinida import DescricaoPredefinida
from app.models.orcamento import Orcamento
from app.models.orcamento_item import OrcamentoItem
from app.models.orcamento_item_custeio_linha import OrcamentoItemCusteioLinha
from app.models.orcamento_item_custeio_linha_operacao import OrcamentoItemCusteioLinhaOperacao
from app.models.orcamento_item_modulo import OrcamentoItemModulo
from app.models.orcamento_item_variavel import OrcamentoItemVariavel
from app.models.orcamento_item_valueset_linha import OrcamentoItemValuesetLinha
from app.models.orcamento_item_valueset_linha_operacao import (
    OrcamentoItemValuesetLinhaOperacao,
)
from app.models.orcamento_tempo_atividade import OrcamentoTempoAtividade
from app.models.orcamento_versao import OrcamentoVersao
from app.models.orcamento_versao_encomenda_phc import OrcamentoVersaoEncomendaPhc
from app.models.orcamento_versao_evento import OrcamentoVersaoEvento
from app.models.orcamento_versao_placa_nao_stock import OrcamentoVersaoPlacaNaoStock
from app.models.orcamento_valueset_linha import OrcamentoValuesetLinha
from app.models.orcamento_valueset_linha_operacao import OrcamentoValuesetLinhaOperacao
from app.models.producao import Producao
from app.models.producao_ocorrencia import ProducaoOcorrencia
from app.models.producao_ocorrencia_anexo import ProducaoOcorrenciaAnexo
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.models.user_permission import UserPermission
from app.models.user_pref import UserPref
from app.models.lista_material_assistente import (
    ListaMaterialAliasPlaca,
    ListaMaterialBarraReceita,
    ListaMaterialCncOperacao,
    ListaMaterialExecucao,
    ListaMaterialModulo,
    ListaMaterialObraConfig,
    ListaMaterialPdfDocumento,
    ListaMaterialPdfExportacao,
    ListaMaterialPdfPreset,
    ListaMaterialPerfil,
    ListaMaterialPlacaSnapshot,
    ListaMaterialRelacaoOrla,
    ListaMaterialSugestao,
)

__all__ = [
    "Cliente",
    "EquipaMembro",
    "DefMaquina",
    "DefMargemPadrao",
    "DefMaquinaEscalaoArea",
    "DefFornecedor",
    "DefMateriaPrima",
    "DefMateriaPrimaPrecoHistorico",
    "DefModulo",
    "DefModuloCategoria",
    "DefModuloLinha",
    "DefOperacao",
    "DefPeca",
    "DefPecaComponente",
    "DefPecaOperacao",
    "DefPecaUserPref",
    "DefRegraQuantidade",
    "DefValuesetChave",
    "DefValuesetModelo",
    "DefValuesetModeloLinha",
    "DefValuesetModeloLinhaOperacao",
    "DescricaoPredefinida",
    "Orcamento",
    "OrcamentoItem",
    "OrcamentoItemCusteioLinha",
    "OrcamentoItemCusteioLinhaOperacao",
    "OrcamentoItemModulo",
    "OrcamentoItemVariavel",
    "OrcamentoItemValuesetLinha",
    "OrcamentoItemValuesetLinhaOperacao",
    "OrcamentoTempoAtividade",
    "OrcamentoVersao",
    "OrcamentoVersaoEncomendaPhc",
    "OrcamentoVersaoEvento",
    "OrcamentoVersaoPlacaNaoStock",
    "OrcamentoValuesetLinha",
    "OrcamentoValuesetLinhaOperacao",
    "IaPerfilEntrada",
    "Producao",
    "ProducaoOcorrencia",
    "ProducaoOcorrenciaAnexo",
    "SystemSetting",
    "User",
    "UserPermission",
    "UserPref",
    "ListaMaterialAliasPlaca",
    "ListaMaterialBarraReceita",
    "ListaMaterialCncOperacao",
    "ListaMaterialExecucao",
    "ListaMaterialModulo",
    "ListaMaterialObraConfig",
    "ListaMaterialPdfDocumento",
    "ListaMaterialPdfExportacao",
    "ListaMaterialPdfPreset",
    "ListaMaterialPerfil",
    "ListaMaterialPlacaSnapshot",
    "ListaMaterialRelacaoOrla",
    "ListaMaterialSugestao",
]
