"""Regressão do conteúdo e leitor do piloto Centro de Ajuda."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.permission_service import DEFAULT_USER_PERMISSIONS
from app.ui.ajuda import carregar_guias
from app.ui.pages.ajuda_page import AjudaPage


_app = QApplication.instance() or QApplication([])


def test_guia_criar_orcamento_e_local_e_completo() -> None:
    guias = carregar_guias()
    guia = next(guia for guia in guias if guia.id == "criar_orcamento")

    assert guia.versao == 1
    assert len(guia.passos) == 7
    assert all(passo.imagem.is_file() for passo in guia.passos)
    assert all(len(passo.falas) == 2 for passo in guia.passos)
    assert all({fala.narrador for fala in passo.falas} == {"Marta", "João"} for passo in guia.passos)


def test_leitor_abre_guia_e_navega_com_narracao_local() -> None:
    pagina = AjudaPage()

    assert pagina.abrir_guia("criar_orcamento") is True
    assert pagina.progresso.text() == "Passo 1 de 7"
    assert pagina.repetir_audio.isEnabled() is True
    assert pagina.automatico_button.text() == "⏸ Pausar guia"

    pagina._mudar_passo(1)
    assert pagina.progresso.text() == "Passo 2 de 7"
    assert "João" in pagina.transcricao.toPlainText()
    assert pagina.automatico_button.text() == "▶ Retomar automático"
    assert pagina.abrir_guia("guia_inexistente") is False


def test_ajuda_esta_ativa_por_predefinicao() -> None:
    assert DEFAULT_USER_PERMISSIONS["menu.ajuda"] is True
