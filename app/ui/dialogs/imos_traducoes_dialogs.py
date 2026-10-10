"""Janelas das traduções do iX: fechar os programas, aplicar e repor uma cópia.

Fazem parte do menu IMOS IX › Traduções do iX (ver
:mod:`app.services.imos_traducoes_service`). Nenhuma grava sem a pessoa
carregar no botão, e a que grava mostra linha a linha o que mudou.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core import diario_bordo
from app.services import imos_traducoes_service as servico
from app.ui import tema
from app.ui.icones import icone_imagem

#: De quanto em quanto tempo se volta a ver se os programas já fecharam.
INTERVALO_PROGRAMAS_MS = 1500


def estilo_ficha(fundo: str, texto: str) -> str:
    """Uma «ficha» de estado (fundo suave, texto escuro), como nas listas do Martelo."""
    return (
        f"background-color: {fundo}; color: {texto}; font-weight: bold;"
        " border-radius: 9px; padding: 2px 10px;"
    )


def _ficha(rotulo: QLabel, aberto: bool) -> None:
    rotulo.setText("aberto" if aberto else "fechado")
    rotulo.setStyleSheet(
        estilo_ficha(tema.OCRE_SUAVE, tema.OCRE_ESCURO)
        if aberto
        else estilo_ficha(tema.VERDE_SUAVE, tema.VERDE_ESCURO)
    )


class FecharProgramasDialog(QDialog):
    """Pede para fechar o iX CAD e o iX Organizer e só deixa continuar com os dois fechados."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        estado: Callable[[], dict[str, bool]] = servico.estado_programas,
        titulo_acao: str = "aplicar as traduções",
    ) -> None:
        super().__init__(parent)
        self._estado = estado
        self.setWindowTitle("Feche o iX CAD e o iX Organizer")
        self.setWindowIcon(icone_imagem("imos_ix.png"))
        self.setModal(True)
        self.setMinimumWidth(520)

        explica = QLabel(
            "O ficheiro das traduções (imos.msg) é lido pelo iX enquanto está "
            f"aberto. Para {titulo_acao}, feche estes programas — grave antes o "
            "que estiver a desenhar. Esta janela vê sozinha quando fecharem."
        )
        explica.setWordWrap(True)

        self._fichas: dict[str, QLabel] = {}
        lista = QVBoxLayout()
        for executavel, nome in servico.PROGRAMAS_IX.items():
            linha = QHBoxLayout()
            rotulo = QLabel(f"<b>{nome}</b><br><span style='color:{tema.CINZA_ESCURO}'>{executavel}</span>")
            ficha = QLabel()
            ficha.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ficha.setMinimumWidth(80)
            linha.addWidget(rotulo, 1)
            linha.addWidget(ficha)
            lista.addLayout(linha)
            self._fichas[nome] = ficha

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.setToolTip("Não mexer em nada")
        self.cancelar_button.clicked.connect(self.reject)
        self.verificar_button = QPushButton("Verificar outra vez")
        self.verificar_button.setToolTip("Ver já se o iX CAD e o Organizer continuam abertos")
        self.verificar_button.clicked.connect(self.verificar)
        self.continuar_button = QPushButton("Continuar")
        self.continuar_button.setToolTip("Só fica ativo com os dois programas fechados")
        self.continuar_button.clicked.connect(self.accept)
        botoes = QHBoxLayout()
        botoes.addStretch()
        for botao in (self.cancelar_button, self.verificar_button, self.continuar_button):
            botoes.addWidget(botao)

        layout = QVBoxLayout(self)
        layout.addWidget(explica)
        layout.addLayout(lista)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self._relogio = QTimer(self)
        self._relogio.setInterval(INTERVALO_PROGRAMAS_MS)
        self._relogio.timeout.connect(self.verificar)
        self._relogio.start()
        self.verificar()

    def verificar(self) -> bool:
        estados = self._estado()
        for nome, ficha in self._fichas.items():
            _ficha(ficha, bool(estados.get(nome)))
        abertos = [nome for nome, aberto in estados.items() if aberto]
        self.continuar_button.setEnabled(not abertos)
        self.continuar_button.setDefault(not abertos)
        if abertos:
            self.status_label.setText("À espera que feche: " + " e ".join(abertos) + ".")
            self.status_label.setStyleSheet(f"color: {tema.TEXTO_AVISO};")
        else:
            self.status_label.setText("Tudo fechado. Pode continuar.")
            self.status_label.setStyleSheet(f"color: {tema.TEXTO_OK};")
        return not abertos

    def done(self, resultado: int) -> None:  # noqa: D102 - QDialog
        self._relogio.stop()
        super().done(resultado)


def garantir_programas_fechados(parent: QWidget | None, **kwargs) -> bool:
    """True se o iX CAD e o Organizer estão (ou ficaram) fechados."""
    estado = kwargs.get("estado", servico.estado_programas)
    if not any(estado().values()):
        return True
    return FecharProgramasDialog(parent, **kwargs).exec() == QDialog.DialogCode.Accepted


