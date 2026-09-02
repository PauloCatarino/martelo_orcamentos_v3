"""Customers page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.clientes_lista import filtrar_clientes
from app.domain.clientes_simplex import simplex_demasiado_longo, validar_simplex
from app.repositories.cliente_repository import ClienteListaResumo, ClienteRepository
from app.services.cliente_phc_sync_service import ClientePhcSyncService
from app.services.cliente_temporario_service import (
    ClienteEmUsoError,
    ClienteTemporarioService,
    DadosClienteTemporario,
)
from app.services import phc_sql
from app.ui import tema
from app.ui.dialogs.cliente_detalhe_dialog import ClienteDetalheDialog
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.ui.widgets.realce_rato_delegate import RealceRatoDelegate


class ClientesPage(QWidget):
    """Customers page with temporary and PHC customer lists."""

    TABLE_HEADERS = [
        "Nome",
        "Simplex",
        "Email envio or\u00e7amentos",
        "Email envio projeto produ\u00e7\u00e3o",
        "Morada",
        "Email",
        "WEB",
        "Telefone",
        "Telem\u00f3vel",
        "Num PHC",
        "Info 1",
        "Info 2",
    ]
    COLUMN_WIDTHS = {
        "Nome": 220,
        "Simplex": 160,
        "Email envio or\u00e7amentos": 220,
        "Email envio projeto produ\u00e7\u00e3o": 220,
        "Morada": 260,
        "Email": 220,
        "WEB": 220,
        "Telefone": 110,
        "Telem\u00f3vel": 110,
        "Num PHC": 90,
        "Info 1": 180,
        "Info 2": 180,
    }
    #: Colunas que o Martelo escreve (as \u00fanicas edit\u00e1veis num cliente PHC).
    COL_EMAIL_ORCAMENTOS = 2
    COL_EMAIL_PROJETO = 3

    def __init__(self) -> None:
        super().__init__()

        self._todos: list[ClienteListaResumo] = []
        self._linhas: list[ClienteListaResumo] = []
        self._phc_todos: list[ClienteListaResumo] = []
        self._phc_linhas: list[ClienteListaResumo] = []
        self._cliente_id: int | None = None

        self.cabecalho = BarraCabecalho("Clientes")

        tabs = QTabWidget()
        tabs.addTab(self._criar_tab_temporarios(), "Clientes Tempor\u00e1rios")
        tabs.addTab(self._criar_tab_phc(), "Clientes PHC")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addWidget(tabs, stretch=1)
        self.setLayout(layout)

        self.carregar()
        self.carregar_phc()

    def _criar_tab_temporarios(self) -> QWidget:
        tab = QWidget()

        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar \u2014 espa\u00e7o ou % para v\u00e1rios termos\u2026"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)
        self.refresh_button.setToolTip("Recarregar clientes temporários")

        self.status_label = QLabel("")
        self.status_label.setObjectName("clientesStatus")

        self.new_button = QPushButton("Novo")
        self.new_button.clicked.connect(self._on_novo)
        self.new_button.setToolTip("Criar um cliente temporário")
        self.save_button = QPushButton("Guardar")
        self.save_button.clicked.connect(self._on_guardar)
        self.save_button.setToolTip("Guardar o cliente temporário")
        self.delete_button = QPushButton("Eliminar")
        self.delete_button.clicked.connect(self._on_eliminar)
        self.delete_button.setToolTip("Eliminar o cliente temporário selecionado")

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.campo_pesquisa)
        toolbar.addWidget(self.new_button)
        toolbar.addWidget(self.save_button)
        toolbar.addWidget(self.delete_button)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch()

        form_group = QGroupBox("Dados do Cliente")
        form_layout = QGridLayout()
        self.ed_nome = QLineEdit()
        self.ed_simplex = QLineEdit()
        self.ed_simplex.setPlaceholderText("Gerado do nome se vazio (máx. 19 caracteres)")
        self.ed_simplex.setToolTip(
            "Nome abreviado do cliente — dá o nome à pasta da obra, ao plano "
            "CUT-RITE e à encomenda iMos. Máximo 19 caracteres."
        )
        self.ed_num_phc = QLineEdit()
        self.ed_telefone = QLineEdit()
        self.ed_telemovel = QLineEdit()
        self.ed_email = QLineEdit()
        self.ed_web = QLineEdit()
        self.ed_morada = QTextEdit()
        self.ed_morada.setFixedHeight(48)
        self.ed_info1 = QTextEdit()
        self.ed_info1.setFixedHeight(60)
        self.ed_info2 = QTextEdit()
        self.ed_info2.setFixedHeight(60)

        form_layout.addWidget(QLabel("Nome"), 0, 0)
        form_layout.addWidget(self.ed_nome, 0, 1)
        form_layout.addWidget(QLabel("Simplex"), 0, 2)
        form_layout.addWidget(self.ed_simplex, 0, 3)
        form_layout.addWidget(QLabel("Num PHC"), 1, 0)
        form_layout.addWidget(self.ed_num_phc, 1, 1)
        form_layout.addWidget(QLabel("Telefone"), 1, 2)
        form_layout.addWidget(self.ed_telefone, 1, 3)
        form_layout.addWidget(QLabel("Telem\u00f3vel"), 2, 0)
        form_layout.addWidget(self.ed_telemovel, 2, 1)
        form_layout.addWidget(QLabel("E-Mail"), 2, 2)
        form_layout.addWidget(self.ed_email, 2, 3)
        form_layout.addWidget(QLabel("P\u00e1gina WEB"), 3, 0)
        form_layout.addWidget(self.ed_web, 3, 1, 1, 3)
        form_layout.addWidget(QLabel("Morada"), 4, 0)
        form_layout.addWidget(self.ed_morada, 4, 1, 1, 3)
        form_layout.addWidget(QLabel("Info 1"), 5, 0)
        form_layout.addWidget(self.ed_info1, 5, 1, 1, 3)
        form_layout.addWidget(QLabel("Info 2"), 6, 0)
        form_layout.addWidget(self.ed_info2, 6, 1, 1, 3)
        form_layout.setColumnStretch(1, 1)
        form_layout.setColumnStretch(3, 1)
        form_group.setLayout(form_layout)

        self.table = self._nova_tabela_clientes()
        self.table.itemSelectionChanged.connect(self._on_selecao)
        self.table.itemDoubleClicked.connect(self._abrir_ficha_temporario)
        ligar_persistencia_larguras(self.table, "clientes_temporarios")

        self.footer_label = QLabel("")
        self.footer_label.setObjectName("clientesFooter")
        self.footer_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addLayout(toolbar)
        layout.addWidget(self.status_label)
        layout.addWidget(form_group)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.footer_label)
        tab.setLayout(layout)

        return tab

    def _criar_tab_phc(self) -> QWidget:
        tab = QWidget()

        info = QLabel(
            "Clientes PHC (oficiais). S\u00e3o criados no PHC e aqui apenas "
            "consultados (s\u00f3 leitura). Use \u00abAtualizar PHC\u00bb para "
            "sincronizar a partir do PHC.\n"
            "Duplo-clique numa linha abre a ficha do cliente, onde se editam "
            "os \u00abEmail envio or\u00e7amentos\u00bb e \u00abEmail envio projeto produ\u00e7\u00e3o\u00bb \u2014 "
            "s\u00e3o do Martelo e a sincroniza\u00e7\u00e3o n\u00e3o os apaga."
        )
        info.setObjectName("pageSubtitle")
        info.setWordWrap(True)

        self.phc_campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar \u2014 espa\u00e7o ou % para v\u00e1rios termos\u2026"
        )
        self.phc_campo_pesquisa.pesquisa_mudou.connect(self._render_phc)

        self.phc_refresh_button = QPushButton("Atualizar")
        self.phc_refresh_button.clicked.connect(self.carregar_phc)
        self.phc_refresh_button.setToolTip("Recarregar a lista local de clientes PHC")
        self.phc_test_button = QPushButton("Testar liga\u00e7\u00e3o PHC")
        self.phc_test_button.clicked.connect(self._testar_ligacao_phc)
        self.phc_test_button.setToolTip("Testar a ligação ao PHC sem alterar dados")
        self.phc_sync_button = QPushButton("Atualizar PHC")
        self.phc_sync_button.clicked.connect(self._sincronizar_phc)
        self.phc_sync_button.setToolTip("Sincronizar clientes a partir do PHC")

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.phc_campo_pesquisa)
        toolbar.addWidget(self.phc_refresh_button)
        toolbar.addWidget(self.phc_test_button)
        toolbar.addWidget(self.phc_sync_button)
        toolbar.addStretch()

        self.phc_status_label = QLabel("")
        self.phc_status_label.setObjectName("clientesStatus")

        self.phc_table = self._nova_tabela_clientes()
        self.phc_table.itemDoubleClicked.connect(self._abrir_ficha_phc)
        ligar_persistencia_larguras(self.phc_table, "clientes_phc")

        self.phc_footer_label = QLabel("")
        self.phc_footer_label.setObjectName("clientesFooter")
        self.phc_footer_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(info)
        layout.addLayout(toolbar)
        layout.addWidget(self.phc_status_label)
        layout.addWidget(self.phc_table, stretch=1)
        layout.addWidget(self.phc_footer_label)
        tab.setLayout(layout)

        return tab

    def _nova_tabela_clientes(self) -> QTableWidget:
        table = QTableWidget(0, len(self.TABLE_HEADERS))
        table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Realce da célula sob o rato: castanho escuro com texto branco, para
        # não se perder a linha de vista numa lista com 12 colunas.
        table.setMouseTracking(True)
        table.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        table.setItemDelegate(RealceRatoDelegate(table))
        table.setToolTip("Duplo-clique numa linha para abrir a ficha do cliente")
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        self._aplicar_larguras_colunas(table)
        return table

    def _aplicar_larguras_colunas(self, table: QTableWidget) -> None:
        for column_index, header in enumerate(self.TABLE_HEADERS):
            largura = self.COLUMN_WIDTHS.get(header)
            if largura is not None:
                table.setColumnWidth(column_index, largura)

    def _povoar_tabela(
        self,
        table: QTableWidget,
        clientes: list[ClienteListaResumo],
    ) -> None:
        colunas_email = {self.COL_EMAIL_ORCAMENTOS, self.COL_EMAIL_PROJETO}

        table.blockSignals(True)
        try:
            table.setRowCount(len(clientes))

            for row_index, cliente in enumerate(clientes):
                values = [
                    cliente.nome,
                    cliente.nome_simplex or "",
                    cliente.email_orcamentos or "",
                    cliente.email_projeto_producao or "",
                    cliente.morada or "",
                    cliente.email or "",
                    cliente.pagina_web or "",
                    cliente.telefone or "",
                    cliente.telemovel or "",
                    cliente.num_cliente_phc or "",
                    cliente.info_1 or "",
                    cliente.info_2 or "",
                ]

                for column_index, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    )
                    if value:
                        item.setToolTip(value)
                    if column_index == 0:
                        item.setData(Qt.ItemDataRole.UserRole, cliente.id)
                    if column_index == 1:
                        self._marcar_simplex(item, cliente)
                    if column_index in colunas_email and not value:
                        item.setToolTip(
                            "Vazio — é usado o email do cliente.\n"
                            "Duplo-clique na linha para escrever os destinos "
                            "(vários separados por ;)."
                        )
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row_index, column_index, item)
        finally:
            table.blockSignals(False)

    @staticmethod
    def _marcar_simplex(item: QTableWidgetItem, cliente: ClienteListaResumo) -> None:
        """Assinala o nome abreviado em falta ou grande demais para o iMos.

        É este nome que dá origem à pasta da obra e à encomenda iMos, por isso
        vale a pena vê-lo mal na lista antes de dar erro ao criar o processo.
        Vermelho = passa dos 19 caracteres (o iMos recusa); ocre = falta no PHC.
        """
        erro = validar_simplex(cliente.nome_simplex, nome_cliente=cliente.nome)
        if erro is None:
            return

        if simplex_demasiado_longo(cliente.nome_simplex):
            item.setBackground(QColor(tema.VERMELHO_SUAVE))
            item.setForeground(QColor(tema.VERMELHO_ESCURO))
        else:
            item.setBackground(QColor(tema.OCRE_SUAVE))
            item.setForeground(QColor(tema.OCRE_ESCURO))
            item.setText("(vazio no PHC)")
        item.setToolTip(erro)

    def carregar(self) -> None:
        """Load temporary customers from the database."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                clientes = ClienteRepository(session).list_temporarios()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os clientes.")
            return

        self._todos = list(clientes)
        self._render()

        if not self._todos:
            self.status_label.setText("Sem clientes temporarios para mostrar.")

    def carregar_phc(self) -> None:
        """Load PHC customers from the local database."""
        self.phc_table.setRowCount(0)
        self.phc_status_label.clear()

        try:
            with SessionLocal() as session:
                clientes = ClienteRepository(session).list_phc()
        except SQLAlchemyError:
            self.phc_status_label.setText("Nao foi possivel carregar os clientes PHC.")
            return

        self._phc_todos = list(clientes)
        self._render_phc()

        if not self._phc_todos:
            self.phc_status_label.setText("Sem clientes PHC para mostrar.")

    def _render(self, *_args) -> None:
        """Render the in-memory list using the current search."""
        filtrados = filtrar_clientes(self._todos, texto=self.campo_pesquisa.texto())
        self._preencher_tabela(filtrados)
        self.footer_label.setText(f"{len(filtrados)} clientes")

    def _render_phc(self, *_args) -> None:
        """Render the PHC in-memory list using the current search."""
        filtrados = filtrar_clientes(
            self._phc_todos, texto=self.phc_campo_pesquisa.texto()
        )
        self._phc_linhas = list(filtrados)
        self._povoar_tabela(self.phc_table, filtrados)
        self.phc_footer_label.setText(f"{len(filtrados)} clientes")

    def _abrir_ficha_phc(self, item: QTableWidgetItem) -> None:
        """Abre a ficha do cliente PHC da linha em que se fez duplo-clique."""
        linha = item.row()
        if 0 <= linha < len(self._phc_linhas):
            self._abrir_ficha(self._phc_linhas[linha], self.phc_status_label)

    def _abrir_ficha_temporario(self, item: QTableWidgetItem) -> None:
        """Abre a ficha do cliente temporário (os dados editam-se no form)."""
        linha = item.row()
        if 0 <= linha < len(self._linhas):
            self._abrir_ficha(self._linhas[linha], self.status_label)

    def _abrir_ficha(self, resumo: ClienteListaResumo, status: QLabel) -> None:
        dialog = ClienteDetalheDialog(resumo, self)
        if not dialog.exec():
            return
        if not dialog.houve_alteracoes():
            return

        try:
            with SessionLocal() as session:
                atualizado = ClienteRepository(session).atualizar_emails_envio(
                    id=resumo.id,
                    email_orcamentos=dialog.email_orcamentos(),
                    email_projeto_producao=dialog.email_projeto_producao(),
                )
                session.commit()
        except (SQLAlchemyError, ValueError) as erro:
            QMessageBox.warning(
                self,
                "Cliente",
                f"Não foi possível guardar os emails de envio:\n\n{erro}",
            )
            return

        self._substituir_em_cache(atualizado)
        status.setText(f"Emails de envio de {atualizado.nome} guardados.")

    def _substituir_em_cache(self, cliente: ClienteListaResumo) -> None:
        """Atualiza as listas em memória e volta a desenhar o que está visível."""
        for cache in (self._phc_todos, self._todos):
            for indice, existente in enumerate(cache):
                if existente.id == cliente.id:
                    cache[indice] = cliente
                    break

        self._render()
        self._render_phc()

    def _testar_ligacao_phc(self) -> None:
        """Test the read-only PHC connection and show the dbo.CL row count."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with SessionLocal() as session:
                total = phc_sql.contar_clientes_phc(session)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self,
                "Testar liga\u00e7\u00e3o PHC",
                f"N\u00e3o foi poss\u00edvel ligar ao PHC:\n\n{exc}",
            )
            return

        QApplication.restoreOverrideCursor()
        QMessageBox.information(
            self,
            "Testar liga\u00e7\u00e3o PHC",
            f"Liga\u00e7\u00e3o OK (s\u00f3 leitura).\n\n{total} clientes em dbo.CL.",
        )

    def _sincronizar_phc(self) -> None:
        """Import/update PHC customers (read-only on PHC; writes only to Martelo)."""
        resposta = QMessageBox.question(
            self,
            "Atualizar PHC",
            "Isto vai importar/atualizar os clientes a partir do PHC (dbo.CL).\n\n"
            "No PHC \u00e9 apenas LEITURA; a escrita \u00e9 s\u00f3 na base de dados do Martelo.\n\n"
            "Continuar?",
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with SessionLocal() as session:
                resumo = ClientePhcSyncService(session).sincronizar()
        except Exception as exc:  # liga\u00e7\u00e3o/SQL/config externos
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self,
                "Atualizar PHC",
                f"N\u00e3o foi poss\u00edvel atualizar a partir do PHC:\n\n{exc}",
            )
            return
        QApplication.restoreOverrideCursor()

        self.carregar_phc()
        QMessageBox.information(
            self,
            "Atualizar PHC",
            "Atualiza\u00e7\u00e3o conclu\u00edda.\n\n"
            f"Total no PHC: {resumo.total_phc}\n"
            f"Criados: {resumo.criados}\n"
            f"Atualizados: {resumo.atualizados}\n"
            f"Ignorados: {resumo.ignorados}",
        )

    def _preencher_tabela(self, clientes: list[ClienteListaResumo]) -> None:
        """Fill the table with customer read models."""
        self._linhas = list(clientes)
        self._povoar_tabela(self.table, self._linhas)

    def _on_selecao(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._linhas):
            return

        resumo = self._linhas[row]
        self._cliente_id = resumo.id
        self.ed_nome.setText(resumo.nome or "")
        self.ed_simplex.setText(resumo.nome_simplex or "")
        self.ed_num_phc.setText(resumo.num_cliente_phc or "")
        self.ed_telefone.setText(resumo.telefone or "")
        self.ed_telemovel.setText(resumo.telemovel or "")
        self.ed_email.setText(resumo.email or "")
        self.ed_web.setText(resumo.pagina_web or "")
        self.ed_morada.setPlainText(resumo.morada or "")
        self.ed_info1.setPlainText(resumo.info_1 or "")
        self.ed_info2.setPlainText(resumo.info_2 or "")

    def _on_novo(self) -> None:
        self._cliente_id = None
        self.table.clearSelection()
        for campo in (
            self.ed_nome,
            self.ed_simplex,
            self.ed_num_phc,
            self.ed_telefone,
            self.ed_telemovel,
            self.ed_email,
            self.ed_web,
        ):
            campo.clear()
        for campo in (self.ed_morada, self.ed_info1, self.ed_info2):
            campo.clear()
        self.ed_nome.setFocus()

    def _recolher_dados(self) -> DadosClienteTemporario:
        return DadosClienteTemporario(
            nome=self.ed_nome.text(),
            nome_simplex=self.ed_simplex.text(),
            morada=self.ed_morada.toPlainText(),
            email=self.ed_email.text(),
            pagina_web=self.ed_web.text(),
            telefone=self.ed_telefone.text(),
            telemovel=self.ed_telemovel.text(),
            num_cliente_phc=self.ed_num_phc.text(),
            info_1=self.ed_info1.toPlainText(),
            info_2=self.ed_info2.toPlainText(),
        )

    def _on_guardar(self) -> None:
        dados = self._recolher_dados()
        try:
            with SessionLocal() as session:
                servico = ClienteTemporarioService(session)
                if self._cliente_id is None:
                    resumo = servico.criar(dados)
                else:
                    resumo = servico.editar(self._cliente_id, dados)
            novo_id = resumo.id
        except ValueError as exc:
            QMessageBox.warning(self, "Dados em falta", str(exc))
            return
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel guardar o cliente.")
            return

        self.carregar()
        self._selecionar_por_id(novo_id)
        self.status_label.setText("Cliente guardado.")

    def _on_eliminar(self) -> None:
        if self._cliente_id is None:
            self.status_label.setText("Selecione um cliente para eliminar.")
            return

        resposta = QMessageBox.question(
            self,
            "Confirmar",
            "Eliminar o cliente selecionado?",
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                ClienteTemporarioService(session).eliminar(self._cliente_id)
        except ClienteEmUsoError as exc:
            QMessageBox.warning(
                self,
                "Cliente em uso",
                f"{exc}\n\nElimine/realoque os orcamentos associados antes de o apagar.",
            )
            return
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel eliminar o cliente.")
            return

        self.carregar()
        self._on_novo()
        self.status_label.setText("Cliente eliminado.")

    def _selecionar_por_id(self, cliente_id: int) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == cliente_id:
                self.table.selectRow(row)
                return
