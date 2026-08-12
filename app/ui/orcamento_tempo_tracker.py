"""Contador discreto do tempo ativo dentro de uma versão de orçamento."""

from __future__ import annotations

import logging
from time import monotonic

from PySide6.QtCore import QEvent, QObject, QTimer, Qt, Signal
from PySide6.QtWidgets import QApplication, QMainWindow

from app.db.session import SessionLocal
from app.domain.tempo_atividade import incremento_tempo_ativo
from app.services.orcamento_tempo_atividade_service import (
    OrcamentoTempoAtividadeService,
)


logger = logging.getLogger(__name__)


class OrcamentoTempoTracker(QObject):
    """Count only foreground, recently active time in the current budget."""

    tempoAtualizado = Signal(int, int)

    INTERVALO_TICK_MS = 10_000
    INTERVALO_GRAVACAO_SEGUNDOS = 60
    EVENTOS_ATIVIDADE = {
        QEvent.Type.KeyPress,
        QEvent.Type.MouseButtonPress,
        QEvent.Type.MouseButtonDblClick,
        QEvent.Type.MouseMove,
        QEvent.Type.Wheel,
        QEvent.Type.TouchBegin,
    }

    def __init__(
        self,
        janela: QMainWindow,
        *,
        user_id: int | None,
        relogio=monotonic,
    ) -> None:
        super().__init__(janela)
        self._janela = janela
        self._user_id = int(user_id) if user_id is not None else None
        self._relogio = relogio
        self._orcamento_versao_id: int | None = None
        self._ultima_atividade: float | None = None
        self._ultimo_tick = self._relogio()
        self._segundos_pendentes = 0.0

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            app.applicationStateChanged.connect(self._mudou_estado_aplicacao)

        self._timer = QTimer(self)
        self._timer.setInterval(self.INTERVALO_TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @property
    def orcamento_versao_id(self) -> int | None:
        return self._orcamento_versao_id

    def definir_orcamento(self, orcamento_versao_id: int | None) -> None:
        """Switch counting context, flushing the version being left."""
        novo_id = int(orcamento_versao_id) if orcamento_versao_id else None
        if novo_id == self._orcamento_versao_id:
            return

        self._tick()
        self._gravar_pendente()
        agora = self._relogio()
        # Never carry a fraction of the preceding version into the next one.
        self._segundos_pendentes = 0.0
        self._orcamento_versao_id = novo_id
        # Opening a budget is itself an intentional user action.
        self._ultima_atividade = agora if novo_id is not None else None
        self._ultimo_tick = agora

    def registar_atividade(self) -> None:
        if self._orcamento_versao_id is not None:
            self._ultima_atividade = self._relogio()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt override)
        if event.type() == QEvent.Type.WindowStateChange:
            self._ultimo_tick = self._relogio()
            if self._janela.isMinimized():
                self._ultima_atividade = None
        if event.type() in self.EVENTOS_ATIVIDADE:
            self.registar_atividade()
        return super().eventFilter(obj, event)

    def _mudou_estado_aplicacao(self, _estado) -> None:
        """Never bridge a foreground/background transition with one time slice."""
        self._ultimo_tick = self._relogio()
        self._ultima_atividade = None

    def _aplicacao_esta_ativa(self) -> bool:
        app = QApplication.instance()
        return bool(
            app is not None
            and app.applicationState() == Qt.ApplicationState.ApplicationActive
            and self._janela.isVisible()
            and not self._janela.isMinimized()
        )

    def _tick(self) -> None:
        agora = self._relogio()
        incremento = incremento_tempo_ativo(
            agora=agora,
            ultimo_tick=self._ultimo_tick,
            ultima_atividade=self._ultima_atividade,
            contexto_ativo=(
                self._orcamento_versao_id is not None and self._user_id is not None
            ),
            aplicacao_ativa=self._aplicacao_esta_ativa(),
        )
        self._ultimo_tick = agora
        self._segundos_pendentes += incremento
        if self._segundos_pendentes >= self.INTERVALO_GRAVACAO_SEGUNDOS:
            self._gravar_pendente()

    def _gravar_pendente(self) -> None:
        segundos = int(self._segundos_pendentes)
        if (
            segundos <= 0
            or self._orcamento_versao_id is None
            or self._user_id is None
        ):
            return

        try:
            with SessionLocal() as session:
                total = OrcamentoTempoAtividadeService(session).adicionar_segundos(
                    self._orcamento_versao_id,
                    self._user_id,
                    segundos,
                )
        except Exception:  # noqa: BLE001 - tracking must never block the budget UI
            logger.exception("Não foi possível gravar o tempo ativo do orçamento")
            return

        self._segundos_pendentes -= segundos
        self.tempoAtualizado.emit(self._orcamento_versao_id, total)

    def encerrar(self) -> None:
        """Flush the final slice and detach from the application."""
        self._tick()
        self._gravar_pendente()
        self._timer.stop()
        app = QApplication.instance()
        if app is not None:
            try:
                app.applicationStateChanged.disconnect(
                    self._mudou_estado_aplicacao
                )
            except (RuntimeError, TypeError):
                pass
            app.removeEventFilter(self)
