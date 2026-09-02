"""Aviso diário: há clientes novos ou editados no PHC?

Todos os dias úteis, a partir das 09h00, o Martelo vai espreitar o ``dbo.CL`` do
PHC (só leitura) e compara com a lista que tem cá dentro. Se houver clientes
novos ou alterados, pergunta ao utilizador se quer atualizar; se não houver,
fica calado — o objetivo é avisar, não incomodar.

Tanto a espreitadela como a atualização correm numa thread própria: a consulta
ao PHC passa por PowerShell e demora segundos, e na thread da UI isso prendia a
janela toda.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core import diario_bordo
from app.db.session import SessionLocal
from app.domain import agenda_clientes_phc
from app.repositories.cliente_repository import DiferencasPHC
from app.services.cliente_phc_sync_service import (
    ClientePhcSyncService,
    ResumoSincronizacaoPHC,
)
from app.services.user_pref_service import UserPrefService

#: Chave (por utilizador) com a data da última verificação já feita.
CHAVE_ULTIMA_VERIFICACAO = "clientes_phc_ultima_verificacao"

#: De quanto em quanto tempo se pergunta "já são horas?". Não é a frequência da
#: verificação — essa é uma vez por dia; é só o relógio que dá pelas 09h00 num
#: Martelo que ficou aberto desde a véspera.
INTERVALO_RELOGIO_MS = 10 * 60 * 1000

#: Espera antes da primeira verificação, para não competir com o arranque.
ATRASO_ARRANQUE_MS = 20 * 1000

#: Quantos nomes se mostram na mensagem antes de resumir com "e mais N".
MAX_NOMES_NA_MENSAGEM = 8

#: Título das caixas de mensagem deste aviso.
TITULO = "Analisador diário de clientes do PHC"

#: Como o aviso se apresenta. A caixa aparece sozinha, sem ninguém a ter
#: pedido: quem a vê tem de perceber logo quem fala, o que faz e quando.
APRESENTACAO = (
    "Sou o analisador diário dos clientes do PHC.\n"
    "Todos os dias úteis, às 09h00, vou ver se há clientes novos ou "
    "alterados no PHC.\n\n"
    "Hoje encontrei novidades:"
)


class _TrabalhoPHC(QObject):
    """Vive na thread de trabalho; fala com o PHC e responde por sinais."""

    verificado = Signal(object)   # DiferencasPHC
    sincronizado = Signal(object)  # ResumoSincronizacaoPHC
    falhou = Signal(str)

    @Slot()
    def verificar(self) -> None:
        """Espreitar o PHC (só leitura) e dizer o que mudou."""
        try:
            with SessionLocal() as session:
                diferencas = ClientePhcSyncService(session).verificar_alteracoes()
        except Exception as erro:  # noqa: BLE001 - PHC/rede/config são externos
            self.falhou.emit(str(erro))
            return
        self.verificado.emit(diferencas)

    @Slot()
    def sincronizar(self) -> None:
        """Importar/atualizar os clientes a partir do PHC."""
        try:
            with SessionLocal() as session:
                resumo = ClientePhcSyncService(session).sincronizar()
        except Exception as erro:  # noqa: BLE001 - PHC/rede/config são externos
            self.falhou.emit(str(erro))
            return
        self.sincronizado.emit(resumo)


class VerificadorClientesPHC(QObject):
    """Agenda a verificação diária e trata da conversa com o utilizador."""

    pedir_verificacao = Signal()
    pedir_sincronizacao = Signal()

    #: Emitido depois de uma atualização com sucesso, para quem mostra a lista
    #: de clientes se voltar a carregar.
    clientes_atualizados = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        user_id: int | None = None,
        ativo: bool = True,
    ) -> None:
        super().__init__(parent)
        self._user_id = user_id
        self._ativo = ativo
        self._a_trabalhar = False

        self._thread = QThread(self)
        self._trabalho = _TrabalhoPHC()
        self._trabalho.moveToThread(self._thread)
        self.pedir_verificacao.connect(self._trabalho.verificar)
        self.pedir_sincronizacao.connect(self._trabalho.sincronizar)
        self._trabalho.verificado.connect(self._on_verificado)
        self._trabalho.sincronizado.connect(self._on_sincronizado)
        self._trabalho.falhou.connect(self._on_falhou)
        self._thread.start()

        aplicacao = QApplication.instance()
        if aplicacao is not None:
            aplicacao.aboutToQuit.connect(self.parar)

        self._relogio = QTimer(self)
        self._relogio.setInterval(INTERVALO_RELOGIO_MS)
        self._relogio.timeout.connect(self.verificar_se_e_hora)
        if self._ativo:
            self._relogio.start()
            QTimer.singleShot(ATRASO_ARRANQUE_MS, self.verificar_se_e_hora)

    # ---- agenda -------------------------------------------------------------
    @Slot()
    def verificar_se_e_hora(self) -> None:
        """Se já for hora e ainda não se tiver verificado hoje, vai ao PHC."""
        if not self._ativo or self._a_trabalhar or self._user_id is None:
            return
        hoje = datetime.now()
        if not agenda_clientes_phc.deve_verificar(hoje, self._ultima_verificacao()):
            return

        # Marca já o dia como feito. Se o PHC estiver em baixo, o utilizador não
        # leva o mesmo erro de dez em dez minutos — e continua a poder usar o
        # botão «Atualizar PHC» na página dos Clientes.
        self._guardar_verificacao(hoje.date())
        self._a_trabalhar = True
        diario_bordo.registar_acao("Verificação diária de clientes do PHC")
        self.pedir_verificacao.emit()

    def _ultima_verificacao(self):
        try:
            with SessionLocal() as session:
                valor = UserPrefService(session).obter_valor(
                    self._user_id, CHAVE_ULTIMA_VERIFICACAO
                )
        except Exception:  # noqa: BLE001 - sem preferências, verifica-se na mesma
            return None
        return agenda_clientes_phc.ler_data(valor)

    def _guardar_verificacao(self, dia) -> None:
        try:
            with SessionLocal() as session:
                UserPrefService(session).guardar_valor(
                    self._user_id,
                    CHAVE_ULTIMA_VERIFICACAO,
                    agenda_clientes_phc.escrever_data(dia),
                )
        except Exception:  # noqa: BLE001 - não vale a pena falhar por isto
            pass

    # ---- respostas da thread ------------------------------------------------
    @Slot(object)
    def _on_verificado(self, diferencas: DiferencasPHC) -> None:
        self._a_trabalhar = False
        if not diferencas:
            # Nada mudou: o utilizador nem dá por isto.
            return

        caixa = QMessageBox(self._janela())
        caixa.setWindowTitle(TITULO)
        caixa.setIcon(QMessageBox.Icon.Question)
        caixa.setText(self.mensagem_diferencas(diferencas))
        # A lista completa fica atrás do "Mostrar detalhes": com 40 clientes
        # novos a caixa crescia até não caber no ecrã.
        detalhe = self.detalhe_diferencas(diferencas)
        if detalhe:
            caixa.setDetailedText(detalhe)
        sim = caixa.addButton(
            "Sim, atualizar agora", QMessageBox.ButtonRole.YesRole
        )
        caixa.addButton("Agora não", QMessageBox.ButtonRole.NoRole)
        caixa.setDefaultButton(sim)
        caixa.exec()
        if caixa.clickedButton() is not sim:
            return

        self._a_trabalhar = True
        self.pedir_sincronizacao.emit()

    @Slot(object)
    def _on_sincronizado(self, resumo: ResumoSincronizacaoPHC) -> None:
        self._a_trabalhar = False
        self.clientes_atualizados.emit()
        QMessageBox.information(
            self._janela(),
            TITULO,
            "Já está: a tabela de clientes do Martelo ficou igual à do PHC.\n\n"
            f"Clientes lidos no PHC: {resumo.total_phc}\n"
            f"Criados de novo: {resumo.criados}\n"
            f"Atualizados: {resumo.atualizados}\n\n"
            "Volto a verificar amanhã de manhã.",
        )

    @Slot(str)
    def _on_falhou(self, erro: str) -> None:
        self._a_trabalhar = False
        # Em silêncio de propósito: isto corre sozinho e o utilizador pode nem
        # ter ligação ao PHC nesta máquina. Fica no diário para se poder ver.
        diario_bordo.registar_erro(
            f"Verificação diária de clientes do PHC falhou: {erro}"
        )

    # ---- texto --------------------------------------------------------------
    @staticmethod
    def mensagem_diferencas(diferencas: DiferencasPHC) -> str:
        """Mensagem a mostrar ao utilizador (pura, para poder ser testada).

        Começa por se apresentar: a caixa aparece sozinha, sem ninguém lhe ter
        pedido nada, e quem a vê tem de perceber logo o que é e de onde veio.
        """
        linhas = [APRESENTACAO, ""]
        if diferencas.novos:
            linhas.append(f"Clientes novos: {len(diferencas.novos)}")
            linhas.extend(_amostra(diferencas.novos))
        if diferencas.alterados:
            if diferencas.novos:
                linhas.append("")
            linhas.append(f"Clientes editados: {len(diferencas.alterados)}")
            linhas.extend(_amostra(diferencas.alterados))
        linhas.extend(
            [
                "",
                "Quer que atualize agora a tabela de clientes do Martelo?",
                "No PHC só leio; escrevo apenas na base de dados do Martelo.",
            ]
        )
        return "\n".join(linhas)

    @staticmethod
    def detalhe_diferencas(diferencas: DiferencasPHC) -> str:
        """Lista completa, para o «Mostrar detalhes» da caixa de mensagem.

        Vazia quando a caixa já mostra tudo — assim o botão de detalhes só
        aparece quando há mesmo mais alguma coisa para ver.
        """
        if diferencas.total <= MAX_NOMES_NA_MENSAGEM:
            return ""
        blocos = []
        if diferencas.novos:
            blocos.append(
                "\n".join(["CLIENTES NOVOS:", *diferencas.novos])
            )
        if diferencas.alterados:
            blocos.append(
                "\n".join(["CLIENTES EDITADOS:", *diferencas.alterados])
            )
        return "\n\n".join(blocos)

    def _janela(self) -> QWidget | None:
        """A janela que serve de pai às caixas de mensagem."""
        pai = self.parent()
        return pai if isinstance(pai, QWidget) else None

    # ---- fim ----------------------------------------------------------------
    @Slot()
    def parar(self) -> None:
        """Parar o relógio e fechar a thread (ao sair da aplicação)."""
        self._ativo = False
        self._relogio.stop()
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)


def _amostra(etiquetas: tuple[str, ...]) -> list[str]:
    """As primeiras etiquetas, com um "e mais N" quando forem muitas."""
    mostradas = [f"  • {etiqueta}" for etiqueta in etiquetas[:MAX_NOMES_NA_MENSAGEM]]
    restantes = len(etiquetas) - MAX_NOMES_NA_MENSAGEM
    if restantes > 0:
        mostradas.append(f"  • … e mais {restantes}")
    return mostradas
