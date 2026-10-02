"""Avisos do Registo de Horas: dias por registar e envio do mês.

Só existe para quem tem o menu «Registo de Horas». Dois avisos, cada um
desligável nas Definições da própria pessoa:

* **dias por registar** — uma vez por dia, ao abrir o Martelo (ou ao passar
  a meia-noite com ele aberto): se ficaram dias úteis para trás sem horas,
  pergunta se as quer registar agora. O Paulo passa às vezes vários dias sem
  registar e esquece-se deles;
* **envio à contabilidade** — no dia 2 de cada mês, a partir das 9h20 (ou na
  primeira vez que o Martelo abrir depois disso), mostra a folha do mês
  anterior e pede confirmação para a enviar. «Lembrar amanhã» adia um dia;
  nunca envia sem a pessoa carregar no botão.

A consulta é à base do Martelo (rápida): não precisa de thread própria.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core import diario_bordo
from app.db.session import SessionLocal
from app.domain import registo_horas as regra
from app.services.registo_horas_service import RegistoHorasService
from app.ui.dialogs.registo_horas_envio_dialog import ACAO_CORRIGIR
from app.ui.helpers import registo_horas_acoes as acoes

#: O relógio só pergunta «já são horas?».
INTERVALO_RELOGIO_MS = 10 * 60 * 1000
#: Depois do assistente (30 s) e dos avisos do PHC (60 s): um de cada vez.
ATRASO_ARRANQUE_MS = 90 * 1000


class AvisosRegistoHoras(QObject):
    def __init__(
        self,
        janela: QWidget,
        *,
        user_id: int | None,
        nome: str = "",
        email: str = "",
        ativo: bool = False,
        abrir_dia: Callable[[date, bool], None] | None = None,
    ) -> None:
        super().__init__(janela)
        self._janela = janela
        self._user_id = user_id
        self._nome = nome
        self._email = email
        self._ativo = bool(ativo and user_id is not None)
        self._abrir_dia = abrir_dia
        self._ocupado = False

        self._relogio = QTimer(self)
        self._relogio.setInterval(INTERVALO_RELOGIO_MS)
        self._relogio.timeout.connect(self.verificar)
        if self._ativo:
            self._relogio.start()
            QTimer.singleShot(ATRASO_ARRANQUE_MS, self.verificar)

    @property
    def ativo(self) -> bool:
        return self._ativo

    @Slot()
    def verificar(self, agora: datetime | None = None) -> None:
        if not self._ativo or self._ocupado:
            return
        # Com outra janela a pedir resposta, fica para a volta seguinte do relógio.
        if QApplication.activeModalWidget() is not None:
            return
        self._ocupado = True
        try:
            agora = agora or datetime.now()
            if not self._verificar_envio(agora):
                self._verificar_dias_em_falta(agora.date())
        finally:
            self._ocupado = False

    # ---- envio do mês ----------------------------------------------------
    def _verificar_envio(self, agora: datetime) -> bool:
        """Mostra o envio do mês, se for altura. Devolve se mostrou."""
        hoje = agora.date()
        try:
            with SessionLocal() as session:
                servico = RegistoHorasService(session)
                config = servico.config(self._user_id)
                if not config.envio_mensal or servico.envio_adiado(self._user_id) == hoje:
                    return False
                pendentes = servico.meses_por_enviar(self._user_id, agora, config)
                if not pendentes:
                    return False
                # Marca-se já: um erro a meio não volta de dez em dez minutos.
                servico.adiar_envio(self._user_id, hoje)
                servico.marcar_lembrete(self._user_id, hoje)
        except Exception as erro:  # noqa: BLE001 - base em baixo não pode parar o Martelo
            diario_bordo.registar_erro(f"Registo de Horas (envio do mês): {erro}")
            return False
        ano, mes = pendentes[0]
        diario_bordo.registar_acao("Registo de Horas — aviso de envio", f"{ano}-{mes:02d}")
        acao = acoes.enviar_mes(
            self._janela,
            user_id=self._user_id,
            nome_conta=self._nome,
            email_conta=self._email,
            ano=ano,
            mes=mes,
            automatico=True,
        )
        # «Lembrar amanhã» não precisa de mais nada: já ficou adiado para amanhã.
        if acao == ACAO_CORRIGIR and self._abrir_dia is not None:
            self._abrir_dia(date(ano, mes, 1), False)
        return True

    # ---- dias por registar -----------------------------------------------
    def _verificar_dias_em_falta(self, hoje: date) -> None:
        try:
            with SessionLocal() as session:
                servico = RegistoHorasService(session)
                config = servico.config(self._user_id)
                if not config.lembrete_diario:
                    return
                if not regra.deve_lembrar_hoje(hoje, servico.ultimo_lembrete(self._user_id)):
                    return
                servico.marcar_lembrete(self._user_id, hoje)
                em_falta = servico.dias_em_falta(self._user_id, hoje, config)
        except Exception as erro:  # noqa: BLE001
            diario_bordo.registar_erro(f"Registo de Horas (lembrete): {erro}")
            return
        if not em_falta:
            return
        diario_bordo.registar_acao("Registo de Horas — lembrete", f"{len(em_falta)} dia(s)")
        caixa = QMessageBox(self._janela)
        caixa.setIcon(QMessageBox.Icon.Information)
        caixa.setWindowTitle(acoes.TITULO)
        if len(em_falta) == 1:
            caixa.setText(f"Ficou um dia por registar: {regra.lista_de_dias(em_falta)}.")
        else:
            caixa.setText(
                f"Ficaram {len(em_falta)} dias úteis por registar: "
                f"{regra.lista_de_dias(em_falta)}."
            )
        caixa.setInformativeText(
            "Quer registá-los agora? Abre o primeiro; com «Guardar e seguinte» "
            "passa ao dia a seguir."
        )
        registar = caixa.addButton("Registar agora", QMessageBox.ButtonRole.AcceptRole)
        caixa.addButton("Mais tarde", QMessageBox.ButtonRole.RejectRole)
        caixa.setDefaultButton(registar)
        caixa.exec()
        if caixa.clickedButton() is registar and self._abrir_dia is not None:
            self._abrir_dia(em_falta[0], True)
