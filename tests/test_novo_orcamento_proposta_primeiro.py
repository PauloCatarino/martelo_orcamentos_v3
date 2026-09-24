"""Novo Orçamento: primeiro a proposta no PHC, depois o «Guardar».

Pedido do Paulo (24-09-2026): já aconteceu alguém carregar logo em «Guardar»,
esquecer-se da proposta no PHC, e o orçamento ficar com um número que o PHC
não conhece — e os seguintes deixarem de bater com as propostas.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox

from app.services.registar_proposta_phc_service import (
    _obrano_do_codigo,
    aviso_guardar_sem_proposta,
)
from app.ui.dialogs import novo_orcamento_dialog as modulo
from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog


# ----- o texto do aviso -----


def test_aviso_diz_a_ordem_e_o_numero_que_vai_ser_dado() -> None:
    texto = aviso_guardar_sem_proposta(ano=2026, numero_martelo="260961", proxima_phc=961)

    assert "1.º «Criar proposta no PHC…»" in texto
    assert "2.º «Guardar»" in texto
    assert "260961" in texto
    assert "também seria a 961" in texto
    assert "À MÃO" in texto and "número 961" in texto


def test_aviso_grita_quando_os_numeros_ja_nao_batem() -> None:
    texto = aviso_guardar_sem_proposta(ano=2026, numero_martelo="260961", proxima_phc=963)

    assert "JÁ NÃO BATEM" in texto
    assert "963 (→ 260963)" in texto
    assert "também seria" not in texto


def test_aviso_sem_phc_nem_base_nao_rebenta() -> None:
    texto = aviso_guardar_sem_proposta(ano=2026, numero_martelo=None, proxima_phc=None)

    assert "Não consegui ler o PHC" in texto
    assert "com o mesmo número" in texto


def test_aviso_para_cliente_sem_numero_phc() -> None:
    texto = aviso_guardar_sem_proposta(
        ano=2026, numero_martelo="260961", proxima_phc=961, pode_criar_no_phc=False
    )

    assert "não tem nº de cliente no PHC" in texto


def test_numero_da_proposta_a_partir_do_codigo() -> None:
    assert _obrano_do_codigo(2026, "260961") == 961
    assert _obrano_do_codigo(2026, "250961") is None  # outro ano
    assert _obrano_do_codigo(2026, "abc") is None
    assert _obrano_do_codigo(2026, None) is None


# ----- a janela -----


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def dialog(_app, monkeypatch):
    janela = NovoOrcamentoDialog()
    janela._cliente_id = 1
    janela._cliente_nome = "MÓVEIS J.F. VIVA"
    janela._cliente_temporario = False
    janela._num_cliente_phc = "35"
    janela._atualizar_criar_phc_disponivel()
    monkeypatch.setattr(janela, "_numeros_em_jogo", lambda _ano: ("260961", 961))
    janela.avisos_diario = []
    monkeypatch.setattr(
        modulo.diario_bordo, "registar_aviso", lambda *a: janela.avisos_diario.append(a)
    )
    yield janela
    janela.close()


def _guardar(dialog) -> QDialogButtonBox:
    return dialog.button_box.button(QDialogButtonBox.StandardButton.Save)


def test_os_botoes_mostram_a_ordem(dialog) -> None:
    assert dialog.criar_phc_button.text().startswith("1.º")
    assert _guardar(dialog).text().startswith("2.º")
    assert "PRIMEIRO" in dialog.criar_phc_button.toolTip()
    assert "SEGUNDO" in _guardar(dialog).toolTip()


def test_orcamento_antigo_nao_tem_passo_do_phc(dialog) -> None:
    dialog.antigo_checkbox.setChecked(True)

    assert _guardar(dialog).text() == "Guardar"
    assert not dialog._form_layout.isRowVisible(dialog._phc_widget)

    dialog.antigo_checkbox.setChecked(False)
    assert _guardar(dialog).text() == "2.º Guardar"
    assert dialog._form_layout.isRowVisible(dialog._phc_widget)


def test_guardar_sem_proposta_pergunta_e_voltar_nao_guarda(dialog, monkeypatch) -> None:
    perguntas = []
    monkeypatch.setattr(
        dialog,
        "_perguntar_guardar_sem_proposta",
        lambda texto, pode: perguntas.append((texto, pode)) or False,
    )

    dialog._validate_and_accept()

    assert dialog.result() == 0
    assert len(perguntas) == 1
    assert "260961" in perguntas[0][0] and perguntas[0][1] is True
    assert "1.º Criar proposta no PHC" in dialog.error_label.text()
    assert dialog.avisos_diario == []


def test_guardar_sem_proposta_confirmado_guarda_e_fica_no_diario(dialog, monkeypatch) -> None:
    monkeypatch.setattr(dialog, "_perguntar_guardar_sem_proposta", lambda *a: True)

    dialog._validate_and_accept()

    assert dialog.result() == 1
    assert len(dialog.avisos_diario) == 1
    titulo, detalhe = dialog.avisos_diario[0]
    assert "SEM proposta" in titulo
    assert "260961" in detalhe and "961" in detalhe


def test_com_a_proposta_criada_o_guardar_nao_pergunta(dialog, monkeypatch) -> None:
    perguntas = []
    monkeypatch.setattr(
        dialog, "_perguntar_guardar_sem_proposta", lambda *a: perguntas.append(a) or False
    )
    dialog._adotar_proposta(961, 2026)

    dialog._validate_and_accept()

    assert perguntas == []
    assert dialog.result() == 1


def test_por_omissao_a_pergunta_manda_voltar(dialog, monkeypatch) -> None:
    """Enter ou Esc na pergunta = voltar, nunca guardar."""
    vistas = []

    def _exec(caixa):
        vistas.append(caixa)
        return 0

    monkeypatch.setattr(QMessageBox, "exec", _exec)

    assert dialog._perguntar_guardar_sem_proposta("texto", True) is False
    caixa = vistas[0]
    assert caixa.defaultButton().text() == "Voltar e criar a proposta no PHC"
    assert caixa.escapeButton() is caixa.defaultButton()
