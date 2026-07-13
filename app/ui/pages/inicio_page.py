"""Home dashboard for budgets, alerts and production."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.orcamento_repository import OrcamentoResumo
from app.services.inicio_dashboard_service import calcular_dashboard_orcamentos
from app.services.custeio_auditoria_service import CusteioAuditoriaService
from app.services.orcamento_service import OrcamentoService
from app.services.producao_dashboard_service import calcular_dashboard as calcular_producao
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.ui.widgets.estilo_tabela_orcamentos import (
    aplicar_estilo_linha_orcamento,
    configurar_tabela_orcamentos,
)
from app.utils.formatters import format_currency


class InicioPage(QWidget):
    """Operational landing page backed only by existing read services."""

    def __init__(
        self,
        *,
        on_open_orcamentos: Callable[[], None] | None = None,
        on_open_producao: Callable[[], None] | None = None,
        on_open_auditoria: Callable[[], None] | None = None,
        on_open_orcamento: Callable[[OrcamentoResumo], None] | None = None,
        titulo: str = "Painel Inicial",
        incluir_producao: bool = True,
    ) -> None:
        super().__init__()
        self.on_open_orcamentos = on_open_orcamentos
        self.on_open_producao = on_open_producao
        self.on_open_auditoria = on_open_auditoria
        self.on_open_orcamento = on_open_orcamento
        self.incluir_producao = incluir_producao
        self._recentes_por_linha: dict[int, OrcamentoResumo] = {}

        self.cabecalho = BarraCabecalho(
            titulo,
            ["Resumo rápido dos orçamentos, avisos e produção do Martelo V3."
             if incluir_producao else "Dashboard comercial dos orçamentos do Martelo V3."],
        )
        self.atualizar_button = QPushButton("Atualizar painel")
        self.atualizar_button.setToolTip("Recalcular todos os indicadores com os dados atuais")
        self.atualizar_button.clicked.connect(self.carregar)

        topo = QHBoxLayout()
        topo.addWidget(self.cabecalho, stretch=1)
        topo.addWidget(self.atualizar_button)

        self.pesquisa = CampoPesquisa(
            placeholder="Pesquisar orçamento, cliente, obra, referência ou descrição…"
        )
        self.estado_combo = QComboBox()
        self.estado_combo.setToolTip("Filtra os indicadores e a lista de Orçamentos")
        self.cliente_combo = QComboBox()
        self.utilizador_combo = QComboBox()
        self.periodo_combo = QComboBox()
        self.periodo_combo.setToolTip("Filtra Orçamentos pela data de criação")
        self.periodo_combo.addItems(["Todos", "Hoje", "Este mês", "Este ano"])
        self.relogio_label = QLabel("")
        self.relogio_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px 8px;"
        )
        self.pesquisa.pesquisa_mudou.connect(lambda _="": self.carregar())
        self.pesquisa.limpar_clicado.connect(self.carregar)
        for combo in (self.estado_combo, self.cliente_combo, self.utilizador_combo,
                      self.periodo_combo):
            combo.currentTextChanged.connect(lambda _="": self.carregar())
        filtros = QHBoxLayout()
        filtros.addWidget(self.pesquisa, stretch=2)
        for titulo_filtro, combo in (
            ("Estado", self.estado_combo), ("Cliente", self.cliente_combo),
            ("Utilizador", self.utilizador_combo), ("Período", self.periodo_combo),
        ):
            filtros.addWidget(QLabel(titulo_filtro))
            filtros.addWidget(combo, stretch=1)
        filtros.addWidget(self.relogio_label)

        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(12)
        self.cards = {
            "em_curso": self._criar_cartao("Orçamentos em curso", tema.OCRE_ESCURO),
            "adjudicados": self._criar_cartao("Adjudicados", tema.VERDE_ESCURO),
            "falta": self._criar_cartao("Falta orçamentar", tema.OCRE_ESCURO),
            "alertas": self._criar_cartao("Alertas de custo", tema.VERMELHO_ESCURO),
        }
        if incluir_producao:
            self.cards["producao"] = self._criar_cartao("Em produção", tema.AZUL_ESCURO)
            self.cards["atrasadas"] = self._criar_cartao("Produções atrasadas", tema.VERMELHO_ESCURO)
            self.cards["desenho"] = self._criar_cartao("Em desenho", tema.AZUL_ESCURO)
            self.cards["finalizadas"] = self._criar_cartao("Produções finalizadas", tema.VERDE_ESCURO)
            self.cards["valor_producao"] = self._criar_cartao("Valor em produção", tema.VERDE_ESCURO)
            self.cards["sem_preco_producao"] = self._criar_cartao("Produções sem preço", tema.VERMELHO_ESCURO)
        for indice, card in enumerate(self.cards.values()):
            self.cards_layout.addWidget(card[0], indice // 5, indice % 5)

        recentes_box = QGroupBox("Orçamentos recentes")
        recentes_layout = QVBoxLayout(recentes_box)
        self.recentes_table = QTableWidget(0, 10)
        self.recentes_table.setHorizontalHeaderLabels(
            ["Orçamento", "Estado", "Cliente", "Ref. Cliente", "Enc. PHC",
             "Obra", "Descrição", "Data", "Total", "Utilizador"]
        )
        self.recentes_table.verticalHeader().setVisible(False)
        self.recentes_table.setAlternatingRowColors(True)
        self.recentes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recentes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        configurar_tabela_orcamentos(self.recentes_table, compacta=True)
        self.recentes_table.horizontalHeader().setStretchLastSection(False)
        self.recentes_table.cellDoubleClicked.connect(self._abrir_recente)
        ligar_persistencia_larguras(self.recentes_table, "inicio_orcamentos_recentes")
        recentes_layout.addWidget(self.recentes_table)
        ver_orcamentos = QPushButton("Ver todos os orçamentos")
        ver_orcamentos.clicked.connect(lambda: self._chamar(self.on_open_orcamentos))
        recentes_layout.addWidget(ver_orcamentos, alignment=Qt.AlignmentFlag.AlignRight)

        avisos_box = QGroupBox("Centros de avisos")
        avisos_layout = QVBoxLayout(avisos_box)
        orcamentos_avisos_box = QGroupBox("Orçamentos")
        self.avisos_layout = QVBoxLayout(orcamentos_avisos_box)
        avisos_layout.addWidget(orcamentos_avisos_box)
        producao_avisos_box = QGroupBox("Produção")
        self.producao_avisos_layout = QVBoxLayout(producao_avisos_box)
        producao_avisos_box.setVisible(incluir_producao)
        avisos_layout.addWidget(producao_avisos_box)
        avisos_layout.addStretch()
        botoes_avisos = QHBoxLayout()
        auditoria = QPushButton("Abrir Auditoria")
        auditoria.clicked.connect(lambda: self._chamar(self.on_open_auditoria))
        botoes_avisos.addWidget(auditoria)
        if incluir_producao:
            producao_button = QPushButton("Ver Produção")
            producao_button.clicked.connect(lambda: self._chamar(self.on_open_producao))
            botoes_avisos.addWidget(producao_button)
        avisos_layout.addLayout(botoes_avisos)

        centro = QHBoxLayout()
        centro.addWidget(recentes_box, stretch=3)
        centro.addWidget(avisos_box, stretch=2)

        self.status_label = QLabel("")
        self.status_label.setObjectName("inicioStatus")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        layout.addLayout(topo)
        layout.addLayout(filtros)
        layout.addLayout(self.cards_layout)
        layout.addLayout(centro, stretch=1)
        layout.addWidget(self.status_label)
        self.carregar()

    def _criar_cartao(self, titulo: str, cor: str) -> tuple[QGroupBox, QLabel, QLabel]:
        box = QGroupBox(titulo)
        box.setMinimumHeight(105)
        layout = QVBoxLayout(box)
        valor = QLabel("—")
        valor.setStyleSheet(f"font-size: 25px; font-weight: bold; color: {cor};")
        detalhe = QLabel("")
        detalhe.setWordWrap(True)
        detalhe.setStyleSheet(f"color: {tema.CINZA_ESCURO};")
        layout.addWidget(valor)
        layout.addWidget(detalhe)
        return box, valor, detalhe

    def carregar(self) -> None:
        self.status_label.clear()
        agora = datetime.now()
        self.relogio_label.setText(agora.strftime("%d/%m/%Y  |  %H:%M"))
        try:
            with SessionLocal() as session:
                orcamentos = OrcamentoService(session).list_orcamentos()
                self._atualizar_filtros(orcamentos)
                orcamentos_filtrados = self._filtrar_orcamentos(orcamentos, agora.date())
                dados = calcular_dashboard_orcamentos(orcamentos_filtrados)
                try:
                    auditoria_custeio = CusteioAuditoriaService(session).executar()
                except Exception:
                    auditoria_custeio = None
                try:
                    cliente_producao = self.cliente_combo.currentText()
                    utilizador_producao = self.utilizador_combo.currentText()
                    producao = calcular_producao(
                        session,
                        texto=self.pesquisa.texto(),
                        cliente=None if cliente_producao in ("", "Todos") else cliente_producao,
                        utilizador=None if utilizador_producao in ("", "Todos") else utilizador_producao,
                    )
                except Exception:  # fonte de produção pode estar temporariamente indisponível
                    producao = None
                if not self.incluir_producao:
                    producao = None
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar o painel inicial.")
            return

        self._set_card("em_curso", dados.em_curso, f"Valor: {format_currency(dados.valor_em_curso)}")
        self._set_card("adjudicados", dados.adjudicados, f"Valor: {format_currency(dados.valor_adjudicado)}")
        self._set_card("falta", dados.falta_orcamentar, "Orçamentos que precisam de conclusão")
        alertas_custeio = auditoria_custeio.criticos if auditoria_custeio else 0
        detalhe_alertas = f"{dados.sem_total} sem total · {dados.com_preco_manual} manuais · {alertas_custeio} críticos de custeio"
        if auditoria_custeio and auditoria_custeio.impacto_conhecido:
            detalhe_alertas += f" · {format_currency(auditoria_custeio.impacto_conhecido)} conhecidos"
        self._set_card("alertas", dados.sem_total + dados.com_preco_manual + alertas_custeio, detalhe_alertas)
        if self.incluir_producao:
            self._set_card("producao", producao.em_producao if producao else "—", "Dados de Produção" if producao else "Fonte indisponível")
            self._set_card("atrasadas", producao.atrasadas if producao else "—", "Prazo de entrega ultrapassado" if producao else "Fonte indisponível")
            self._set_card("desenho", producao.em_desenho if producao else "—", "Em preparação técnica" if producao else "Fonte indisponível")
            self._set_card("finalizadas", producao.finalizadas if producao else "—", "Trabalhos terminados" if producao else "Fonte indisponível")
            self._set_card("valor_producao", format_currency(producao.valor_aberto) if producao else "—", "Valor dos trabalhos ainda abertos" if producao else "Fonte indisponível")
            self._set_card("sem_preco_producao", producao.sem_preco if producao else "—", "Trabalhos abertos sem preço" if producao else "Fonte indisponível")
        self._preencher_recentes(dados.recentes)
        self._preencher_avisos(dados.avisos)
        self._preencher_avisos_producao(producao)

    def _atualizar_filtros(self, orcamentos: list[OrcamentoResumo]) -> None:
        conjuntos = (
            (self.estado_combo, sorted({o.estado for o in orcamentos if o.estado})),
            (self.cliente_combo, sorted({o.cliente_nome for o in orcamentos if o.cliente_nome})),
            (self.utilizador_combo, sorted({o.utilizador for o in orcamentos if o.utilizador})),
        )
        for combo, valores in conjuntos:
            atual = combo.currentText() or "Todos"
            bloqueado = combo.blockSignals(True)
            combo.clear()
            combo.addItem("Todos")
            combo.addItems(valores)
            indice = combo.findText(atual)
            combo.setCurrentIndex(indice if indice >= 0 else 0)
            combo.blockSignals(bloqueado)

    def _filtrar_orcamentos(
        self, orcamentos: list[OrcamentoResumo], hoje: date
    ) -> list[OrcamentoResumo]:
        termos = [t.casefold() for t in self.pesquisa.texto().split() if t]
        estado = self.estado_combo.currentText()
        cliente = self.cliente_combo.currentText()
        utilizador = self.utilizador_combo.currentText()
        periodo = self.periodo_combo.currentText()
        resultado = []
        for orcamento in orcamentos:
            texto = " ".join(str(valor or "") for valor in (
                orcamento.codigo_versao, orcamento.cliente_nome, orcamento.ref_cliente,
                orcamento.obra, orcamento.descricao, orcamento.enc_phc,
                orcamento.utilizador,
            )).casefold()
            criado = orcamento.created_at.date()
            if termos and not all(termo in texto for termo in termos):
                continue
            if estado not in ("", "Todos") and orcamento.estado != estado:
                continue
            if cliente not in ("", "Todos") and orcamento.cliente_nome != cliente:
                continue
            if utilizador not in ("", "Todos") and orcamento.utilizador != utilizador:
                continue
            if periodo == "Hoje" and criado != hoje:
                continue
            if periodo == "Este mês" and (criado.year, criado.month) != (hoje.year, hoje.month):
                continue
            if periodo == "Este ano" and criado.year != hoje.year:
                continue
            resultado.append(orcamento)
        return resultado

    def _set_card(self, chave: str, valor, detalhe: str) -> None:
        _box, valor_label, detalhe_label = self.cards[chave]
        valor_label.setText(str(valor))
        detalhe_label.setText(detalhe)

    def _preencher_recentes(self, recentes) -> None:
        self._recentes_por_linha = {}
        self.recentes_table.setRowCount(len(recentes))
        for row, orcamento in enumerate(recentes):
            self._recentes_por_linha[row] = orcamento
            valores = [
                orcamento.codigo_versao, orcamento.estado, orcamento.cliente_nome,
                orcamento.ref_cliente or "", orcamento.enc_phc or "",
                orcamento.obra or "", orcamento.descricao or "",
                orcamento.created_at.strftime("%d/%m/%Y"),
                format_currency(orcamento.preco_total), orcamento.utilizador or "",
            ]
            for col, texto in enumerate(valores):
                item = QTableWidgetItem(texto)
                if texto:
                    item.setToolTip(texto)
                self.recentes_table.setItem(row, col, item)
            aplicar_estilo_linha_orcamento(
                self.recentes_table,
                row,
                coluna_codigo=0,
                coluna_estado=1,
                estado=orcamento.estado,
                coluna_total=8,
                preco_manual=orcamento.tem_preco_manual,
            )

    def _preencher_avisos(self, avisos) -> None:
        while self.avisos_layout.count():
            item = self.avisos_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not avisos:
            self.avisos_layout.addWidget(QLabel("Sem avisos de orçamento."))
            return
        cores = {"crítico": tema.VERMELHO_SUAVE, "atenção": tema.OCRE_SUAVE, "informação": tema.AZUL_SUAVE}
        for aviso in avisos:
            label = QLabel(f"<b>{aviso.titulo}</b><br>{aviso.detalhe}")
            label.setWordWrap(True)
            label.setStyleSheet(f"background: {cores.get(aviso.nivel, tema.CINZA_SUAVE)}; padding: 7px; border-radius: 5px;")
            self.avisos_layout.addWidget(label)

    def _preencher_avisos_producao(self, producao) -> None:
        while self.producao_avisos_layout.count():
            item = self.producao_avisos_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.incluir_producao:
            return
        if producao is None:
            self.producao_avisos_layout.addWidget(QLabel("Fonte de Produção indisponível."))
            return
        avisos = []
        if producao.atrasadas:
            avisos.append(("Produções atrasadas", f"{producao.atrasadas} trabalhos ultrapassaram o prazo", tema.VERMELHO_SUAVE))
        if producao.sem_preco:
            avisos.append(("Produções sem preço", f"{producao.sem_preco} trabalhos abertos sem valor", tema.OCRE_SUAVE))
        for item in producao.lista_atrasadas[:3]:
            avisos.append(("Prazo ultrapassado", f"{item['codigo']} · {item['cliente']} · {item['dias_atraso']} dias", tema.VERMELHO_SUAVE))
        if not avisos:
            self.producao_avisos_layout.addWidget(QLabel("Sem avisos de Produção."))
            return
        for titulo, detalhe, cor in avisos:
            label = QLabel(f"<b>{titulo}</b><br>{detalhe}")
            label.setWordWrap(True)
            label.setStyleSheet(f"background: {cor}; padding: 7px; border-radius: 5px;")
            self.producao_avisos_layout.addWidget(label)

    def _abrir_recente(self, row: int, _column: int) -> None:
        orcamento = self._recentes_por_linha.get(row)
        if orcamento is not None and self.on_open_orcamento is not None:
            self.on_open_orcamento(orcamento)

    @staticmethod
    def _chamar(callback: Callable[[], None] | None) -> None:
        if callback is not None:
            callback()