class _TrabalhoAplicar(QThread):
    passo = Signal(str, str)
    terminado = Signal(object)
    falhou = Signal(str)

    def __init__(self, caminho_msg: Path, lista: servico.ListaTraducoes, parent=None) -> None:
        super().__init__(parent)
        self._caminho = caminho_msg
        self._lista = lista

    def run(self) -> None:  # noqa: D102 - QThread
        try:
            resultado = servico.aplicar(self._caminho, self._lista, ao_passo=self.passo.emit)
        except Exception as erro:  # noqa: BLE001 - tudo tem de chegar ao ecrã
            self.falhou.emit(str(erro) or erro.__class__.__name__)
        else:
            self.terminado.emit(resultado)


class AplicarTraducoesDialog(QDialog):
    """Aplica as traduções e mostra, linha a linha, o que mudou."""

    def __init__(
        self,
        caminho_msg: Path,
        lista: servico.ListaTraducoes,
        parent: QWidget | None = None,
        *,
        arrancar: bool = True,
    ) -> None:
        super().__init__(parent)
        self._caminho = Path(caminho_msg)
        self._lista = lista
        self._trabalho: _TrabalhoAplicar | None = None
        self.resultado: servico.ResultadoAplicacao | None = None
        self.erro = ""

        self.setWindowTitle("A aplicar as traduções do iX")
        self.setWindowIcon(icone_imagem("imos_ix.png"))
        self.setModal(True)
        self.setMinimumSize(720, 420)

        self.progresso = QProgressBar()
        self.progresso.setRange(0, 0)  # a correr
        self.progresso.setTextVisible(False)
        self.registo = QPlainTextEdit()
        self.registo.setReadOnly(True)
        fonte = QFont("Consolas")
        fonte.setStyleHint(QFont.StyleHint.Monospace)
        self.registo.setFont(fonte)
        self.registo.setToolTip("O que foi feito, passo a passo. Pode selecionar e copiar (Ctrl+C).")
        self.resumo_label = QLabel()
        self.resumo_label.setWordWrap(True)

        self.pasta_button = QPushButton("Abrir pasta da cópia")
        self.pasta_button.setToolTip("Abrir no Explorador a pasta do iX onde ficou a cópia do imos.msg")
        self.pasta_button.clicked.connect(self._abrir_pasta)
        self.pasta_button.setVisible(False)
        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.setToolTip("Fechar esta janela (só depois de terminar)")
        self.fechar_button.clicked.connect(self.accept)
        self.fechar_button.setEnabled(False)
        botoes = QHBoxLayout()
        botoes.addStretch()
        botoes.addWidget(self.pasta_button)
        botoes.addWidget(self.fechar_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.progresso)
        layout.addWidget(self.registo, 1)
        layout.addWidget(self.resumo_label)
        layout.addLayout(botoes)

        self._escrever(f"Excel: {lista.excel} — {len(lista.traducoes)} traduções", "ok")
        if lista.repetidas:
            self._escrever(
                "Repetidas no Excel (vale a última linha): " + ", ".join(lista.repetidas), "info"
            )
        if arrancar:
            self.arrancar()

    def arrancar(self) -> None:
        self._trabalho = _TrabalhoAplicar(self._caminho, self._lista, self)
        self._trabalho.passo.connect(self._escrever)
        self._trabalho.terminado.connect(self._terminou)
        self._trabalho.falhou.connect(self._falhou)
        self._trabalho.start()

    def _escrever(self, texto: str, tipo: str = "info") -> None:
        marca = {"ok": "✓ ", "muda": "    ", "erro": "✗ "}.get(tipo, "  ")
        self.registo.appendPlainText(marca + texto)

    def _fim(self) -> None:
        self.progresso.setRange(0, 1)
        self.progresso.setValue(1)
        self.fechar_button.setEnabled(True)
        self.fechar_button.setDefault(True)
        self.fechar_button.setFocus()

    def _terminou(self, resultado: servico.ResultadoAplicacao) -> None:
        self.resultado = resultado
        partes = [
            f"{len(resultado.alteradas)} alterada(s)",
            f"{len(resultado.certas)} já estavam certas",
        ]
        if resultado.nao_encontradas:
            partes.append(
                f"{len(resultado.nao_encontradas)} não existem no imos.msg ("
                + ", ".join(resultado.nao_encontradas)
                + ")"
            )
        texto = " · ".join(partes) + "."
        if resultado.alteradas:
            texto += " Pode voltar a abrir o iX CAD."
            self.pasta_button.setVisible(True)
        self.resumo_label.setText(texto)
        self.resumo_label.setStyleSheet(f"color: {tema.TEXTO_OK}; font-weight: bold;")
        diario_bordo.registar_acao(
            "Traduções do iX aplicadas",
            f"{len(resultado.alteradas)} alteradas; cópia: {resultado.copia or '—'}",
        )
        self._fim()

    def _falhou(self, mensagem: str) -> None:
        self.erro = mensagem
        self._escrever(mensagem, "erro")
        self.resumo_label.setText("Não foi possível aplicar as traduções. Veja o motivo acima.")
        self.resumo_label.setStyleSheet(f"color: {tema.TEXTO_ERRO}; font-weight: bold;")
        diario_bordo.registar_erro("Traduções do iX", mensagem)
        self._fim()

    def _abrir_pasta(self) -> None:
        try:
            os.startfile(str(self._caminho.parent))  # noqa: S606 - pasta do iX
        except OSError as erro:
            QMessageBox.warning(self, "Abrir pasta", f"Não foi possível abrir a pasta:\n{erro}")

    def reject(self) -> None:  # noqa: D102 - não fecha a meio da gravação
        if self._trabalho is not None and self._trabalho.isRunning():
            return
        super().reject()

    def done(self, resultado: int) -> None:  # noqa: D102 - QDialog
        if self._trabalho is not None and self._trabalho.isRunning():
            self._trabalho.wait(10_000)
        super().done(resultado)


