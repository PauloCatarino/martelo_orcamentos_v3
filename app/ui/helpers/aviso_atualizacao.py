"""Aviso da manhã: há uma versão nova do Martelo no servidor?

Pedido do Paulo (01-10-2026): até aqui, cada versão nova obrigava-o a ir dizer
a cada colega que a instalasse em Ajuda → «Atualizar agora…». Agora o próprio
Martelo avisa: dias úteis, a partir das 09h30, uma vez por dia e por PC, se a
pasta dos instaladores tiver uma versão mais recente do que a instalada,
aparece uma caixa a perguntar se quer instalar.

Nunca instala sem a pessoa carregar no botão (como o serviço, de propósito: uma
versão com um problema não pode entrar em todos os PCs sem ninguém decidir). O
botão por defeito é «Mais tarde», porque a caixa aparece sozinha e pode
apanhar um Enter de quem estava a escrever. E antes de fechar o Martelo
pergunta-se, em todos os menus, se há alterações por gravar — para ninguém
perder o que estava a fazer a meio de um orçamento ou de uma obra.

A data do último aviso fica neste PC (``QSettings``), não na base: quem usa
dois PCs tem de atualizar os dois. A leitura da pasta do servidor corre numa
thread própria, para uma rede lenta não prender a janela.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from datetime import date, datetime, time

from PySide6.QtCore import QObject, QSettings, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core import diario_bordo
from app.domain import agenda_diaria_phc
from app.services.atualizacao_service import (
    EstadoVersao,
    InstaladorIndisponivel,
    preparar_instalador_local,
)

#: A partir desta hora, uma vez por dia (dias úteis), como os outros avisos.
HORA_AVISO = time(9, 30)

#: De quanto em quanto tempo se pergunta "já são horas?" num Martelo aberto.
INTERVALO_RELOGIO_MS = 10 * 60 * 1000

#: Espera depois de abrir o Martelo: depois dos analisadores do PHC (30 s e
#: 60 s), para as caixas não aparecerem umas em cima das outras.
ATRASO_ARRANQUE_MS = 2 * 60 * 1000

#: Onde fica a data do último aviso, nas definições deste PC.
_ORG = "Lanca Encanto"
_APP = "Martelo Orcamentos V3"
CHAVE_ULTIMO_AVISO = "atualizacao/ultimo_aviso"

TITULO = "Aviso de atualizações do Martelo"


def ler_ultimo_aviso() -> date | None:
    try:
        valor = QSettings(_ORG, _APP).value(CHAVE_ULTIMO_AVISO)
    except Exception:  # noqa: BLE001 - sem registo, avisa-se na mesma
        return None
    return agenda_diaria_phc.ler_data(str(valor) if valor else None)


def guardar_ultimo_aviso(dia: date) -> None:
    try:
        QSettings(_ORG, _APP).setValue(
            CHAVE_ULTIMO_AVISO, agenda_diaria_phc.escrever_data(dia)
        )
    except Exception:  # noqa: BLE001 - não vale a pena falhar por isto
        pass


def instalar_e_fechar(
    parent: QWidget | None,
    estado: EstadoVersao,
    *,
    pode_fechar: Callable[[], bool] | None = None,
) -> bool:
    """Copiar o instalador para o PC, abri-lo e fechar o Martelo.

    ``pode_fechar`` pergunta, menu a menu, se há alterações por gravar; se a
    pessoa escolher Cancelar, não se instala nada. Devolve True quando o
    instalador ficou aberto e o Martelo vai fechar.
    """
    if estado.caminho_instalador is None:
        return False
    if pode_fechar is not None and not pode_fechar():
        return False

    # Copiar para o PC ANTES de abrir. O instalador esta' numa pasta de
    # rede, e desde que instalar passou a pedir a conta ADMIN_<pessoa> o
    # UAC eleva para ESSA conta -- que nao tem sessao no servidor de
    # ficheiros. Abrir direto da rede dava "ShellExecuteEx falhou; codigo
    # 1385", com o Martelo ja' fechado e ninguem para explicar porque'.
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        caminho = preparar_instalador_local(estado.caminho_instalador)
    except InstaladorIndisponivel as erro:
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(parent, "Atualizar o Martelo", str(erro))
        return False
    QApplication.restoreOverrideCursor()

    try:
        # ``startfile`` abre o instalador como o Windows o abriria a partir
        # do Explorador: com o utilizador normal, e o UAC a pedir permissao
        # quando for preciso. Se o abrissemos de dentro do Martelo de outra
        # maneira, o instalador herdava o que o Martelo e' -- e e' isso que
        # deixa o Outlook sem falar com o Martelo depois de instalar.
        os.startfile(str(caminho))  # noqa: S606
    except OSError as erro:
        # So' se chega aqui com o Martelo ainda aberto: nada de fechar a
        # aplicacao em cima de um erro que a pessoa ainda nao leu.
        QMessageBox.critical(
            parent,
            "Atualizar o Martelo",
            "Não foi possível abrir o instalador:\n"
            f"{caminho}\n\n{erro}\n\n"
            "Se a mensagem falar em «1385», o Windows recusou a conta de "
            "administrador. O instalador já está copiado para este PC, "
            "no caminho acima: instale-o a partir daí.",
        )
        return False

    diario_bordo.registar_acao(
        "Abriu o instalador da versão nova", f"{estado.instalada} -> {estado.disponivel}"
    )
    QGuiApplication.quit()
    return True


def perguntar_instalar(
    parent: QWidget | None, estado: EstadoVersao, trabalho_aberto: str = ""
) -> bool:
    """A caixa da manhã. True = «Instalar agora»."""
    caixa = QMessageBox(parent)
    caixa.setIcon(QMessageBox.Icon.Information)
    caixa.setWindowTitle(TITULO)
    caixa.setText(
        "Sou o aviso de atualizações do Martelo. Todos os dias úteis, a partir "
        "das 9h30, vejo se há uma versão nova no servidor.\n\n"
        f"Há a versão {estado.disponivel} (este PC tem a {estado.instalada})."
    )
    texto = (
        "Para instalar, o Martelo fecha-se e o instalador abre a seguir — pede "
        "a password de administrador, como de costume. Antes de fechar, o "
        "Martelo pergunta se quer gravar o que tiver por gravar."
    )
    if trabalho_aberto:
        texto += (
            f"\n\nEstá a trabalhar {trabalho_aberto}. Se está a meio, escolha "
            "«Mais tarde» e grave primeiro."
        )
    texto += (
        "\n\n«Mais tarde»: volto a lembrar amanhã de manhã. Também pode "
        "instalar quando quiser em Ajuda → «Atualizar agora…»."
    )
    caixa.setInformativeText(texto)
    instalar = caixa.addButton("Instalar agora", QMessageBox.ButtonRole.AcceptRole)
    instalar.setToolTip(
        f"Fechar o Martelo e instalar a versão {estado.disponivel} por cima da atual"
    )
    depois = caixa.addButton("Mais tarde", QMessageBox.ButtonRole.RejectRole)
    depois.setToolTip("Continuar a trabalhar; o aviso volta amanhã de manhã")
    # A caixa aparece sozinha: um Enter de quem estava a escrever não instala.
    caixa.setDefaultButton(depois)
    caixa.setEscapeButton(depois)
    caixa.exec()
    return caixa.clickedButton() is instalar


def _ler_estado() -> EstadoVersao:
    from app.db.session import SessionLocal
    from app.services.atualizacao_service import AtualizacaoService

    with SessionLocal() as session:
        return AtualizacaoService(session).estado()


class _TrabalhoVersao(QObject):
    """Vive na thread de trabalho: lê a pasta dos instaladores."""

    lido = Signal(object)  # EstadoVersao
    falhou = Signal(str)

    def __init__(self, ler_estado: Callable[[], EstadoVersao]) -> None:
        super().__init__()
        self._ler_estado = ler_estado

    @Slot()
    def ler(self) -> None:
        try:
            estado = self._ler_estado()
        except Exception as erro:  # noqa: BLE001 - rede/base são externas
            self.falhou.emit(str(erro))
            return
        self.lido.emit(estado)


class AvisoAtualizacao(QObject):
    """Agenda o aviso da manhã e trata da conversa com o utilizador."""

    pedir_leitura = Signal()

    def __init__(
        self,
        janela: QWidget | None = None,
        *,
        ativo: bool | None = None,
        ler_estado: Callable[[], EstadoVersao] = _ler_estado,
        pode_fechar: Callable[[], bool] | None = None,
        trabalho_aberto: Callable[[], str] | None = None,
        ler_ultimo: Callable[[], date | None] = ler_ultimo_aviso,
        guardar_ultimo: Callable[[date], None] = guardar_ultimo_aviso,
        agora: Callable[[], datetime] = datetime.now,
    ) -> None:
        super().__init__(janela)
        # Só no Martelo instalado: a correr do código-fonte não há nada a instalar.
        self.ativo = bool(getattr(sys, "frozen", False)) if ativo is None else ativo
        self._janela = janela
        self._pode_fechar = pode_fechar
        self._trabalho_aberto = trabalho_aberto
        self._ler_ultimo = ler_ultimo
        self._guardar_ultimo = guardar_ultimo
        self._agora = agora
        self._a_ler = False

        self._thread = QThread(self)
        self._trabalho = _TrabalhoVersao(ler_estado)
        self._trabalho.moveToThread(self._thread)
        self.pedir_leitura.connect(self._trabalho.ler)
        self._trabalho.lido.connect(self._ao_ler)
        self._trabalho.falhou.connect(self._ao_falhar)

        self._relogio = QTimer(self)
        self._relogio.setInterval(INTERVALO_RELOGIO_MS)
        self._relogio.timeout.connect(self.verificar_se_e_hora)
        if self.ativo:
            self._thread.start()
            aplicacao = QApplication.instance()
            if aplicacao is not None:
                aplicacao.aboutToQuit.connect(self.parar)
            self._relogio.start()
            QTimer.singleShot(ATRASO_ARRANQUE_MS, self.verificar_se_e_hora)

    @Slot()
    def verificar_se_e_hora(self) -> None:
        """Se já for hora e ainda não se avisou hoje neste PC, vai ver a pasta."""
        if not self.ativo or self._a_ler:
            return
        if not agenda_diaria_phc.deve_verificar(
            self._agora(), self._ler_ultimo(), hora=HORA_AVISO
        ):
            return
        if QApplication.activeModalWidget() is not None:
            # Há outra caixa aberta: tenta-se no próximo toque do relógio.
            return
        self._a_ler = True
        self.pedir_leitura.emit()

    @Slot(object)
    def _ao_ler(self, estado: EstadoVersao) -> None:
        self._a_ler = False
        # Uma vez por dia, com ou sem versão nova, e qualquer que seja a resposta.
        self._guardar_ultimo(self._agora().date())
        if estado.problema:
            diario_bordo.registar_aviso(TITULO, estado.problema)
            return
        if not estado.ha_atualizacao:
            return

        diario_bordo.registar_acao(
            "Aviso de versão nova", f"{estado.instalada} -> {estado.disponivel}"
        )
        trabalho = self._trabalho_aberto() if self._trabalho_aberto else ""
        if not perguntar_instalar(self._janela, estado, trabalho):
            diario_bordo.registar_acao("Aviso de versão nova: «Mais tarde»")
            return
        instalar_e_fechar(self._janela, estado, pode_fechar=self._pode_fechar)

    @Slot(str)
    def _ao_falhar(self, erro: str) -> None:
        # Sem rede ou sem base: fica no diário e o dia conta como feito, para não
        # repetir o mesmo erro de dez em dez minutos.
        self._a_ler = False
        self._guardar_ultimo(self._agora().date())
        diario_bordo.registar_erro(f"{TITULO}: não foi possível ver a pasta", erro)

    @Slot()
    def parar(self) -> None:
        self._relogio.stop()
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
