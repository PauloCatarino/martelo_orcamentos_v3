""""Origem dados" nos diálogos de ValueSet é só etiqueta: mudar reverte + informa."""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QComboBox

from app.ui.dialogs import orcamento_item_valueset_linha_dialog as item_mod
from app.ui.dialogs import orcamento_valueset_linha_dialog as orc_mod

_app = QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    "mod,cls_name",
    [
        (item_mod, "OrcamentoItemValuesetLinhaDialog"),
        (orc_mod, "OrcamentoValuesetLinhaDialog"),
    ],
)
def test_mudar_origem_dados_reverte_e_informa(mod, cls_name, monkeypatch) -> None:
    avisos: list = []
    monkeypatch.setattr(
        mod.QMessageBox, "information", lambda *a, **k: avisos.append(a)
    )

    combo = QComboBox()
    combo.setEditable(True)
    for origem in mod.ORIGEM_DADOS_OPCOES:
        combo.addItem(origem)
    # Simula o utilizador a mudar para MATERIA_PRIMA...
    combo.setCurrentText("MATERIA_PRIMA")
    fake = SimpleNamespace(
        origem_dados_input=combo, _origem_dados_atual="EDITADO_LOCALMENTE"
    )

    getattr(mod, cls_name)._avisar_origem_dados(fake, 0)

    # ...mas reverte para a proveniência real e mostra a mensagem de info.
    assert combo.currentText() == "EDITADO_LOCALMENTE"
    assert len(avisos) == 1
