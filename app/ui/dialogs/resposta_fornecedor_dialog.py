"""Dialog to review a supplier's price answer before it touches the catalog."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.domain.resposta_fornecedor import (
    ESTADO_ANOMALIA,
    ESTADO_ATUALIZA,
    ESTADO_DESCONHECIDO,
    ESTADO_DESCONTINUADO,
    ESTADO_SEM_ALTERACAO,
    ESTADO_SEM_RESPOSTA,
    PropostaPreco,
    resumir,
)
from app.ui import tema
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency

CORES_ESTADO = {
    ESTADO_ATUALIZA: (tema.VERDE_SUAVE, tema.VERDE_ESCURO),
    ESTADO_ANOMALIA: (tema.OCRE_SUAVE, tema.OCRE_ESCURO),
    ESTADO_DESCONTINUADO: (tema.VERMELHO_SUAVE, tema.VERMELHO_ESCURO),
    ESTADO_DESCONHECIDO: (tema.VERMELHO_SUAVE, tema.VERMELHO_ESCURO),
    ESTADO_SEM_ALTERACAO: (tema.CINZA_SUAVE, tema.CINZA_ESCURO),
    ESTADO_SEM_RESPOSTA: (tema.CINZA_SUAVE, tema.CINZA_ESCURO),
}


class RespostaFornecedorDialog(QDialog):
    """Rever o que o fornecedor respondeu, linha a linha.

    Nada entra no catálogo sem um visto: mesmo com o ficheiro bem preenchido, um
    engano do fornecedor (uma vírgula a mais) chegaria aos orçamentos.
    """

    TABLE_HEADERS = [
        "✓",
        "Estado",
        "Código",
        "Descrição",
        "Preço atual",
        "Preço novo",
        "Variação",
        "Desc%",
        "O que o V3 assinala",
        "Observações do fornecedor",
    ]

    HEADER_TOOLTIPS = [
        "Marque o que quer aplicar ao catálogo.",
        "O que o V3 percebeu desta linha.",
        "A nossa referência — é por ela que a linha é reconhecida.",
        "Descrição no nosso catálogo.",
        "Preço de tabela que temos hoje.",
        "Preço de tabela que o fornecedor indicou.",
        "De quanto muda o preço.",
        "Desconto indicado pelo fornecedor.",
        "O que parece estranho nesta linha — leia antes de aplicar.",
        "O que o fornecedor escreveu.",
    ]

    COLUNA_VISTO = 0
    COLUNA_ESTADO = 1
    COLUNA_VARIACAO = 6
    COLUNA_AVISOS = 8

    def __init__(
        self,
        propostas: list[PropostaPreco],
        caminho: str | None = None,
        parent=None,
        on_aplicar: Callable[[list[PropostaPreco]], bool] | None = None,
        notas=None,
    ) -> None:
        super().__init__(parent)

        self.propostas = propostas
        self.on_aplicar = on_aplicar
        self.notas = list(notas or [])

        self.setWindowTitle("Resposta do fornecedor")
        self.setModal(True)
        self.setMinimumSize(1100, 600)
        self._dimensionar_ao_ecra()

        self.resumo_label = QLabel(resumir(propostas))
        self.resumo_label.setStyleSheet("font-weight: bold;")
        self.resumo_label.setWordWrap(True)

        self.caminho_label = QLabel(
            f"Ficheiro: {caminho}" if caminho else "Ficheiro do fornecedor."
        )
        self.caminho_label.setWordWrap(True)

        self.notas_label = QLabel("\n".join(f"• {nota}" for nota in self.notas))
        self.notas_label.setWordWrap(True)
        self.notas_label.setVisible(bool(self.notas))
        self.notas_label.setToolTip(
            "Como o ficheiro foi lido. O que aqui aparece é um palpite do V3 e "
            "pede uma vista de olhos."
        )
        self.notas_label.setStyleSheet(
            f"background: {tema.OCRE_SUAVE}; color: {tema.OCRE_ESCURO};"
            " padding: 6px; border-radius: 4px;"
        )

        self.mostrar_tudo_input = QCheckBox("Mostrar também o que não muda nada")
        self.mostrar_tudo_input.setToolTip(
            "Linhas sem alteração, por preencher ou com códigos que não existem."
        )
        self.mostrar_tudo_input.stateChanged.connect(self._preencher)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        cabecalho = self.table.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        cabecalho.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        ligar_persistencia_larguras(self.table, "dialog_resposta_fornecedor")
        for indice, tooltip in enumerate(self.HEADER_TOOLTIPS):
            item = self.table.horizontalHeaderItem(indice)
            if item is not None:
                item.setToolTip(tooltip)

        self.aplicar_button = QPushButton("Aplicar as selecionadas")
        self.aplicar_button.setToolTip(
            "Grava os preços marcados no catálogo, com registo no histórico."
        )
        self.aplicar_button.clicked.connect(self._aplicar)

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.setToolTip("Fechar sem mudar nada.")
        self.cancelar_button.clicked.connect(self.reject)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        filtros = QHBoxLayout()
        filtros.addWidget(self.mostrar_tudo_input)
        filtros.addStretch()

        botoes = QHBoxLayout()
        botoes.addStretch()
        botoes.addWidget(self.aplicar_button)
        botoes.addWidget(self.cancelar_button)

        layout = QVBoxLayout()
        layout.addWidget(self.resumo_label)
        layout.addWidget(self.caminho_label)
        layout.addWidget(self.notas_label)
        layout.addLayout(filtros)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        self._preencher()

    def _dimensionar_ao_ecra(self) -> None:
        ecra = QGuiApplication.primaryScreen()
        if ecra is None:
            self.resize(1300, 800)
            return

        disponivel = ecra.availableGeometry()
        self.resize(
            max(min(int(disponivel.width() * 0.9), 1700), 1100),
            max(min(int(disponivel.height() * 0.85), 950), 600),
        )

    def propostas_visiveis(self) -> list[PropostaPreco]:
        """As que interessam agora: por omissão só as que podem mudar algo."""
        if self.mostrar_tudo_input.isChecked():
            return list(self.propostas)

        return [proposta for proposta in self.propostas if proposta.aplicavel]

    def _preencher(self) -> None:
        """Encher a tabela, marcando de início só o que é seguro."""
        visiveis = self.propostas_visiveis()
        self.table.setRowCount(len(visiveis))
        self._por_linha: dict[int, PropostaPreco] = {}

        for linha, proposta in enumerate(visiveis):
            self._por_linha[linha] = proposta

            visto = QTableWidgetItem()
            if proposta.aplicavel:
                visto.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                )
                visto.setCheckState(
                    Qt.CheckState.Checked
                    if proposta.sugerido
                    else Qt.CheckState.Unchecked
                )
            else:
                visto.setFlags(Qt.ItemFlag.NoItemFlags)
            self.table.setItem(linha, self.COLUNA_VISTO, visto)

            valores = [
                proposta.estado,
                proposta.codigo or "",
                proposta.descricao or "",
                format_currency(proposta.preco_atual),
                format_currency(proposta.preco_novo),
                self._texto_variacao(proposta),
                f"{proposta.desconto_novo:g}%" if proposta.desconto_novo is not None else "",
                " · ".join(proposta.avisos),
                proposta.observacoes or "",
            ]
            for coluna, valor in enumerate(valores, start=1):
                item = QTableWidgetItem(valor)
                if proposta.detalhe:
                    item.setToolTip(proposta.detalhe)
                self.table.setItem(linha, coluna, item)

            fundo, texto = CORES_ESTADO.get(proposta.estado, (None, None))
            if fundo is not None:
                estado_item = self.table.item(linha, self.COLUNA_ESTADO)
                estado_item.setBackground(QColor(fundo))
                estado_item.setForeground(QColor(texto))

        self.table.resizeColumnsToContents()
        self._atualizar_status()

    def _texto_variacao(self, proposta: PropostaPreco) -> str:
        if proposta.variacao is None:
            return ""

        sinal = "+" if proposta.variacao > 0 else ""
        return f"{sinal}{proposta.variacao:.1f}%".replace(".", ",")

    def _atualizar_status(self) -> None:
        """Linha do supervisor: o que está marcado e o que exige atenção."""
        marcadas = len(self.propostas_marcadas())
        a_confirmar = sum(
            1 for proposta in self.propostas if proposta.estado == ESTADO_ANOMALIA
        )
        desconhecidas = sum(
            1 for proposta in self.propostas if proposta.estado == ESTADO_DESCONHECIDO
        )

        partes = [f"{marcadas} linhas marcadas para aplicar"]
        if a_confirmar:
            partes.append(f"{a_confirmar} com variação invulgar, por confirmar")
        if desconhecidas:
            partes.append(f"{desconhecidas} com código que não existe no catálogo")

        self.status_label.setText(" · ".join(partes) + ".")

    def propostas_marcadas(self) -> list[PropostaPreco]:
        """As linhas com visto — e só as que podem mesmo ser aplicadas."""
        marcadas = []
        for linha, proposta in getattr(self, "_por_linha", {}).items():
            item = self.table.item(linha, self.COLUNA_VISTO)
            if (
                item is not None
                and item.checkState() == Qt.CheckState.Checked
                and proposta.aplicavel
            ):
                marcadas.append(proposta)

        return marcadas

    def _aplicar(self) -> None:
        """Aplicar ao catálogo o que ficou marcado."""
        marcadas = self.propostas_marcadas()
        if not marcadas:
            self.status_label.setText("Não há nada marcado para aplicar.")
            return

        if self.on_aplicar is not None and not self.on_aplicar(marcadas):
            return

        self.accept()
