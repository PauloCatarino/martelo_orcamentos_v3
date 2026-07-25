"""Diálogo de teste: criar a proposta base no PHC (Fatia 1).

Recolhe cliente + ref. cliente + linha de designação e conduz o PHC para criar
a proposta, mostrando o número atribuído. Nesta fase **não** escreve na base de
dados do V3 — serve para validar a automação da janela do PHC.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.db.session import SessionLocal
from app.services.phc_automation_service import (
    PhcAutomationError,
    PhcAutomationService,
    construir_designacao,
    construir_plano,
    descrever_plano,
    formatar_num_cliente_phc,
)
from app.services.phc_propostas_service import (
    ler_max_obrano,
    localizar_proposta_criada,
)


class CriarPropostaPhcDialog(QDialog):
    """Diálogo isolado para testar a criação da proposta no PHC."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Criar Proposta no PHC (teste)")
        self.setModal(True)
        self.setMinimumWidth(480)

        self._cliente_id: int | None = None
        self._num_cliente_phc: str | None = None
        # A designação segue a ref. cliente enquanto o utilizador não a editar.
        self._designacao_manual = False

        self.cliente_label = QLabel("— nenhum cliente escolhido —")
        self.cliente_label.setToolTip(
            "Cliente cujo número PHC será usado para criar a proposta."
        )
        self.escolher_cliente_button = QPushButton("Escolher cliente…")
        self.escolher_cliente_button.setToolTip("Procurar e escolher o cliente.")
        self.escolher_cliente_button.clicked.connect(self._escolher_cliente)
        cliente_widget = QWidget()
        cliente_layout = QHBoxLayout(cliente_widget)
        cliente_layout.setContentsMargins(0, 0, 0, 0)
        cliente_layout.addWidget(self.cliente_label, stretch=1)
        cliente_layout.addWidget(self.escolher_cliente_button)

        self.ref_cliente_input = QLineEdit()
        self.ref_cliente_input.setToolTip(
            "Referência do cliente para a obra (ex.: 2510008). Preenche a "
            "coluna 'Ref. Cliente' e a linha 'Obra:'."
        )
        self.ref_cliente_input.textChanged.connect(self._ref_cliente_mudou)

        self.designacao_input = QLineEdit(construir_designacao(""))
        self.designacao_input.setToolTip(
            "Linha a escrever na coluna 'Designação' da proposta."
        )
        self.designacao_input.textEdited.connect(self._marcar_designacao_manual)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Cliente", cliente_widget)
        form_layout.addRow("Ref. cliente", self.ref_cliente_input)
        form_layout.addRow("Designação", self.designacao_input)

        self.criar_button = QPushButton("Criar no PHC")
        self.criar_button.setToolTip(
            "Conduz a janela do PHC (Dossiers Internos → Proposta) e cria a "
            "proposta base. Não mexas no rato/teclado durante o processo."
        )
        self.criar_button.clicked.connect(self._criar_no_phc)

        self.diagnostico_button = QPushButton("Diagnóstico PHC")
        self.diagnostico_button.setToolTip(
            "Lê (sem escrever) os controlos da janela do PHC e grava um "
            "ficheiro de texto para afinar a leitura do número da proposta."
        )
        self.diagnostico_button.clicked.connect(self._diagnostico)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.clicked.connect(self.reject)

        botoes_layout = QHBoxLayout()
        botoes_layout.addWidget(self.criar_button)
        botoes_layout.addWidget(self.diagnostico_button)
        botoes_layout.addStretch()
        botoes_layout.addWidget(self.fechar_button)

        ajuda = QLabel(
            "Abre primeiro o PHC → Dossiers → 'Proposta' e deixa essa janela "
            "aberta. Depois carrega em 'Criar no PHC'."
        )
        ajuda.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(ajuda)
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addLayout(botoes_layout)
        self.setLayout(layout)

    # -- Recolha de dados --------------------------------------------------

    def _escolher_cliente(self) -> None:
        from app.ui.dialogs.selecionar_cliente_dialog import SelecionarClienteDialog

        dialog = SelecionarClienteDialog(self)
        if not dialog.exec() or dialog.selected_cliente is None:
            return

        cliente = dialog.selected_cliente
        self._cliente_id = cliente.id
        self._num_cliente_phc = (cliente.num_cliente_phc or "").strip() or None
        num = (
            formatar_num_cliente_phc(self._num_cliente_phc)
            if self._num_cliente_phc
            else "sem nº PHC"
        )
        self.cliente_label.setText(f"{cliente.nome}  (PHC {num})")
        self.error_label.setText("")

    def _ref_cliente_mudou(self, texto: str) -> None:
        if not self._designacao_manual:
            self.designacao_input.setText(construir_designacao(texto))

    def _marcar_designacao_manual(self, _texto: str) -> None:
        self._designacao_manual = True

    # -- Ações -------------------------------------------------------------

    def _criar_no_phc(self) -> None:
        if self._cliente_id is None:
            self.error_label.setText("Escolha um cliente.")
            return
        if not self._num_cliente_phc:
            self.error_label.setText(
                "O cliente escolhido não tem número de cliente PHC — não é "
                "possível criar a proposta no PHC."
            )
            return

        ref_cliente = self.ref_cliente_input.text().strip() or None
        designacao = self.designacao_input.text().strip() or construir_designacao(
            ref_cliente
        )
        num_cliente_fmt = formatar_num_cliente_phc(self._num_cliente_phc)

        try:
            plano = construir_plano(
                num_cliente_phc=self._num_cliente_phc,
                ref_cliente=ref_cliente,
                designacao=designacao,
            )
        except ValueError as exc:
            self.error_label.setText(str(exc))
            return

        confirmar = QMessageBox.question(
            self,
            "Confirmar criação no PHC",
            (
                "Vou conduzir a janela do PHC e criar esta proposta:\n\n"
                f"  Nº cliente PHC: {num_cliente_fmt}\n"
                f"  Ref. cliente:   {ref_cliente or '(vazio)'}\n"
                f"  Designação:     {designacao}\n\n"
                "Durante o processo NÃO mexas no rato nem no teclado.\n\n"
                "Continuar?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmar != QMessageBox.StandardButton.Yes:
            return

        self.error_label.setText("")
        ano = date.today().year

        # Marca de água: maior nº de proposta do ano ANTES de criar. É o que
        # permite identificar a nova proposta sem depender do ecrã.
        obrano_base, erro_sql = self._ler_marca_de_agua(ano)
        if erro_sql:
            continuar = QMessageBox.question(
                self,
                "Sem leitura automática do número",
                (
                    "Não consegui ler o último número de proposta do PHC:\n\n"
                    f"{erro_sql}\n\n"
                    "Posso criar a proposta e pedir-te o número no fim. "
                    "Continuar?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if continuar != QMessageBox.StandardButton.Yes:
                return

        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            resultado = PhcAutomationService().criar_proposta(
                num_cliente_phc=self._num_cliente_phc,
                ref_cliente=ref_cliente,
                designacao=designacao,
            )
        except PhcAutomationError as exc:
            QMessageBox.critical(self, "Erro na automação do PHC", str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - mostrar erro inesperado
            QMessageBox.critical(
                self,
                "Erro inesperado",
                f"A automação falhou:\n\n{exc}\n\nPlano tentado:\n"
                f"{descrever_plano(plano)}",
            )
            return
        finally:
            QGuiApplication.restoreOverrideCursor()

        proposta = None
        if obrano_base is not None:
            proposta = self._localizar_no_phc(
                ano=ano,
                obrano_base=obrano_base,
                ref_cliente=ref_cliente,
            )

        if proposta is not None:
            self._mostrar_proposta_encontrada(proposta, num_cliente_fmt)
            return

        # Sem leitura automática: confirmar à mão (não inventar o número).
        numero, ok = QInputDialog.getText(
            self,
            "Número da proposta",
            "A proposta foi gravada no PHC, mas não consegui confirmar o "
            "número na base de dados.\nEscreve o número que vês no PHC:",
        )
        if not ok:
            return

        QMessageBox.information(
            self,
            "Proposta criada",
            (
                f"Proposta PHC nº {numero.strip() or '(por confirmar)'} criada "
                f"para o cliente {num_cliente_fmt}.\n\n"
                "Nesta fase de teste o número ainda não é gravado no V3.\n\n"
                f"Diagnóstico gravado em:\n{resultado.log_path}"
            ),
        )

    def _ler_marca_de_agua(self, ano: int) -> tuple[int | None, str | None]:
        """Maior nº de proposta do ano antes de criar. (valor, erro)."""
        try:
            with SessionLocal() as session:
                return ler_max_obrano(session, ano=ano), None
        except Exception as exc:  # noqa: BLE001 - SQL/PowerShell/config
            return None, str(exc)

    def _localizar_no_phc(
        self, *, ano: int, obrano_base: int, ref_cliente: str | None
    ):
        """Procurar a proposta criada; ``None`` se não der para confirmar."""
        try:
            with SessionLocal() as session:
                return localizar_proposta_criada(
                    session,
                    ano=ano,
                    obrano_base=obrano_base,
                    num_cliente=self._num_cliente_phc,
                    ref_cliente=ref_cliente,
                )
        except Exception:  # noqa: BLE001 - cai no modo manual
            return None

    def _mostrar_proposta_encontrada(self, proposta, num_cliente_fmt: str) -> None:
        """Mostrar o número lido do PHC e o código que ficaria no V3."""
        codigo_v3 = f"{proposta.ano % 100:02d}{proposta.numero:04d}"
        QMessageBox.information(
            self,
            "Proposta criada no PHC",
            (
                f"Proposta PHC nº {proposta.numero} ({proposta.ano}) criada "
                f"para o cliente {num_cliente_fmt}.\n\n"
                f"  Ref. cliente no PHC: {proposta.ref_cliente or '(vazio)'}\n"
                f"  Data:                {proposta.data or '—'}\n\n"
                f"No V3 este orçamento ficaria com o nº {codigo_v3}.\n\n"
                "Nesta fase de teste o número ainda não é gravado no V3."
            ),
        )

    def _diagnostico(self) -> None:
        try:
            caminho = PhcAutomationService().diagnosticar()
        except PhcAutomationError as exc:
            QMessageBox.critical(self, "Erro no diagnóstico", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erro inesperado", str(exc))
            return

        QMessageBox.information(
            self,
            "Diagnóstico do PHC",
            f"Árvore de controlos gravada em:\n{caminho}\n\n"
            "Envia-me este ficheiro para afinar a leitura do número.",
        )
