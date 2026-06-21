"""Application dialogs package."""

from app.ui.dialogs.descricoes_predefinidas_dialog import DescricoesPredefinidasDialog
from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialog, NovaDefPecaDialogData
from app.ui.dialogs.novo_item_dialog import NovoItemDialog, NovoItemDialogData
from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog, NovoOrcamentoDialogData
from app.ui.dialogs.selecionar_cliente_dialog import SelecionarClienteDialog

__all__ = [
    "DescricoesPredefinidasDialog",
    "NovaDefPecaDialog",
    "NovaDefPecaDialogData",
    "NovoItemDialog",
    "NovoItemDialogData",
    "NovoOrcamentoDialog",
    "NovoOrcamentoDialogData",
    "SelecionarClienteDialog",
]
