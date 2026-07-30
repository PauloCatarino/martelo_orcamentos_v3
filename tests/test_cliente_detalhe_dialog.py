"""Ficha do cliente aberta por duplo-clique na lista."""

from __future__ import annotations

import sys
from datetime import datetime

import pytest

from app.repositories.cliente_repository import ClienteListaResumo


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _cliente(**campos) -> ClienteListaResumo:
    base = {
        "id": 1,
        "nome": "WERNAGEN - IMOBILIARIA LDA",
        "nome_simplex": "WERNAGEN",
        "morada": "RUA A",
        "email": "geral@wernagen.pt",
        "email_orcamentos": "compras@wernagen.pt",
        "email_projeto_producao": None,
        "pagina_web": None,
        "telefone": "244000000",
        "telemovel": None,
        "num_cliente_phc": "490",
        "info_1": None,
        "info_2": None,
        "is_temporary": False,
        "created_at": datetime(2026, 1, 1),
    }
    base.update(campos)
    return ClienteListaResumo(**base)


def test_so_os_emails_de_envio_sao_editaveis(_app) -> None:
    from PySide6.QtWidgets import QLineEdit

    from app.ui.dialogs.cliente_detalhe_dialog import ClienteDetalheDialog

    dialog = ClienteDetalheDialog(_cliente())

    assert dialog.ed_email_orcamentos.isReadOnly() is False
    assert dialog.ed_email_producao.isReadOnly() is False

    editaveis = [
        campo
        for campo in dialog.findChildren(QLineEdit)
        if not campo.isReadOnly()
    ]
    assert set(editaveis) == {dialog.ed_email_orcamentos, dialog.ed_email_producao}


def test_campos_trazem_os_dados_do_cliente_e_tooltips(_app) -> None:
    from app.ui.dialogs.cliente_detalhe_dialog import ClienteDetalheDialog

    dialog = ClienteDetalheDialog(_cliente())

    assert dialog.ed_email_orcamentos.text() == "compras@wernagen.pt"
    assert dialog.ed_email_producao.text() == ""
    assert "orçamento" in dialog.ed_email_orcamentos.toolTip()
    assert "projeto de produção" in dialog.ed_email_producao.toolTip()
    assert "WERNAGEN - IMOBILIARIA LDA" in dialog.windowTitle()


def test_houve_alteracoes_so_quando_muda(_app) -> None:
    from app.ui.dialogs.cliente_detalhe_dialog import ClienteDetalheDialog

    dialog = ClienteDetalheDialog(_cliente())
    assert dialog.houve_alteracoes() is False

    dialog.ed_email_producao.setText("producao@wernagen.pt")
    assert dialog.houve_alteracoes() is True
    assert dialog.email_projeto_producao() == "producao@wernagen.pt"

    dialog.ed_email_producao.setText("   ")
    assert dialog.email_projeto_producao() is None
    assert dialog.houve_alteracoes() is False


def test_ficha_abre_com_os_campos_todos_a_vista(_app) -> None:
    """A zona dos dados abre com a altura do conteúdo (scroll só como recurso)."""
    from PySide6.QtWidgets import QScrollArea

    from app.ui.dialogs.cliente_detalhe_dialog import ALTURA_MINIMA, ClienteDetalheDialog

    dialog = ClienteDetalheDialog(_cliente())
    area = dialog.findChild(QScrollArea)

    assert area.minimumHeight() >= area.widget().sizeHint().height()
    assert dialog.height() >= ALTURA_MINIMA


def test_ficha_avisa_quando_o_nome_abreviado_esta_mal(_app) -> None:
    from app.ui.dialogs.cliente_detalhe_dialog import ClienteDetalheDialog

    dialog = ClienteDetalheDialog(_cliente(nome_simplex="WERNAGEN__IMOBILIARIA_LDA"))

    avisos = [
        etiqueta
        for etiqueta in dialog.findChildren(type(dialog.status_label))
        if "caracteres" in etiqueta.text()
    ]
    assert avisos
