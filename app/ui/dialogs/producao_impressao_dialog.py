"""Dialog that lists the obra documents and prints them in the user's order."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services import producao_impressao_service as svc
from app.ui import tema


_COL_SEL = 0
_COL_PRIORIDADE = 1
_COL_FICHEIRO = 2
_COL_CATEGORIA = 3
_COL_ORIGEM = 4
_COL_QT = 5
_COL_PAPEL = 6
_COL_ORIENTACAO = 7
_COL_DUPLEX = 8
_COL_COR = 9

_CABECALHOS = [
    "",
    "Prioridade",
    "Ficheiro",
    "Categoria",
    "Origem",
    "Qt",
    "Papel",
    "Orientação",
    "Duplex",
    "Cor",
]

_LARGURAS = {
    _COL_SEL: 34,
    _COL_PRIORIDADE: 80,
    _COL_FICHEIRO: 330,
    _COL_CATEGORIA: 190,
    _COL_ORIGEM: 100,
    _COL_QT: 55,
    _COL_PAPEL: 70,
    _COL_ORIENTACAO: 110,
    _COL_DUPLEX: 65,
    _COL_COR: 80,
}


class ProducaoImpressaoDialog(QDialog):
    """Print the obra documents, by priority, with the order kept per user."""

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
        self._documentos: list[svc.DocumentoImpressao] = []
        self._prioridades_guardadas = svc.prioridades_default()
        self._documento_pre_visto: str | None = None

        self.setWindowTitle("Imprimir Documentos")
        self.setModal(True)
        self.resize(1560, 900)

        processo_label = QLabel(f"Processo: {codigo_processo or '-'}")
        processo_label.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold;"
        )
        self.pasta_label = QLabel(pasta_obra or "(pasta da obra não definida)")
        self.pasta_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.pasta_label.setWordWrap(True)
        self.pasta_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        cabecalho_esquerda = QVBoxLayout()
        cabecalho_esquerda.addWidget(processo_label)
        cabecalho_esquerda.addWidget(self.pasta_label)
        cabecalho_esquerda.addStretch()

        pre_visualizacao = QGroupBox("Pré-visualização")
        pre_visualizacao.setStyleSheet(
            f"QGroupBox {{ color: {tema.CASTANHO_ESCURO}; font-weight: bold; }}"
        )
        pre_visualizacao.setMinimumWidth(500)
        # Sem limite de altura a pré-visualização come a lista de documentos.
        pre_visualizacao.setMaximumHeight(340)
        self.imagem_label = QLabel("Selecione um documento na lista.")
        self.imagem_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imagem_label.setMinimumSize(480, 260)
        self.imagem_label.setStyleSheet(
            f"QLabel {{ border: 1px solid {tema.CINZA_CASTANHO}; "
            f"background-color: {tema.BEGE_AREIA}; color: {tema.CASTANHO_ESCURO}; }}"
        )
        self.nome_pre_visto_label = QLabel("")
        self.nome_pre_visto_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")
        pre_layout = QVBoxLayout(pre_visualizacao)
        pre_layout.addWidget(self.imagem_label, stretch=1)
        pre_layout.addWidget(self.nome_pre_visto_label)

        topo = QHBoxLayout()
        topo.addLayout(cabecalho_esquerda, stretch=1)
        topo.addWidget(pre_visualizacao)

        self.tabela = QTableWidget(0, len(_CABECALHOS))
        self.tabela.setHorizontalHeaderLabels(_CABECALHOS)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        for coluna, largura in _LARGURAS.items():
            self.tabela.setColumnWidth(coluna, largura)
        # O nome do ficheiro é o que cresce; as outras colunas ficam justas.
        cabecalho.setStretchLastSection(False)
        cabecalho.setSectionResizeMode(_COL_FICHEIRO, QHeaderView.ResizeMode.Stretch)
        self.tabela.itemSelectionChanged.connect(self._mostrar_pre_visualizacao)
        self.tabela.setToolTip(
            "Documentos encontrados na pasta da obra. Marque o que quer "
            "imprimir e use Subir/Descer para mudar a ordem de impressão."
        )

        self.recarregar_button = QPushButton("Recarregar")
        self.recarregar_button.setToolTip("Voltar a ler a pasta da obra")
        self.recarregar_button.clicked.connect(self._carregar)

        self.subir_button = QPushButton("▲ Subir")
        self.subir_button.setToolTip("Imprimir este documento mais cedo")
        self.subir_button.clicked.connect(lambda: self._mover(-1))

        self.descer_button = QPushButton("▼ Descer")
        self.descer_button.setToolTip("Imprimir este documento mais tarde")
        self.descer_button.clicked.connect(lambda: self._mover(1))

        self.repor_button = QPushButton("Repor ordem")
        self.repor_button.setToolTip(
            "Voltar à ordem de origem (a que vem de fábrica), sem gravar"
        )
        self.repor_button.clicked.connect(self._repor_ordem)

        self.tudo_button = QPushButton("Selecionar tudo")
        self.tudo_button.setToolTip("Marcar todos os documentos")
        self.tudo_button.clicked.connect(lambda: self._marcar_todos(True))

        self.limpar_button = QPushButton("Limpar seleção")
        self.limpar_button.setToolTip("Desmarcar todos os documentos")
        self.limpar_button.clicked.connect(lambda: self._marcar_todos(False))

        self.imprimir_button = QPushButton("Imprimir Selecionados")
        self.imprimir_button.setToolTip(
            "Enviar para a impressora os documentos marcados, pela ordem da lista"
        )
        self.imprimir_button.clicked.connect(self._imprimir)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.setToolTip("Fechar sem imprimir")
        self.fechar_button.clicked.connect(self.reject)

        self.status_label = QLabel("")
        self.status_label.setObjectName("impressaoStatus")

        acoes = QHBoxLayout()
        acoes.addWidget(self.recarregar_button)
        acoes.addWidget(self.subir_button)
        acoes.addWidget(self.descer_button)
        acoes.addWidget(self.repor_button)
        acoes.addWidget(self.tudo_button)
        acoes.addWidget(self.limpar_button)
        acoes.addStretch()
        acoes.addWidget(self.imprimir_button)
        acoes.addWidget(self.fechar_button)

        layout = QVBoxLayout(self)
        layout.addLayout(topo)
        layout.addLayout(acoes)
        layout.addWidget(self.tabela, stretch=1)
        layout.addWidget(self.status_label)

        self._carregar()

    # ---- carregar / mostrar ------------------------------------------------
    def _carregar(self) -> None:
        try:
            with SessionLocal() as session:
                self._prioridades_guardadas = svc.obter_prioridades_utilizador(
                    session, self._user_id
                )
        except SQLAlchemyError:
            self._prioridades_guardadas = svc.prioridades_default()

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._documentos = svc.listar_documentos(
                self._pasta_obra,
                nome_plano_cut_rite=self._nome_plano_cut_rite,
                nome_enc_imos=self._nome_enc_imos,
                prioridades=self._prioridades_guardadas,
            )
        finally:
            QApplication.restoreOverrideCursor()

        self._mostrar_documentos()
        self.status_label.setText(
            f"{len(self._documentos)} documento(s) encontrados na pasta da obra."
            if self._documentos
            else "Sem PDFs na pasta da obra."
        )
        if self._documentos:
            self.tabela.selectRow(0)

    def _mostrar_documentos(self) -> None:
        self.tabela.setRowCount(len(self._documentos))
        for linha, documento in enumerate(self._documentos):
            selecao = QTableWidgetItem()
            selecao.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
            )
            selecao.setCheckState(
                Qt.CheckState.Checked
                if documento.selecionado
                else Qt.CheckState.Unchecked
            )
            selecao.setToolTip("Marcar para imprimir")
            self.tabela.setItem(linha, _COL_SEL, selecao)

            prioridade = QTableWidgetItem(str(documento.prioridade))
            prioridade.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            prioridade.setToolTip(
                "Ordem de impressão desta categoria — mude com Subir/Descer"
            )
            self.tabela.setItem(linha, _COL_PRIORIDADE, prioridade)

            ficheiro = QTableWidgetItem(documento.nome)
            ficheiro.setToolTip(str(documento.caminho))
            self.tabela.setItem(linha, _COL_FICHEIRO, ficheiro)

            self.tabela.setItem(linha, _COL_CATEGORIA, QTableWidgetItem(documento.categoria))
            self.tabela.setItem(linha, _COL_ORIGEM, QTableWidgetItem(documento.origem))

            quantidade = QSpinBox()
            quantidade.setRange(1, 99)
            quantidade.setValue(int(documento.quantidade or 1))
            quantidade.setToolTip("Quantas cópias imprimir deste documento")
            quantidade.valueChanged.connect(
                lambda valor, doc=documento: setattr(doc, "quantidade", int(valor))
            )
            self.tabela.setCellWidget(linha, _COL_QT, quantidade)

            papel = QComboBox()
            papel.addItems(list(svc.PAPEIS))
            papel.setCurrentText(documento.papel)
            papel.setToolTip(self._dica_formato(documento))
            self.tabela.setCellWidget(linha, _COL_PAPEL, papel)

            orientacao = QComboBox()
            orientacao.addItems(list(svc.ORIENTACOES))
            orientacao.setCurrentText(documento.orientacao)
            orientacao.setToolTip(self._dica_formato(documento))
            self.tabela.setCellWidget(linha, _COL_ORIENTACAO, orientacao)

            papel.currentTextChanged.connect(
                lambda valor, doc=documento, combo=orientacao: self._mudar_papel(
                    doc, combo, valor
                )
            )
            orientacao.currentTextChanged.connect(
                lambda valor, doc=documento: setattr(doc, "orientacao", valor)
            )
            # Com "Do PDF" cada página sai como está gravada: forçar a
            # orientação por cima disso não faria sentido.
            orientacao.setEnabled(not documento.segue_o_pdf)

            duplex = QTableWidgetItem()
            duplex.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            duplex.setCheckState(
                Qt.CheckState.Checked if documento.duplex else Qt.CheckState.Unchecked
            )
            duplex.setToolTip("Imprimir frente e verso")
            self.tabela.setItem(linha, _COL_DUPLEX, duplex)

            cor = QComboBox()
            cor.addItems(["cor", "pb"])
            cor.setCurrentText(documento.cor)
            cor.setToolTip("Cor ou preto e branco")
            cor.currentTextChanged.connect(
                lambda valor, doc=documento: setattr(doc, "cor", valor)
            )
            self.tabela.setCellWidget(linha, _COL_COR, cor)

    def _dica_formato(self, documento: svc.DocumentoImpressao) -> str:
        """Explain what the PDF holds and what "Do PDF" does."""
        linhas = [
            '"Do PDF" imprime cada página no papel e na orientação com que '
            "foi gravada; A4/A3 força o formato e ajusta o desenho à folha."
        ]
        if documento.resumo_paginas:
            linhas.append(f"Este PDF tem: {documento.resumo_paginas}.")
        return "\n".join(linhas)

    def _mudar_papel(
        self, documento: svc.DocumentoImpressao, combo_orientacao, valor: str
    ) -> None:
        """Keep paper and orientation coherent when the user changes paper."""
        documento.papel = valor
        segue_o_pdf = valor == svc.DO_PDF
        combo_orientacao.setEnabled(not segue_o_pdf)
        if segue_o_pdf:
            combo_orientacao.setCurrentText(svc.DO_PDF)
        elif combo_orientacao.currentText() == svc.DO_PDF:
            # Ao forçar o papel, arranca-se da orientação que o PDF já tem.
            combo_orientacao.setCurrentText(
                documento.orientacao_ficheiro or svc.ORIENTACAO_HORIZONTAL
            )

    def _linha_selecionada(self) -> int:
        linhas = self.tabela.selectionModel().selectedRows()
        return linhas[0].row() if linhas else -1

    def _ler_marcados(self) -> None:
        """Copy the checkboxes back into the documents."""
        for linha, documento in enumerate(self._documentos):
            item_sel = self.tabela.item(linha, _COL_SEL)
            if item_sel is not None:
                documento.selecionado = item_sel.checkState() == Qt.CheckState.Checked
            item_duplex = self.tabela.item(linha, _COL_DUPLEX)
            if item_duplex is not None:
                documento.duplex = item_duplex.checkState() == Qt.CheckState.Checked

    def _marcar_todos(self, marcar: bool) -> None:
        estado = Qt.CheckState.Checked if marcar else Qt.CheckState.Unchecked
        for linha in range(self.tabela.rowCount()):
            item = self.tabela.item(linha, _COL_SEL)
            if item is not None:
                item.setCheckState(estado)
        self._ler_marcados()

    # ---- ordem de impressão ------------------------------------------------
    def _mover(self, passo: int) -> None:
        linha = self._linha_selecionada()
        destino = linha + passo
        if linha < 0 or destino < 0 or destino >= len(self._documentos):
            return

        self._ler_marcados()
        documentos = self._documentos
        documentos[linha], documentos[destino] = documentos[destino], documentos[linha]
        # A prioridade passa a ser a posição na lista: é o que se lê no ecrã e
        # o que fica guardado como modelo do utilizador.
        for posicao, documento in enumerate(documentos):
            documento.prioridade = posicao
        self._mostrar_documentos()
        self.tabela.selectRow(destino)
        self.status_label.setText(
            "Ordem alterada — ao imprimir pode gravá-la para as próximas obras."
        )

    def _repor_ordem(self) -> None:
        self._ler_marcados()
        prioridades = svc.prioridades_default()
        for documento in self._documentos:
            documento.prioridade = prioridades.get(documento.categoria, 8)
        self._documentos = svc.ordenar_documentos(self._documentos)
        self._mostrar_documentos()
        self.status_label.setText("Ordem de origem reposta (ainda não gravada).")

    def _perguntar_gravar_ordem(self) -> None:
        """Ask whether the new order is only for this obra or the new model."""
        if not svc.ordem_foi_alterada(self._documentos, self._prioridades_guardadas):
            return

        pergunta = QMessageBox(self)
        pergunta.setWindowTitle("Ordem de impressão")
        pergunta.setIcon(QMessageBox.Icon.Question)
        pergunta.setText("Mudou a ordem de impressão dos documentos.")
        pergunta.setInformativeText(
            "Quer gravar esta ordem para as próximas obras (fica só para si), "
            "ou usá-la apenas nesta impressão?"
        )
        gravar = pergunta.addButton(
            "Gravar para as próximas obras", QMessageBox.ButtonRole.AcceptRole
        )
        pergunta.addButton("Só nesta obra", QMessageBox.ButtonRole.RejectRole)
        pergunta.exec()

        if pergunta.clickedButton() is not gravar:
            self.status_label.setText("Ordem usada só nesta obra.")
            return

        prioridades = svc.prioridades_dos_documentos(self._documentos)
        try:
            with SessionLocal() as session:
                svc.guardar_prioridades_utilizador(session, self._user_id, prioridades)
        except SQLAlchemyError as erro:
            QMessageBox.warning(
                self,
                "Ordem de impressão",
                f"Não foi possível gravar a ordem.\n\n{erro}",
            )
            return
        self._prioridades_guardadas = prioridades
        self.status_label.setText("Ordem gravada para as próximas impressões.")

    # ---- imprimir ----------------------------------------------------------
    def _imprimir(self) -> None:
        self._ler_marcados()
        escolhidos = [doc for doc in self._documentos if doc.selecionado]
        if not escolhidos:
            QMessageBox.information(
                self, "Imprimir Documentos", "Nenhum documento selecionado."
            )
            return

        self._perguntar_gravar_ordem()

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with SessionLocal() as session:
                avisos = svc.imprimir_documentos(session, escolhidos)
        except (SQLAlchemyError, OSError) as erro:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Imprimir Documentos",
                f"Não foi possível imprimir os documentos.\n\n{erro}",
            )
            return
        QApplication.restoreOverrideCursor()

        mensagem = f"Impressão enviada: {len(escolhidos)} documento(s)."
        if avisos:
            mensagem += "\n\n" + "\n".join(avisos)
        QMessageBox.information(self, "Imprimir Documentos", mensagem)
        self.status_label.setText(mensagem.splitlines()[0])

    # ---- pré-visualização --------------------------------------------------
    def _mostrar_pre_visualizacao(self) -> None:
        linha = self._linha_selecionada()
        if linha < 0 or linha >= len(self._documentos):
            return

        documento = self._documentos[linha]
        caminho = Path(documento.caminho)
        self.nome_pre_visto_label.setText(documento.nome)
        if str(caminho) == self._documento_pre_visto:
            return
        self._documento_pre_visto = str(caminho)

        imagem = self._primeira_pagina(caminho)
        if imagem is None:
            self.imagem_label.setPixmap(QPixmap())
            self.imagem_label.setText("Sem pré-visualização para este documento.")
            return
        self.imagem_label.setPixmap(imagem)
        self.imagem_label.setText("")

    def _primeira_pagina(self, caminho: Path) -> QPixmap | None:
        try:
            from PySide6.QtPdf import QPdfDocument
        except ImportError:  # pragma: no cover - depende do PySide6 instalado
            return None

        if not caminho.is_file():
            return None

        documento = QPdfDocument(self)
        documento.load(str(caminho))
        if documento.pageCount() <= 0:
            return None

        tamanho = documento.pagePointSize(0)
        if tamanho.width() <= 0 or tamanho.height() <= 0:
            return None

        alvo = self.imagem_label.size()
        escala = min(
            max(alvo.width(), 200) / tamanho.width(),
            max(alvo.height(), 200) / tamanho.height(),
        )
        imagem = documento.render(
            0,
            QSize(int(tamanho.width() * escala), int(tamanho.height() * escala)),
        )
        if imagem.isNull():
            return None
        return QPixmap.fromImage(imagem)
