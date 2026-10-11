"""Botão «Descrições…» ao lado de um campo de texto livre do orçamento.

Os campos Info 1 e Info 2 servem quase sempre para dizer os materiais do
orçamento ("INTERIORES MLM LINHO CANCUN", "FRENTES MDF BRANCO"). Esses textos
já estão escritos nas descrições pré-definidas que se usam nos items: este
botão abre o mesmo menu e acrescenta ao campo as descrições marcadas.

Ao contrário da descrição do item, no Info vão linhas simples — sem o
tabulador nem o marcador ("-" / "*") — porque é assim que se escreve lá e é
o texto que aparece na coluna da lista de orçamentos.
"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def linhas_para_info(entries: Iterable) -> list[str]:
    """Texto de cada descrição escolhida, uma por linha, sem marcador."""
    linhas: list[str] = []
    for entry in entries:
        texto = " ".join((getattr(entry, "texto", "") or "").split())
        if texto:
            linhas.append(texto)
    return linhas


def acrescentar_linhas(campo: QTextEdit, linhas: Iterable[str]) -> int:
    """Acrescentar ``linhas`` no fim do campo; devolve quantas entraram.

    Uma linha que o campo já tenha (sem olhar a maiúsculas) não se repete:
    quem volta ao menu para juntar mais um material não fica com os outros
    em duplicado.
    """
    existente = campo.toPlainText()
    ja_tem = {linha.strip().casefold() for linha in existente.splitlines()}
    novas: list[str] = []
    for linha in linhas:
        chave = linha.strip().casefold()
        if not chave or chave in ja_tem:
            continue
        ja_tem.add(chave)
        novas.append(linha.strip())
    if not novas:
        return 0
    cursor = campo.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    if existente.strip() and not existente.endswith("\n"):
        cursor.insertText("\n")
    cursor.insertText("\n".join(novas))
    campo.setTextCursor(cursor)
    return len(novas)


def campo_com_descricoes(
    campo: QTextEdit, destino: str
) -> tuple[QWidget, QPushButton]:
    """Embrulhar ``campo`` com o botão «Descrições…» à direita.

    Devolve ``(widget a pôr no formulário, botão)``. ``destino`` é o nome do
    campo tal como aparece no formulário ("Info 1"): vai para o título do
    menu e para as dicas, para se saber onde as linhas vão entrar.
    """
    botao = QPushButton("Descrições…")
    botao.setToolTip(
        f"Abrir as descrições pré-definidas (as mesmas dos items) e "
        f"acrescentar as que marcar ao {destino}, uma por linha.\n"
        "Útil para indicar os materiais do orçamento sem os escrever à mão."
    )
    # Sem isto, com o foco no botão, o Enter reabria o menu em vez de gravar.
    botao.setAutoDefault(False)
    botao.clicked.connect(lambda: abrir_descricoes_para(campo, destino))

    coluna_botao = QVBoxLayout()
    coluna_botao.setContentsMargins(0, 0, 0, 0)
    coluna_botao.addWidget(botao)
    coluna_botao.addStretch()

    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(campo, stretch=1)
    layout.addLayout(coluna_botao)
    layout.setAlignment(coluna_botao, Qt.AlignmentFlag.AlignTop)
    return widget, botao


def abrir_descricoes_para(campo: QTextEdit, destino: str) -> int:
    """Abrir o menu de descrições e acrescentar as marcadas a ``campo``."""
    from app.core.session import app_session
    from app.ui.dialogs.descricoes_predefinidas_dialog import (
        DescricoesPredefinidasDialog,
    )

    janela = campo.window()
    user = app_session.current_user
    user_id = user.id if user is not None else None
    if user_id is None:
        QMessageBox.warning(
            janela,
            "Descrições pré-definidas",
            "Utilizador não identificado: as descrições são de cada utilizador.",
        )
        return 0
    dialog = DescricoesPredefinidasDialog(janela, user_id=user_id, destino=destino)
    if not dialog.exec():
        return 0
    inseridas = acrescentar_linhas(campo, linhas_para_info(dialog.checked_entries()))
    campo.setFocus()
    return inseridas
