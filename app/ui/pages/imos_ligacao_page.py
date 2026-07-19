"""Configuração e diagnóstico da ligação SQL iMos apenas de leitura."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.db.session import SessionLocal
from app.services.imos_sql import (
    ImosConfig,
    diagnosticar_ligacao,
    explicar_erro_ligacao,
    load_imos_config,
    save_imos_config,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho


class ImosLigacaoPage(QWidget):
    """Página sem importação: configura e valida o acesso read-only."""

    def __init__(self, on_back=None) -> None:
        super().__init__()
        self.on_back = on_back
        self.cabecalho = BarraCabecalho(
            "Ligação iMos — somente leitura",
            [
                "O Martelo apenas executa consultas SELECT. O teste valida a "
                "ligação e informa se a conta SQL também é somente de leitura."
            ],
        )
        self.server_edit = QLineEdit()
        self.database_edit = QLineEdit()
        self.user_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_password_check = QCheckBox("Mostrar password")
        self.show_password_check.toggled.connect(self._mostrar_password)
        self.trusted_check = QCheckBox("Usar autenticação Windows")
        self.trust_cert_check = QCheckBox("Confiar no certificado do servidor")
        self.trusted_check.toggled.connect(self._atualizar_credenciais)

        formulario = QFormLayout()
        formulario.addRow("Servidor / instância", self.server_edit)
        formulario.addRow("Base de dados", self.database_edit)
        formulario.addRow("Utilizador SQL", self.user_edit)
        formulario.addRow("Password", self.password_edit)
        formulario.addRow("", self.show_password_check)
        formulario.addRow("", self.trusted_check)
        formulario.addRow("", self.trust_cert_check)
        grupo = QGroupBox("Dados de ligação")
        grupo.setLayout(formulario)

        self.save_button = QPushButton("Guardar configuração")
        self.save_button.clicked.connect(self.guardar)
        self.test_button = QPushButton("Testar ligação e permissões")
        self.test_button.clicked.connect(self.testar)
        self.voltar_button = QPushButton("Voltar às Configurações")
        self.voltar_button.setToolTip("Regressar ao menu Configurações.")
        self.voltar_button.clicked.connect(
            lambda: self.on_back() if self.on_back else None
        )
        acoes = QHBoxLayout()
        acoes.addWidget(self.save_button)
        acoes.addWidget(self.test_button)
        acoes.addStretch()
        acoes.addWidget(self.voltar_button)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("imosLigacaoStatus")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addWidget(grupo)
        layout.addLayout(acoes)
        layout.addWidget(self.status_label)
        layout.addStretch()
        self.carregar()

    def _config_formulario(self) -> ImosConfig:
        return {
            "server": self.server_edit.text().strip(),
            "database": self.database_edit.text().strip(),
            "user": self.user_edit.text().strip(),
            "password": self.password_edit.text(),
            "trusted": self.trusted_check.isChecked(),
            "trust_server_certificate": self.trust_cert_check.isChecked(),
        }

    def carregar(self) -> None:
        with SessionLocal() as session:
            cfg = load_imos_config(session)
        self.server_edit.setText(cfg["server"])
        self.database_edit.setText(cfg["database"])
        self.user_edit.setText(cfg["user"])
        self.password_edit.setText(cfg["password"])
        self.trusted_check.setChecked(cfg["trusted"])
        self.trust_cert_check.setChecked(cfg["trust_server_certificate"])
        self._atualizar_credenciais()

    def guardar(self) -> None:
        cfg = self._config_formulario()
        try:
            # Valida os campos sem abrir qualquer ligação externa.
            from app.services.imos_sql import build_connection_string

            build_connection_string(cfg)
            with SessionLocal() as session:
                save_imos_config(session, cfg)
        except (ValueError, RuntimeError) as exc:
            self.status_label.setText(str(exc))
            QMessageBox.warning(self, "Ligação iMos", str(exc))
            return
        self.status_label.setText(
            "Configuração guardada. Ainda não foram consultados nem importados dados iMos."
        )

    def testar(self) -> None:
        self.test_button.setEnabled(False)
        self.status_label.setText("A testar ligação e permissões de leitura…")
        try:
            diagnostico = diagnosticar_ligacao(self._config_formulario())
        except (ValueError, RuntimeError, OSError) as exc:
            texto = explicar_erro_ligacao(exc)
            self.status_label.setText(f"Teste falhou: {texto}")
            QMessageBox.warning(self, "Diagnóstico iMos", texto)
        else:
            texto = (
                "Ligação SQL validada. A barreira do Martelo aceita apenas SELECT. "
                f"Servidor: {diagnostico.servidor} | Base: {diagnostico.base_dados} | "
                f"Login: {diagnostico.login} | "
                f"Tabelas consultáveis: {diagnostico.tabelas_consultaveis}. "
            )
            if diagnostico.conta_sql_somente_leitura:
                texto += "A conta SQL também foi confirmada como somente de leitura. "
            else:
                texto += (
                    "ATENÇÃO: a conta SQL tem permissões de escrita; o Martelo não "
                    "as utiliza, mas futuramente recomenda-se uma conta read-only. "
                )
            texto += "Nenhum dado foi importado ou alterado."
            self.status_label.setText(texto)
            QMessageBox.information(self, "Diagnóstico iMos", texto)
        finally:
            self.test_button.setEnabled(True)

    def _atualizar_credenciais(self) -> None:
        enabled = not self.trusted_check.isChecked()
        self.user_edit.setEnabled(enabled)
        self.password_edit.setEnabled(enabled)

    def _mostrar_password(self, mostrar: bool) -> None:
        modo = QLineEdit.EchoMode.Normal if mostrar else QLineEdit.EchoMode.Password
        self.password_edit.setEchoMode(modo)
