"""A equipa: quem recebe tickets e em que endereço do Teams."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.texto_endereco import endereco_suspeito
from app.services import teams_service
from app.services.equipa_service import (
    atualizar_membro,
    criar_membro,
    eliminar_membro,
    listar_membros,
    preencher_emails_de_users,
    semear_de_producao,
)
from app.ui import tema
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class EquipaDialog(QDialog):
    """Edit the people a ticket can be handed to.

    O endereço é o do Microsoft Teams (normalmente o email de trabalho): é ele
    que abre a conversa certa quando se envia um ticket.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Equipa")
        self.setModal(True)
        self.resize(680, 480)

        cabecalho = QLabel(
            "Quem pode ficar responsável por um ticket. Sem endereço de Teams, "
            "o ticket ainda se copia para colar no chat — só não abre a conversa "
            "sozinho."
        )
        cabecalho.setWordWrap(True)
        cabecalho.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        self.formato_combo = QComboBox()
        self.formato_combo.setToolTip(
            "Se o Teams abrir sem o destinatário preenchido no 'Para:', "
            "experimente outro formato. Depende de a conta ser de trabalho ou "
            "pessoal e da versão do Teams instalada."
        )
        for chave, rotulo, _base in teams_service.FORMATOS_LINK:
            self.formato_combo.addItem(rotulo, chave)
        self.formato_combo.currentIndexChanged.connect(self._gravar_formato)

        linha_formato = QHBoxLayout()
        linha_formato.addWidget(QLabel("Formato do link do Teams:"))
        linha_formato.addWidget(self.formato_combo, stretch=1)
        linha_formato.addStretch()

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nome", "Endereço de Teams", "Ativo"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        cabecalho_tabela = self.table.horizontalHeader()
        cabecalho_tabela.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        cabecalho_tabela.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(2, 70)
        ligar_persistencia_larguras(self.table, "equipa", forcar_interativas=False)

        self.acrescentar_button = QPushButton("Acrescentar pessoa")
        self.acrescentar_button.setToolTip("Juntar uma linha nova à equipa")
        self.acrescentar_button.clicked.connect(self._acrescentar)

        self.importar_button = QPushButton("Trazer nomes das obras")
        self.importar_button.setToolTip(
            "Acrescenta à equipa os nomes que já aparecem como Responsável das "
            "obras na Produção, para não os ter de escrever de novo. Quem já cá "
            "estiver não é duplicado."
        )
        self.importar_button.clicked.connect(self._importar)

        self.emails_button = QPushButton("Preencher endereços")
        self.emails_button.setToolTip(
            "Preencher os endereços em falta com o email da conta do Martelo da "
            "mesma pessoa. Nunca escreve por cima do que já preencheu."
        )
        self.emails_button.clicked.connect(self._preencher_emails)

        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.setToolTip("Tirar esta pessoa da equipa")
        self.eliminar_button.clicked.connect(self._eliminar)

        self.gravar_button = QPushButton("Gravar")
        self.gravar_button.setToolTip("Gravar os nomes e endereços da tabela")
        self.gravar_button.setDefault(True)
        self.gravar_button.clicked.connect(self._gravar)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.clicked.connect(self.accept)

        botoes = QHBoxLayout()
        botoes.addWidget(self.acrescentar_button)
        botoes.addWidget(self.importar_button)
        botoes.addWidget(self.emails_button)
        botoes.addWidget(self.eliminar_button)
        botoes.addStretch()
        botoes.addWidget(self.gravar_button)
        botoes.addWidget(self.fechar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("equipaStatus")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(cabecalho)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(linha_formato)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self.carregar()
        self._carregar_formato()

    # ---- dados -----------------------------------------------------------
    def carregar(self) -> None:
        """Load the team."""
        try:
            with SessionLocal() as session:
                linhas = [
                    (int(m.id), m.nome, m.email or "", bool(m.ativo))
                    for m in listar_membros(session, incluir_inativos=True)
                ]
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar a equipa.")
            return

        self.table.setRowCount(len(linhas))
        for indice, (identificador, nome, email, ativo) in enumerate(linhas):
            self._preencher_linha(indice, identificador, nome, email, ativo)

        self.status_label.setText(
            f"{len(linhas)} pessoa(s) na equipa."
            if linhas
            else "Equipa vazia — use 'Importar das obras' para começar."
        )

    def _preencher_linha(
        self, indice: int, identificador: int | None, nome: str, email: str, ativo: bool
    ) -> None:
        item_nome = QTableWidgetItem(nome)
        item_nome.setData(Qt.ItemDataRole.UserRole, identificador)
        self.table.setItem(indice, 0, item_nome)
        self.table.setItem(indice, 1, QTableWidgetItem(email))

        item_ativo = QTableWidgetItem()
        item_ativo.setFlags(
            Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        )
        item_ativo.setCheckState(
            Qt.CheckState.Checked if ativo else Qt.CheckState.Unchecked
        )
        item_ativo.setToolTip("Desligue quem já não recebe tickets")
        self.table.setItem(indice, 2, item_ativo)

    def _carregar_formato(self) -> None:
        """Show which link format is in use."""
        try:
            with SessionLocal() as session:
                formato = teams_service.formato_configurado(session)
        except SQLAlchemyError:
            formato = teams_service.FORMATO_PADRAO

        indice = self.formato_combo.findData(formato)
        self.formato_combo.blockSignals(True)
        self.formato_combo.setCurrentIndex(max(indice, 0))
        self.formato_combo.blockSignals(False)

    def _gravar_formato(self) -> None:
        """Guardar o formato do link NESTE computador.

        Já não vai à base de dados. Era o mesmo valor para toda a gente — e as
        contas normais nem sequer podem escrever na tabela onde ele estava (é
        de propósito: é lá que vivem as credenciais das ligações e o
        interruptor da escrita no iMos). Quem tentava mudar levava com um "Não
        foi possível gravar o formato do link" e ficava sem saída.

        O formato depende do Teams que está instalado em cada máquina, por isso
        é em cada máquina que fica — como as larguras das colunas.
        """
        teams_service.guardar_formato(self.formato_combo.currentData())
        self.status_label.setText(
            "Formato do link guardado NESTE computador. Experimente enviar um "
            "ticket para ver se o 'Para:' fica preenchido."
        )

    # ---- ações -----------------------------------------------------------
    def _acrescentar(self) -> None:
        indice = self.table.rowCount()
        self.table.insertRow(indice)
        self._preencher_linha(indice, None, "", "", True)
        self.table.setCurrentCell(indice, 0)
        self.table.editItem(self.table.item(indice, 0))
        self.status_label.setText("Escreva o nome e o endereço, depois grave.")

    def _importar(self) -> None:
        try:
            with SessionLocal() as session:
                criados = semear_de_producao(session)
                session.commit()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível importar os nomes das obras.")
            return

        self.carregar()
        self.status_label.setText(
            f"{criados} nome(s) trazidos das obras — falta preencher os endereços."
            if criados
            else "Já cá estavam todos os responsáveis das obras — nada a trazer."
        )

    def _preencher_emails(self) -> None:
        """Fill the missing addresses from the matching Martelo accounts."""
        try:
            with SessionLocal() as session:
                preenchidos = preencher_emails_de_users(session)
                session.commit()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível preencher os endereços.")
            return

        self.carregar()
        if preenchidos:
            self.status_label.setText(
                f"{preenchidos} endereço(s) preenchidos a partir das contas do "
                "Martelo. Confirme antes de enviar — o endereço do Teams pode "
                "não ser o mesmo do login."
            )
        else:
            self.status_label.setText(
                "Não encontrei contas do Martelo para os nomes em falta. "
                "Escreva os endereços à mão."
            )

    def _eliminar(self) -> None:
        indice = self.table.currentRow()
        if indice < 0:
            self.status_label.setText("Selecione uma pessoa para eliminar.")
            return

        item = self.table.item(indice, 0)
        identificador = item.data(Qt.ItemDataRole.UserRole) if item else None
        nome = item.text() if item else ""

        if identificador is None:
            self.table.removeRow(indice)
            return

        resposta = QMessageBox.question(
            self,
            "Eliminar da equipa",
            f"Tirar '{nome}' da equipa?\n\nOs tickets antigos continuam a mostrar o nome.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                eliminar_membro(session, int(identificador))
                session.commit()
        except ValueError as erro:
            self.status_label.setText(str(erro))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível eliminar esta pessoa.")
            return

        self.carregar()
        self.status_label.setText(f"'{nome}' saiu da equipa.")

    def _gravar(self) -> None:
        """Write the whole table back — novas linhas incluídas."""
        erros: list[str] = []
        limpos: list[str] = []
        try:
            with SessionLocal() as session:
                for indice in range(self.table.rowCount()):
                    item = self.table.item(indice, 0)
                    if item is None:
                        continue
                    nome = item.text().strip()
                    email = (self.table.item(indice, 1).text() or "").strip()
                    ativo = (
                        self.table.item(indice, 2).checkState()
                        == Qt.CheckState.Checked
                    )
                    identificador = item.data(Qt.ItemDataRole.UserRole)

                    if not nome:
                        continue
                    if endereco_suspeito(email):
                        # Um espaço invisível colado do chat faz o Teams
                        # desistir do endereço sem dizer porquê.
                        limpos.append(nome)
                    try:
                        if identificador is None:
                            criar_membro(session, nome=nome, email=email)
                        else:
                            atualizar_membro(
                                session,
                                int(identificador),
                                nome=nome,
                                email=email,
                                ativo=ativo,
                            )
                    except ValueError as erro:
                        erros.append(str(erro))
                session.commit()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível gravar a equipa.")
            return

        self.carregar()
        partes = ["Equipa gravada."]
        if limpos:
            partes.append(
                f"Tirei espaços invisíveis do endereço de {', '.join(limpos)} — "
                "eram eles que impediam o Teams de reconhecer a pessoa."
            )
        partes.extend(erros)
        self.status_label.setText(" ".join(partes))
