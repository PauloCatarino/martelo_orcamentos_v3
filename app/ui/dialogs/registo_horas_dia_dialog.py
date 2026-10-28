"""Registar (ou ver) as horas de um dia.

O diálogo não fala com a base de dados: quem o abre dá-lhe três funções —
ler um dia, guardar e apagar — e ele trata só do formulário. Assim o mesmo
diálogo serve para a própria pessoa (edita) e para o administrador a ver as
horas de outra pessoa (só consulta).

Desde 19-10-2026 (respostas do Paulo ao mockup) cada dia tem linhas
Entrada/Saída: uma por defeito e o botão «+» acrescenta outra por baixo (até
6), em todos os tipos de dia menos a Folga. As linhas são postas pela ordem do
dia; se se sobrepõem, a janela avisa a vermelho e não deixa guardar. Quando o
intervalo entre duas linhas já é a hora de almoço, «Descontar almoço»
desliga-se sozinho e a janela diz porquê. No fim de semana, feriado e férias
ainda se pode escrever só o total de horas (é assim que estão os dias antigos).

No Teletrabalho (28-10-2026) o horário habitual está no ponto da empresa: o
dia novo abre com a linha vazia, para escrever só as horas fora do horário, e
cada linha diz o que conta e o que fica no ponto. Não há almoço nem «Ausência
justificada»; um dia sem linhas guarda-se na mesma («ponto»).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from html import escape

from PySide6.QtCore import Qt
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
from app.ui.widgets.campo_hora import CampoHora
from app.ui.widgets.combo_sem_scroll import SpinDuploSemScroll

#: Saídas mais comuns, num clique (a folha em papel ia até à meia-noite).
SAIDAS_RAPIDAS = (17, 18, 19, 20, 21, 22)
DICA_NOITE = (
    " Se sair depois da meia-noite, indique a hora do dia seguinte (ex.: 01:30)."
)


def _spin_horas(minimo: float, maximo: float, tooltip: str) -> SpinDuploSemScroll:
    spin = SpinDuploSemScroll()
    spin.setRange(minimo, maximo)
    spin.setSingleStep(0.5)
    spin.setDecimals(1)
    spin.setSuffix(" h")
    spin.setToolTip(tooltip)
    return spin


def ajuda_do_tipo(tipo: str, config: regra.ConfigHoras) -> str:
    """O texto por baixo dos tipos de dia (o do teletrabalho leva o horário da pessoa)."""
    if tipo == regra.TIPO_TELETRABALHO:
        entrada, saida = (regra.hora_texto(m) for m in config.horario)
        return (
            f"Dia na empresa com horas extra fora do horário. Das {entrada} às {saida} "
            "as horas ficam no ponto da empresa e aqui não contam. Só contam as horas "
            f"antes das {entrada} ou depois das {saida}, todas como extra. Não desconta nada."
        )
    return regra.AJUDA_TIPOS[tipo]


class LinhaHorario(QWidget):
    """Uma linha Entrada/Saída: número, as duas horas, o ✕ e (na última) as saídas rápidas."""

    def __init__(self, dialogo: "RegistoHorasDiaDialog") -> None:
        super().__init__()
        self.numero_label = QLabel()
        self.numero_label.setFixedSize(20, 20)
        self.numero_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.numero_label.setStyleSheet(
            f"background-color: {tema.BEGE_AREIA}; color: {tema.CASTANHO_ESCURO};"
            " border-radius: 10px; font-size: 11px; font-weight: bold;"
        )
        self.entrada = CampoHora(sugestao=dialogo._sugestao_entrada)
        self.saida = CampoHora(sugestao=lambda: dialogo._sugestao_saida(self))
        self.tirar_button = QPushButton("✕")
        self.tirar_button.setFixedWidth(30)
        self.tirar_button.clicked.connect(lambda: dialogo._tirar_linha(self))
        #: No teletrabalho: «conta 2h», «conta 2h · 9h no ponto», «no ponto, não conta».
        self.conta_label = QLabel()
        self.conta_label.hide()

        self.rapidas = QWidget()
        rapidas = QHBoxLayout(self.rapidas)
        rapidas.setContentsMargins(0, 0, 0, 0)
        rapidas.setSpacing(4)
        self.botoes_rapidos: list[QPushButton] = []
        for hora in SAIDAS_RAPIDAS:
            botao = QPushButton(f"{hora}h")
            botao.setFixedWidth(42)
            botao.clicked.connect(lambda _c=False, h=hora: dialogo._saida_rapida(self, h))
            rapidas.addWidget(botao)
            self.botoes_rapidos.append(botao)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.numero_label)
        layout.addWidget(QLabel("Entrada"))
        layout.addWidget(self.entrada)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Saída"))
        layout.addWidget(self.saida)
        layout.addWidget(self.tirar_button)
        layout.addWidget(self.conta_label)
        layout.addStretch()
        layout.addWidget(self.rapidas)

    def numerar(self, numero: int, total: int) -> None:
        self.numero_label.setText(str(numero))
        sufixo = f" (linha {numero})" if total > 1 else ""
        self.entrada.setToolTip(f"Hora a que começou{sufixo}.")
        self.saida.setToolTip(f"Hora a que acabou{sufixo}.{DICA_NOITE}")
        self.tirar_button.setToolTip(f"Tirar a linha {numero}")
        for botao, hora in zip(self.botoes_rapidos, SAIDAS_RAPIDAS):
            botao.setToolTip(f"Saída{sufixo} às {hora}h00")

    def valores(self) -> tuple[int | None, int | None]:
        return (self.entrada.minutos(), self.saida.minutos())

    def definir(self, entrada: int | None, saida: int | None) -> None:
        self.entrada.definir(entrada)
        self.saida.definir(saida)


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
        #: As linhas da janela, de cima para baixo.
        self.linhas: list[LinhaHorario] = []
        #: A pessoa já mexeu nas horas deste dia (mudar de tipo não as apaga).
        self._tocado = False
        self._a_carregar = False
        #: Almoço automático: o intervalo que já é o almoço, e se fomos nós a
        #: desligar o «Descontar almoço» por causa dele.
        self._intervalo_almoco: tuple[int, int] | None = None
        self._almoco_desligado_sozinho = False

        titulo = "Registo de horas"
        if nome:
            titulo += f" — {nome}"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(600)

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
            radio.setToolTip(ajuda_do_tipo(tipo, config))
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

        # ---- linhas Entrada/Saída ----------------------------------------
        self.bloco_linhas = QWidget()
        self.linhas_layout = QVBoxLayout(self.bloco_linhas)
        self.linhas_layout.setContentsMargins(0, 0, 0, 0)
        self.linhas_layout.setSpacing(6)
        self.mais_button = QPushButton("+  Acrescentar entrada e saída")
        self.mais_button.clicked.connect(self._mais_linha)
        mais = QHBoxLayout()
        mais.addWidget(self.mais_button)
        mais.addStretch()

        self.almoco_check = QCheckBox(
            f"Descontar almoço ({regra.formatar_total(config.pausa_almoco)})"
        )
        self.almoco_check.setToolTip(
            "Tira a pausa do almoço às horas do dia. Se o intervalo entre duas "
            "linhas já é o almoço, desliga-se sozinho."
        )
        self.almoco_check.clicked.connect(self._almoco_mexido)
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
        self.nota_almoco_label = QLabel()
        self.nota_almoco_label.setWordWrap(True)

        self.acerto_spin = _spin_horas(
            -12,
            12,
            "Acerto de horas: some horas feitas fora do horário (ex.: +2) ou tire "
            "pausas a mais (ex.: −1). Normalmente fica a 0.",
        )
        self.linha_acerto = QWidget()
        acerto = QHBoxLayout(self.linha_acerto)
        acerto.setContentsMargins(0, 0, 0, 0)
        acerto.addWidget(QLabel("Acerto"))
        acerto.addWidget(self.acerto_spin)
        acerto.addStretch()

        self.bloco_pausas = QWidget()
        layout_pausas = QVBoxLayout(self.bloco_pausas)
        layout_pausas.setContentsMargins(0, 0, 0, 0)
        layout_pausas.addLayout(mais)
        layout_pausas.addLayout(pausas)
        layout_pausas.addWidget(self.nota_almoco_label)
        layout_pausas.addWidget(self.linha_acerto)

        # ---- só o total de horas (folga, e fora do horário sem linhas) ------
        self.horas_label = QLabel("Horas trabalhadas")
        self.horas_spin = _spin_horas(0, 24, "Número de horas (pode usar meias horas: 2,5).")
        self.bloco_horas = QWidget()
        layout_horas = QHBoxLayout(self.bloco_horas)
        layout_horas.setContentsMargins(0, 0, 0, 0)
        layout_horas.addWidget(self.horas_label)
        layout_horas.addWidget(self.horas_spin)
        layout_horas.addStretch()
        self.so_total_check = QCheckBox("Só o total de horas")
        self.so_total_check.setToolTip(
            "Para quando não se lembra das horas de entrada e saída: escreve só o total."
        )
        self.so_total_check.toggled.connect(self._ao_mudar_so_total)
        self.nota_dia_label = QLabel()
        self.nota_dia_label.setWordWrap(True)
        self.nota_dia_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        caixa_horas = QGroupBox("Horas")
        layout_caixa = QVBoxLayout(caixa_horas)
        layout_caixa.addWidget(self.bloco_linhas)
        layout_caixa.addWidget(self.bloco_pausas)
        layout_caixa.addWidget(self.bloco_horas)
        layout_caixa.addWidget(self.so_total_check)
        layout_caixa.addWidget(self.nota_dia_label)

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
        self.detalhe_label.setTextFormat(Qt.TextFormat.RichText)
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
        # Com menos linhas (ao mudar de dia) o espaço que sobra fica aqui, e não
        # espalhado dentro da caixa das horas.
        layout.addStretch(1)
        layout.addLayout(botoes)

        for caixa in (self.almoco_check, self.jantar_check):
            caixa.toggled.connect(self._atualizar_resultado)
        for spin in (self.acerto_spin, self.horas_spin):
            spin.valueChanged.connect(self._atualizar_resultado)

        if self._so_leitura:
            for widget in (
                *self._radios.values(),
                self.bloco_linhas,
                self.bloco_pausas,
                self.bloco_horas,
                self.so_total_check,
                self.observacoes_edit,
            ):
                widget.setEnabled(False)
            self.mais_button.hide()
            self.guardar_button.hide()
            self.guardar_seguinte_button.hide()
            self.apagar_button.hide()
            self.fechar_button.setDefault(True)

        self._carregar(dia)

    # ------------------------------------------------------------------
    @property
    def dia(self) -> date:
        return self._dia

    def tipo(self) -> str:
        for tipo, radio in self._radios.items():
            if radio.isChecked():
                return tipo
        return regra.TIPO_UTIL

    def _com_horario(self) -> bool:
        return self.tipo() in regra.TIPOS_COM_HORARIO

    def _so_total(self) -> bool:
        return self.tipo() in regra.TIPOS_FORA_DO_HORARIO and self.so_total_check.isChecked()

    def _usa_linhas(self) -> bool:
        return self.tipo() != regra.TIPO_FOLGA and not self._so_total()

    def _teletrabalho(self) -> bool:
        return self.tipo() == regra.TIPO_TELETRABALHO

    def _periodos_padrao(self, tipo: str) -> list[tuple[int | None, int | None]]:
        # No teletrabalho o horário está no ponto: escrevem-se só as horas de fora.
        if tipo == regra.TIPO_UTIL:
            return [self._config.horario]
        return [(None, None)]

    def _almoco_padrao(self, tipo: str) -> bool:
        """O almoço só se desconta por defeito no dia útil (no teletrabalho é no ponto)."""
        return self._config.descontar_almoco if tipo == regra.TIPO_UTIL else False

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
            if registo.teletrabalho_regra_antiga:
                partes.append("gravado com a regra antiga do teletrabalho (ao guardar, fica com a nova)")
        self.subtitulo_label.setText(" · ".join(partes))

        self._a_carregar = True
        try:
            tipo = (
                registo.tipo if registo is not None
                else regra.tipo_por_defeito(dia, config.tipo_habitual)
            )
            self._radios[tipo].setChecked(True)
            com_horario = tipo in regra.TIPOS_COM_HORARIO
            if registo is not None:
                periodos = list(registo.lista_periodos) or [(None, None)]
                almoco, jantar = registo.almoco, registo.jantar
                acerto = registo.acerto if com_horario else 0
                so_total = registo.so_total
                horas = registo.horas
            else:
                periodos = self._periodos_padrao(tipo)
                almoco = self._almoco_padrao(tipo)
                jantar, acerto, so_total = False, 0, False
                horas = regra.HORAS_FOLGA_PADRAO if tipo == regra.TIPO_FOLGA else 0
            self._definir_linhas(periodos)
            self.almoco_check.setChecked(almoco)
            self.jantar_check.setChecked(jantar)
            self.acerto_spin.setValue(acerto / 60)
            self.so_total_check.setChecked(so_total)
            self.horas_spin.setValue(horas / 60)
            self.observacoes_edit.setText(registo.observacoes if registo is not None else "")
            # Um dia gravado abre como foi gravado: o almoço automático só
            # reage ao que se mudar daqui para a frente.
            self._intervalo_almoco = self._intervalo_atual()
            self._almoco_desligado_sozinho = False
            self._tocado = registo is not None
        finally:
            self._a_carregar = False
        self.apagar_button.setVisible(not self._so_leitura and registo is not None)
        self.erro_label.setText("")
        self._ao_mudar_tipo()

    def _ir_para(self, dia: date) -> None:
        self._carregar(dia)

    # ---- linhas ------------------------------------------------------
    def _definir_linhas(self, periodos: list[tuple[int | None, int | None]]) -> None:
        while len(self.linhas) > len(periodos):
            self._remover_widget(self.linhas.pop())
        while len(self.linhas) < len(periodos):
            self._nova_linha()
        for linha, (entrada, saida) in zip(self.linhas, periodos):
            linha.definir(entrada, saida)
        self._arrumar_linhas()

    def _nova_linha(self) -> LinhaHorario:
        linha = LinhaHorario(self)
        for campo in (linha.entrada, linha.saida):
            campo.alterado.connect(self._atualizar_resultado)
            campo.editado.connect(self._marcar_tocado)
        linha.saida.editingFinished.connect(self._ordenar_linhas)
        if self._so_leitura:
            linha.tirar_button.hide()
            linha.rapidas.hide()
        self.linhas.append(linha)
        self.linhas_layout.addWidget(linha)
        return linha

    def _remover_widget(self, linha: LinhaHorario) -> None:
        self.linhas_layout.removeWidget(linha)
        linha.hide()
        linha.deleteLater()

    def _arrumar_linhas(self) -> None:
        total = len(self.linhas)
        com_horario = self._com_horario()
        for numero, linha in enumerate(self.linhas, start=1):
            linha.numerar(numero, total)
            linha.tirar_button.setVisible(numero > 1 and not self._so_leitura)
            linha.rapidas.setVisible(numero == total and com_horario and not self._so_leitura)
        cheio = total >= regra.MAX_PERIODOS
        self.mais_button.setEnabled(not cheio)
        self.mais_button.setToolTip(
            f"Já tem {regra.MAX_PERIODOS} linhas (o máximo)." if cheio
            else "Acrescenta outra linha Entrada/Saída por baixo, para quando saiu e "
            "voltou no mesmo dia."
        )

    def _mais_linha(self) -> None:
        if len(self.linhas) >= regra.MAX_PERIODOS:
            return
        linha = self._nova_linha()
        self._tocado = True
        self._arrumar_linhas()
        linha.entrada.setFocus()
        self._atualizar_resultado()

    def _tirar_linha(self, linha: LinhaHorario) -> None:
        if linha not in self.linhas or len(self.linhas) <= 1:
            return
        self.linhas.remove(linha)
        self._remover_widget(linha)
        self._tocado = True
        self._arrumar_linhas()
        self._atualizar_resultado()

    def _saida_rapida(self, linha: LinhaHorario, hora: int) -> None:
        if linha.entrada.minutos() is None and linha is self.linhas[0]:
            if not self._teletrabalho():
                linha.entrada.definir(self._config.entrada_habitual)
            elif hora * 60 > self._config.saida_habitual:
                # Teletrabalho: as horas de fora começam quando acaba o horário.
                linha.entrada.definir(self._config.saida_habitual)
        linha.saida.definir(hora * 60)
        self._tocado = True

    def _sugestao_entrada(self) -> int | None:
        """A primeira seta num campo vazio: a saída da linha de cima, ou a entrada habitual.

        No teletrabalho, sem linha de cima, é a hora a que acaba o horário.
        """
        anteriores = [l.saida.minutos() for l in self.linhas if l.saida.minutos() is not None]
        if anteriores:
            return anteriores[-1]
        if self._teletrabalho():
            return self._config.saida_habitual
        return self._config.entrada_habitual

    def _sugestao_saida(self, linha: LinhaHorario) -> int | None:
        if linha.entrada.minutos() is not None:
            return (linha.entrada.minutos() + 60) % regra.MINUTOS_DIA
        return self._config.saida_habitual

    def _marcar_tocado(self) -> None:
        if not self._a_carregar:
            self._tocado = True

    def _ordenar_linhas(self) -> None:
        """Põe as linhas pela ordem do dia (as vazias ficam no fim), se as contas baterem."""
        if self._a_carregar or not self._usa_linhas():
            return
        try:
            periodos = regra.ordenar_periodos(l.valores() for l in self.linhas)
        except regra.ErroRegistoHoras:
            return
        if any(l.entrada.invalido() or l.saida.invalido() for l in self.linhas):
            return
        cheias = [l.valores() for l in self.linhas if l.valores() != (None, None)]
        ordem = [(e % regra.MINUTOS_DIA, s % regra.MINUTOS_DIA) for e, s in periodos]
        if cheias == ordem:
            return
        vazias = len(self.linhas) - len(ordem)
        self._definir_linhas([*ordem, *([(None, None)] * vazias)])

    def _intervalo_atual(self) -> tuple[int, int] | None:
        if not self._usa_linhas():
            return None
        try:
            return regra.intervalo_almoco(regra.ordenar_periodos(l.valores() for l in self.linhas))
        except regra.ErroRegistoHoras:
            return None

    def _almoco_mexido(self, _marcado: bool) -> None:
        """A pessoa mexeu no «Descontar almoço»: a escolha é dela."""
        self._almoco_desligado_sozinho = False

    def _almoco_automatico(self) -> None:
        """Desliga (ou volta a ligar) o almoço quando um intervalo entre linhas já o é."""
        try:
            periodos = regra.ordenar_periodos(l.valores() for l in self.linhas)
        except regra.ErroRegistoHoras:
            return  # a meio de escrever uma linha: não mexe no almoço
        intervalo = regra.intervalo_almoco(periodos)
        if intervalo == self._intervalo_almoco:
            return
        if intervalo is not None and self._intervalo_almoco is None and self.almoco_check.isChecked():
            self.almoco_check.blockSignals(True)
            self.almoco_check.setChecked(False)
            self.almoco_check.blockSignals(False)
            self._almoco_desligado_sozinho = True
        elif intervalo is None and self._almoco_desligado_sozinho:
            self.almoco_check.blockSignals(True)
            self.almoco_check.setChecked(True)
            self.almoco_check.blockSignals(False)
            self._almoco_desligado_sozinho = False
        self._intervalo_almoco = intervalo

    # ---- tipo e visibilidade --------------------------------------------
    def _ao_mudar_tipo(self, _id: int = -1, marcado: bool = True) -> None:
        if not marcado:
            return
        tipo = self.tipo()
        if not self._a_carregar and not self._tocado:
            # Dia por mexer: cada tipo abre com as suas horas (um sábado novo
            # não pode herdar as 08:00–17:00 do dia útil).
            self._a_carregar = True
            try:
                self._definir_linhas(self._periodos_padrao(tipo))
                self.almoco_check.setChecked(self._almoco_padrao(tipo))
                self._intervalo_almoco = None
                self._almoco_desligado_sozinho = False
            finally:
                self._a_carregar = False
        if tipo == regra.TIPO_FOLGA and not self.horas_spin.value():
            self.horas_spin.setValue(regra.HORAS_FOLGA_PADRAO / 60)
        self.tipo_ajuda.setText(ajuda_do_tipo(tipo, self._config))
        self._atualizar_visibilidade()
        self._atualizar_resultado()

    def _ao_mudar_so_total(self, _marcado: bool) -> None:
        if not self._a_carregar:
            self._tocado = True
        self._atualizar_visibilidade()
        self._atualizar_resultado()

    def _atualizar_visibilidade(self) -> None:
        tipo = self.tipo()
        com_horario = tipo in regra.TIPOS_COM_HORARIO
        fora = tipo in regra.TIPOS_FORA_DO_HORARIO
        linhas = self._usa_linhas()
        self.bloco_linhas.setVisible(linhas)
        self.bloco_pausas.setVisible(linhas)
        self.almoco_check.setVisible(tipo != regra.TIPO_TELETRABALHO)
        self.jantar_check.setVisible(com_horario)
        self.linha_acerto.setVisible(com_horario)
        self.bloco_horas.setVisible(not linhas)
        self.horas_label.setText(
            "Horas a descontar" if tipo == regra.TIPO_FOLGA else "Horas trabalhadas"
        )
        self.so_total_check.setVisible(fora)
        registo = self._registo
        antigo = registo is not None and registo.so_total and self._so_total()
        self.nota_dia_label.setText(
            "Este dia foi registado só com o total. Pode deixá-lo assim, ou "
            "desmarcar «Só o total de horas» e pôr as entradas e saídas."
            if antigo else ""
        )
        self.nota_dia_label.setVisible(antigo)
        self._arrumar_linhas()

    # ---- contas --------------------------------------------------------
    def _erro_nos_campos(self) -> str:
        if not self._usa_linhas():
            return ""
        for numero, linha in enumerate(self.linhas, start=1):
            for campo in (linha.entrada, linha.saida):
                if campo.invalido():
                    onde = f" na linha {numero}" if len(self.linhas) > 1 else ""
                    return (
                        f"Hora inválida{onde}: «{campo.text().strip()}». Escreva, por "
                        "exemplo, 08:30."
                    )
        return ""

    def dados(self) -> regra.DadosDia:
        tipo = self.tipo()
        if not self._usa_linhas():
            return regra.DadosDia(tipo=tipo, horas=int(round(self.horas_spin.value() * 60)))
        com_horario = tipo in regra.TIPOS_COM_HORARIO
        return regra.DadosDia(
            tipo=tipo,
            periodos=tuple(linha.valores() for linha in self.linhas),
            almoco=tipo != regra.TIPO_TELETRABALHO and self.almoco_check.isChecked(),
            jantar=com_horario and self.jantar_check.isChecked(),
            acerto=int(round(self.acerto_spin.value() * 60)) if com_horario else 0,
        )

    def _calcular(self, dados: regra.DadosDia) -> regra.CalculoDia:
        try:
            return regra.calcular_dia(
                dados,
                horas_normais=self._config.horas_normais_dia,
                pausa=self._config.pausa_almoco,
                horario=self._config.horario,
            )
        except regra.ErroRegistoHoras as erro:
            if str(erro) == "Indique as horas trabalhadas." and self._usa_linhas():
                raise regra.ErroRegistoHoras(
                    "Indique as horas trabalhadas: a entrada e a saída, ou marque «Só o "
                    "total de horas»."
                ) from erro
            raise

    def _atualizar_resultado(self, *_args) -> None:
        if self._a_carregar:
            return
        self._atualizar_contas_linhas()
        erro = self._erro_nos_campos()
        if erro:
            self._mostrar_erro(erro)
            self._atualizar_nota_almoco(None)
            return
        if self._usa_linhas() and not self._teletrabalho():
            self._almoco_automatico()
        dados = self.dados()
        try:
            calculo = self._calcular(dados)
        except regra.ErroRegistoHoras as erro_regra:
            self._mostrar_erro(str(erro_regra))
            self._atualizar_nota_almoco(None)
            return
        self.resultado_label.setText(
            regra.horas_como_na_folha(
                dados.tipo, calculo.normais, calculo.extra, calculo.trabalhado
            )
            or "0"
        )
        self.detalhe_label.setText(self._detalhe(dados, calculo))
        self.detalhe_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")
        self._atualizar_nota_almoco(regra.intervalo_almoco(calculo.periodos))

    def _mostrar_erro(self, texto: str) -> None:
        self.resultado_label.setText("—")
        self.detalhe_label.setText(escape(texto))
        self.detalhe_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")

    def _atualizar_contas_linhas(self) -> None:
        """No teletrabalho, cada linha diz o que conta e o que fica no ponto (a cinzento)."""
        teletrabalho = self._teletrabalho() and self._usa_linhas()
        horario = self._config.horario
        de, ate = (regra.hora_texto(m) for m in horario)
        for linha in self.linhas:
            entrada, saida = linha.valores()
            if not teletrabalho or entrada is None or saida is None:
                linha.conta_label.hide()
                continue
            ((entrada, saida),) = regra.ordenar_periodos([(entrada, saida)])
            no_ponto = sum(b - a for a, b in regra.partes_no_horario([(entrada, saida)], horario))
            conta = saida - entrada - no_ponto
            total = regra.formatar_total
            if not conta:
                texto, fundo, cor = "no ponto, não conta", tema.CINZA_SUAVE, tema.CINZA_ESCURO
            else:
                texto = f"conta {total(conta)}" + (f" · {total(no_ponto)} no ponto" if no_ponto else "")
                fundo, cor = tema.VERDE_SUAVE, tema.VERDE_ESCURO
            linha.conta_label.setText(texto)
            linha.conta_label.setStyleSheet(
                f"background-color: {fundo}; color: {cor}; border-radius: 8px; padding: 1px 8px;"
            )
            linha.conta_label.setToolTip(
                f"Só contam as horas antes das {de} ou depois das {ate}; as do horário "
                "estão no ponto da empresa."
            )
            linha.conta_label.show()

    def _detalhe(self, dados: regra.DadosDia, calculo: regra.CalculoDia) -> str:
        total = regra.formatar_total
        vermelho = f"<span style='color: {tema.TEXTO_ERRO};'>{{}}</span>"
        cinzento = f"<span style='color: {tema.CAMPO_BLOQUEADO_TEXTO};'>{{}}</span>"
        partes: list[str] = []
        if dados.tipo == regra.TIPO_TELETRABALHO:
            partes.append(
                f"{total(calculo.extra)} extra (fora do horário)" if calculo.extra
                else "sem horas extra"
            )
            no_ponto = regra.partes_no_horario(calculo.periodos, self._config.horario)
            if no_ponto:
                bocados = " e ".join(
                    f"{regra.hora_texto(de)}–{regra.hora_texto(ate)}" for de, ate in no_ponto
                )
                partes.append(cinzento.format(f"{bocados} fica no ponto da empresa"))
            elif not calculo.periodos:
                partes.append(cinzento.format("o horário fica no ponto da empresa"))
            partes.append("não desconta nada")
        elif dados.tipo == regra.TIPO_UTIL:
            partes.append(f"{total(calculo.trabalhado)} trabalhadas")
            if calculo.extra > 0:
                partes.append(f"{total(calculo.extra)} extra")
            elif calculo.extra < 0:
                partes.append(vermelho.format(f"desconta {total(-calculo.extra)} ao mês"))
            else:
                partes.append("sem horas extra")
        elif dados.tipo == regra.TIPO_FOLGA:
            partes.append(vermelho.format(f"desconta {total(dados.horas)} ao total do mês"))
        elif calculo.trabalhado:
            partes.append(f"{total(calculo.trabalhado)} extra")
        else:
            partes.append(f"{regra.NOMES_TIPOS[dados.tipo]} sem horas trabalhadas")
        if dados.tipo in regra.TIPOS_COM_HORARIO and dados.acerto:
            partes.append(f"inclui acerto de {total(dados.acerto, com_mais=True)}")
        if calculo.periodos and calculo.periodos[-1][1] > regra.MINUTOS_DIA:
            partes.append("acaba no dia seguinte")
        return " · ".join(partes)

    def _atualizar_nota_almoco(self, intervalo: tuple[int, int] | None) -> None:
        texto, cor = "", tema.CASTANHO_MEDIO
        if intervalo is not None and self._usa_linhas() and not self._teletrabalho():
            de, ate = (regra.hora_texto(m) for m in intervalo)
            if self.almoco_check.isChecked():
                texto = (
                    f"O intervalo {de} → {ate} parece ser o almoço: está a descontar a "
                    "pausa duas vezes?"
                )
                cor = tema.TEXTO_AVISO
            elif self._almoco_desligado_sozinho:
                texto = f"Almoço não descontado: o intervalo {de} → {ate} já inclui a pausa."
        self.nota_almoco_label.setText(texto)
        self.nota_almoco_label.setStyleSheet(f"color: {cor};")
        self.nota_almoco_label.setVisible(bool(texto))

    # ------------------------------------------------------------------
    def _gravar(self, *, seguinte: bool) -> None:
        if self._guardar is None:
            return
        erro = self._erro_nos_campos()
        if erro:
            self.erro_label.setText(erro)
            return
        self._ordenar_linhas()
        dados = self.dados()
        try:
            self._calcular(dados)
        except regra.ErroRegistoHoras as erro_regra:
            self.erro_label.setText(str(erro_regra))
            return
        try:
            gravado = self._guardar(self._dia, dados, self.observacoes_edit.text())
        except regra.ErroRegistoHoras as erro_regra:
            self.erro_label.setText(str(erro_regra))
            return
        except Exception as erro_base:  # noqa: BLE001 - mostra e deixa tentar outra vez
            self.erro_label.setText(f"Não foi possível guardar: {erro_base}")
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
