"""Dialogs for the production preparation panel (checks + operational steps)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services import producao_preparacao_service as svc
from app.ui import tema


_COL_ACAO = 0
_COL_VALIDACAO = 1
_COL_ESTADO = 2
_COL_DETALHE = 3


class PreparacaoPreferenciasDialog(QDialog):
    """Let each user choose which file checks show up in the panel."""

    def __init__(self, user_id: object, parent=None) -> None:
        super().__init__(parent)

        self._user_id = user_id

        self.setWindowTitle("Preferências da Preparação")
        self.setModal(True)
        self.resize(560, 460)

        info = QLabel(
            "Escolha as validações que quer ver no painel de Preparação de "
            "Produção. Esta escolha é sua: cada utilizador tem as suas.\n"
            "As validações dos programas CNC estão sempre visíveis e são "
            "sempre obrigatórias."
        )
        info.setWordWrap(True)

        self.lista = QListWidget()
        self.lista.setAlternatingRowColors(True)
        self.lista.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.lista.setToolTip(
            "Marque as validações que contam para a obra ficar pronta para produção"
        )
        self._carregar_opcoes()

        # Escolha pessoal, à parte das validações: nem todos falam com o cliente.
        self.email_projeto_check = QCheckBox(
            "Ao passar a obra para Produção, preparar o email do projeto para o cliente"
        )
        self.email_projeto_check.setToolTip(
            "O Martelo prepara o email (destinatário, assunto, corpo, imagem e o "
            "2_Projeto_Producao.pdf em anexo). Quem envia é você, depois de o rever."
        )
        self._carregar_email_projeto()

        self.tudo_button = QPushButton("Selecionar tudo")
        self.tudo_button.setToolTip("Marcar todas as validações")
        self.tudo_button.clicked.connect(
            lambda: self._marcar_todas(Qt.CheckState.Checked)
        )

        self.limpar_button = QPushButton("Limpar")
        self.limpar_button.setToolTip("Desmarcar todas as validações")
        self.limpar_button.clicked.connect(
            lambda: self._marcar_todas(Qt.CheckState.Unchecked)
        )

        self.gravar_button = QPushButton("Gravar")
        self.gravar_button.setToolTip("Gravar as suas preferências e voltar ao painel")
        self.gravar_button.clicked.connect(self._gravar)

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.setToolTip("Fechar sem alterar as preferências")
        self.cancelar_button.clicked.connect(self.reject)

        self.status_label = QLabel("")
        self.status_label.setObjectName("preparacaoPreferenciasStatus")

        botoes = QHBoxLayout()
        botoes.addWidget(self.tudo_button)
        botoes.addWidget(self.limpar_button)
        botoes.addStretch()
        botoes.addWidget(self.gravar_button)
        botoes.addWidget(self.cancelar_button)

        layout = QVBoxLayout(self)
        layout.addWidget(info)
        layout.addWidget(self.lista, stretch=1)
        layout.addWidget(self.email_projeto_check)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

    def _carregar_opcoes(self) -> None:
        with SessionLocal() as session:
            escolhidas = svc.obter_validacoes_utilizador(session, self._user_id)

        for opcao in svc.listar_validacoes_configuraveis():
            item = QListWidgetItem(opcao["label"])
            item.setData(Qt.ItemDataRole.UserRole, opcao["key"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if opcao["key"] in escolhidas
                else Qt.CheckState.Unchecked
            )
            self.lista.addItem(item)

    def _carregar_email_projeto(self) -> None:
        with SessionLocal() as session:
            ativo = svc.obter_email_projeto_ativo(session, self._user_id)
        self.email_projeto_check.setChecked(ativo)

    def _marcar_todas(self, estado: Qt.CheckState) -> None:
        for linha in range(self.lista.count()):
            self.lista.item(linha).setCheckState(estado)

    def _keys_marcadas(self) -> list[str]:
        keys: list[str] = []
        for linha in range(self.lista.count()):
            item = self.lista.item(linha)
            if item.checkState() == Qt.CheckState.Checked:
                keys.append(str(item.data(Qt.ItemDataRole.UserRole) or ""))
        return keys

    def _gravar(self) -> None:
        try:
            with SessionLocal() as session:
                svc.guardar_validacoes_utilizador(
                    session, self._user_id, self._keys_marcadas()
                )
                svc.guardar_email_projeto_ativo(
                    session, self._user_id, self.email_projeto_check.isChecked()
                )
        except Exception as exc:  # pragma: no cover - depende da base de dados
            QMessageBox.critical(
                self,
                "Preferências da Preparação",
                f"Não foi possível gravar as preferências.\n\n{exc}",
            )
            return
        self.accept()


class ProducaoPreparacaoDialog(QDialog):
    """Show what is done and what is missing before the obra goes to production."""

    def __init__(
        self,
        *,
        codigo_processo: str,
        pasta_obra: str,
        nome_enc_imos: str,
        nome_plano_cut_rite: str,
        user_id: object,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._codigo_processo = codigo_processo
        self._pasta_obra = pasta_obra
        self._nome_enc_imos = nome_enc_imos
        self._nome_plano_cut_rite = nome_plano_cut_rite
        self._user_id = user_id
        self._contexto: svc.PreparacaoContexto | None = None
        self._estados: list[svc.PreparacaoEstado] = []

        self.setWindowTitle("Preparação de Produção")
        self.setModal(True)
        self.resize(1500, 860)

        intro = QLabel(
            "Painel de preparação da obra para Produção: valida o que já está "
            "feito na pasta da obra e deixa executar os passos que faltam."
        )
        intro.setWordWrap(True)

        contexto_group = QGroupBox("Contexto")
        contexto_group.setStyleSheet(
            f"QGroupBox {{ color: {tema.CASTANHO_ESCURO}; font-weight: bold; }}"
        )
        contexto_form = QFormLayout(contexto_group)
        self.processo_label = self._label_contexto()
        self.pasta_label = self._label_contexto()
        self.nome_enc_label = self._label_contexto()
        self.plano_label = self._label_contexto()
        contexto_form.addRow("Processo:", self.processo_label)
        contexto_form.addRow("Pasta da obra:", self.pasta_label)
        contexto_form.addRow("Nome Enc IMOS IX:", self.nome_enc_label)
        contexto_form.addRow("Nome Plano CUT-RITE:", self.plano_label)

        self.resumo_label = QLabel("")
        self.resumo_label.setWordWrap(True)

        self.tabela = QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(
            ["Ação", "Validação", "Estado", "Detalhe"]
        )
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setWordWrap(True)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        for coluna in (_COL_ACAO, _COL_VALIDACAO, _COL_ESTADO):
            cabecalho.setSectionResizeMode(
                coluna, QHeaderView.ResizeMode.ResizeToContents
            )
        cabecalho.setSectionResizeMode(_COL_DETALHE, QHeaderView.ResizeMode.Stretch)

        self.atualizar_button = QPushButton("Atualizar")
        self.atualizar_button.setToolTip("Voltar a ler a pasta da obra e as origens")
        self.atualizar_button.clicked.connect(self._atualizar)

        self.preferencias_button = QPushButton("Preferências...")
        self.preferencias_button.setToolTip(
            "Escolher as validações que quer ver neste painel (por utilizador)"
        )
        self.preferencias_button.clicked.connect(self._abrir_preferencias)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.setToolTip("Fechar o painel de preparação")
        self.fechar_button.clicked.connect(self.accept)

        self.status_label = QLabel("")
        self.status_label.setObjectName("preparacaoStatus")

        botoes = QHBoxLayout()
        botoes.addWidget(self.atualizar_button)
        botoes.addWidget(self.preferencias_button)
        botoes.addStretch()
        botoes.addWidget(self.fechar_button)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(contexto_group)
        layout.addWidget(self.resumo_label)
        layout.addWidget(self.tabela, stretch=1)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self._atualizar()

    def _label_contexto(self) -> QLabel:
        label = QLabel("-")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setWordWrap(True)
        return label

    def _atualizar(self) -> None:
        try:
            with SessionLocal() as session:
                obrigatorias = svc.obter_keys_obrigatorias(session, self._user_id)
                self._contexto = svc.resolver_contexto(
                    session,
                    codigo_processo=self._codigo_processo,
                    pasta_obra=self._pasta_obra,
                    nome_enc_imos=self._nome_enc_imos,
                    nome_plano_cut_rite=self._nome_plano_cut_rite,
                )
            self._estados = svc.recolher_estados(
                self._contexto, keys_obrigatorias=obrigatorias
            )
        except (ValueError, SQLAlchemyError, OSError) as erro:
            self._contexto = None
            self._estados = []
            self.tabela.setRowCount(0)
            self.resumo_label.setText(str(erro))
            self.resumo_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
            self.status_label.setText("Preparação não pôde ser calculada.")
            return

        self._mostrar_contexto()
        self._mostrar_resumo()
        self._mostrar_estados()

    def _mostrar_contexto(self) -> None:
        if self._contexto is None:
            return
        self.processo_label.setText(self._contexto.codigo_processo or "-")
        self.pasta_label.setText(str(self._contexto.pasta_obra))
        self.nome_enc_label.setText(self._contexto.nome_enc_imos or "-")
        self.plano_label.setText(self._contexto.nome_plano_cut_rite or "-")

    def _mostrar_resumo(self) -> None:
        pendentes = svc.pendencias_obrigatorias(self._estados)
        if pendentes:
            self.resumo_label.setText(
                "Pendências obrigatórias: \n- " + "\n- ".join(pendentes)
            )
            self.resumo_label.setStyleSheet(f"color: {tema.TEXTO_AVISO};")
        else:
            self.resumo_label.setText(
                "Sem pendências obrigatórias — a obra está pronta para produção."
            )
            self.resumo_label.setStyleSheet(f"color: {tema.TEXTO_OK};")

    def _mostrar_estados(self) -> None:
        self.tabela.setRowCount(len(self._estados))
        for linha, estado in enumerate(self._estados):
            self.tabela.setCellWidget(linha, _COL_ACAO, self._widget_acao(estado))

            validacao_item = QTableWidgetItem(estado.label)
            validacao_item.setToolTip(self._dica_validacao(estado))

            estado_item = QTableWidgetItem(self._texto_estado(estado))
            estado_item.setIcon(self._icone_estado(estado))
            estado_item.setForeground(QBrush(QColor(self._cor_estado(estado))))

            detalhe_item = QTableWidgetItem(estado.detalhe)
            detalhe_item.setToolTip(estado.detalhe)

            self.tabela.setItem(linha, _COL_VALIDACAO, validacao_item)
            self.tabela.setItem(linha, _COL_ESTADO, estado_item)
            self.tabela.setItem(linha, _COL_DETALHE, detalhe_item)
            self.tabela.setRowHeight(linha, 46)

    def _widget_acao(self, estado: svc.PreparacaoEstado) -> QWidget:
        caixa = QWidget()
        layout = QHBoxLayout(caixa)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if estado.acao and not estado.ok:
            botao = QPushButton(estado.acao_label or "Executar")
            botao.setToolTip(
                f"{estado.acao_label or 'Executar'} este passo agora — "
                "a validação é refeita a seguir"
            )
            botao.clicked.connect(
                lambda _=False, acao=estado.acao, rotulo=estado.acao_label: (
                    self._executar_acao(acao, rotulo)
                )
            )
            layout.addWidget(botao)
        return caixa

    def _dica_validacao(self, estado: svc.PreparacaoEstado) -> str:
        linhas = [estado.descricao or estado.label]
        linhas.append(
            "Obrigatório." if estado.obrigatorio else "Opcional para si (Preferências)."
        )
        return "\n".join(linhas)

    def _texto_estado(self, estado: svc.PreparacaoEstado) -> str:
        return {
            svc.ESTADO_OK: "OK",
            svc.ESTADO_PENDENTE: "Pendente",
            svc.ESTADO_DESATUALIZADO: "Desatualizado",
        }.get(estado.estado, "Bloqueado")

    def _icone_estado(self, estado: svc.PreparacaoEstado):
        estilo = self.style()
        if estado.estado == svc.ESTADO_OK:
            return estilo.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        if estado.estado == svc.ESTADO_BLOQUEADO:
            return estilo.standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
        return estilo.standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)

    def _cor_estado(self, estado: svc.PreparacaoEstado) -> str:
        if estado.estado == svc.ESTADO_OK:
            return tema.TEXTO_OK
        if estado.estado == svc.ESTADO_BLOQUEADO:
            return tema.TEXTO_ERRO
        return tema.TEXTO_AVISO

    def _executar_acao(self, acao: str, rotulo: str) -> None:
        if self._contexto is None:
            return

        acoes = {
            svc.ACAO_GERAR_PROJETO_PDF: (
                svc.gerar_projeto_producao_pdf,
                "PDF do projeto de produção gerado:",
            ),
            svc.ACAO_COPIAR_PROGRAMAS_OBRA: (
                svc.copiar_programas_para_obra,
                "Programas CNC copiados para a obra:",
            ),
            svc.ACAO_ENVIAR_PROGRAMAS_CNC: (
                svc.enviar_programas_para_cnc,
                "Programas CNC enviados para as máquinas:",
            ),
        }
        funcao_mensagem = acoes.get(acao)
        if funcao_mensagem is None:
            return
        funcao, mensagem = funcao_mensagem

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            destino = funcao(self._contexto)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Preparação de Produção",
                f"Não foi possível {(rotulo or 'executar').lower()} este passo."
                f"\n\n{exc}",
            )
            self.status_label.setText("O passo de preparação falhou.")
            self._atualizar()
            return
        QApplication.restoreOverrideCursor()

        QMessageBox.information(
            self, "Preparação de Produção", f"{mensagem}\n\n{destino}"
        )
        self.status_label.setText(f"{mensagem} {destino}")
        self._atualizar()

    def _abrir_preferencias(self) -> None:
        dialogo = PreparacaoPreferenciasDialog(self._user_id, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.status_label.setText("Preferências gravadas.")
            self._atualizar()
