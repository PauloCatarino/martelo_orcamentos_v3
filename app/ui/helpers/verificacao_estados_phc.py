"""Aviso diário: que obras minhas é que já foram finalizadas ou arquivadas?

Quem fecha uma obra não é quem a desenha. O ``Finalizado`` e o ``Arquivado``
são marcados por outras pessoas da empresa — no PHC, para as encomendas de
cliente, e no Streamlit, para as de cliente final (os números com ``_``). Sem
isto, essa informação só chegava ao Martelo se alguém se lembrasse do botão
«Sincronizar PHC», escondido no Ponto Situação; numa comparação real havia 86
obras à espera.

Todos os dias úteis, a partir das 09h00, cada pessoa vê **as suas** obras que
mudaram de estado lá fora e decide, linha a linha, o que atualizar. O Martelo
nunca altera nada sozinho.

A consulta corre numa thread própria: passa por PowerShell e demora segundos,
o que na thread da UI prendia a janela toda.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core import diario_bordo
from app.db.session import SessionLocal
from app.domain import agenda_diaria_phc
from app.services.producao_phc_sync_service import (
    LevantamentoEstados,
    aplicar_estados,
    levantar_estados_de_fora,
)
from app.services.user_pref_service import UserPrefService
from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

#: Chave (por utilizador) com a data da última verificação já feita.
CHAVE_ULTIMA_VERIFICACAO = "estados_phc_ultima_verificacao"

#: De quanto em quanto tempo se pergunta "já são horas?". Não é a frequência da
#: verificação — essa é uma vez por dia; é só o relógio que dá pelas 09h00 num
#: Martelo que ficou aberto desde a véspera.
INTERVALO_RELOGIO_MS = 10 * 60 * 1000

#: Espera antes da primeira verificação. Maior do que a dos clientes, para os
#: dois analisadores não irem ao PHC ao mesmo tempo no arranque.
ATRASO_ARRANQUE_MS = 60 * 1000

#: Título das caixas de mensagem deste aviso.
TITULO = "Analisador diário de estados do PHC"


class _TrabalhoEstados(QObject):
    """Vive na thread de trabalho; fala com o PHC/Streamlit por sinais."""

    verificado = Signal(object)  # LevantamentoEstados
    falhou = Signal(str)

    def __init__(self, responsavel: str = "") -> None:
        super().__init__()
        self._responsavel = responsavel

    @Slot()
    def verificar(self) -> None:
        try:
            levantamento = levantar_estados_de_fora(
                SessionLocal,
                responsavel=self._responsavel or None,
            )
        except Exception as erro:  # noqa: BLE001 - PHC/rede/config são externos
            self.falhou.emit(str(erro))
            return
        self.verificado.emit(levantamento)


class VerificadorEstadosPHC(QObject):
    """Agenda a verificação diária e trata da conversa com o utilizador."""

    pedir_verificacao = Signal()

    #: Emitido depois de gravar estados, para quem mostra a lista de obras se
    #: voltar a carregar.
    estados_atualizados = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        user_id: int | None = None,
        responsavel: str = "",
        ativo: bool = True,
    ) -> None:
        super().__init__(parent)
        self._user_id = user_id
        self._responsavel = (responsavel or "").strip()
        self._ativo = ativo
        self._a_trabalhar = False

        self._thread = QThread(self)
        self._trabalho = _TrabalhoEstados(self._responsavel)
        self._trabalho.moveToThread(self._thread)
        self.pedir_verificacao.connect(self._trabalho.verificar)
        self._trabalho.verificado.connect(self._on_verificado)
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
        if not agenda_diaria_phc.deve_verificar(hoje, self._ultima_verificacao()):
            return

        # Marca já o dia como feito. Se o PHC estiver em baixo, o utilizador não
        # leva o mesmo erro de dez em dez minutos — e continua a poder usar o
        # botão «Sincronizar PHC» no Ponto Situação.
        self._guardar_verificacao(hoje.date())
        self._a_trabalhar = True
        diario_bordo.registar_acao("Verificação diária de estados do PHC")
        self.pedir_verificacao.emit()

    def _ultima_verificacao(self):
        try:
            with SessionLocal() as session:
                valor = UserPrefService(session).obter_valor(
                    self._user_id, CHAVE_ULTIMA_VERIFICACAO
                )
        except Exception:  # noqa: BLE001 - sem preferências, verifica-se na mesma
            return None
        return agenda_diaria_phc.ler_data(valor)

    def _guardar_verificacao(self, dia) -> None:
        try:
            with SessionLocal() as session:
                UserPrefService(session).guardar_valor(
                    self._user_id,
                    CHAVE_ULTIMA_VERIFICACAO,
                    agenda_diaria_phc.escrever_data(dia),
                )
        except Exception:  # noqa: BLE001 - não vale a pena falhar por isto
            pass

    # ---- respostas da thread ------------------------------------------------
    @Slot(object)
    def _on_verificado(self, levantamento: LevantamentoEstados) -> None:
        self._a_trabalhar = False

        if levantamento.falharam_as_duas:
            self._on_falhou(
                f"PHC: {levantamento.erro_phc} | "
                f"Streamlit: {levantamento.erro_streamlit}"
            )
            return
        for fonte, erro in (
            ("PHC", levantamento.erro_phc),
            ("Streamlit", levantamento.erro_streamlit),
        ):
            if erro:
                # Metade da resposta chegou; a outra fica no diário e o
                # utilizador vê na mesma o que há.
                diario_bordo.registar_erro(
                    f"Verificação diária de estados: {fonte} não respondeu: {erro}"
                )

        if not levantamento:
            # Nada mudou: o utilizador nem dá por isto.
            return

        caixa = ProducaoPhcSyncDialog(
            levantamento.diferencas,
            self._janela(),
            automatico=True,
        )
        if not caixa.exec():
            return

        atualizacoes = caixa.selecionados()
        if not atualizacoes:
            return

        try:
            with SessionLocal() as session:
                quantas = aplicar_estados(
                    session, atualizacoes, current_user_id=self._user_id
                )
        except Exception as erro:  # noqa: BLE001 - base de dados
            diario_bordo.registar_erro(
                f"Verificação diária de estados: não gravou: {erro}"
            )
            QMessageBox.warning(
                self._janela(),
                TITULO,
                "Não consegui gravar os estados no Martelo.\n\n"
                "Tente pelo botão «Sincronizar PHC», no Ponto Situação.",
            )
            return

        self.estados_atualizados.emit()
        QMessageBox.information(
            self._janela(),
            TITULO,
            f"{quantas} obra(s) atualizada(s) no Martelo.\n\n"
            "Volto a verificar amanhã de manhã.",
        )

    @Slot(str)
    def _on_falhou(self, erro: str) -> None:
        self._a_trabalhar = False
        # Em silêncio de propósito: isto corre sozinho e o utilizador pode nem
        # ter ligação ao PHC nesta máquina. Fica no diário para se poder ver.
        diario_bordo.registar_erro(
            f"Verificação diária de estados do PHC falhou: {erro}"
        )

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
