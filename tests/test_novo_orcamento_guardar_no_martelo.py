"""Criar a proposta no PHC não cria o orçamento no Martelo.

Já aconteceu: alguém cria a proposta no PHC, vê a caixa a dizer que correu bem
e fecha a janela — a pensar que o PHC tratou dos dois lados. Fica com a
proposta lá e sem orçamento cá.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox

from app.ui.dialogs import novo_orcamento_dialog as modulo
from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def dialog(_app):
    janela = NovoOrcamentoDialog()
    yield janela
    janela.close()


def test_ao_adotar_a_proposta_o_botao_guardar_pede_a_atencao(dialog) -> None:
    dialog._proposta_phc = "877"
    dialog._realcar_guardar()

    guardar = dialog.button_box.button(QDialogButtonBox.StandardButton.Save)

    assert guardar.text() == "Guardar no Martelo"
    assert "Martelo" in guardar.toolTip()
    assert "só fica no Martelo" in dialog.error_label.text()


def test_sair_com_proposta_criada_e_nada_guardado_pergunta(
    monkeypatch, dialog
) -> None:
    perguntas: list[str] = []

    def _perguntar(_pai, _titulo, texto, *args, **kwargs):
        perguntas.append(texto)
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(modulo.QMessageBox, "question", _perguntar)
    dialog._proposta_phc = "877"

    dialog.reject()

    assert len(perguntas) == 1
    assert "877" in perguntas[0]
    assert "ainda não existe no Martelo" in perguntas[0]
    # Respondeu "não": não se aceitou nem se rejeitou nada.
    assert dialog.result() == 0


def test_sem_proposta_no_phc_o_cancelar_fecha_logo(monkeypatch, dialog) -> None:
    perguntas: list[str] = []
    monkeypatch.setattr(
        modulo.QMessageBox,
        "question",
        lambda *a, **k: perguntas.append(1),
    )

    dialog.reject()

    assert perguntas == []


def test_a_mensagem_de_proposta_criada_avisa_que_falta_guardar() -> None:
    """O texto que aparece a seguir a criar a proposta no PHC."""
    import inspect

    fonte = inspect.getsource(NovoOrcamentoDialog._criar_proposta_phc)

    assert "Falta guardar no Martelo" in fonte
    assert "_realcar_guardar()" in fonte
