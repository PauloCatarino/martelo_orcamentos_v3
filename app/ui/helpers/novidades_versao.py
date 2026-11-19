"""Novidades da versão («What's New»): abrir o HTML e o aviso do 1.º arranque.

Pedido do Paulo (19-11-2026): como nos programas a sério, depois de instalar uma
versão nova, o Martelo mostra no 1.º arranque «O Martelo foi atualizado — ver as
novidades», e o botão abre no navegador o HTML que está na pasta dos instaladores
(subpasta ``Novidades``). Quem saltou versões vê as de todas as que saltou.

A versão cujas novidades já se mostraram fica neste PC (``QSettings``), como a data
do aviso da manhã. Só no Martelo instalado. A leitura da pasta do servidor corre numa
thread própria, para uma rede lenta não prender a janela.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.config.versao import version_completa
from app.core import diario_bordo
from app.domain import novidades_versao

_ORG = "Lanca Encanto"
_APP = "Martelo Orcamentos V3"
CHAVE_ULTIMA_VISTA = "novidades/ultima_versao_vista"

#: Espera depois de abrir o Martelo (antes dos avisos do PHC, aos 30 s).
ATRASO_ARRANQUE_MS = 15 * 1000
#: Se houver outra caixa aberta, tenta-se outra vez daqui a pouco.
ATRASO_REPETIR_MS = 60 * 1000

TITULO = "Martelo atualizado"


def ler_ultima_vista() -> str | None:
    try:
        valor = QSettings(_ORG, _APP).value(CHAVE_ULTIMA_VISTA)
    except Exception:  # noqa: BLE001 - sem registo, mostra-se na mesma
        return None
    return str(valor) if valor else None


def guardar_ultima_vista(versao: str) -> None:
    try:
        QSettings(_ORG, _APP).setValue(CHAVE_ULTIMA_VISTA, versao)
    except Exception:  # noqa: BLE001 - não vale a pena falhar por isto
        pass


def abrir_novidades(parent: QWidget | None, caminho: Path | None) -> bool:
    """Abre o HTML (ou PDF) das novidades no programa do Windows (o navegador)."""
    if caminho is None:
        return False
    if QDesktopServices.openUrl(QUrl.fromLocalFile(str(caminho))):
        diario_bordo.registar_acao("Abriu as novidades da versão", caminho.name)
        return True
    QMessageBox.warning(
        parent,
        "Novidades do Martelo",
        f"Não foi possível abrir as novidades:\n{caminho}\n\nVerifique a ligação ao servidor.",
    )
    return False


def _ler_novidades() -> tuple[Path | None, list]:
    from app.db.session import SessionLocal
    from app.services.atualizacao_service import AtualizacaoService, listar_novidades

    with SessionLocal() as session:
        pasta = AtualizacaoService(session).pasta()
    return pasta, (listar_novidades(pasta) if pasta else [])


class _Leitura(QObject):
    """Vive na thread de trabalho: lê a pasta das novidades."""

    lido = Signal(object)  # (pasta, [Novidades])
    falhou = Signal(str)

    def __init__(self, ler: Callable[[], tuple]) -> None:
        super().__init__()
        self._ler = ler

    @Slot()
    def ler(self) -> None:
        try:
            resultado = self._ler()
        except Exception as erro:  # noqa: BLE001 - rede/base são externas
            self.falhou.emit(str(erro))
            return
        self.lido.emit(resultado)


class NovidadesAposAtualizar(QObject):
    """No 1.º arranque de uma versão nova, oferece as novidades."""

    pedir_leitura = Signal()

    def __init__(
        self,
        janela: QWidget | None = None,
        *,
        ativo: bool | None = None,
        instalada: Callable[[], str] = version_completa,
        ler: Callable[[], tuple] = _ler_novidades,
        ler_ultima: Callable[[], str | None] = ler_ultima_vista,
        guardar_ultima: Callable[[str], None] = guardar_ultima_vista,
        abrir: Callable[[QWidget | None, Path], bool] = abrir_novidades,
        perguntar: Callable[[QWidget | None, str, list], bool] | None = None,
    ) -> None:
        super().__init__(janela)
        # Só no Martelo instalado: a correr do código-fonte não se instala nada.
        self.ativo = bool(getattr(sys, "frozen", False)) if ativo is None else ativo
        self._janela = janela
        self._instalada = instalada
        self._ler_ultima = ler_ultima
        self._guardar_ultima = guardar_ultima
        self._abrir = abrir
        self._perguntar = perguntar or perguntar_ver_novidades

        self._thread = QThread(self)
        self._leitura = _Leitura(ler)
        self._leitura.moveToThread(self._thread)
        self.pedir_leitura.connect(self._leitura.ler)
        self._leitura.lido.connect(self._ao_ler)
        self._leitura.falhou.connect(self._ao_falhar)
        if self.ativo and novidades_versao.ha_versao_nova_instalada(
            self._ler_ultima(), self._instalada()
        ):
            self._thread.start()
            aplicacao = QApplication.instance()
            if aplicacao is not None:
                aplicacao.aboutToQuit.connect(self.parar)
            QTimer.singleShot(ATRASO_ARRANQUE_MS, self.verificar)

    @Slot()
    def verificar(self) -> None:
        if QApplication.activeModalWidget() is not None:
            QTimer.singleShot(ATRASO_REPETIR_MS, self.verificar)
            return
        self.pedir_leitura.emit()

    @Slot(object)
    def _ao_ler(self, resultado: tuple) -> None:
        _pasta, todas = resultado
        instalada = self._instalada()
        por_versao = {n.versao: n for n in todas}
        versoes = novidades_versao.versoes_por_mostrar(
            list(por_versao), self._ler_ultima(), instalada
        )
        if not versoes:
            # Ainda não há novidades desta versão no servidor: tenta-se no próximo
            # arranque (não se marca como vista).
            return
        if QApplication.activeModalWidget() is not None:
            QTimer.singleShot(ATRASO_REPETIR_MS, self.verificar)
            return
        lista = [por_versao[v] for v in versoes]
        self._guardar_ultima(instalada)
        diario_bordo.registar_acao("Aviso de novidades da versão", ", ".join(versoes))
        if self._perguntar(self._janela, instalada, lista):
            for novidades in lista:
                self._abrir(self._janela, novidades.html)

    @Slot(str)
    def _ao_falhar(self, erro: str) -> None:
        diario_bordo.registar_erro(f"{TITULO}: não foi possível ver as novidades", erro)

    @Slot()
    def parar(self) -> None:
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)


def perguntar_ver_novidades(parent: QWidget | None, instalada: str, lista: list) -> bool:
    """A caixa do 1.º arranque. True = «Ver as novidades»."""
    caixa = QMessageBox(parent)
    caixa.setIcon(QMessageBox.Icon.Information)
    caixa.setWindowTitle(TITULO)
    caixa.setText(f"O Martelo foi atualizado para a versão {instalada}.")
    versoes = ", ".join(n.versao for n in lista)
    caixa.setInformativeText(
        f"Quer ver o que mudou? (novidades da {versoes})\n\n"
        "Abre-se no navegador. Cada alteração começa pela área — Orçamentos, Produção "
        "ou Geral — para ler só o que lhe interessa.\n\n"
        "Pode vê-las mais tarde em Ajuda → «Novidades das versões»."
    )
    ver = caixa.addButton("Ver as novidades", QMessageBox.ButtonRole.AcceptRole)
    ver.setToolTip("Abrir no navegador o que mudou nesta versão")
    depois = caixa.addButton("Agora não", QMessageBox.ButtonRole.RejectRole)
    depois.setToolTip("Fechar; as novidades ficam em Ajuda → «Novidades das versões»")
    # Aparece sozinha: um Enter de quem estava a escrever não abre o navegador.
    caixa.setDefaultButton(depois)
    caixa.setEscapeButton(depois)
    caixa.exec()
    return caixa.clickedButton() is ver


def botao_ver_novidades(caixa: QMessageBox, versao: str | None, caminho: Path | None):
    """Acrescenta a uma caixa de «instalar» o botão «Ver as novidades da X» (ou None)."""
    if caminho is None:
        return None
    botao = caixa.addButton(
        f"Ver as novidades da {versao}", QMessageBox.ButtonRole.HelpRole
    )
    botao.setToolTip("Abrir no navegador o que muda nesta versão, antes de instalar")
    return botao
