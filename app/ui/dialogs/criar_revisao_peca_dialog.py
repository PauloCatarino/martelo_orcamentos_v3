"""Confirmation dialog for creating a new catalog-piece revision."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.repositories.def_peca_repository import DefPecaResumo
from app.services.def_peca_revisao_service import PrepararRevisaoPecaResult


@dataclass(frozen=True)
class CriarRevisaoPecaFormData:
    codigo: str
    nome: str


class CriarRevisaoPecaDialog(QDialog):
    """Show the revision impact before the user confirms it."""

    def __init__(
        self,
        peca: DefPecaResumo,
        preparacao: PrepararRevisaoPecaResult,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Criar nova revisão da peça")
        self.setMinimumWidth(560)

        explicacao = QLabel(
            f"Será criada a revisão R{preparacao.proxima_revisao} a partir de "
            f"{peca.codigo} · R{preparacao.revisao_atual}."
        )
        explicacao.setWordWrap(True)

        impacto = QLabel(
            f"Serão copiadas {preparacao.operacoes_a_copiar} operação(ões) e "
            f"{preparacao.componentes_a_copiar} associado(s). A revisão atual "
            "fica inativa para novos orçamentos; os orçamentos existentes não são alterados."
        )
        impacto.setWordWrap(True)
        impacto.setObjectName("criarRevisaoImpacto")

        self.codigo_input = QLineEdit(preparacao.codigo_sugerido)
        self.nome_input = QLineEdit(peca.nome)
        form = QFormLayout()
        form.addRow("Código da nova revisão", self.codigo_input)
        form.addRow("Nome", self.nome_input)

        self.erro_label = QLabel("")
        self.erro_label.setObjectName("criarRevisaoErro")
        self.erro_label.setWordWrap(True)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            "Criar revisão"
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.buttons.accepted.connect(self._validar_e_aceitar)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(explicacao)
        layout.addWidget(impacto)
        layout.addLayout(form)
        layout.addWidget(self.erro_label)
        layout.addWidget(self.buttons)

    def form_data(self) -> CriarRevisaoPecaFormData:
        return CriarRevisaoPecaFormData(
            codigo=self.codigo_input.text().strip(),
            nome=self.nome_input.text().strip(),
        )

    def _validar_e_aceitar(self) -> None:
        dados = self.form_data()
        if not dados.codigo:
            self.erro_label.setText("O código da nova revisão é obrigatório.")
            self.codigo_input.setFocus()
            return
        if not dados.nome:
            self.erro_label.setText("O nome da nova revisão é obrigatório.")
            self.nome_input.setFocus()
            return
        self.accept()
