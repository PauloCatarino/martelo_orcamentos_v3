"""Light test for the edit budget dialog (phase 9.0)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.orcamento_estados import ESTADO_INICIAL
from app.ui.dialogs.editar_orcamento_dialog import (
    EditarOrcamentoDialog,
    EditarOrcamentoDialogData,
)

_app = QApplication.instance() or QApplication([])


def test_dialog_preenche_e_devolve_os_valores() -> None:
    dados = EditarOrcamentoDialogData(
        obra="Obra Inicial",
        descricao="Descricao Inicial",
        localizacao="Local Inicial",
        ref_cliente="REF-1",
        estado="Enviado",
    )
    dialog = EditarOrcamentoDialog(None, dados)

    resultado = dialog.get_data()

    assert resultado == dados


def test_dialog_texto_vazio_vira_none_excepto_obra() -> None:
    dados = EditarOrcamentoDialogData(
        obra="Obra",
        descricao=None,
        localizacao=None,
        ref_cliente=None,
        estado=ESTADO_INICIAL,
    )
    dialog = EditarOrcamentoDialog(None, dados)

    resultado = dialog.get_data()

    assert resultado.obra == "Obra"
    assert resultado.descricao is None
    assert resultado.localizacao is None
    assert resultado.ref_cliente is None
    assert resultado.estado == ESTADO_INICIAL


def test_dialog_mostra_estado_antigo_fora_da_lista() -> None:
    dados = EditarOrcamentoDialogData(
        obra="Obra",
        descricao=None,
        localizacao=None,
        ref_cliente=None,
        estado="rascunho",
    )
    dialog = EditarOrcamentoDialog(None, dados)

    assert dialog.get_data().estado == "rascunho"
