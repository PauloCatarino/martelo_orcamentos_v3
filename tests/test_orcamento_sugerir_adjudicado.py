"""Juntar uma encomenda PHC lembra que o orcamento costuma estar Adjudicado.

O problema real: quem regista a encomenda esta' a dizer que o cliente
encomendou, mas o estado ficava no que estivesse -- quase sempre "Enviado" --
porque ninguem se lembrava de o ir mudar. Depois os mapas mostravam trabalho
por fechar que ja' estava ganho.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from app.domain.orcamento_estados import (
    ESTADO_ADJUDICADO,
    ESTADO_INICIAL,
    estado_apos_encomenda_phc,
)
from app.ui.dialogs import editar_orcamento_dialog as mod
from app.ui.dialogs.editar_orcamento_dialog import (
    EditarOrcamentoDialog,
    EditarOrcamentoDialogData,
)

_app = QApplication.instance() or QApplication([])


# ---------------------------------------------------------------- a regra --
@pytest.mark.parametrize(
    "estado",
    ["Enviado", ESTADO_INICIAL, "Não Enviado", "Concluído",
     "Não Adjudicado", None, ""],
)
def test_sugere_adjudicado_a_partir_dos_estados_em_aberto(estado):
    assert estado_apos_encomenda_phc(estado) == ESTADO_ADJUDICADO


@pytest.mark.parametrize("estado", [ESTADO_ADJUDICADO, "Cancelado", "Sem Interesse"])
def test_cala_se_quando_alguem_ja_decidiu(estado):
    """Fechar o orcamento foi uma decisao; nao convidar a desfaze-la."""
    assert estado_apos_encomenda_phc(estado) is None


# ------------------------------------------------------------- o dialogo --
def _dialogo(monkeypatch, estado: str) -> EditarOrcamentoDialog:
    monkeypatch.setattr(
        EditarOrcamentoDialog, "_carregar_utilizadores", lambda _self: None
    )
    dados = EditarOrcamentoDialogData(
        obra="Obra",
        descricao="",
        localizacao="",
        ref_cliente="",
        estado=estado,
    )
    return EditarOrcamentoDialog(None, dados)


def _responder(monkeypatch, resposta) -> list[str]:
    """Substituir a caixa de pergunta e guardar o texto que ela mostraria."""
    vistos: list[str] = []

    def _pergunta(_parent, _titulo, texto, *_a, **_k):
        vistos.append(texto)
        return resposta

    monkeypatch.setattr(mod.QMessageBox, "question", staticmethod(_pergunta))
    return vistos


def test_dizer_sim_muda_o_estado_para_adjudicado(monkeypatch):
    dialog = _dialogo(monkeypatch, "Enviado")
    textos = _responder(monkeypatch, QMessageBox.StandardButton.Yes)

    dialog.nova_encomenda_input.setText("1556")
    dialog._adicionar_encomenda()

    assert dialog.estado_combo.currentText() == ESTADO_ADJUDICADO
    assert len(textos) == 1
    assert "1556" in textos[0], "a pergunta tem de dizer QUAL a encomenda"
    assert "Enviado" in textos[0] and ESTADO_ADJUDICADO in textos[0]


def test_dizer_nao_deixa_o_estado_como_estava(monkeypatch):
    dialog = _dialogo(monkeypatch, "Enviado")
    _responder(monkeypatch, QMessageBox.StandardButton.No)

    dialog.nova_encomenda_input.setText("1556")
    dialog._adicionar_encomenda()

    assert dialog.estado_combo.currentText() == "Enviado"


def test_depois_de_um_nao_nao_volta_a_insistir(monkeypatch):
    """Perguntar a cada encomenda que se juntasse seria chatice."""
    dialog = _dialogo(monkeypatch, "Enviado")
    textos = _responder(monkeypatch, QMessageBox.StandardButton.No)

    for numero in ("1556", "1557", "1558"):
        dialog.nova_encomenda_input.setText(numero)
        dialog._adicionar_encomenda()

    assert len(textos) == 1, "insistiu depois de a pessoa ter dito que nao"
    assert dialog.estado_combo.currentText() == "Enviado"


def test_ja_adjudicado_nao_pergunta_nada(monkeypatch):
    dialog = _dialogo(monkeypatch, ESTADO_ADJUDICADO)
    textos = _responder(monkeypatch, QMessageBox.StandardButton.Yes)

    dialog.nova_encomenda_input.setText("1556")
    dialog._adicionar_encomenda()

    assert textos == []


def test_encomenda_repetida_nao_pergunta(monkeypatch):
    """Se a encomenda nem chega a entrar, nao ha' nada a sugerir."""
    dialog = _dialogo(monkeypatch, "Enviado")
    _responder(monkeypatch, QMessageBox.StandardButton.No)
    dialog.nova_encomenda_input.setText("1556")
    dialog._adicionar_encomenda()

    textos = _responder(monkeypatch, QMessageBox.StandardButton.Yes)
    dialog.nova_encomenda_input.setText("1556")
    dialog._adicionar_encomenda()

    assert textos == []
    assert "já existe" in dialog.error_label.text()
