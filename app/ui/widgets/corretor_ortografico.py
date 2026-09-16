"""Sublinhado vermelho e sugestões no botão direito, como no Word.

Liga-se a qualquer caixa de texto de várias linhas::

    ligar_corretor(self.descricao_input)

O sublinhado é só visual (formatação do ``QSyntaxHighlighter``): não entra no
texto gravado, nem no HTML do email.
"""

from __future__ import annotations

import weakref

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QMenu, QMessageBox, QPlainTextEdit, QTextEdit

from app.domain.ortografia import palavra_em, palavras_a_verificar
from app.services.corretor_ortografico_service import Corretor, corretor

COR_SUBLINHADO = QColor("#D32F2F")

#: Os realces vivos — para voltar a pintar tudo quando alguém acrescenta uma
#: palavra ao dicionário (senão continuava sublinhada nas outras caixas).
_realces: "weakref.WeakSet[RealceOrtografico]" = weakref.WeakSet()


class RealceOrtografico(QSyntaxHighlighter):
    """Pinta com ondulado vermelho as palavras que o corretor não conhece."""

    def __init__(self, documento, obter_corretor=corretor) -> None:
        super().__init__(documento)
        self._obter_corretor = obter_corretor
        self._formato = QTextCharFormat()
        self._formato.setUnderlineStyle(
            QTextCharFormat.UnderlineStyle.SpellCheckUnderline
        )
        self._formato.setUnderlineColor(COR_SUBLINHADO)
        _realces.add(self)

    def highlightBlock(self, texto: str) -> None:  # noqa: N802 (Qt override)
        verificador: Corretor = self._obter_corretor()
        if not verificador.disponivel:
            return
        for palavra in palavras_a_verificar(texto):
            if not verificador.correta(palavra.texto):
                self.setFormat(palavra.inicio, palavra.tamanho, self._formato)


class _MenuCorretor(QObject):
    """Acrescenta as sugestões ao menu do botão direito."""

    def __init__(self, edit, obter_corretor=corretor) -> None:
        super().__init__(edit)
        self._edit = edit
        self._obter_corretor = obter_corretor

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 (Qt override)
        if evento.type() != QEvent.Type.ContextMenu:
            return False
        menu = self.construir_menu(evento.pos())
        if menu is None:
            return False
        menu.exec(evento.globalPos())
        menu.deleteLater()
        return True

    def construir_menu(self, posicao) -> QMenu | None:
        """O menu com as sugestões para a palavra em ``posicao`` (ou None)."""
        edit = self._edit
        if edit.isReadOnly():
            return None
        verificador = self._obter_corretor()
        if not verificador.disponivel:
            return None

        cursor = edit.cursorForPosition(posicao)
        bloco = cursor.block()
        palavra = palavra_em(bloco.text(), cursor.position() - bloco.position())
        if palavra is None or verificador.correta(palavra.texto):
            return None

        inicio = bloco.position() + palavra.inicio
        fim = bloco.position() + palavra.fim
        menu = edit.createStandardContextMenu(posicao)
        primeira = menu.actions()[0] if menu.actions() else None

        sugestoes = verificador.sugestoes(palavra.texto)
        acoes = []
        if sugestoes:
            for sugestao in sugestoes:
                acao = menu.addAction(sugestao)
                fonte = acao.font()
                fonte.setBold(True)
                acao.setFont(fonte)
                acao.triggered.connect(
                    lambda _=False, s=sugestao: self._substituir(inicio, fim, s)
                )
                acoes.append(acao)
        else:
            sem = menu.addAction("(sem sugestões)")
            sem.setEnabled(False)
            acoes.append(sem)

        adicionar = menu.addAction(f"Adicionar «{palavra.texto}» ao dicionário")
        adicionar.setToolTip(
            "A palavra passa a ser aceite para todos os utilizadores do Martelo"
        )
        adicionar.triggered.connect(lambda _=False: self._adicionar(palavra.texto))
        acoes.append(adicionar)

        separador = menu.addSeparator()
        acoes.append(separador)
        # Pôr as sugestões no topo, antes de Desfazer/Copiar/Colar.
        for acao in acoes:
            menu.removeAction(acao)
        if primeira is not None:
            menu.insertActions(primeira, acoes)
        else:
            menu.addActions(acoes)
        return menu

    def _substituir(self, inicio: int, fim: int, texto: str) -> None:
        cursor = QTextCursor(self._edit.document())
        cursor.setPosition(inicio)
        cursor.setPosition(fim, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(texto)

    def _adicionar(self, palavra: str) -> None:
        from app.core.session import app_session

        user = app_session.current_user
        try:
            self._obter_corretor().adicionar(
                palavra, getattr(user, "id", None) if user else None
            )
        except Exception as erro:  # noqa: BLE001 - base, permissões…
            QMessageBox.warning(
                self._edit,
                "Dicionário",
                f"Não foi possível acrescentar «{palavra}» ao dicionário.\n\n{erro}",
            )
            return
        repintar_todos()


def repintar_todos() -> None:
    for realce in list(_realces):
        try:
            realce.rehighlight()
        except RuntimeError:
            pass  # a caixa já foi fechada


def ligar_corretor(edit: QTextEdit | QPlainTextEdit, obter_corretor=corretor):
    """Ligar o corretor a uma caixa de texto. Devolve o realce criado.

    Nunca falha: se o corretor não existir neste PC, a caixa fica como estava.
    """
    existente = getattr(edit, "_realce_ortografico", None)
    if existente is not None:
        return existente
    try:
        verificador = obter_corretor()
        if verificador.recarregar_dicionario():
            repintar_todos()
    except Exception:  # noqa: BLE001 - o corretor é uma ajuda
        return None

    realce = RealceOrtografico(edit.document(), obter_corretor)
    menu = _MenuCorretor(edit, obter_corretor)
    edit.viewport().installEventFilter(menu)
    edit._realce_ortografico = realce  # type: ignore[attr-defined]
    edit._menu_corretor = menu  # type: ignore[attr-defined]
    edit.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
    return realce
