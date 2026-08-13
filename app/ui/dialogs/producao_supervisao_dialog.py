"""Supervisor que confirma a obra antes de ela passar a Produção.

Vinha do V2 a ideia de avisar quem muda o estado para Produção sem ter tudo
preparado. No V3 o aviso é interativo: mostra o que falta, deixa resolver ali
mesmo (Preparação), volta a verificar e só depois deixa seguir — ou deixa
continuar à mesma, porque é um aviso e não uma proibição. As validações são as
que **este** utilizador escolheu nas Preferências da Preparação.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.db.session import SessionLocal
from app.services import producao_preparacao_service as svc
from app.ui import tema
from app.ui.dialogs.producao_preparacao_dialog import (
    PreparacaoPreferenciasDialog,
    ProducaoPreparacaoDialog,
)


_COL_VALIDACAO = 0
_COL_ESTADO = 1
_COL_DETALHE = 2

_TEXTOS_ESTADO = {
    svc.ESTADO_OK: "OK",
    svc.ESTADO_PENDENTE: "Pendente",
    svc.ESTADO_DESATUALIZADO: "Desatualizado",
}


class SupervisaoProducaoDialog(QDialog):
    """Warn about what is still missing before the obra goes to production."""

    def __init__(
        self,
        *,
        codigo_processo: str,
        pasta_obra: str,
        nome_enc_imos: str,
        nome_plano_cut_rite: str,
        user_id: object,
        estado_anterior: str,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._codigo_processo = codigo_processo
        self._pasta_obra = pasta_obra
        self._nome_enc_imos = nome_enc_imos
        self._nome_plano_cut_rite = nome_plano_cut_rite
        self._user_id = user_id
        self._estado_anterior = str(estado_anterior or "").strip() or "-"
        self._supervisao = svc.SupervisaoProducao(validou=False)

        #: True quando o utilizador decide mesmo passar a obra a Produção.
        self.continuar = False

        self.setWindowTitle("Supervisor de Produção")
        self.setModal(True)
        self.resize(1180, 620)

        self.titulo_label = QLabel(
            f"🔨 A obra {codigo_processo or '-'} vai passar a Produção."
        )
        self.titulo_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; font-size: 14px;"
        )
        self.titulo_label.setWordWrap(True)

        self.resumo_label = QLabel("")
        self.resumo_label.setWordWrap(True)

        self.detalhe_label = QLabel(
            "Estas são as validações que escolheu em Preparação → Preferências "
            "(as dos programas CNC são sempre obrigatórias)."
        )
        self.detalhe_label.setWordWrap(True)
        self.detalhe_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        self.tabela = QTableWidget(0, 3)
        self.tabela.setHorizontalHeaderLabels(["Validação", "Estado", "O que falta"])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setWordWrap(True)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabela.setToolTip(
            "O que ainda falta na pasta da obra para ela poder ir para produção"
        )
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        for coluna in (_COL_VALIDACAO, _COL_ESTADO):
            cabecalho.setSectionResizeMode(
                coluna, QHeaderView.ResizeMode.ResizeToContents
            )
        cabecalho.setSectionResizeMode(_COL_DETALHE, QHeaderView.ResizeMode.Stretch)

        self.preparacao_button = QPushButton("Abrir Preparação...")
        self.preparacao_button.setToolTip(
            "Abrir o painel de Preparação para resolver as pendências agora — "
            "ao fechar, o supervisor volta a verificar"
        )
        self.preparacao_button.clicked.connect(self._abrir_preparacao)

        self.preferencias_button = QPushButton("Preferências...")
        self.preferencias_button.setToolTip(
            "Escolher que validações contam para si (cada utilizador tem as suas)"
        )
        self.preferencias_button.clicked.connect(self._abrir_preferencias)

        self.verificar_button = QPushButton("Voltar a verificar")
        self.verificar_button.setToolTip("Ler outra vez a pasta da obra e as origens")
        self.verificar_button.clicked.connect(self.verificar)

        self.continuar_button = QPushButton("Passar a Produção mesmo assim")
        self.continuar_button.clicked.connect(self._continuar)

        self.cancelar_button = QPushButton(
            f"Cancelar (fica em {self._estado_anterior})"
        )
        self.cancelar_button.setToolTip(
            "Não gravar nada e manter a obra no estado em que estava"
        )
        self.cancelar_button.clicked.connect(self.reject)

        self.status_label = QLabel("")
        self.status_label.setObjectName("supervisaoProducaoStatus")

        botoes = QHBoxLayout()
        botoes.addWidget(self.preparacao_button)
        botoes.addWidget(self.preferencias_button)
        botoes.addWidget(self.verificar_button)
        botoes.addStretch()
        botoes.addWidget(self.continuar_button)
        botoes.addWidget(self.cancelar_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.titulo_label)
        layout.addWidget(self.resumo_label)
        layout.addWidget(self.detalhe_label)
        layout.addWidget(self.tabela, stretch=1)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

    # ---- verificação ------------------------------------------------------
    def mostrar(self, supervisao: svc.SupervisaoProducao) -> None:
        """Show a check the caller already did (avoids reading the server twice)."""
        self._supervisao = supervisao
        self._mostrar_resumo()
        self._mostrar_pendencias()
        # Janela à medida do que há para mostrar: com duas pendências não faz
        # sentido ocupar o ecrã todo.
        altura = 220 + 52 * len(supervisao.pendencias)
        self.resize(1180, max(300, min(760, altura)))

    def verificar(self) -> None:
        """Read the obra folder again and refresh what is missing."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with SessionLocal() as session:
                supervisao = svc.supervisionar_para_producao(
                    session,
                    codigo_processo=self._codigo_processo,
                    pasta_obra=self._pasta_obra,
                    nome_enc_imos=self._nome_enc_imos,
                    nome_plano_cut_rite=self._nome_plano_cut_rite,
                    user_id=self._user_id,
                )
        finally:
            QApplication.restoreOverrideCursor()

        self.mostrar(supervisao)
        self.status_label.setText(
            "Tudo validado." if supervisao.pronta else "Verificação refeita."
        )

    def _mostrar_resumo(self) -> None:
        supervisao = self._supervisao
        if not supervisao.validou:
            self.resumo_label.setText(
                "Não consegui validar a preparação desta obra:\n"
                f"{supervisao.motivo}\n"
                "Confirme a pasta da obra e o Nome Enc IMOS IX."
            )
            self.resumo_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
            self.continuar_button.setText("Passar a Produção mesmo assim")
            self.continuar_button.setToolTip(
                "Gravar a mudança para Produção sem o supervisor ter validado nada"
            )
            self.continuar_button.setDefault(False)
            self.cancelar_button.setDefault(True)
            return

        if supervisao.pronta:
            self.resumo_label.setText(
                "Está tudo validado — a obra pode ir para produção."
            )
            self.resumo_label.setStyleSheet(
                f"color: {tema.TEXTO_OK}; font-weight: bold;"
            )
            self.continuar_button.setText("Passar a Produção")
            self.continuar_button.setToolTip("Gravar a obra já em Produção")
            self.continuar_button.setDefault(True)
            self.cancelar_button.setDefault(False)
            return

        total = len([e for e in supervisao.estados if e.key != "obra_pronta"])
        faltam = len(supervisao.pendencias)
        self.resumo_label.setText(
            f"Atenção: {faltam} de {total} validações ainda não estão OK. "
            "Resolva-as na Preparação ou continue por sua conta."
        )
        self.resumo_label.setStyleSheet(
            f"color: {tema.TEXTO_AVISO}; font-weight: bold;"
        )
        self.continuar_button.setText("Passar a Produção mesmo assim")
        self.continuar_button.setToolTip(
            "Gravar a mudança para Produção mesmo com pendências — fica ao seu critério"
        )
        self.continuar_button.setDefault(False)
        self.cancelar_button.setDefault(True)

    def _mostrar_pendencias(self) -> None:
        pendencias = self._supervisao.pendencias
        self.tabela.setRowCount(len(pendencias))
        for linha, estado in enumerate(pendencias):
            validacao_item = QTableWidgetItem(estado.label)
            validacao_item.setToolTip(estado.descricao or estado.label)

            estado_item = QTableWidgetItem(
                _TEXTOS_ESTADO.get(estado.estado, "Bloqueado")
            )
            estado_item.setIcon(self._icone_estado(estado))
            estado_item.setForeground(QBrush(QColor(_cor_estado(estado))))

            detalhe_item = QTableWidgetItem(estado.detalhe)
            detalhe_item.setToolTip(estado.detalhe)

            self.tabela.setItem(linha, _COL_VALIDACAO, validacao_item)
            self.tabela.setItem(linha, _COL_ESTADO, estado_item)
            self.tabela.setItem(linha, _COL_DETALHE, detalhe_item)
            self.tabela.setRowHeight(linha, 46)
        self.tabela.setVisible(bool(pendencias))

    def _icone_estado(self, estado: svc.PreparacaoEstado):
        estilo = self.style()
        if estado.estado == svc.ESTADO_OK:
            return estilo.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        if estado.estado == svc.ESTADO_BLOQUEADO:
            return estilo.standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
        return estilo.standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)

    # ---- ações ------------------------------------------------------------
    def _abrir_preparacao(self) -> None:
        dialogo = ProducaoPreparacaoDialog(
            codigo_processo=self._codigo_processo,
            pasta_obra=self._pasta_obra,
            nome_enc_imos=self._nome_enc_imos,
            nome_plano_cut_rite=self._nome_plano_cut_rite,
            user_id=self._user_id,
            parent=self,
        )
        dialogo.exec()
        self.verificar()

    def _abrir_preferencias(self) -> None:
        dialogo = PreparacaoPreferenciasDialog(self._user_id, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.verificar()

    def _continuar(self) -> None:
        if not self._supervisao.pronta and not self._confirmar_com_pendencias():
            return
        self.continuar = True
        self.accept()

    def _confirmar_com_pendencias(self) -> bool:
        faltam = len(self._supervisao.pendencias) or "várias"
        resposta = QMessageBox.question(
            self,
            "Supervisor de Produção",
            f"A obra {self._codigo_processo or ''} vai para produção com "
            f"{faltam} validação(ões) por resolver.\n\nConfirma?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return resposta == QMessageBox.StandardButton.Yes


def _cor_estado(estado: svc.PreparacaoEstado) -> str:
    if estado.estado == svc.ESTADO_OK:
        return tema.TEXTO_OK
    if estado.estado == svc.ESTADO_BLOQUEADO:
        return tema.TEXTO_ERRO
    return tema.TEXTO_AVISO