def _tamanho(octetos: int) -> str:
    return f"{octetos / (1024 * 1024):.1f} MB".replace(".", ",")


class ReporCopiaDialog(QDialog):
    """Escolher uma cópia do imos.msg para voltar a pôr no lugar."""

    def __init__(self, caminho_msg: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._caminho = Path(caminho_msg)
        self._copias = servico.listar_copias(self._caminho)
        self.reposta: Path | None = None

        self.setWindowTitle("Repor uma cópia do imos.msg")
        self.setWindowIcon(icone_imagem("imos_ix.png"))
        self.setModal(True)
        self.setMinimumSize(640, 360)

        explica = QLabel(
            "Escolha a cópia que quer voltar a pôr no lugar do imos.msg. O "
            "ficheiro que lá está agora também fica guardado numa cópia — "
            "nenhuma cópia é apagada."
        )
        explica.setWordWrap(True)

        self.tabela = QTableWidget(len(self._copias), 3)
        self.tabela.setHorizontalHeaderLabels(["Feita em", "Tamanho", "Ficheiro"])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.horizontalHeader().setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabela.setToolTip("As cópias na pasta do iX, a mais recente em cima.")
        for linha, copia in enumerate(self._copias):
            for coluna, valor in enumerate(
                (f"{copia.modificado:%d/%m/%Y %H:%M}", _tamanho(copia.tamanho), copia.caminho.name)
            ):
                self.tabela.setItem(linha, coluna, QTableWidgetItem(valor))
        self.tabela.resizeColumnsToContents()
        if self._copias:
            self.tabela.selectRow(0)
        self.tabela.itemDoubleClicked.connect(lambda _i: self._repor())

        self.status_label = QLabel(
            "" if self._copias else "Ainda não há cópias na pasta do iX deste PC."
        )
        self.status_label.setWordWrap(True)

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.setToolTip("Não mexer em nada")
        self.cancelar_button.clicked.connect(self.reject)
        self.repor_button = QPushButton("Repor esta cópia")
        self.repor_button.setToolTip(
            "Pôr a cópia selecionada no lugar do imos.msg (pede para fechar o iX "
            "CAD e o Organizer)"
        )
        self.repor_button.setEnabled(bool(self._copias))
        self.repor_button.clicked.connect(self._repor)
        botoes = QHBoxLayout()
        botoes.addStretch()
        botoes.addWidget(self.cancelar_button)
        botoes.addWidget(self.repor_button)

        layout = QVBoxLayout(self)
        layout.addWidget(explica)
        layout.addWidget(self.tabela, 1)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

    def _repor(self) -> None:
        linha = self.tabela.currentRow()
        if not 0 <= linha < len(self._copias):
            self.status_label.setText("Escolha uma cópia na lista.")
            return
        copia = self._copias[linha]
        resposta = QMessageBox.question(
            self,
            "Repor uma cópia",
            f"Pôr a cópia de {copia.modificado:%d/%m/%Y %H:%M} no lugar do imos.msg?\n\n"
            "O ficheiro atual fica guardado numa cópia nova.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        if not garantir_programas_fechados(self, titulo_acao="repor a cópia"):
            self.status_label.setText("Cancelado: nada foi alterado.")
            return
        try:
            guardado = servico.repor_copia(self._caminho, copia.caminho)
        except servico.ErroTraducoes as erro:
            QMessageBox.warning(self, "Repor uma cópia", str(erro))
            return
        diario_bordo.registar_acao(
            "Traduções do iX: cópia reposta", f"{copia.caminho.name}; atual guardado em {guardado.name}"
        )
        self.reposta = copia.caminho
        QMessageBox.information(
            self,
            "Repor uma cópia",
            f"Cópia reposta. O ficheiro que lá estava ficou em:\n{guardado.name}",
        )
        self.accept()
