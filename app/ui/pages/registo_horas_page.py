"""Registo de Horas: a folha de horas do mês, dentro do Martelo.

Substitui a app PHP isolada (decisão do Paulo, 02-10-2026). Cada pessoa vê e
regista as suas horas; o administrador escolhe de quem quer ver a folha (só
consulta). As regras de cálculo estão em :mod:`app.domain.registo_horas`.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core import diario_bordo
from app.db.session import SessionLocal
from app.domain import registo_horas as regra
from app.services import registo_horas_importacao as importacao
from app.services.registo_horas_service import RegistoHorasService
from app.ui import tema
from app.ui.dialogs.registo_horas_definicoes_dialog import RegistoHorasDefinicoesDialog
from app.ui.dialogs.registo_horas_dia_dialog import RegistoHorasDiaDialog
from app.ui.dialogs.registo_horas_envio_dialog import ACAO_CORRIGIR
from app.ui.helpers import registo_horas_acoes as acoes
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.combo_sem_scroll import ComboSemScroll

COLUNAS = (
    "Dia", "", "Tipo", "Horário", "Horas", "Normais", "Extra",
    "Subs. Alimentação", "Observações",
)
COL_HORARIO = 3
COL_EXTRA = 6
COL_SUBSIDIO = 7
COL_OBS = 8
DICA_SUBSIDIO = (
    "Subsídio de alimentação: extra pago pela empresa nos dias fora do horário "
    "normal (sábado, domingo, feriado e dia de férias trabalhado) — 1,25 € por "
    "cada hora inteira, no máximo 10 € por dia. Os dias úteis não contam, "
    "mesmo com horas extra."
)
#: Quantos meses aparecem na lista «Últimos meses».
MESES_HISTORICO = 12


class RegistoHorasPage(QWidget):
    def __init__(
        self,
        *,
        user_id: int | None,
        nome: str = "",
        email: str = "",
        admin: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._user_id = user_id
        self._nome_conta = nome
        self._email_conta = email
        self._admin = admin
        #: De quem é a folha que está à vista (o admin pode ver a de outros).
        self._visto_id = user_id
        self._visto_nome = nome
        hoje = date.today()
        self._ano, self._mes = hoje.year, hoje.month
        self._config = regra.ConfigHoras()
        self._dias: dict[date, regra.LinhaDia] = {}

        self.cabecalho = BarraCabecalho("Registo de Horas")

        # ---- navegação ---------------------------------------------------
        self.anterior_button = QPushButton("◀")
        self.anterior_button.setFixedWidth(36)
        self.anterior_button.setToolTip("Mês anterior")
        self.anterior_button.clicked.connect(lambda: self._mudar_mes(-1))
        self.mes_label = QLabel()
        self.mes_label.setMinimumWidth(170)
        self.mes_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mes_label.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {tema.CASTANHO_ESCURO};"
        )
        self.seguinte_button = QPushButton("▶")
        self.seguinte_button.setFixedWidth(36)
        self.seguinte_button.setToolTip("Mês seguinte")
        self.seguinte_button.clicked.connect(lambda: self._mudar_mes(1))
        self.este_mes_button = QPushButton("Este mês")
        self.este_mes_button.setToolTip("Voltar ao mês atual")
        self.este_mes_button.clicked.connect(self._ir_para_este_mes)

        self.colaborador_combo = ComboSemScroll()
        self.colaborador_combo.setToolTip(
            "De quem é a folha de horas à vista (só o administrador escolhe; as "
            "folhas dos outros são só para consultar)."
        )
        self.colaborador_combo.setMinimumWidth(200)
        self.colaborador_combo.currentIndexChanged.connect(self._ao_mudar_colaborador)
        self.colaborador_label = QLabel("Colaborador:")
        self.colaborador_combo.setVisible(admin)
        self.colaborador_label.setVisible(admin)

        self.atualizar_button = QPushButton("Atualizar")
        self.atualizar_button.setToolTip("Voltar a ler as horas da base de dados")
        self.atualizar_button.clicked.connect(self.carregar)

        navegacao = QHBoxLayout()
        navegacao.addWidget(self.anterior_button)
        navegacao.addWidget(self.mes_label)
        navegacao.addWidget(self.seguinte_button)
        navegacao.addWidget(self.este_mes_button)
        navegacao.addSpacing(16)
        navegacao.addWidget(self.colaborador_label)
        navegacao.addWidget(self.colaborador_combo)
        navegacao.addStretch()
        navegacao.addWidget(self.atualizar_button)

        self.ajuda_label = QLabel()
        self.ajuda_label.setWordWrap(True)
        self.ajuda_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        # ---- folha do mês ------------------------------------------------
        self.table = QTableWidget(0, len(COLUNAS))
        self.table.setHorizontalHeaderLabels(list(COLUNAS))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setToolTip("Duplo clique (ou Enter) num dia para o registar ou alterar.")
        self.table.itemDoubleClicked.connect(lambda _i: self._editar_selecionado())
        self.table.itemActivated.connect(lambda _i: self._editar_selecionado())
        cabecalho_tabela = self.table.horizontalHeader()
        cabecalho_tabela.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        cabecalho_tabela.setSectionResizeMode(COL_OBS, QHeaderView.ResizeMode.Stretch)
        for coluna, largura in enumerate((44, 44, 110, 170, 80, 70, 70, 120)):
            self.table.setColumnWidth(coluna, largura)
        self.table.horizontalHeaderItem(COL_SUBSIDIO).setToolTip(DICA_SUBSIDIO)

        # ---- painel do lado ----------------------------------------------
        self.resumo_caixa = QGroupBox("Resumo do mês")
        self.resumo_grelha = QGridLayout(self.resumo_caixa)
        self._resumo_valores: list[QLabel] = []
        for linha, (rotulo, _valor) in enumerate(regra.ResumoMes().linhas()):
            etiqueta = QLabel(rotulo)
            valor = QLabel("0h")
            valor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if linha == len(regra.ResumoMes().linhas()) - 1:
                etiqueta.setStyleSheet("font-weight: bold;")
                valor.setStyleSheet("font-weight: bold;")
            self.resumo_grelha.addWidget(etiqueta, linha, 0)
            self.resumo_grelha.addWidget(valor, linha, 1)
            self._resumo_valores.append(valor)
        # O subsídio vem à parte do total: é dinheiro, não são horas.
        rotulo_subsidio, _ = regra.ResumoMes().linha_subsidio()
        etiqueta_subsidio = QLabel(rotulo_subsidio)
        self.subsidio_label = QLabel(regra.formatar_euros(0))
        self.subsidio_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for rotulo in (etiqueta_subsidio, self.subsidio_label):
            rotulo.setToolTip(DICA_SUBSIDIO)
            rotulo.setStyleSheet(
                f"background-color: {tema.OCRE_SUAVE}; color: {tema.OCRE_ESCURO};"
                " font-weight: bold; padding: 3px 4px;"
            )
        linha_subsidio = len(self._resumo_valores)
        self.resumo_grelha.addWidget(etiqueta_subsidio, linha_subsidio, 0)
        self.resumo_grelha.addWidget(self.subsidio_label, linha_subsidio, 1)
        self.contagens_label = QLabel()
        self.contagens_label.setWordWrap(True)
        self.resumo_grelha.addWidget(self.contagens_label, linha_subsidio + 1, 0, 1, 2)
        nota = QLabel("Cada mês fecha por si: o saldo não passa para o mês seguinte.")
        nota.setWordWrap(True)
        nota.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")
        self.resumo_grelha.addWidget(nota, linha_subsidio + 2, 0, 1, 2)

        self.envio_label = QLabel()
        self.envio_label.setWordWrap(True)

        self.historico_lista = QListWidget()
        self.historico_lista.setStyleSheet(tema.ESTILO_LISTAS)
        self.historico_lista.setToolTip("Clique num mês para o abrir.")
        self.historico_lista.itemClicked.connect(self._abrir_mes_da_lista)
        caixa_historico = QGroupBox("Últimos meses (total de horas extra)")
        layout_historico = QVBoxLayout(caixa_historico)
        layout_historico.addWidget(self.historico_lista)

        lado = QVBoxLayout()
        lado.addWidget(self.resumo_caixa)
        lado.addWidget(self.envio_label)
        lado.addWidget(caixa_historico, stretch=1)
        painel = QWidget()
        painel.setLayout(lado)
        painel.setMinimumWidth(300)
        painel.setMaximumWidth(380)

        meio = QHBoxLayout()
        meio.addWidget(self.table, stretch=1)
        meio.addWidget(painel)

        # ---- botões ------------------------------------------------------
        self.registar_hoje_button = QPushButton("Registar hoje")
        self.registar_hoje_button.setToolTip("Abrir o dia de hoje para registar as horas")
        self.registar_hoje_button.clicked.connect(lambda: self.mostrar_dia(date.today(), editar=True))
        self.editar_button = QPushButton("Editar dia")
        self.editar_button.setToolTip("Registar ou alterar o dia selecionado na folha")
        self.editar_button.clicked.connect(self._editar_selecionado)
        self.pdf_button = QPushButton("Folha em PDF")
        self.pdf_button.setToolTip(
            "Gerar a folha de horas deste mês em PDF (fica na pasta das folhas) e abri-la"
        )
        self.pdf_button.clicked.connect(self._gerar_pdf)
        self.enviar_button = QPushButton("Enviar à contabilidade…")
        self.enviar_button.setToolTip(
            "Mostrar a folha deste mês e enviá-la por email à contabilidade "
            "(pede confirmação antes de enviar)"
        )
        self.enviar_button.clicked.connect(self._enviar)
        self.importar_button = QPushButton("Importar da app antiga…")
        self.importar_button.setToolTip(
            "Trazer o histórico da app «Registo de Horas» (XAMPP) deste PC para o "
            "Martelo. Só lê a app antiga; não muda nem apaga nada lá."
        )
        self.importar_button.clicked.connect(self._importar)
        self.definicoes_button = QPushButton("Definições…")
        self.definicoes_button.setToolTip(
            "O seu horário habitual, as horas normais por dia, os avisos e a pasta das folhas"
        )
        self.definicoes_button.clicked.connect(self._definicoes)
        botoes = QHBoxLayout()
        for botao in (
            self.registar_hoje_button,
            self.editar_button,
            self.pdf_button,
            self.enviar_button,
        ):
            botoes.addWidget(botao)
        botoes.addStretch()
        botoes.addWidget(self.importar_button)
        botoes.addWidget(self.definicoes_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("registoHorasStatus")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self.cabecalho)
        layout.addLayout(navegacao)
        layout.addWidget(self.ajuda_label)
        layout.addLayout(meio, stretch=1)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self._preencher_colaboradores()
        self.carregar()

    # ------------------------------------------------------------------
    @property
    def so_leitura(self) -> bool:
        """O administrador a ver a folha de outra pessoa."""
        return self._visto_id != self._user_id

    def _preencher_colaboradores(self) -> None:
        if not self._admin:
            return
        try:
            with SessionLocal() as session:
                colaboradores = RegistoHorasService(session).colaboradores()
        except Exception as erro:  # noqa: BLE001
            diario_bordo.registar_erro(f"Registo de Horas (colaboradores): {erro}")
            colaboradores = []
        self.colaborador_combo.blockSignals(True)
        self.colaborador_combo.clear()
        for colaborador in colaboradores:
            self.colaborador_combo.addItem(colaborador.nome, (colaborador.user_id, colaborador.nome))
        if all(c.user_id != self._user_id for c in colaboradores):
            self.colaborador_combo.addItem(
                f"{self._nome_conta} (a minha folha)", (self._user_id, self._nome_conta)
            )
        self.colaborador_combo.setCurrentIndex(0)
        self.colaborador_combo.blockSignals(False)
        dados = self.colaborador_combo.currentData()
        if dados:
            self._visto_id, self._visto_nome = dados

    def _ao_mudar_colaborador(self, _indice: int) -> None:
        dados = self.colaborador_combo.currentData()
        if not dados:
            return
        self._visto_id, self._visto_nome = dados
        self.carregar()

    def _mudar_mes(self, delta: int) -> None:
        ano, mes = self._ano, self._mes
        passo = regra.mes_seguinte if delta > 0 else regra.mes_anterior
        for _ in range(abs(delta)):
            ano, mes = passo(ano, mes)
        self._ano, self._mes = ano, mes
        self.carregar()

    def _ir_para_este_mes(self) -> None:
        hoje = date.today()
        self._ano, self._mes = hoje.year, hoje.month
        self.carregar()

    def _abrir_mes_da_lista(self, item: QListWidgetItem) -> None:
        dados = item.data(Qt.ItemDataRole.UserRole)
        if dados:
            self._ano, self._mes = dados
            self.carregar()

    # ------------------------------------------------------------------
    def carregar(self) -> None:
        """Lê a folha do mês à vista e preenche a página."""
        if self._visto_id is None:
            self.status_label.setText("Sem sessão iniciada: não há folha de horas para mostrar.")
            return
        hoje = date.today()
        try:
            with SessionLocal() as session:
                servico = RegistoHorasService(session)
                self._config = servico.config(self._visto_id)
                dias = servico.listar_mes(self._visto_id, self._ano, self._mes)
                totais = servico.totais_por_mes(self._visto_id)
                envio = servico.ultimo_envio(self._visto_id, self._ano, self._mes)
                em_falta = acoes.em_falta_no_mes(
                    servico, self._visto_id, self._ano, self._mes, self._config, hoje
                )
        except Exception as erro:  # noqa: BLE001 - base em baixo não pode parar o Martelo
            diario_bordo.registar_erro(f"Registo de Horas: {erro}")
            self.status_label.setText(f"Não foi possível ler as horas: {erro}")
            return
        self._dias = {d.data: d for d in dias}
        nome = acoes.nome_na_folha(self._config, self._visto_nome)
        self.cabecalho.definir("Registo de Horas", [nome, regra.nome_mes(self._ano, self._mes)])
        self.mes_label.setText(regra.nome_mes(self._ano, self._mes).capitalize())
        self.este_mes_button.setEnabled((self._ano, self._mes) != (hoje.year, hoje.month))
        historico = date(self._ano, self._mes, 1) < date(
            self._config.inicio_registo.year, self._config.inicio_registo.month, 1
        )
        if self.so_leitura:
            ajuda = f"Folha de {nome} — só consulta (cada pessoa regista as suas horas)."
        elif historico:
            ajuda = (
                "Histórico (antes do registo oficial): os dias em falta não são "
                "assinalados e o mês não segue para a contabilidade."
            )
        else:
            ajuda = (
                f"Dia útil: até {regra.formatar_total(self._config.horas_normais_dia)} são "
                "horas normais e o resto é extra; fins de semana, feriados e férias "
                "contam tudo como extra; a folga desconta. Duplo clique num dia para "
                "o registar."
            )
        self.ajuda_label.setText(ajuda)
        self._preencher_tabela(set(em_falta), hoje)
        self._preencher_resumo(regra.resumir_mes(dias))
        self._preencher_envio(envio, historico, em_falta)
        self._preencher_historico(totais)
        for botao in (
            self.registar_hoje_button,
            self.enviar_button,
            self.importar_button,
            self.definicoes_button,
        ):
            botao.setVisible(not self.so_leitura)
        self.editar_button.setText("Ver dia" if self.so_leitura else "Editar dia")

    def _preencher_tabela(self, em_falta: set[date], hoje: date) -> None:
        dias_mes = regra.dias_do_mes(self._ano, self._mes)
        self.table.setRowCount(len(dias_mes))
        fundo_fds = QBrush(QColor(tema.BEGE_CLARO))
        vermelho = QBrush(QColor(tema.TEXTO_ERRO))
        negrito = QFont()
        negrito.setBold(True)
        selecionar = 0
        for linha, dia in enumerate(dias_mes):
            registo = self._dias.get(dia)
            nome_feriado = regra.feriado(dia)
            if registo is not None:
                tipo = regra.NOMES_TIPOS[registo.tipo].replace(" (desconta)", "")
                horario = registo.horario
                horas = registo.horas_folha
                normais = regra.formatar_horas(registo.normais) if registo.normais else ""
                extra = (
                    regra.formatar_total(registo.extra, com_mais=True) if registo.extra else ""
                )
                subsidio = registo.subsidio_folha
                obs = registo.observacoes_folha()
                if registo.tipo == regra.TIPO_FERIADO and nome_feriado:
                    obs = " – ".join(p for p in (nome_feriado, registo.observacoes) if p)
            else:
                tipo = "Feriado" if nome_feriado else ""
                horario = "por registar" if dia in em_falta else ""
                horas = normais = extra = subsidio = ""
                obs = nome_feriado
            valores = (
                str(dia.day),
                regra.SEMANA_CURTO[dia.weekday()],
                tipo,
                horario,
                horas,
                normais,
                extra,
                subsidio,
                obs,
            )
            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setData(Qt.ItemDataRole.UserRole, dia)
                if coluna in (0, 1, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif coluna == COL_SUBSIDIO:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if regra.e_fim_de_semana(dia) or nome_feriado:
                    item.setBackground(fundo_fds)
                if dia == hoje:
                    item.setFont(negrito)
                self.table.setItem(linha, coluna, item)
            if dia in em_falta:
                self.table.item(linha, COL_HORARIO).setForeground(vermelho)
            if registo is not None and registo.extra < 0:
                self.table.item(linha, COL_EXTRA).setForeground(vermelho)
            if dia == hoje:
                selecionar = linha
        self.table.clearSelection()
        self.table.setCurrentCell(selecionar, 0)

    def _preencher_resumo(self, resumo: regra.ResumoMes) -> None:
        for etiqueta, (_rotulo, valor) in zip(self._resumo_valores, resumo.linhas()):
            etiqueta.setText(valor)
        self.subsidio_label.setText(resumo.linha_subsidio()[1])
        self.contagens_label.setText(
            f"Dias registados: {resumo.dias_registados} · férias: {resumo.dias_ferias} · "
            f"feriados: {resumo.dias_feriado} · folgas: {resumo.dias_folga}"
        )

    def _preencher_envio(self, envio, historico: bool, em_falta: list[date]) -> None:
        partes = []
        if historico:
            partes.append("Histórico: não segue para a contabilidade.")
        elif envio is not None:
            partes.append(
                f"Enviado à contabilidade a {envio.enviado_em:%d/%m/%Y %H:%M} "
                f"({envio.destinatario})."
            )
        else:
            momento = regra.momento_envio(self._ano, self._mes)
            partes.append(
                f"Ainda não enviado à contabilidade (envio previsto a {momento:%d/%m/%Y} "
                f"às {momento:%Hh%M})."
            )
        if em_falta:
            partes.append(f"{len(em_falta)} dia(s) útil(eis) por registar.")
        self.envio_label.setText(" ".join(partes))
        cor = tema.TEXTO_ERRO if em_falta else (tema.TEXTO_OK if envio else tema.CASTANHO_MEDIO)
        self.envio_label.setStyleSheet(f"color: {cor};")

    def _preencher_historico(self, totais) -> None:
        self.historico_lista.clear()
        for ano, mes, resumo in reversed(totais[-MESES_HISTORICO:]):
            dias = resumo.dias_registados
            texto = (
                f"{regra.MESES[mes - 1][:3]} {ano}   {regra.formatar_total(resumo.total_extra)}"
                f"   ({dias} {'dia' if dias == 1 else 'dias'})"
            )
            item = QListWidgetItem(texto)
            item.setData(Qt.ItemDataRole.UserRole, (ano, mes))
            if (ano, mes) == (self._ano, self._mes):
                fonte = item.font()
                fonte.setBold(True)
                item.setFont(fonte)
            self.historico_lista.addItem(item)
        if not totais:
            self.historico_lista.addItem("Ainda sem meses registados.")

    # ------------------------------------------------------------------
    def mostrar_dia(self, dia: date, *, editar: bool = False) -> None:
        """Vai ao mês do dia, seleciona-o e (se pedido) abre o editor."""
        if (dia.year, dia.month) != (self._ano, self._mes):
            self._ano, self._mes = dia.year, dia.month
            self.carregar()
        self.table.setCurrentCell(dia.day - 1, 0)
        if editar:
            self._abrir_editor(dia)

    def _dia_selecionado(self) -> date | None:
        linha = self.table.currentRow()
        if linha < 0:
            return None
        item = self.table.item(linha, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _editar_selecionado(self) -> None:
        dia = self._dia_selecionado()
        if dia is None:
            self.status_label.setText("Selecione um dia na folha.")
            return
        self._abrir_editor(dia)

    def _obter_dia(self, dia: date) -> regra.LinhaDia | None:
        with SessionLocal() as session:
            return RegistoHorasService(session).obter_dia(self._visto_id, dia)

    def _guardar_dia(self, dia: date, dados: regra.DadosDia, observacoes: str):
        with SessionLocal() as session:
            servico = RegistoHorasService(session)
            envio = servico.ultimo_envio(self._user_id, dia.year, dia.month)
            if envio is not None:
                resposta = QMessageBox.question(
                    QApplication.activeModalWidget() or self,
                    acoes.TITULO,
                    f"As horas de {regra.nome_mes(dia.year, dia.month)} já foram "
                    f"enviadas à contabilidade a {envio.enviado_em:%d/%m/%Y}.\n\n"
                    "Se alterar este dia, tem de voltar a enviar o mês (botão «Enviar "
                    "à contabilidade…»). Alterar mesmo assim?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if resposta != QMessageBox.StandardButton.Yes:
                    return None
            linha = servico.guardar_dia(
                self._user_id, dia, dados, observacoes=observacoes, config=self._config
            )
        diario_bordo.registar_acao("Registo de Horas — dia guardado", dia.isoformat())
        self.status_label.setText(f"{regra.titulo_dia(dia)}: {linha.horas_folha or '0'} guardado.")
        return linha

    def _apagar_dia(self, dia: date) -> bool:
        with SessionLocal() as session:
            apagado = RegistoHorasService(session).apagar_dia(self._user_id, dia)
        if apagado:
            diario_bordo.registar_acao("Registo de Horas — dia apagado", dia.isoformat())
            self.status_label.setText(f"Registo de {regra.titulo_dia(dia)} apagado.")
        return apagado

    def _abrir_editor(self, dia: date) -> None:
        if self._visto_id is None:
            return
        dialogo = RegistoHorasDiaDialog(
            self,
            dia=dia,
            config=self._config,
            obter=self._obter_dia,
            guardar=None if self.so_leitura else self._guardar_dia,
            apagar=None if self.so_leitura else self._apagar_dia,
            nome=acoes.nome_na_folha(self._config, self._visto_nome) if self.so_leitura else "",
        )
        dialogo.exec()
        ultimo = dialogo.dia
        if dialogo.alterou or (ultimo.year, ultimo.month) != (self._ano, self._mes):
            self._ano, self._mes = ultimo.year, ultimo.month
            self.carregar()
            self.table.setCurrentCell(ultimo.day - 1, 0)

    # ------------------------------------------------------------------
    def _gerar_pdf(self) -> None:
        if self._visto_id is None:
            return
        try:
            caminho = acoes.gerar_folha(self._visto_id, self._visto_nome, self._ano, self._mes)
        except Exception as erro:  # noqa: BLE001
            QMessageBox.warning(self, acoes.TITULO, f"Não foi possível gerar a folha:\n{erro}")
            return
        acoes.abrir_ficheiro(caminho)
        self.status_label.setText(f"Folha gerada: {caminho}")

    def _enviar(self) -> None:
        if self._user_id is None or self.so_leitura:
            return
        acao = acoes.enviar_mes(
            self,
            user_id=self._user_id,
            nome_conta=self._nome_conta,
            email_conta=self._email_conta,
            ano=self._ano,
            mes=self._mes,
        )
        if acao == ACAO_CORRIGIR:
            self.status_label.setText(
                "Corrija os dias e depois envie com «Enviar à contabilidade…»."
            )
        self.carregar()

    def _definicoes(self) -> None:
        if self._user_id is None or self.so_leitura:
            return
        try:
            with SessionLocal() as session:
                servico = RegistoHorasService(session)
                config = servico.config(self._user_id)
                email = servico.email_contabilidade()
        except Exception as erro:  # noqa: BLE001
            QMessageBox.warning(self, acoes.TITULO, f"Não foi possível ler as definições:\n{erro}")
            return
        dialogo = RegistoHorasDefinicoesDialog(
            self,
            config=config,
            nome_conta=self._nome_conta,
            email_contabilidade=email,
            pode_mudar_email=self._admin,
        )
        if not dialogo.exec():
            return
        try:
            with SessionLocal() as session:
                servico = RegistoHorasService(session)
                servico.guardar_config(self._user_id, dialogo.config())
                novo_email = dialogo.email_contabilidade()
                if novo_email is not None and novo_email != email:
                    servico.guardar_email_contabilidade(novo_email)
        except Exception as erro:  # noqa: BLE001
            QMessageBox.warning(self, acoes.TITULO, f"Não foi possível guardar:\n{erro}")
            return
        self.status_label.setText("Definições do Registo de Horas guardadas.")
        self.carregar()

    def _importar(self) -> None:
        if self._user_id is None or self.so_leitura:
            return
        instalacao = importacao.ler_instalacao()
        if instalacao is None:
            QMessageBox.information(
                self,
                acoes.TITULO,
                "A app antiga «Registo de Horas» não está instalada neste PC "
                f"(não encontrei {importacao.PASTA_APP_ANTIGA}).",
            )
            return
        try:
            dias = importacao.ler_dias(instalacao)
        except importacao.ErroImportacao as erro:
            QMessageBox.warning(self, acoes.TITULO, str(erro))
            return
        if not dias:
            QMessageBox.information(self, acoes.TITULO, "A app antiga não tem dias registados.")
            return
        with SessionLocal() as session:
            existentes = RegistoHorasService(session).datas_registadas(
                self._user_id, dias[0].data, dias[-1].data
            )
        novos = [d for d in dias if d.data not in existentes]
        aviso_nome = ""
        if instalacao.nome and instalacao.nome.casefold() != (self._nome_conta or "").casefold():
            aviso_nome = (
                f"\n\nATENÇÃO: a app antiga deste PC é de «{instalacao.nome}», mas a "
                f"sessão do Martelo é de «{self._nome_conta}». As horas ficam em nome "
                "de quem tem a sessão iniciada."
            )
        meses = sorted({(d.data.year, d.data.month) for d in novos})
        texto = (
            f"A app antiga tem {len(dias)} dias registados, de "
            f"{dias[0].data:%d/%m/%Y} a {dias[-1].data:%d/%m/%Y}.\n\n"
            f"Vão entrar no Martelo {len(novos)} dias ({len(meses)} meses), em nome de "
            f"{self._nome_conta}."
        )
        if len(novos) < len(dias):
            texto += (
                f"\n{len(dias) - len(novos)} dia(s) já estão no Martelo e ficam como estão."
            )
        texto += (
            "\n\nOs totais de cada dia vêm tal como estão na app antiga. A app antiga "
            "não é alterada." + aviso_nome + "\n\nImportar?"
        )
        if not novos:
            QMessageBox.information(
                self, acoes.TITULO, "Todos os dias da app antiga já estão no Martelo."
            )
            return
        resposta = QMessageBox.question(
            self,
            acoes.TITULO,
            texto,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        try:
            with SessionLocal() as session:
                entraram, _ja = RegistoHorasService(session).importar_dias(self._user_id, novos)
        except Exception as erro:  # noqa: BLE001
            QMessageBox.warning(self, acoes.TITULO, f"A importação falhou (nada ficou a meio):\n{erro}")
            return
        diario_bordo.registar_acao("Registo de Horas — importou a app antiga", f"{entraram} dias")
        self.status_label.setText(
            f"Importados {entraram} dias da app antiga ({len(meses)} meses)."
        )
        self.carregar()
