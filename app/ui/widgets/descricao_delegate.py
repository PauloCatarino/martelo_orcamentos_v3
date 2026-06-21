"""Rich-text delegate to render formatted item descriptions in a table cell."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from app.domain.descricao_format import descricao_para_html

_MARGEM = 6


class DescricaoItemDelegate(QStyledItemDelegate):
    """Paints the multi-line, formatted item description; sizes rows to content."""

    def paint(self, painter, option, index) -> None:
        texto = index.data(Qt.ItemDataRole.DisplayRole) or ""
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        doc = self._documento(texto, option.rect.width())
        painter.translate(option.rect.left() + _MARGEM, option.rect.top() + _MARGEM / 2)
        doc.drawContents(painter)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        texto = index.data(Qt.ItemDataRole.DisplayRole) or ""
        largura = option.rect.width() if option.rect.width() > 0 else 320
        doc = self._documento(texto, largura)
        return QSize(int(doc.idealWidth()) + 2 * _MARGEM, int(doc.size().height()) + _MARGEM)

    @staticmethod
    def _documento(texto: str, largura: int) -> QTextDocument:
        doc = QTextDocument()
        doc.setHtml(descricao_para_html(texto))
        doc.setTextWidth(max(40, largura - 2 * _MARGEM))
        return doc
