"""Registar (ou ver) as horas de um dia.

O diálogo não fala com a base de dados: quem o abre dá-lhe três funções —
ler um dia, guardar e apagar — e ele trata só do formulário. Assim o mesmo
diálogo serve para a própria pessoa (edita) e para o administrador a ver as
horas de outra pessoa (só consulta).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app.domain import registo_horas as regra
from app.ui import tema
from app.ui.widgets.combo_sem_scroll import HoraSemScroll, SpinDuploSemScroll

#: Saídas mais comuns, num clique (a folha em papel ia até à meia-noite).
SAIDAS_RAPIDAS = (17, 18, 19, 20, 21, 22)


def _qtime(minutos: int | None) -> QTime:
    minutos = (minutos or 0) % regra.MINUTOS_DIA
    return QTime(minutos // 60, minutos % 60)


def _minutos(campo: HoraSemScroll) -> int:
    hora = campo.time()
    return hora.hour() * 60 + hora.minute()


def _novo_campo_hora(tooltip: str) -> HoraSemScroll:
    campo = HoraSemScroll()
    campo.setDisplayFormat("HH:mm")
    campo.setToolTip(tooltip)
    campo.setMinimumWidth(80)
    return campo


class RegistoHorasDiaDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        dia: date,
        config: regra.ConfigHoras,
        obter: Callable[[date], regra.LinhaDia | None],
        guardar: Callable[[date, regra.DadosDia, str], regra.LinhaDia | None] | None = None,
        apagar: Callable[[date], bool] | None = None,
        nome: str = "",
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._obter = obter
        self._guardar = guardar
        self._apagar = apagar
        self._so_leitura = guardar is None
        self._dia = dia
        self._registo: regra.LinhaDia | None = None
        #: Algum dia foi gravado ou apagado (a página tem de recarregar).
        self.alterou = False

        titulo = "Registo de horas"
        if nome:
            titulo += f" — {nome}"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(560)

        # ---- cabeçalho com a navegação entre dias ------------------------
        self.anterior_button = QPushButton("◀")
        self.anterior_button.setFixedWidth(36)
        self.anterior_button.setToolTip("Dia anterior")
        self.anterior_button.clicked.connect(lambda: self._ir_para(self._dia - timedelta(days=1)))
        self.seguinte_button = QPushButton("▶")
        self.seguinte_button.setFixedWidth(36)
        self.seguinte_button.setToolTip("Dia seguinte")
        self.seguinte_button.clicked.connect(lambda: self._ir_para(self._dia + timedelta(days=1)))
        self.titulo_label = QLabel()
        self.titulo_label.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {tema.CASTANHO_ESCURO};"
        )
        self.subtitulo_label = QLabel()
        self.subtitulo_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")
        textos = QVBoxLayout()
        textos.addWidget(self.titulo_label)
        textos.addWidget(self.subtitulo_label)
        cabecalho = QHBoxLayout()
        cabecalho.addWidget(self.anterior_button)
        cabecalho.addLayout(textos, stretch=1)
        cabecalho.addWidget(self.seguinte_button)

        # ---- tipo de dia -------------------------------------------------
        self.tipo_grupo = QButtonGroup(self)
        tipos = QHBoxLayout()
        self._radios: dict[str, QRadioButton] = {}
        for indice, tipo in enumerate(regra.TIPOS):
            radio = QRadioButton(regra.NOMES_TIPOS[tipo])
            radio.setToolTip(regra.AJUDA_TIPOS[tipo])
            self.tipo_grupo.addButton(radio, indice)
            self._radios[tipo] = radio
            tipos.addWidget(radio)
        tipos.addStretch()
        self.tipo_grupo.idToggled.connect(self._ao_mudar_tipo)
        self.tipo_ajuda = QLabel()
        self.tipo_ajuda.setWordWrap(True)
        self.tipo_ajuda.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")
        caixa_tipo = QGroupBox("Tipo de dia")
        layout_tipo = QVBoxLayout(caixa_tipo)
        layout_tipo.addLayout(tipos)
        layout_tipo.addWidget(self.tipo_ajuda)

        # ---- dia útil ----------------------------------------------------
        dica_noite = (
            " Se sair depois da meia-noite, indique a hora do dia seguinte "
            "(ex.: 01:30)."
        )
        self.entrada_edit = _novo_campo_hora("Hora a que começou a trabalhar.")
        self.saida_edit = _novo_campo_hora("Hora a que acabou." + dica_noite)
        saidas = QHBoxLayout()
        saidas.setSpacing(4)
        for hora in SAIDAS_RAPIDAS:
            botao = QPushButton(f"{hora}h")
            botao.setFixedWidth(42)
            botao.setToolTip(f"Saída às {hora}h00")
            botao.clicked.connect(lambda _c=False, h=hora: self.saida_edit.setTime(QTime(h, 0)))
            saidas.addWidget(botao)
        saidas.addStretch()
        linha1 = QHBoxLayout()
        linha1.addWidget(QLabel("Entrada"))
        linha1.addWidget(self.entrada_edit)
        linha1.addSpacing(12)
        linha1.addWidget(QLabel("Saída"))
        linha1.addWidget(self.saida_edit)
        linha1.addSpacing(8)
        linha1.addLayout(saidas, stretch=1)

        self.almoco_check = QCheckBox(
            f"Descontar almoço ({regra.formatar_total(config.pausa_almoco)})"
        )
        self.almoco_check.setToolTip("Tira a pausa do almoço às horas do dia.")
        self.jantar_check = QCheckBox(
            f"Descontar jantar ({regra.formatar_total(config.pausa_almoco)})"
        )
        self.jantar_check.setToolTip(
            "Tira também uma pausa para o jantar (dias em que se fica até tarde)."
        )
        pausas = QHBoxLayout()
        pausas.addWidget(self.almoco_check)
        pausas.addWidget(self.jantar_check)
        pausas.addStretch()

        self.segundo_check = QCheckBox("2.º período (ex.: horas feitas em casa, à noite)")
        self.segundo_check.setToolTip(
            "Para quem sai e volta a trabalhar mais tarde: indique a entrada e a "
            "saída desse 2.º período. Conta para as horas do dia como o 1.º."
        )
        self.entrada2_edit = _novo_campo_hora("Hora a que recomeçou (2.º período).")
        self.saida2_edit = _novo_campo_hora("Hora a que acabou o 2.º período." + dica_noite)
        linha2 = QHBoxLayout()
        linha2.addWidget(self.segundo_check)
        linha2.addSpacing(8)
        linha2.addWidget(QLabel("Entrada"))
        linha2.addWidget(self.entrada2_edit)
        linha2.addWidget(QLabel("Saída"))
        linha2.addWidget(self.saida2_edit)
        linha2.addStretch()
        self.segundo_check.toggled.connect(self._atualizar_segundo)

        self.acerto_spin = SpinDuploSemScroll()
        self.acerto_spin.setRange(-12, 12)
        self.acerto_spin.setSingleStep(0.5)
        self.acerto_spin.setDecimals(1)
        self.acerto_spin.setSuffix(" h")
        self.acerto_spin.setToolTip(
            "Acerto de horas: some horas feitas fora do horário (ex.: +2) ou tire "
            "pausas a mais (ex.: −1). Normalmente fica a 0."
        )
        acerto = QHBoxLayout()
        acerto.addWidget(QLabel("Acerto"))
        acerto.addWidget(self.acerto_spin)
        acerto.addStretch()

        self.bloco_util = QWidget()
        layout_util = QVBoxLayout(self.bloco_util)
        layout_util.setContentsMargins(0, 0, 0, 0)
        layout_util.addLayout(linha1)
        layout_util.addLayout(pausas)
        layout_util.addLayout(linha2)
        layout_util.addLayout(acerto)

        # ---- outros dias: só o número de horas ---------------------------
        self.horas_label = QLabel("Horas trabalhadas")
        self.horas_spin = SpinDuploSemScroll()
        self.horas_spin.setRange(0, 24)
        self.horas_spin.setSingleStep(0.5)
        self.horas_spin.setDecimals(1)
        self.horas_spin.setSuffix(" h")
        self.horas_spin.setToolTip("Número de horas (pode usar meias horas: 2,5).")
        self.bloco_horas = QWidget()
        layout_horas = QHBoxLayout(self.bloco_horas)
        layout_horas.setContentsMargins(0, 0, 0, 0)
        layout_horas.addWidget(self.horas_label)
        layout_horas.addWidget(self.horas_spin)
        layout_horas.addStretch()

        caixa_horas = QGroupBox("Horas")
        layout_caixa = QVBoxLayout(caixa_horas)
        layout_caixa.addWidget(self.bloco_util)
        layout_caixa.addWidget(self.bloco_horas)

        self.observacoes_edit = QLineEdit()
        self.observacoes_edit.setMaxLength(255)
        self.observacoes_edit.setPlaceholderText("Ex.: Evento Blum Sohapil (tarde)")
        self.observacoes_edit.setToolTip("Nota que aparece na folha de horas deste dia.")
        formulario = QFormLayout()
        formulario.addRow("Observações", self.observacoes_edit)

        # ---- resultado e erros -------------------------------------------
        self.resultado_label = QLabel()
        self.resultado_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {tema.CASTANHO_ESCURO};"
        )
        self.detalhe_label = QLabel()
        self.detalhe_label.setWordWrap(True)
        self.erro_label = QLabel()
        self.erro_label.setWordWrap(True)
        self.erro_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")

        # ---- botões ------------------------------------------------------
        self.guardar_button = QPushButton("Guardar")
        self.guardar_button.setToolTip("Guardar este dia e fechar")
        self.guardar_button.setDefault(True)
        self.guardar_button.clicked.connect(lambda: self._gravar(seguinte=False))
        self.guardar_seguinte_button = QPushButton("Guardar e seguinte")
        self.guardar_seguinte_button.setToolTip(
            "Guardar este dia e passar ao dia seguinte (para pôr vários dias em dia)"
        )
        self.guardar_seguinte_button.clicked.connect(lambda: self._gravar(seguinte=True))
        self.apagar_button = QPushButton("Apagar dia")
        self.apagar_button.setToolTip("Apagar o registo deste dia (pede confirmação)")
        self.apagar_button.clicked.connect(self._apagar_dia)
        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.setToolTip("Fechar sem guardar as alterações deste dia")
        self.fechar_button.clicked.connect(self.reject)
        botoes = QHBoxLayout()
        botoes.addWidget(self.apagar_button)
        botoes.addStretch()
        botoes.addWidget(self.guardar_button)
        botoes.addWidget(self.guardar_seguinte_button)
        botoes.addWidget(self.fechar_button)

        layout = QVBoxLayout(self)
        layout.addLayout(cabecalho)
        layout.addWidget(caixa_tipo)
        layout.addWidget(caixa_horas)
        layout.addLayout(formulario)
        layout.addWidget(self.resultado_label)
        layout.addWidget(self.detalhe_label)
        layout.addWidget(self.erro_label)
        layout.addLayout(botoes)

        for campo in (
            self.entrada_edit,
            self.saida_edit,
            self.entrada2_edit,
            self.saida2_edit,
        ):
            campo.timeChanged.connect(self._atualizar_resultado)
        for caixa in (self.almoco_check, self.jantar_check, self.segundo_check):
            caixa.toggled.connect(self._atualizar_resultado)
        self.acerto_spin.valueChanged.connect(self._atualizar_resultado)
        self.horas_spin.valueChanged.connect(self._atualizar_resultado)

        if self._so_leitura:
            for widget in (
                *self._radios.values(),
                self.bloco_util,
                self.bloco_horas,
                self.observacoes_edit,
            ):
                widget.setEnabled(False)
            self.guardar_button.hide()
            self.guardar_seguinte_button.hide()
            self.apagar_button.hide()
            self.fechar_button.setDefault(True)

        self._carregar(dia)

    # ------------------------------------------------------------------
    @property
    def dia(self) -> date:
        return self._dia

    def _carregar(self, dia: date) -> None:
        self._dia = dia
        try:
            self._registo = self._obter(dia)
        except Exception as erro:  # noqa: BLE001 - base em baixo: mostra e deixa fechar
            self._registo = None
            self.erro_label.setText(f"Não foi possível ler este dia: {erro}")
        registo = self._registo
        config = self._config

        self.titulo_label.setText(regra.titulo_dia(dia))
        partes = []
        nome_feriado = regra.feriado(dia)
        if nome_feriado:
            partes.append(f"Feriado: {nome_feriado}")
        if registo is None:
            partes.append("Novo registo" if not self._so_leitura else "Sem registo")
        else:
            partes.append("Já registado")
            if registo.origem == "app_antiga":
                partes.append("veio da app antiga")
        self.subtitulo_label.setText(" · ".join(partes))

        tipo = registo.tipo if registo is not None else regra.tipo_por_defeito(dia)
        self._radios[tipo].setChecked(True)
        util = registo is not None and registo.tipo == regra.TIPO_UTIL
        self.entrada_edit.setTime(_qtime(registo.entrada if util else config.entrada_habitual))
        self.saida_edit.setTime(_qtime(registo.saida if util else config.saida_habitual))
        self.almoco_check.setChecked(registo.almoco if util else config.descontar_almoco)
        self.jantar_check.setChecked(registo.jantar if util else False)
        tem_segundo = util and registo.entrada2 is not None
        self.segundo_check.setChecked(bool(tem_segundo))
        self.entrada2_edit.setTime(_qtime(registo.entrada2 if tem_segundo else 20 * 60))
        self.saida2_edit.setTime(_qtime(registo.saida2 if tem_segundo else 23 * 60))
        self.acerto_spin.setValue((registo.acerto if util else 0) / 60)
        if registo is not None and not util:
            self.horas_spin.setValue(registo.horas / 60)
        else:
            self.horas_spin.setValue(
                regra.HORAS_FOLGA_PADRAO / 60 if tipo == regra.TIPO_FOLGA else 0
            )
        self.observacoes_edit.setText(registo.observacoes if registo is not None else "")
        self.apagar_button.setVisible(not self._so_leitura and registo is not None)
        self.erro_label.setText("")
        self._ao_mudar_tipo()

    def _ir_para(self, dia: date) -> None:
        self._carregar(dia)

    def tipo(self) -> str:
        for tipo, radio in self._radios.items():
            if radio.isChecked():
                return tipo
        return regra.TIPO_UTIL

    def dados(self) -> regra.DadosDia:
        tipo = self.tipo()
        if tipo == regra.TIPO_UTIL:
            segundo = self.segundo_check.isChecked()
            return regra.DadosDia(
                tipo=tipo,
                entrada=_minutos(self.entrada_edit),
                saida=_minutos(self.saida_edit),
                entrada2=_minutos(self.entrada2_edit) if segundo else None,
                saida2=_minutos(self.saida2_edit) if segundo else None,
                almoco=self.almoco_check.isChecked(),
                jantar=self.jantar_check.isChecked(),
                acerto=int(round(self.acerto_spin.value() * 60)),
            )
        return regra.DadosDia(tipo=tipo, horas=int(round(self.horas_spin.value() * 60)))

    def _ao_mudar_tipo(self, *_args) -> None:
        tipo = self.tipo()
        util = tipo == regra.TIPO_UTIL
        self.bloco_util.setVisible(util)
        self.bloco_horas.setVisible(not util)
        self.horas_label.setText(
            "Horas a descontar" if tipo == regra.TIPO_FOLGA else "Horas trabalhadas"
        )
        if tipo == regra.TIPO_FOLGA and not self.horas_spin.value():
            self.horas_spin.setValue(regra.HORAS_FOLGA_PADRAO / 60)
        self.tipo_ajuda.setText(regra.AJUDA_TIPOS[tipo])
        self._atualizar_segundo()
        self._atualizar_resultado()

    def _atualizar_segundo(self, *_args) -> None:
        ligado = self.segundo_check.isChecked() and not self._so_leitura
        self.entrada2_edit.setEnabled(ligado)
        self.saida2_edit.setEnabled(ligado)

    def _atualizar_resultado(self, *_args) -> None:
        dados = self.dados()
        try:
            calculo = regra.calcular_dia(
                dados,
                horas_normais=self._config.horas_normais_dia,
                pausa=self._config.pausa_almoco,
            )
        except regra.ErroRegistoHoras as erro:
            self.resultado_label.setText("—")
            self.detalhe_label.setText(str(erro))
            self.detalhe_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
            return
        self.resultado_label.setText(
            regra.horas_como_na_folha(dados.tipo, calculo.normais, calculo.extra, calculo.trabalhado)
            or "0"
        )
        partes: list[str] = []
        if dados.tipo == regra.TIPO_UTIL:
            partes.append(f"{regra.formatar_total(calculo.trabalhado)} trabalhadas")
            if calculo.extra > 0:
                partes.append(f"{regra.formatar_total(calculo.extra)} extra")
            elif calculo.extra < 0:
                partes.append(f"desconta {regra.formatar_total(-calculo.extra)} ao mês")
            else:
                partes.append("sem horas extra")
            if dados.acerto:
                partes.append(f"inclui acerto de {regra.formatar_total(dados.acerto, com_mais=True)}")
            if (calculo.saida2 or calculo.saida or 0) > regra.MINUTOS_DIA:
                partes.append("acaba no dia seguinte")
        elif dados.tipo == regra.TIPO_FOLGA:
            partes.append(f"desconta {regra.formatar_total(dados.horas)} ao total do mês")
        elif dados.horas:
            partes.append(f"{regra.formatar_total(dados.horas)} extra")
        else:
            partes.append(f"{regra.NOMES_TIPOS[dados.tipo]} sem horas trabalhadas")
        self.detalhe_label.setText(" · ".join(partes))
        cor = tema.TEXTO_ERRO if calculo.extra < 0 else tema.CASTANHO_MEDIO
        self.detalhe_label.setStyleSheet(f"color: {cor};")

    # ------------------------------------------------------------------
    def _gravar(self, *, seguinte: bool) -> None:
        if self._guardar is None:
            return
        dados = self.dados()
        try:
            regra.calcular_dia(
                dados,
                horas_normais=self._config.horas_normais_dia,
                pausa=self._config.pausa_almoco,
            )
        except regra.ErroRegistoHoras as erro:
            self.erro_label.setText(str(erro))
            return
        try:
            gravado = self._guardar(self._dia, dados, self.observacoes_edit.text())
        except regra.ErroRegistoHoras as erro:
            self.erro_label.setText(str(erro))
            return
        except Exception as erro:  # noqa: BLE001 - mostra e deixa tentar outra vez
            self.erro_label.setText(f"Não foi possível guardar: {erro}")
            return
        if gravado is None:
            # Quem gravou decidiu não gravar (ex.: a pessoa desistiu num aviso).
            return
        self.alterou = True
        if seguinte:
            self._carregar(self._dia + timedelta(days=1))
            return
        self.accept()

    def _apagar_dia(self) -> None:
        if self._apagar is None or self._registo is None:
            return
        resposta = QMessageBox.question(
            self,
            "Apagar dia",
            f"Apagar o registo de {regra.titulo_dia(self._dia)}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        try:
            apagado = self._apagar(self._dia)
        except Exception as erro:  # noqa: BLE001
            self.erro_label.setText(f"Não foi possível apagar: {erro}")
            return
        if apagado:
            self.alterou = True
            self.accept()
