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


def test_reencaminha_outras_mensagens(capsys) -> None:
    qt_message_handler._handler(
        QtMsgType.QtWarningMsg, None, "QWidget: algum aviso mesmo a sério"
    )
    assert "algum aviso mesmo a sério" in capsys.readouterr().err
