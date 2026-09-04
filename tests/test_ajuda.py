"""A página de Ajuda: em que versão estou, e já saiu uma mais recente.

Aqui viveu um centro de guias narrados pelo motor de voz do Windows, com
transcrição e uma ficha de recolha de comentários. Foi retirado em 2026-09-04 a
pedido do Paulo — ninguém o usava. O que ficou é a única coisa que se consultava
mesmo, e é isso que estes testes guardam.
"""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.services.permission_service import DEFAULT_USER_PERMISSIONS  # noqa: E402
from app.ui.pages.ajuda_page import AjudaPage  # noqa: E402


_app = QApplication.instance() or QApplication([])


def test_a_pagina_mostra_a_versao_instalada() -> None:
    pagina = AjudaPage()

    assert hasattr(pagina, "versao_label")
    assert hasattr(pagina, "atualizar_versao_button")
    assert hasattr(pagina, "verificar_versao_button")
    # O botão de atualizar só aparece quando há mesmo versão nova.
    assert pagina.atualizar_versao_button.isVisible() is False


def test_o_guia_narrado_desapareceu() -> None:
    """Sem isto, o leitor voltava sem ninguém dar por isso numa fusão."""
    fonte = inspect.getsource(AjudaPage)

    for vestigio in (
        "QTextToSpeech",
        "abrir_guia",
        "_criar_leitor",
        "narracao",
        "transcricao",
        "feedback",
    ):
        assert vestigio not in fonte, vestigio


def test_ajuda_esta_ativa_por_predefinicao() -> None:
    assert DEFAULT_USER_PERMISSIONS["menu.ajuda"] is True
