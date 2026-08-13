"""Per-user AI profile page: what each person teaches the assistant."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.services.ia_perfil_service import (
    TIPOS_ENTRADA,
    TIPOS_POR_CHAVE,
    acrescentar_sugestoes,
    atualizar_entrada,
    contar_por_tipo,
    criar_entrada,
    eliminar_entrada,
    listar_entradas,
    sugestoes_em_falta,
)
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho


#: Campos de texto de uma obra, sugeridos na coluna "onde aparece".
CAMPOS_SUGERIDOS = (
    "",
    "Descrição artigos",
    "Matérias usados",
    "Descrição produção",
    "Notas 1",
    "Notas 2",
    "Notas 3",
    "Todos os campos de texto",
    "Data Entrega",
    "Data Início",
    "Estado",
    "Responsável",
    "Cliente",
)


class IaPerfilPage(QWidget):
    """Let the signed-in user write the vocabulary the assistant should learn."""

    def __init__(
        self,
        on_back=None,
        *,
        tipo_inicial: str | None = None,
        expressao_inicial: str = "",
    ) -> None:
        super().__init__()

        self.on_back = on_back
        self._entrada_em_edicao: int | None = None

        self.cabecalho = BarraCabecalho(
            "Assistente — o meu perfil",
            [
                "O que escrever aqui ensina o assistente a perceber as suas "
                "perguntas. Cada utilizador tem o seu perfil e ninguém vê o dos "
                "outros."
            ],
        )

        self.tipo_combo = QComboBox()
        for tipo in TIPOS_ENTRADA:
            self.tipo_combo.addItem(tipo.titulo, tipo.chave)
        self.tipo_combo.setToolTip("Escolha o tipo de informação que quer acrescentar")
        self.tipo_combo.currentIndexChanged.connect(self._on_tipo_mudou)

        self.ajuda_label = QLabel("")
        self.ajuda_label.setWordWrap(True)
        self.ajuda_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        # Uma folha em branco é o que mais trava quem nunca ensinou o
        # assistente: o quadro chega com linhas prontas a escolher.
        self.sugestoes_combo = QComboBox()
        self.sugestoes_combo.setMinimumWidth(340)
        self.sugestoes_combo.setToolTip(
            "Linhas já escritas para este quadro. Escolha uma para a pôr nos "
            "campos — pode alterá-la antes de gravar."
        )
        self.sugestoes_combo.currentIndexChanged.connect(self._usar_sugestao)

        self.adicionar_sugestoes_button = QPushButton("Acrescentar todas")
        self.adicionar_sugestoes_button.setToolTip(
            "Acrescentar de uma vez todas as sugestões que ainda não tem neste "
            "quadro. Pode editar ou eliminar as que não servirem."
        )
        self.adicionar_sugestoes_button.clicked.connect(self._acrescentar_sugestoes)

        self.expressao_label = QLabel("Expressão")
        self.expressao_input = QLineEdit()
        self.significado_label = QLabel("Significado")
        self.significado_input = QLineEdit()

        self.campos_label = QLabel("Onde aparece")
        self.campos_combo = QComboBox()
        self.campos_combo.setEditable(True)
        self.campos_combo.addItems(CAMPOS_SUGERIDOS)
        self.campos_combo.setToolTip(
            "Em que campo da obra é que essa palavra costuma aparecer"
        )

        self.adicionar_button = QPushButton("Adicionar")
        self.adicionar_button.setToolTip("Gravar esta linha no meu perfil")
        self.adicionar_button.clicked.connect(self._gravar)

        self.cancelar_edicao_button = QPushButton("Cancelar edição")
        self.cancelar_edicao_button.setToolTip("Voltar a adicionar uma linha nova")
        self.cancelar_edicao_button.clicked.connect(self._cancelar_edicao)
        self.cancelar_edicao_button.setVisible(False)

        formulario = QHBoxLayout()
        formulario.setSpacing(8)
        formulario.addWidget(self.expressao_label)
        formulario.addWidget(self.expressao_input, stretch=2)
        formulario.addWidget(self.significado_label)
        formulario.addWidget(self.significado_input, stretch=3)
        formulario.addWidget(self.campos_label)
        formulario.addWidget(self.campos_combo, stretch=2)
        formulario.addWidget(self.adicionar_button)
        formulario.addWidget(self.cancelar_edicao_button)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Expressão", "Significado", "Onde aparece"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        cabecalho_tabela = self.table.horizontalHeader()
        cabecalho_tabela.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        cabecalho_tabela.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        cabecalho_tabela.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        cabecalho_tabela.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 260)
        self.table.setColumnWidth(2, 200)
        self.table.itemDoubleClicked.connect(self._editar_linha)

        self.editar_button = QPushButton("Editar")
        self.editar_button.setToolTip("Editar a linha selecionada (ou duplo-clique)")
        self.editar_button.clicked.connect(self._editar_selecionada)

        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.setToolTip("Eliminar a linha selecionada do meu perfil")
        self.eliminar_button.clicked.connect(self._eliminar)

        self.voltar_button = QPushButton("Voltar às Configurações")
        self.voltar_button.setToolTip("Regressar ao menu Configurações")
        self.voltar_button.clicked.connect(lambda: self.on_back() if self.on_back else None)
        self.voltar_button.setVisible(on_back is not None)

        acoes = QHBoxLayout()
        acoes.addWidget(self.editar_button)
        acoes.addWidget(self.eliminar_button)
        acoes.addStretch()
        acoes.addWidget(self.voltar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("iaPerfilStatus")

        self.resumo_label = QLabel("")
        self.resumo_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 4px;"
        )

        linha_tipo = QHBoxLayout()
        linha_tipo.addWidget(QLabel("Quadro"))
        linha_tipo.addWidget(self.tipo_combo)
        linha_tipo.addStretch()
        linha_tipo.addWidget(self.resumo_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        linha_sugestoes = QHBoxLayout()
        linha_sugestoes.addWidget(QLabel("Sugestões"))
        linha_sugestoes.addWidget(self.sugestoes_combo, stretch=1)
        linha_sugestoes.addWidget(self.adicionar_sugestoes_button)
        linha_sugestoes.addStretch()

        layout.addWidget(self.cabecalho)
        layout.addLayout(linha_tipo)
        layout.addWidget(self.ajuda_label)
        layout.addLayout(linha_sugestoes)
        layout.addLayout(formulario)
        layout.addLayout(acoes)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        if tipo_inicial:
            indice = self.tipo_combo.findData(tipo_inicial)
            if indice >= 0:
                self.tipo_combo.setCurrentIndex(indice)

        self._on_tipo_mudou()

        if expressao_inicial:
            # Veio de uma pesquisa que não encontrou nada: a palavra já fica
            # escrita, para a pessoa só ter de dizer o que ela significa.
            self.expressao_input.setText(expressao_inicial)
            self.significado_input.setFocus()
            self.status_label.setText(
                f"«{expressao_inicial}» já está escrita. Diga o que significa e "
                "carregue em Adicionar."
            )

    # ---- estado --------------------------------------------------------
    def _user_id(self) -> int | None:
        return getattr(app_session.current_user, "id", None)

    def _tipo_atual(self):
        return TIPOS_POR_CHAVE[self.tipo_combo.currentData()]

    def _on_tipo_mudou(self, *_args) -> None:
        tipo = self._tipo_atual()
        self.ajuda_label.setText(tipo.ajuda)
        self.expressao_label.setText(tipo.rotulo_expressao)
        self.significado_label.setText(tipo.rotulo_significado)
        self.table.setHorizontalHeaderLabels(
            [tipo.rotulo_expressao, tipo.rotulo_significado, "Onde aparece"]
        )
        for widget in (self.campos_label, self.campos_combo):
            widget.setVisible(tipo.usa_campos)
        self.table.setColumnHidden(2, not tipo.usa_campos)
        self._cancelar_edicao()
        self.carregar()
        self._carregar_sugestoes()

    # ---- sugestões -----------------------------------------------------
    def _carregar_sugestoes(self) -> None:
        """Show the ready-made lines this user has not written yet."""
        user_id = self._user_id()
        pendentes: list[tuple[str, str]] = []
        if user_id is not None:
            try:
                with SessionLocal() as session:
                    pendentes = sugestoes_em_falta(
                        session, user_id, self._tipo_atual().chave
                    )
            except SQLAlchemyError:
                pendentes = []

        self.sugestoes_combo.blockSignals(True)
        self.sugestoes_combo.clear()
        if pendentes:
            self.sugestoes_combo.addItem(
                f"Escolha uma sugestão… ({len(pendentes)} por acrescentar)", None
            )
            for expressao, significado in pendentes:
                rotulo = f"{expressao} — {significado}" if significado else expressao
                self.sugestoes_combo.addItem(rotulo, (expressao, significado))
        else:
            self.sugestoes_combo.addItem("Já tem todas as sugestões deste quadro", None)
        self.sugestoes_combo.blockSignals(False)

        tem_pendentes = bool(pendentes)
        self.sugestoes_combo.setEnabled(tem_pendentes)
        self.adicionar_sugestoes_button.setEnabled(tem_pendentes)

    def _usar_sugestao(self) -> None:
        """Put the chosen suggestion in the fields, ready to adjust and save."""
        dados = self.sugestoes_combo.currentData()
        if not dados:
            return
        expressao, significado = dados
        self._cancelar_edicao()
        self.expressao_input.setText(expressao)
        self.significado_input.setText(significado)
        self.status_label.setText(
            "Sugestão posta nos campos. Altere o que quiser e carregue em Adicionar."
        )

    def _acrescentar_sugestoes(self) -> None:
        """Write every missing suggestion of this quadro at once."""
        user_id = self._user_id()
        if user_id is None:
            self.status_label.setText("Inicie sessão para editar o seu perfil.")
            return

        try:
            with SessionLocal() as session:
                criadas = acrescentar_sugestoes(
                    session, user_id, self._tipo_atual().chave
                )
                session.commit()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível acrescentar as sugestões.")
            return

        self.carregar()
        self._carregar_sugestoes()
        self.status_label.setText(
            f"{criadas} sugestão(ões) acrescentadas. Edite ou elimine as que não "
            "servirem — o perfil é seu."
            if criadas
            else "Não havia sugestões novas para acrescentar."
        )

    # ---- dados ---------------------------------------------------------
    def carregar(self) -> None:
        """Load this user's lines for the selected kind."""
        user_id = self._user_id()
        self.table.setRowCount(0)
        if user_id is None:
            self.status_label.setText("Inicie sessão para editar o seu perfil.")
            return

        try:
            with SessionLocal() as session:
                entradas = listar_entradas(session, user_id, self._tipo_atual().chave)
                contagem = contar_por_tipo(session, user_id)
                linhas = [
                    (e.id, e.expressao, e.significado or "", e.campos or "")
                    for e in entradas
                ]
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar o perfil.")
            return

        self.table.setRowCount(len(linhas))
        for indice, (entrada_id, expressao, significado, campos) in enumerate(linhas):
            item = QTableWidgetItem(expressao)
            item.setData(Qt.ItemDataRole.UserRole, entrada_id)
            self.table.setItem(indice, 0, item)
            self.table.setItem(indice, 1, QTableWidgetItem(significado))
            self.table.setItem(indice, 2, QTableWidgetItem(campos))

        total = sum(contagem.values())
        self.resumo_label.setText(
            f"{len(linhas)} neste quadro · {total} no meu perfil"
        )

    def _gravar(self) -> None:
        user_id = self._user_id()
        if user_id is None:
            self.status_label.setText("Inicie sessão para editar o seu perfil.")
            return

        expressao = self.expressao_input.text()
        significado = self.significado_input.text()
        campos = self.campos_combo.currentText() if self._tipo_atual().usa_campos else ""

        try:
            with SessionLocal() as session:
                if self._entrada_em_edicao is None:
                    criar_entrada(
                        session,
                        user_id=user_id,
                        tipo=self._tipo_atual().chave,
                        expressao=expressao,
                        significado=significado,
                        campos=campos,
                    )
                    mensagem = "Linha acrescentada ao seu perfil."
                else:
                    atualizar_entrada(
                        session,
                        self._entrada_em_edicao,
                        user_id=user_id,
                        expressao=expressao,
                        significado=significado,
                        campos=campos,
                    )
                    mensagem = "Linha atualizada."
                session.commit()
        except ValueError as erro:
            self.status_label.setText(str(erro))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível gravar a linha.")
            return

        self._cancelar_edicao()
        self.status_label.setText(mensagem)
        self.carregar()
        self._carregar_sugestoes()

    def _linha_selecionada(self) -> int | None:
        linha = self.table.currentRow()
        if linha < 0:
            return None
        item = self.table.item(linha, 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _editar_linha(self, item) -> None:
        self._editar(item.row())

    def _editar_selecionada(self) -> None:
        linha = self.table.currentRow()
        if linha < 0:
            self.status_label.setText("Selecione uma linha para editar.")
            return
        self._editar(linha)

    def _editar(self, linha: int) -> None:
        item = self.table.item(linha, 0)
        if item is None:
            return
        self._entrada_em_edicao = int(item.data(Qt.ItemDataRole.UserRole))
        self.expressao_input.setText(item.text())
        self.significado_input.setText(self.table.item(linha, 1).text())
        self.campos_combo.setCurrentText(self.table.item(linha, 2).text())
        self.adicionar_button.setText("Gravar alteração")
        self.cancelar_edicao_button.setVisible(True)
        self.status_label.setText("A editar uma linha existente.")

    def _cancelar_edicao(self) -> None:
        self._entrada_em_edicao = None
        self.expressao_input.clear()
        self.significado_input.clear()
        self.campos_combo.setCurrentIndex(0)
        self.adicionar_button.setText("Adicionar")
        self.cancelar_edicao_button.setVisible(False)

    def _eliminar(self) -> None:
        entrada_id = self._linha_selecionada()
        user_id = self._user_id()
        if entrada_id is None or user_id is None:
            self.status_label.setText("Selecione uma linha para eliminar.")
            return

        resposta = QMessageBox.question(
            self,
            "Eliminar linha",
            "Eliminar esta linha do seu perfil?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                eliminar_entrada(session, entrada_id, user_id=user_id)
                session.commit()
        except ValueError as erro:
            self.status_label.setText(str(erro))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível eliminar a linha.")
            return

        self._cancelar_edicao()
        self.status_label.setText("Linha eliminada.")
        self.carregar()
        self._carregar_sugestoes()
