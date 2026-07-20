"""Fase 2B: coluna "Resolver" no diálogo "Auditar operações"."""

from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.custeio_supervisor import (
    ORIGEM_OPERACOES,
    PAGINA_MAQUINAS_TARIFAS,
    chave_menu,
)
from app.services.orcamento_item_custeio_linha_service import (
    AuditoriaOperacaoLinhaResumo,
)
from app.ui.dialogs.custeio_operacoes_auditoria_dialog import (
    CusteioOperacoesAuditoriaDialog,
)

_app = QApplication.instance() or QApplication([])


def _linha(estado: str, linha_id: int = 1) -> AuditoriaOperacaoLinhaResumo:
    return AuditoriaOperacaoLinhaResumo(
        linha_id=linha_id, ordem=1, tipo_linha="peca", codigo="CALHA_LED",
        descricao="Calha LED", operacoes_efetivas=0, origens="Peça congelada",
        maquinas="", custo_producao=Decimal("0"), estado=estado,
        diagnostico="Existem operações mas o custo de produção está a zero.",
    )


def test_botao_resolver_so_nas_linhas_nao_ok() -> None:
    dlg = CusteioOperacoesAuditoriaDialog(
        [_linha("VERIFICAR", 1), _linha("OK", 2)]
    )
    coluna = dlg.HEADERS.index("Resolver")
    assert dlg.table.cellWidget(0, coluna) is not None  # VERIFICAR -> botão
    assert dlg.table.cellWidget(1, coluna) is None       # OK -> sem botão


def test_navegar_resolver_interna_abre_linha_externa_abre_menu() -> None:
    abertos: list[int] = []
    menus: list[str] = []
    dlg = CusteioOperacoesAuditoriaDialog(
        [_linha("VERIFICAR", 7)],
        on_abrir_linha=abertos.append,
        on_navegar_menu=menus.append,
    )

    dlg._navegar_resolver(_linha("VERIFICAR", 7), ORIGEM_OPERACOES)
    assert abertos == [7] and menus == []

    dlg2 = CusteioOperacoesAuditoriaDialog(
        [_linha("VERIFICAR", 7)],
        on_abrir_linha=abertos.append,
        on_navegar_menu=menus.append,
    )
    dlg2._navegar_resolver(_linha("VERIFICAR", 7), chave_menu(PAGINA_MAQUINAS_TARIFAS))
    assert menus == [PAGINA_MAQUINAS_TARIFAS]
