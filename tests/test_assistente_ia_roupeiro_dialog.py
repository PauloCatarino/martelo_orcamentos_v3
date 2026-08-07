"""Testes de interação do diálogo do piloto IA de roupeiros."""

from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QSplitter

from app.domain.roupeiro_ia import ModuloElegivel, PropostaComposicao, PropostaModulo
from app.ui.dialogs.assistente_ia_roupeiro_dialog import (
    AssistenteIaRoupeiroDialog,
    _CropLabel,
)


_app = QApplication.instance() or QApplication([])


def test_recorte_permanece_ligado_ao_pixmap_ao_redimensionar() -> None:
    preview = _CropLabel()
    preview.resize(300, 200)
    pixmap = QPixmap(100, 100)
    pixmap.fill()
    preview.setPixmap(pixmap)
    preview._selecao = QRect(10, 20, 30, 40)

    preview.resize(500, 350)
    _png, zona = preview.recorte_png()

    assert zona is not None
    assert zona.x == 0.1
    assert zona.y == 0.2
    assert zona.largura == 0.3
    assert zona.altura == 0.4


def test_dialogo_tem_duvidas_com_scroll_respostas_e_area_pdf_independente(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        AssistenteIaRoupeiroDialog,
        "_carregar_contexto_item_e_pdf",
        lambda self: None,
    )
    dialogo = AssistenteIaRoupeiroDialog(item_id=1, user_id=1)

    assert isinstance(dialogo.perguntas_text, QPlainTextEdit)
    assert dialogo.perguntas_text.isReadOnly()
    assert not dialogo.respostas_input.isReadOnly()
    assert dialogo.findChild(QSplitter) is not None


def test_remover_modulo_atualiza_composicao_sem_permitir_lista_vazia(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        AssistenteIaRoupeiroDialog,
        "_carregar_contexto_item_e_pdf",
        lambda self: None,
    )
    dialogo = AssistenteIaRoupeiroDialog(item_id=1, user_id=1)
    dialogo.catalogo = [
        ModuloElegivel(1, "M1", "Módulo 1"),
        ModuloElegivel(2, "M2", "Módulo 2"),
    ]
    dialogo.propostas = [
        PropostaComposicao(
            (
                PropostaModulo(1, "M1", "Módulo 1", 1, Decimal("0")),
                PropostaModulo(2, "M2", "Módulo 2", 2, Decimal("0")),
            ),
            90.0,
            "teste",
            Decimal("2000"),
        )
    ]
    dialogo.componentes_por_proposta = {0: [1, 2]}
    dialogo.proposta_combo.addItem("Proposta 1", 0)
    dialogo._mostrar_proposta()

    dialogo._remover_modulo(0, 0)
    assert dialogo.componentes_por_proposta[0] == [2]
    assert dialogo.modulos_table.rowCount() == 1

    dialogo._remover_modulo(0, 0)
    assert dialogo.componentes_por_proposta[0] == [2]
    assert "pelo menos um módulo" in dialogo.status_label.text()
