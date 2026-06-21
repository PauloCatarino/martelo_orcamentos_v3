"""SQLAlchemy models package."""

from app.models.cliente import Cliente
from app.models.def_maquina import DefMaquina
from app.models.def_margem_padrao import DefMargemPadrao
from app.models.def_maquina_escalao_area import DefMaquinaEscalaoArea
from app.models.def_materia_prima import DefMateriaPrima
from app.models.def_modulo import DefModulo
from app.models.def_modulo_linha import DefModuloLinha
from app.models.def_operacao import DefOperacao
from app.models.def_peca import DefPeca
from app.models.def_peca_componente import DefPecaComponente
from app.models.def_peca_operacao import DefPecaOperacao
from app.models.def_regra_quantidade import DefRegraQuantidade
from app.models.def_valueset_chave import DefValuesetChave
from app.models.def_valueset_modelo import DefValuesetModelo
from app.models.def_valueset_modelo_linha import DefValuesetModeloLinha
from app.models.descricao_predefinida import DescricaoPredefinida
from app.models.orcamento import Orcamento
from app.models.orcamento_item import OrcamentoItem
from app.models.orcamento_item_custeio_linha import OrcamentoItemCusteioLinha
from app.models.orcamento_item_modulo import OrcamentoItemModulo
from app.models.orcamento_item_variavel import OrcamentoItemVariavel
from app.models.orcamento_item_valueset_linha import OrcamentoItemValuesetLinha
from app.models.orcamento_versao import OrcamentoVersao
from app.models.orcamento_versao_placa_nao_stock import OrcamentoVersaoPlacaNaoStock
from app.models.orcamento_valueset_linha import OrcamentoValuesetLinha
from app.models.system_setting import SystemSetting
from app.models.user import User

__all__ = [
    "Cliente",
    "DefMaquina",
    "DefMargemPadrao",
    "DefMaquinaEscalaoArea",
    "DefMateriaPrima",
    "DefModulo",
    "DefModuloLinha",
    "DefOperacao",
    "DefPeca",
    "DefPecaComponente",
    "DefPecaOperacao",
    "DefRegraQuantidade",
    "DefValuesetChave",
    "DefValuesetModelo",
    "DefValuesetModeloLinha",
    "DescricaoPredefinida",
    "Orcamento",
    "OrcamentoItem",
    "OrcamentoItemCusteioLinha",
    "OrcamentoItemModulo",
    "OrcamentoItemVariavel",
    "OrcamentoItemValuesetLinha",
    "OrcamentoVersao",
    "OrcamentoVersaoPlacaNaoStock",
    "OrcamentoValuesetLinha",
    "SystemSetting",
    "User",
]
