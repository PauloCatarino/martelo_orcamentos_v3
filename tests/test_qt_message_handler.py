"""O filtro de mensagens do Qt descarta o ruído benigno e mantém o resto."""

from __future__ import annotations

from PySide6.QtCore import QtMsgType

from app.config import qt_message_handler


def test_descarta_could_not_parse_stylesheet(capsys) -> None:
    qt_message_handler._handler(
        QtMsgType.QtWarningMsg,
        None,
        "Could not parse stylesheet of object QTableWidget(0x270ca1b34d0)",
    )
    assert capsys.readouterr().err == ""


def test_descarta_arredondamento_do_tamanho_da_janela(capsys) -> None:
    """Visto a 19-10-2026 no Novo Orçamento, ao crescer com a pasta escolhida."""
    qt_message_handler._handler(
        QtMsgType.QtWarningMsg,
        None,
        "QWindowsWindow::setGeometry: Unable to set geometry 540x664+1000+377 "
        '(frame: 556x703+992+346) on QWidgetWindow/"NovoOrcamentoDialogClassWindow" '
        'on "MSI G27CQ4 E2 (1)". Resulting geometry: 540x666+1000+377',
    )
    assert capsys.readouterr().err == ""


def test_reencaminha_outras_mensagens(capsys) -> None:
    qt_message_handler._handler(
        QtMsgType.QtWarningMsg, None, "QWidget: algum aviso mesmo a sério"
    )
    assert "algum aviso mesmo a sério" in capsys.readouterr().err
