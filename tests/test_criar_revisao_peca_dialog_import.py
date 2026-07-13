"""Import and behavior checks for the piece-revision confirmation dialog."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.repositories.def_peca_repository import DefPecaResumo
from app.services.def_peca_revisao_service import PrepararRevisaoPecaResult

_app = QApplication.instance() or QApplication([])


def test_criar_revisao_dialog_apresenta_codigo_e_impacto() -> None:
    from app.ui.dialogs.criar_revisao_peca_dialog import CriarRevisaoPecaDialog

    peca = DefPecaResumo(
        id=1,
        codigo="PORTA",
        nome="Porta",
        descricao=None,
        grupo="PORTAS",
        tipo_peca="SIMPLES",
        ativo=True,
        revisao_numero=1,
    )
    preparacao = PrepararRevisaoPecaResult(
        peca_id=1,
        codigo_atual="PORTA",
        revisao_atual=1,
        proxima_revisao=2,
        codigo_sugerido="PORTA_R2",
        operacoes_a_copiar=3,
        componentes_a_copiar=2,
    )
    dialog = CriarRevisaoPecaDialog(peca, preparacao)

    assert dialog.codigo_input.text() == "PORTA_R2"
    assert dialog.nome_input.text() == "Porta"
    assert "3 operação" in dialog.findChild(type(dialog.erro_label), "criarRevisaoImpacto").text()
    assert dialog.form_data().codigo == "PORTA_R2"
