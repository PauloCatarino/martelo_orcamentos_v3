"""Rich-text delegate to render formatted item descriptions in a table cell."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAbstractTextDocumentLayout, QPalette, QTextDocument
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from app.domain.descricao_format import descricao_para_html

_MARGEM = 6


class DescricaoItemDelegate(QStyledItemDelegate):
    """Paints the multi-line, formatted item description; sizes rows to content."""

    def paint(self, painter, option, index) -> None:
        texto = index.data(Qt.ItemDataRole.DisplayRole) or ""
        selecionado = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.save()
        if selecionado:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            fundo = index.data(Qt.ItemDataRole.BackgroundRole)
            if fundo is not None:
                painter.fillRect(option.rect, fundo)
        doc = self._documento(texto, option.rect.width(), com_cor=not selecionado)
        painter.translate(option.rect.left() + _MARGEM, option.rect.top() + _MARGEM / 2)
        contexto = QAbstractTextDocumentLayout.PaintContext()
        cor = option.palette.highlightedText() if selecionado else option.palette.text()
        contexto.palette.setColor(QPalette.ColorRole.Text, cor.color())
        doc.documentLayout().draw(painter, contexto)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        texto = index.data(Qt.ItemDataRole.DisplayRole) or ""
        largura = option.rect.width() if option.rect.width() > 0 else 320
        doc = self._documento(texto, largura)
        return QSize(int(doc.idealWidth()) + 2 * _MARGEM, int(doc.size().height()) + _MARGEM)

    @staticmethod
    def _documento(texto: str, largura: int, *, com_cor: bool = True) -> QTextDocument:
        doc = QTextDocument()
        doc.setHtml(descricao_para_html(texto, com_cor=com_cor))
        doc.setTextWidth(max(40, largura - 2 * _MARGEM))
        return doc
