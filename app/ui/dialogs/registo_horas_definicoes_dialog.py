"""Definições do registo de horas de cada pessoa (e o email da contabilidade).

O horário, os avisos e a pasta das folhas são de cada um (``user_prefs``). O
email da contabilidade é da casa (``system_settings``): só o administrador o
muda — para os outros aparece sombreado, a dizer porquê.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.domain import registo_horas as regra
from app.ui import tema
from app.ui.widgets.combo_sem_scroll import (
    DataSemScroll,
    HoraSemScroll,
    SpinDuploSemScroll,
    SpinSemScroll,
)


def pasta_pdf_padrao() -> Path:
    return Path.home() / "Documents" / "Registo de Horas"


class RegistoHorasDefinicoesDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        config: regra.ConfigHoras,
        nome_conta: str,
        email_contabilidade: str,
        pode_mudar_email: bool,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Registo de Horas — definições")
        self.setMinimumWidth(520)
        self._config = config

        self.nome_edit = QLineEdit(config.nome_folha)
        self.nome_edit.setPlaceholderText(nome_conta)
        self.nome_edit.setToolTip(
            "Nome que aparece na folha de horas e no email à contabilidade. "
            "Vazio = o nome da sua conta do Martelo."
        )

        self.entrada_edit = HoraSemScroll()
        self.entrada_edit.setDisplayFormat("HH:mm")
        self.entrada_edit.setTime(QTime(config.entrada_habitual // 60, config.entrada_habitual % 60))
        self.entrada_edit.setToolTip("Hora de entrada que aparece já escrita num dia novo.")
        saida = config.saida_habitual % regra.MINUTOS_DIA
        self.saida_edit = HoraSemScroll()
        self.saida_edit.setDisplayFormat("HH:mm")
        self.saida_edit.setTime(QTime(saida // 60, saida % 60))
        self.saida_edit.setToolTip("Hora de saída que aparece já escrita num dia novo.")
        horario = QHBoxLayout()
        horario.addWidget(self.entrada_edit)
        horario.addWidget(QLabel("às"))
        horario.addWidget(self.saida_edit)
        horario.addStretch()

        self.horas_normais_spin = SpinDuploSemScroll()
        self.horas_normais_spin.setRange(1, 12)
        self.horas_normais_spin.setSingleStep(0.5)
        self.horas_normais_spin.setDecimals(1)
        self.horas_normais_spin.setSuffix(" h")
        self.horas_normais_spin.setValue(config.horas_normais_dia / 60)
        self.horas_normais_spin.setToolTip(
            "Horas normais de um dia útil (8h). Acima disto são horas extra; "
            "abaixo, a diferença desconta ao mês. Só conta para os dias que "
            "gravar daqui para a frente."
        )
        self.almoco_spin = SpinSemScroll()
        self.almoco_spin.setRange(0, 180)
        self.almoco_spin.setSingleStep(15)
        self.almoco_spin.setSuffix(" min")
        self.almoco_spin.setValue(config.pausa_almoco)
        self.almoco_spin.setToolTip("Quanto desconta a pausa do almoço (e a do jantar).")
        self.almoco_check = QCheckBox("Descontar o almoço por defeito")
        self.almoco_check.setChecked(config.descontar_almoco)
        self.almoco_check.setToolTip("Num dia novo, o «Descontar almoço» já vem marcado.")

        caixa_horario = QGroupBox("O meu horário")
        form_horario = QFormLayout(caixa_horario)
        form_horario.addRow("Nome na folha", self.nome_edit)
        form_horario.addRow("Horário habitual", horario)
        form_horario.addRow("Horas normais por dia", self.horas_normais_spin)
        form_horario.addRow("Pausa do almoço", self.almoco_spin)
        form_horario.addRow("", self.almoco_check)

        self.inicio_edit = DataSemScroll()
        self.inicio_edit.setCalendarPopup(True)
        self.inicio_edit.setDisplayFormat("dd/MM/yyyy")
        inicio = config.inicio_registo
        self.inicio_edit.setDate(QDate(inicio.year, inicio.month, inicio.day))
        self.inicio_edit.setToolTip(
            "Dia em que começou o registo oficial. Antes disto é histórico: não "
            "aparece «por registar» nem segue para a contabilidade."
        )
        self.lembrete_check = QCheckBox("Lembrar-me dos dias úteis que ficaram por registar")
        self.lembrete_check.setChecked(config.lembrete_diario)
        self.lembrete_check.setToolTip(
            "Uma vez por dia, ao abrir o Martelo, avisa se há dias úteis para trás "
            "sem horas registadas. Desligue se só regista os dias com horas extra."
        )
        self.envio_check = QCheckBox(
            f"Enviar as horas do mês à contabilidade (dia {regra.DIA_ENVIO}, às "
            f"{regra.HORA_ENVIO:%Hh%M})"
        )
        self.envio_check.setChecked(config.envio_mensal)
        self.envio_check.setToolTip(
            "No dia 2 de cada mês, às 9h20 (ou quando abrir o Martelo depois "
            "disso), mostra a folha do mês anterior e pergunta se a pode enviar. "
            "Nunca envia sem confirmar."
        )

        self.pasta_edit = QLineEdit(config.pasta_pdf)
        self.pasta_edit.setPlaceholderText(str(pasta_pdf_padrao()))
        self.pasta_edit.setToolTip(
            "Pasta onde ficam as folhas em PDF (também as que seguem por email)."
        )
        self.pasta_button = QPushButton("Escolher…")
        self.pasta_button.setToolTip("Escolher a pasta das folhas em PDF")
        self.pasta_button.clicked.connect(self._escolher_pasta)
        pasta = QHBoxLayout()
        pasta.addWidget(self.pasta_edit, stretch=1)
        pasta.addWidget(self.pasta_button)

        self.email_edit = QLineEdit(email_contabilidade)
        self.email_edit.setToolTip(
            "Email da contabilidade que recebe as folhas de horas de todos."
            if pode_mudar_email
            else "Email da contabilidade (é igual para todos): só o administrador o muda."
        )
        if not pode_mudar_email:
            self.email_edit.setReadOnly(True)
            self.email_edit.setStyleSheet(tema.ESTILO_CAMPO_BLOQUEADO)
        self._pode_mudar_email = pode_mudar_email

        caixa_avisos = QGroupBox("Avisos e envio")
        form_avisos = QFormLayout(caixa_avisos)
        form_avisos.addRow("Início do registo", self.inicio_edit)
        form_avisos.addRow("", self.lembrete_check)
        form_avisos.addRow("", self.envio_check)
        form_avisos.addRow("Email da contabilidade", self.email_edit)
        form_avisos.addRow("Pasta das folhas", pasta)

        self.guardar_button = QPushButton("Guardar")
        self.guardar_button.setDefault(True)
        self.guardar_button.setToolTip("Guardar as definições")
        self.guardar_button.clicked.connect(self.accept)
        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.setToolTip("Fechar sem guardar")
        self.cancelar_button.clicked.connect(self.reject)
        botoes = QHBoxLayout()
        botoes.addStretch()
        botoes.addWidget(self.guardar_button)
        botoes.addWidget(self.cancelar_button)

        layout = QVBoxLayout(self)
        layout.addWidget(caixa_horario)
        layout.addWidget(caixa_avisos)
        layout.addLayout(botoes)

    def _escolher_pasta(self) -> None:
        inicial = self.pasta_edit.text().strip() or str(pasta_pdf_padrao())
        escolhida = QFileDialog.getExistingDirectory(self, "Pasta das folhas de horas", inicial)
        if escolhida:
            self.pasta_edit.setText(escolhida)

    def config(self) -> regra.ConfigHoras:
        entrada = self.entrada_edit.time()
        saida = self.saida_edit.time()
        inicio = self.inicio_edit.date()
        return replace(
            self._config,
            nome_folha=self.nome_edit.text().strip(),
            entrada_habitual=entrada.hour() * 60 + entrada.minute(),
            saida_habitual=saida.hour() * 60 + saida.minute(),
            horas_normais_dia=int(round(self.horas_normais_spin.value() * 60)),
            pausa_almoco=self.almoco_spin.value(),
            descontar_almoco=self.almoco_check.isChecked(),
            lembrete_diario=self.lembrete_check.isChecked(),
            envio_mensal=self.envio_check.isChecked(),
            inicio_registo=inicio.toPython(),
            pasta_pdf=self.pasta_edit.text().strip(),
        )

    def email_contabilidade(self) -> str | None:
        """O email novo, ou ``None`` se esta conta não o pode mudar."""
        if not self._pode_mudar_email:
            return None
        return self.email_edit.text().strip()
