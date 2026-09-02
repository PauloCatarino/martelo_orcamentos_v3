"""Dialog for creating a simple Orcamento."""

from __future__ import annotations
from app.ui import tema

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.margens_padrao_types import (
    AMBITO_CLIENTE,
    AMBITO_CLIENTE_FINAL,
    AMBITO_STANDARD,
    AMBITO_UTILIZADOR,
)
from app.repositories.user_repository import UserRepository
from app.services.def_margem_padrao_service import DefMargemPadraoService
from app.services.system_setting_service import SystemSettingService


@dataclass(frozen=True, kw_only=True)
class NovoOrcamentoDialogData:
    """Data collected by the new budget dialog."""

    cliente_id: int | None = None
    obra: str
    descricao: str | None
    localizacao: str | None
    ref_cliente: str | None
    enc_phc: str | None = None
    info_1: str | None = None
    info_2: str | None = None
    margens_escolha: str = AMBITO_STANDARD
    utilizador_id: int | None = None
    # Registo manual (orçamento antigo): ano + número indicados pelo
    # utilizador e pasta de servidor já existente.
    manual: bool = False
    ano: int | None = None
    num_orcamento: str | None = None
    pasta_manual: str | None = None
    # Proposta criada no PHC antes de gravar o orçamento: o PHC atribui o
    # número e o V3 mapeia-o (num_orcamento = <ano2><nº4>).
    proposta_phc: str | None = None


class NovoOrcamentoDialog(QDialog):
    """Simple modal dialog for creating a budget."""

    MARGENS_TOOLTIP = (
        "Conjunto de margens copiado para o novo orçamento como valor "
        "inicial; dentro do orçamento o utilizador altera livremente. "
        "'Do cliente' fica disponível quando o cliente indicado tem margens "
        "próprias; 'Do utilizador' quando o utilizador autenticado as tem."
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Novo Orçamento")
        self.setModal(True)
        self.setMinimumWidth(460)

        self._cliente_id: int | None = None
        self._num_cliente_phc: str | None = None
        # Nome e tipo do cliente escolhido: nos temporários a proposta vai no
        # cliente genérico do PHC e é o nome que a identifica.
        self._cliente_nome: str = ""
        self._cliente_temporario: bool = False
        self.cliente_label = QLabel("\u2014 nenhum cliente escolhido \u2014")
        self.escolher_cliente_button = QPushButton("Escolher cliente\u2026")
        self.escolher_cliente_button.clicked.connect(self._escolher_cliente)
        cliente_widget = QWidget()
        cliente_layout = QHBoxLayout(cliente_widget)
        cliente_layout.setContentsMargins(0, 0, 0, 0)
        cliente_layout.addWidget(self.cliente_label, stretch=1)
        cliente_layout.addWidget(self.escolher_cliente_button)

        self.antigo_checkbox = QCheckBox("Orçamento antigo (registo manual)")
        self.antigo_checkbox.setToolTip(
            "Registar um orçamento antigo (pré-V3): o ano e o número são "
            "indicados manualmente e os ficheiros (PDF, Excel, relatórios) "
            "gravam diretamente na pasta de servidor escolhida abaixo."
        )
        self.antigo_checkbox.toggled.connect(self._toggle_modo_antigo)

        self.ano_input = QSpinBox()
        self.ano_input.setRange(2000, date.today().year)
        self.ano_input.setValue(date.today().year - 1)
        self.ano_input.setToolTip("Ano do orçamento antigo (ex.: 2025).")

        self.num_orcamento_input = QLineEdit()
        self.num_orcamento_input.setToolTip(
            "Número do orçamento antigo, tal como usado na pasta do servidor "
            "(ex.: 1049)."
        )

        self._pasta_manual: str | None = None
        self.pasta_label = QLabel("— nenhuma pasta escolhida —")
        self.pasta_label.setWordWrap(True)
        self.pasta_label.setToolTip(
            "Pasta do servidor onde os ficheiros deste orçamento serão "
            "gravados (PDF, Excel, relatórios)."
        )
        self.escolher_pasta_button = QPushButton("Escolher pasta…")
        self.escolher_pasta_button.setToolTip(
            "Selecionar a pasta já existente do orçamento antigo no servidor."
        )
        self.escolher_pasta_button.clicked.connect(self._escolher_pasta)
        pasta_widget = QWidget()
        pasta_layout = QHBoxLayout(pasta_widget)
        pasta_layout.setContentsMargins(0, 0, 0, 0)
        pasta_layout.addWidget(self.pasta_label, stretch=1)
        pasta_layout.addWidget(self.escolher_pasta_button)
        self._pasta_widget = pasta_widget

        self.obra_input = QLineEdit()
        self.descricao_input = QTextEdit()
        self.descricao_input.setFixedHeight(90)
        self.localizacao_input = QLineEdit()
        self.ref_cliente_input = QLineEdit()
        self.ref_cliente_input.setToolTip(
            "Referência do cliente para esta obra (ex.: 2510008). É também a "
            "'Ref. Cliente' da proposta no PHC."
        )
        self.ref_cliente_input.textChanged.connect(self._ref_cliente_mudou)
        self.enc_phc_input = QLineEdit()

        # --- Registo no PHC (o PHC atribui o número; o V3 mapeia-o) --------
        self._proposta_phc: str | None = None
        self._proposta_ano: int | None = None
        # A designação acompanha a ref. cliente até o utilizador a editar.
        self._designacao_phc_manual = False

        self.designacao_phc_input = QLineEdit()
        self.designacao_phc_input.setPlaceholderText(
            "linha a escrever na Designação da proposta (ex.: Obra: 2510008)"
        )
        self.designacao_phc_input.setToolTip(
            "Texto da primeira linha da proposta no PHC. Com Ref. cliente "
            "preenchida sugere 'Obra: <ref>'; sem ela fica vazio para "
            "escreveres o que precisares."
        )
        self.designacao_phc_input.textEdited.connect(
            self._marcar_designacao_phc_manual
        )

        self.criar_phc_button = QPushButton("Criar proposta no PHC…")
        self.criar_phc_button.setToolTip(
            "Cria a proposta no PHC (cliente + ref. cliente + linha de "
            "designação) e usa o número que o PHC atribuir como número deste "
            "orçamento. Requer o PHC aberto em Dossiers Internos → Proposta."
        )
        self.criar_phc_button.clicked.connect(self._criar_proposta_phc)

        self.proposta_phc_label = QLabel("— sem proposta no PHC —")
        self.proposta_phc_label.setWordWrap(True)
        self.proposta_phc_label.setToolTip(
            "Número da proposta no PHC, depois de criada."
        )
        phc_widget = QWidget()
        phc_layout = QHBoxLayout(phc_widget)
        phc_layout.setContentsMargins(0, 0, 0, 0)
        phc_layout.addWidget(self.proposta_phc_label, stretch=1)
        phc_layout.addWidget(self.criar_phc_button)
        self.info_1_input = QTextEdit()
        self.info_1_input.setFixedHeight(60)
        self.info_2_input = QTextEdit()
        self.info_2_input.setFixedHeight(60)

        self.utilizador_combo = QComboBox()
        self._carregar_utilizadores()

        self.margens_combo = QComboBox()
        self.margens_combo.setToolTip(self.MARGENS_TOOLTIP)
        self.margens_combo.addItem("Standard", AMBITO_STANDARD)
        self.margens_combo.addItem("Do cliente", AMBITO_CLIENTE)
        self.margens_combo.addItem("Cliente Final", AMBITO_CLIENTE_FINAL)
        self._carregar_disponibilidade_margens()

        self.error_label = QLabel("")
        self.error_label.setObjectName("novoOrcamentoError")
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
        self.error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Cliente", cliente_widget)
        form_layout.addRow("", self.antigo_checkbox)
        form_layout.addRow("Ano", self.ano_input)
        form_layout.addRow("N.º orçamento", self.num_orcamento_input)
        form_layout.addRow("Pasta do orçamento", pasta_widget)
        form_layout.addRow("Obra", self.obra_input)
        form_layout.addRow("Descrição", self.descricao_input)
        form_layout.addRow("Localização", self.localizacao_input)
        form_layout.addRow("Ref. cliente", self.ref_cliente_input)
        form_layout.addRow("Designação (PHC)", self.designacao_phc_input)
        form_layout.addRow("Proposta PHC", phc_widget)
        form_layout.addRow("Enc. PHC", self.enc_phc_input)
        form_layout.addRow("Info 1", self.info_1_input)
        form_layout.addRow("Info 2", self.info_2_input)
        form_layout.addRow("Utilizador", self.utilizador_combo)
        form_layout.addRow("Margens iniciais:", self.margens_combo)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self._form_layout = form_layout
        self._toggle_modo_antigo(False)
        self._atualizar_criar_phc_disponivel()

    def get_data(self) -> NovoOrcamentoDialogData:
        """Return normalized dialog data."""
        manual = self.antigo_checkbox.isChecked()
        # Proposta criada no PHC: o número do orçamento passa a ser o código
        # <ano2><nº4> derivado dela, e o ano é o da proposta.
        num_do_phc: str | None = None
        ano_do_phc: int | None = None
        if self._proposta_phc and self._proposta_ano and not manual:
            from app.services.registar_proposta_phc_service import (
                formatar_codigo_v3,
            )

            num_do_phc = formatar_codigo_v3(
                self._proposta_ano, int(self._proposta_phc)
            )
            ano_do_phc = self._proposta_ano

        return NovoOrcamentoDialogData(
            cliente_id=self._cliente_id,
            obra=self.obra_input.text().strip(),
            descricao=self._empty_to_none(self.descricao_input.toPlainText()),
            localizacao=self._empty_to_none(self.localizacao_input.text()),
            ref_cliente=self._empty_to_none(self.ref_cliente_input.text()),
            enc_phc=self._empty_to_none(self.enc_phc_input.text()),
            info_1=self._empty_to_none(self.info_1_input.toPlainText()),
            info_2=self._empty_to_none(self.info_2_input.toPlainText()),
            margens_escolha=self.margens_combo.currentData() or AMBITO_STANDARD,
            utilizador_id=self.utilizador_combo.currentData(),
            manual=manual,
            ano=self.ano_input.value() if manual else ano_do_phc,
            num_orcamento=(
                self._empty_to_none(self.num_orcamento_input.text())
                if manual
                else num_do_phc
            ),
            pasta_manual=self._pasta_manual if manual else None,
            proposta_phc=self._proposta_phc if not manual else None,
        )

    # -- Proposta no PHC ---------------------------------------------------

    def _ref_cliente_mudou(self, texto: str) -> None:
        """Sugerir a designação do PHC a partir da ref. cliente."""
        if self._designacao_phc_manual:
            return
        from app.services.registar_proposta_phc_service import designacao_sugerida

        self.designacao_phc_input.setText(designacao_sugerida(texto))

    def _marcar_designacao_phc_manual(self, _texto: str) -> None:
        """O utilizador editou a designação: deixar de a sobrepor."""
        self._designacao_phc_manual = True

    def _criar_proposta_phc(self) -> None:
        """Criar a proposta no PHC e adotar o número que ele atribuir."""
        from datetime import date as _date

        from PySide6.QtCore import Qt as _Qt
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QInputDialog

        from app.services.phc_automation_service import (
            PhcAutomationError,
            construir_designacao,
            formatar_num_cliente_phc,
        )
        from app.services.registar_proposta_phc_service import (
            descrever_resultado,
            registar_proposta_no_phc,
        )

        if self._proposta_phc:
            QMessageBox.information(
                self,
                "Proposta já criada",
                f"Este orçamento já tem a proposta PHC nº {self._proposta_phc}.\n\n"
                "Para não duplicar propostas no PHC, cancela e começa de novo "
                "se precisares de outra.",
            )
            return

        if self._cliente_id is None:
            self.error_label.setText("Escolha um cliente antes de criar no PHC.")
            return

        num_cliente, nome_cliente = self._cliente_phc_da_proposta()
        if not num_cliente:
            self.error_label.setText(
                "O cliente escolhido não tem número de cliente PHC nem nome — "
                "não é possível criar a proposta no PHC."
            )
            return

        ref_cliente = self._empty_to_none(self.ref_cliente_input.text())
        designacao = self._empty_to_none(self.designacao_phc_input.text())
        if not designacao:
            designacao = construir_designacao(ref_cliente)

        detalhes = [f"  Nº cliente PHC: {formatar_num_cliente_phc(num_cliente)}"]
        if nome_cliente:
            detalhes.append(f"  Nome a escrever: {nome_cliente}")
        detalhes.append(f"  Ref. cliente:   {ref_cliente or '(vazio)'}")
        detalhes.append(f"  Designação:     {designacao}")

        aviso_temporario = ""
        if nome_cliente:
            aviso_temporario = (
                "\nEste cliente é TEMPORÁRIO (não existe no PHC): a proposta "
                "vai no cliente genérico 063 «CONSUMIDOR FINAL» e o PHC abre "
                "uma janela onde o nome é substituído pelo nome acima.\n"
            )

        confirmar = QMessageBox.question(
            self,
            "Confirmar criação no PHC",
            (
                "Vou conduzir a janela do PHC e criar esta proposta:\n\n"
                + "\n".join(detalhes)
                + "\n"
                + aviso_temporario
                + "\nO PHC tem de estar aberto em Dossiers Internos com "
                "'Proposta' escolhido no seletor.\n"
                "Durante o processo NÃO mexas no rato nem no teclado.\n\n"
                "Continuar?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmar != QMessageBox.StandardButton.Yes:
            return

        self.error_label.setText("")
        ano = _date.today().year
        QGuiApplication.setOverrideCursor(_Qt.CursorShape.WaitCursor)
        try:
            with SessionLocal() as session:
                resultado = registar_proposta_no_phc(
                    session,
                    ano=ano,
                    num_cliente_phc=num_cliente,
                    ref_cliente=ref_cliente,
                    designacao=designacao,
                    nome_cliente=nome_cliente,
                )
        except PhcAutomationError as exc:
            QMessageBox.critical(self, "Erro na automação do PHC", str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - mostrar erro inesperado
            QMessageBox.critical(self, "Erro inesperado", str(exc))
            return
        finally:
            QGuiApplication.restoreOverrideCursor()

        texto = descrever_resultado(
            resultado, num_cliente_phc=num_cliente, nome_cliente=nome_cliente
        )

        if resultado.tipo_errado:
            QMessageBox.critical(self, "Documento errado no PHC", texto)
            return

        numero = resultado.numero_confirmado
        if numero is None:
            escrito, ok = QInputDialog.getText(
                self,
                "Número da proposta",
                f"{texto}\n\nEscreve o número que vês no PHC:",
            )
            if not ok or not escrito.strip().isdigit():
                return
            numero = int(escrito.strip())

        self._adotar_proposta(numero, ano)

        # A proposta ja' existe no PHC, mas no Martelo ainda nao ha' orcamento
        # nenhum: isso so' acontece no «Guardar» desta janela. Ja' houve quem
        # fechasse aqui a pensar que o PHC tinha tratado dos dois lados.
        texto += (
            "\n\n"
            "⚠️ Falta guardar no Martelo.\n"
            "A proposta ficou criada no PHC, mas o orçamento ainda NÃO existe "
            "no Martelo. Carregue em «Guardar» nesta janela para o criar — se "
            "fechar agora, fica com a proposta no PHC e sem orçamento cá."
        )

        if resultado.avisos:
            QMessageBox.warning(self, "Proposta criada — com diferenças", texto)
        else:
            QMessageBox.information(self, "Proposta criada no PHC", texto)

        self._realcar_guardar()

    def _realcar_guardar(self) -> None:
        """Deixar claro que ainda falta o «Guardar» deste lado."""
        guardar = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        guardar.setText("Guardar no Martelo")
        guardar.setDefault(True)
        guardar.setStyleSheet(
            f"QPushButton {{ background-color: {tema.CASTANHO_ESCURO};"
            " color: #FFFFFF; font-weight: 600; padding: 6px 14px;"
            " border-radius: 4px; }"
            f"QPushButton:hover {{ background-color: {tema.CASTANHO_MEDIO}; }}"
        )
        guardar.setToolTip(
            "A proposta já está no PHC. Falta criar o orçamento no Martelo."
        )
        guardar.setFocus()
        self.error_label.setStyleSheet(f"color: {tema.TEXTO_AVISO};")
        self.error_label.setText(
            "Proposta criada no PHC. O orçamento só fica no Martelo depois de "
            "carregar em «Guardar no Martelo»."
        )

    def reject(self) -> None:  # noqa: D102 - assinatura do Qt
        """Confirmar antes de sair com uma proposta criada e nada guardado."""
        if self._proposta_phc:
            resposta = QMessageBox.question(
                self,
                "Sair sem guardar?",
                f"A proposta {self._proposta_phc} já foi criada no PHC, mas o "
                "orçamento ainda não existe no Martelo.\n\n"
                "Se sair agora, fica com a proposta no PHC e sem orçamento cá "
                "— e terá de a registar à mão mais tarde.\n\n"
                "Quer mesmo sair sem guardar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
        super().reject()

    def _adotar_proposta(self, numero: int, ano: int) -> None:
        """Fixar a proposta e mostrar o nº do orçamento que dela resulta."""
        from app.services.registar_proposta_phc_service import formatar_codigo_v3

        self._proposta_phc = str(numero)
        self._proposta_ano = ano
        codigo = formatar_codigo_v3(ano, numero)
        self.proposta_phc_label.setText(
            f"Proposta {numero} ({ano}) → orçamento {codigo}"
        )
        # Impedir uma segunda proposta para o mesmo orçamento.
        self.criar_phc_button.setEnabled(False)
        self.antigo_checkbox.setEnabled(False)
        self.antigo_checkbox.setToolTip(
            "Indisponível: este orçamento já tem uma proposta criada no PHC."
        )

    def _toggle_modo_antigo(self, checked: bool) -> None:
        """Show/hide the manual fields of the legacy-budget mode."""
        self._form_layout.setRowVisible(self.ano_input, checked)
        self._form_layout.setRowVisible(self.num_orcamento_input, checked)
        self._form_layout.setRowVisible(self._pasta_widget, checked)
        self.error_label.setText("")
        self.adjustSize()

    def _escolher_pasta(self) -> None:
        """Pick the existing server folder of the legacy budget."""
        inicio = ""
        try:
            with SessionLocal() as session:
                base = SystemSettingService(session).obter_valor(
                    "pasta_base_orcamentos"
                )
        except SQLAlchemyError:
            base = None

        if base:
            candidato = Path(base) / str(self.ano_input.value())
            if candidato.exists():
                inicio = str(candidato)
            elif Path(base).exists():
                inicio = base

        pasta = QFileDialog.getExistingDirectory(
            self,
            "Escolher pasta do orçamento",
            inicio,
        )
        if not pasta:
            return

        self._pasta_manual = pasta
        self.pasta_label.setText(pasta)

    def _carregar_utilizadores(self) -> None:
        """Populate the active-users combo, preselecting the logged-in user."""
        try:
            with SessionLocal() as session:
                utilizadores = UserRepository(session).list_active_users()
        except SQLAlchemyError:
            utilizadores = []

        self.utilizador_combo.clear()
        for utilizador in utilizadores:
            self.utilizador_combo.addItem(utilizador.username, utilizador.id)

        current_user = app_session.current_user
        if current_user is None:
            return

        index = self.utilizador_combo.findData(current_user.id)
        if index >= 0:
            self.utilizador_combo.setCurrentIndex(index)

    def _escolher_cliente(self) -> None:
        from app.ui.dialogs.selecionar_cliente_dialog import SelecionarClienteDialog

        dialog = SelecionarClienteDialog(self)
        if not dialog.exec() or dialog.selected_cliente is None:
            return

        cliente = dialog.selected_cliente
        self._cliente_id = cliente.id
        self._num_cliente_phc = (cliente.num_cliente_phc or "").strip() or None
        self._cliente_nome = (cliente.nome or "").strip()
        self._cliente_temporario = bool(cliente.is_temporary)
        tipo = "Tempor\u00e1rio" if cliente.is_temporary else "PHC"
        self.cliente_label.setText(f"{cliente.nome} ({tipo})")
        self._atualizar_criar_phc_disponivel()
        self._atualizar_opcao_margens_cliente()

    def _cliente_phc_da_proposta(self) -> tuple[str | None, str | None]:
        """(n\u00ba de cliente a escrever no PHC, nome a escrever) para este cliente.

        Cliente do PHC: o seu pr\u00f3prio n\u00famero, sem nome a escrever (o PHC vai
        busc\u00e1-lo). Cliente **tempor\u00e1rio**: n\u00e3o existe no PHC, por isso a
        proposta \u00e9 feita no cliente gen\u00e9rico ``063`` (\u00abCONSUMIDOR FINAL\u00bb) e o
        nome verdadeiro \u00e9 escrito na janela que o PHC abre a seguir.
        """
        from app.services.phc_automation_service import CLIENTE_GENERICO_PHC

        if self._cliente_temporario:
            nome = (self._cliente_nome or "").strip()
            return (CLIENTE_GENERICO_PHC, nome) if nome else (None, None)
        return (self._num_cliente_phc, None)

    def _atualizar_criar_phc_disponivel(self) -> None:
        """Quem pode ir para o PHC: cliente com n\u00ba PHC, ou tempor\u00e1rio com nome."""
        if self._proposta_phc:
            return
        num_cliente, nome = self._cliente_phc_da_proposta()
        self.criar_phc_button.setEnabled(bool(num_cliente))
        if not num_cliente:
            self.proposta_phc_label.setText(
                "\u2014 cliente sem n\u00ba PHC nem nome: n\u00e3o d\u00e1 para criar proposta \u2014"
            )
        elif nome:
            self.proposta_phc_label.setText(
                "\u2014 sem proposta no PHC (cliente tempor\u00e1rio: vai no 063) \u2014"
            )
        else:
            self.proposta_phc_label.setText("\u2014 sem proposta no PHC \u2014")

    def _carregar_disponibilidade_margens(self) -> None:
        """Enable the margin options that have an applicable record."""
        current_user = app_session.current_user
        tem_margens_user = False
        if current_user is not None:
            try:
                with SessionLocal() as session:
                    tem_margens_user = (
                        DefMargemPadraoService(session).margens_utilizador(
                            current_user.id
                        )
                        is not None
                    )
            except SQLAlchemyError:
                tem_margens_user = False

        self._set_opcao_margens_enabled(AMBITO_UTILIZADOR, tem_margens_user)
        try:
            with SessionLocal() as session:
                tem_cliente_final = (
                    DefMargemPadraoService(session).obter_cliente_final() is not None
                )
        except SQLAlchemyError:
            tem_cliente_final = False
        self._set_opcao_margens_enabled(AMBITO_CLIENTE_FINAL, tem_cliente_final)
        self._atualizar_opcao_margens_cliente()

    def _atualizar_opcao_margens_cliente(self) -> None:
        """Enable 'Do cliente' when the selected customer has its own margins."""
        try:
            with SessionLocal() as session:
                margens = DefMargemPadraoService(session).margens_cliente(
                    self._cliente_id
                )
        except SQLAlchemyError:
            margens = None

        self._set_opcao_margens_enabled(AMBITO_CLIENTE, margens is not None)

    def _set_opcao_margens_enabled(self, ambito: str, enabled: bool) -> None:
        """Enable/disable one margins-combo option, resetting if selected."""
        index = self.margens_combo.findData(ambito)
        if index < 0:
            return

        item = self.margens_combo.model().item(index)
        if item is None:
            return

        flags = item.flags()
        if enabled:
            item.setFlags(flags | Qt.ItemFlag.ItemIsEnabled)
        else:
            item.setFlags(flags & ~Qt.ItemFlag.ItemIsEnabled)
            if self.margens_combo.currentIndex() == index:
                self.margens_combo.setCurrentIndex(
                    self.margens_combo.findData(AMBITO_STANDARD)
                )

    def _validate_and_accept(self) -> None:
        """Validate required fields before accepting."""
        data = self.get_data()

        if data.cliente_id is None:
            self.error_label.setText("Escolha um cliente.")
            return

        if data.manual:
            if not data.num_orcamento:
                self.error_label.setText(
                    "Indique o número do orçamento antigo."
                )
                return
            if not data.pasta_manual:
                self.error_label.setText(
                    "Escolha a pasta do orçamento no servidor."
                )
                return
            if not Path(data.pasta_manual).exists():
                self.error_label.setText(
                    f"A pasta escolhida não existe:\n{data.pasta_manual}"
                )
                return

        self.accept()

    def _empty_to_none(self, value: str) -> str | None:
        """Normalize empty text input."""
        normalized = value.strip()
        return normalized or None
