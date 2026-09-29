"""Gerar no Martelo as listas de ferragens do iMos, sem abrir o iMos.

Mostra, para a obra selecionada, a hora da última gravação do desenho no iMos
e, para cada lista, se a que está na pasta da obra saiu dessa gravação ou de
uma anterior. O utilizador escolhe as listas e o Martelo gera-as para a pasta
da obra (as anteriores ficam em ``Listas_IMOS_anteriores``).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.db.session import SessionLocal
from app.services.imos_listas_service import (
    LISTAS_IMOS,
    PASTA_ANTERIORES,
    SITUACAO_ATUALIZADA,
    SITUACAO_DESATUALIZADA,
    SITUACAO_EM_FALTA,
    ConfigListasImos,
    EncomendaImos,
    EstadoLista,
    ResultadoGeracao,
    carregar_config,
    estado_listas,
    gerar_listas,
    procurar_encomenda_imos,
)
from app.ui import tema
from app.ui.icones import decorar_botoes
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras

FORMATO_DATA = "%d-%m-%Y %H:%M"


def _data(valor) -> str:
    return valor.strftime(FORMATO_DATA) if valor else "—"


def texto_situacao(estado: EstadoLista, encomenda: EncomendaImos | None) -> tuple[str, str]:
    """(texto, cor) da coluna Situação."""
    if estado.situacao == SITUACAO_EM_FALTA:
        texto = "Ainda não existe na pasta da obra"
        if estado.pendente_imos is not None:
            texto += " (há uma do iMos por importar em C:\\IMOS_Output_Batches)"
        return texto, tema.CINZA_ESCURO
    if estado.situacao == SITUACAO_ATUALIZADA:
        return "Atualizada — saiu da última gravação do desenho", tema.TEXTO_OK
    if estado.situacao == SITUACAO_DESATUALIZADA:
        gravado = _data(encomenda.ultima_gravacao) if encomenda else "—"
        return f"Desatualizada — o desenho foi gravado depois ({gravado})", tema.TEXTO_AVISO
    return "Sem data de gravação no iMos para comparar", tema.CINZA_ESCURO


class _TrabalhoGeracao(QThread):
    """Gera as listas fora da thread do ecrã (o Resumo demora uns segundos)."""

    progresso = Signal(int, int, str)
    terminado = Signal(object)
    falhou = Signal(str)

    def __init__(self, config, *, pasta_obra, nome_enc, dir_id, listas, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._pasta_obra = pasta_obra
        self._nome_enc = nome_enc
        self._dir_id = dir_id
        self._listas = listas

    def run(self) -> None:  # noqa: D102 - QThread
        try:
            resultado = gerar_listas(
                self._config,
                pasta_obra=self._pasta_obra,
                nome_enc=self._nome_enc,
                dir_id=self._dir_id,
                listas=self._listas,
                ao_progresso=self.progresso.emit,
            )
        except Exception as erro:  # noqa: BLE001 - tudo tem de chegar ao ecrã
            self.falhou.emit(str(erro) or erro.__class__.__name__)
        else:
            self.terminado.emit(resultado)


class GerarListasImosDialog(QDialog):
    """Escolher e gerar as listas do iMos para a pasta da obra."""

    COLUNAS = ["Lista", "O que traz", "Na pasta da obra", "Situação"]

    def __init__(
        self,
        *,
        codigo_processo: str,
        nome_enc: str,
        pasta_obra: str | Path,
        dir_id: int | None = None,
        depois_importa: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._codigo = str(codigo_processo or "")
        self._nome_enc = str(nome_enc or "").strip()
        self._pasta_obra = Path(pasta_obra)
        self._dir_id = dir_id
        self._config: ConfigListasImos | None = None
        self._encomenda: EncomendaImos | None = None
        self._estados: list[EstadoLista] = []
        self._trabalho: _TrabalhoGeracao | None = None
        self.resultado: ResultadoGeracao | None = None

        self.setWindowTitle("Gerar listas iMOS (ferragens)")
        self.setModal(True)
        self.setMinimumSize(1000, 560)

        texto = (
            "O Martelo gera estas listas com os mesmos relatórios (.rdl) e o mesmo "
            "motor que o iMos, a partir da <b>última gravação do desenho</b>. "
            "Grave o desenho no iMos antes de gerar. As listas vão direto para a "
            "pasta da obra; as que lá estavam passam para a subpasta "
            f"<i>{PASTA_ANTERIORES}</i>, com a data em que tinham sido geradas."
        )
        if depois_importa:
            texto += (
                "<br><br>Ao fechar esta janela, as listas da pasta da obra são "
                "importadas para a Lista Material."
            )
        self.cabecalho = QLabel(texto)
        self.cabecalho.setWordWrap(True)

        # --- a obra --------------------------------------------------------
        self.obra_label = QLabel(self._codigo or "—")
        self.encomenda_label = QLabel(self._nome_enc or "—")
        self.encomenda_label.setToolTip(
            "Encomenda do iMos de onde saem as listas (Nome Enc IMOS IX da obra) "
            "e o seu número na base do iMos."
        )
        self.gravacao_label = QLabel("A ler…")
        fonte = QFont(self.gravacao_label.font())
        fonte.setBold(True)
        self.gravacao_label.setFont(fonte)
        self.gravacao_label.setToolTip(
            "Hora a que o desenho foi gravado pela última vez no iMos. As listas "
            "saem sempre desta gravação: se alterou o desenho, grave-o no iMos e "
            "carregue em Atualizar."
        )
        self.pasta_label = QLabel(str(self._pasta_obra))
        self.pasta_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.pasta_label.setToolTip("Pasta da obra, onde fica a Lista Material e onde as listas são gravadas.")

        grupo_obra = QGroupBox("Obra")
        formulario = QFormLayout(grupo_obra)
        formulario.addRow("Obra:", self.obra_label)
        formulario.addRow("Encomenda iMos:", self.encomenda_label)
        formulario.addRow("Última gravação do desenho:", self.gravacao_label)
        formulario.addRow("Pasta da obra:", self.pasta_label)

        # --- as listas -----------------------------------------------------
        self.tabela = QTableWidget(len(LISTAS_IMOS), len(self.COLUNAS))
        self.tabela.setHorizontalHeaderLabels(self.COLUNAS)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tabela.setWordWrap(True)
        self.tabela.setToolTip(
            "Marque as listas a gerar. A coluna Situação diz se a lista que está na "
            "pasta da obra saiu da última gravação do desenho no iMos."
        )
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # A Situação ocupa o resto da largura (é a coluna que mais se lê).
        cabecalho.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for coluna, largura in enumerate((200, 380, 190)):
            self.tabela.setColumnWidth(coluna, largura)
        # Sem forçar: as três primeiras ficam ajustáveis e guardadas, a
        # Situação continua a esticar.
        ligar_persistencia_larguras(
            self.tabela, "dialog_gerar_listas_imos", forcar_interativas=False
        )
        for linha, lista in enumerate(LISTAS_IMOS):
            item = QTableWidgetItem(lista.chave)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setToolTip(f"{lista.titulo} — relatório {lista.ficheiro_rdl}")
            self.tabela.setItem(linha, 0, item)
            descricao = QTableWidgetItem(lista.descricao)
            descricao.setToolTip(lista.descricao)
            self.tabela.setItem(linha, 1, descricao)
            self.tabela.setItem(linha, 2, QTableWidgetItem("—"))
            self.tabela.setItem(linha, 3, QTableWidgetItem("—"))
        self.tabela.resizeRowsToContents()

        # --- botões e supervisor -------------------------------------------
        self.todas_button = QPushButton("Marcar todas")
        self.todas_button.setToolTip("Marcar as quatro listas; carregue outra vez para desmarcar todas.")
        self.todas_button.clicked.connect(self._marcar_todas)

        self.atualizar_button = QPushButton("Atualizar")
        self.atualizar_button.setToolTip(
            "Voltar a ler a hora da última gravação no iMos e a situação das "
            "listas na pasta da obra (use depois de gravar o desenho)."
        )
        self.atualizar_button.clicked.connect(self._atualizar)

        self.gerar_button = QPushButton("Gerar listas marcadas")
        self.gerar_button.setToolTip(
            "Gerar as listas marcadas a partir da última gravação do desenho e "
            "gravá-las na pasta da obra. Nada é apagado: as anteriores ficam em "
            f"{PASTA_ANTERIORES}."
        )
        self.gerar_button.clicked.connect(self._gerar)
        self.gerar_button.setEnabled(False)

        self.pasta_button = QPushButton("Abrir pasta da obra")
        self.pasta_button.setToolTip("Abrir no Explorador a pasta da obra.")
        self.pasta_button.clicked.connect(self._abrir_pasta)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.setToolTip("Fechar esta janela.")
        self.fechar_button.clicked.connect(self.accept)

        barra = QHBoxLayout()
        for botao in (self.todas_button, self.atualizar_button, self.gerar_button, self.pasta_button):
            barra.addWidget(botao)
        barra.addStretch(1)
        barra.addWidget(self.fechar_button)
        decorar_botoes(
            self.todas_button, self.atualizar_button, self.gerar_button,
            self.pasta_button, self.fechar_button,
        )

        self.progresso = QProgressBar()
        self.progresso.setVisible(False)
        self.progresso.setToolTip("Progresso da geração das listas.")

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.cabecalho)
        layout.addWidget(grupo_obra)
        layout.addWidget(self.tabela, 1)
        layout.addLayout(barra)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progresso)

        QTimer.singleShot(0, self._atualizar)

    # ------------------------------------------------------------------
    def _listas_marcadas(self):
        return [
            lista
            for linha, lista in enumerate(LISTAS_IMOS)
            if self.tabela.item(linha, 0).checkState() == Qt.CheckState.Checked
        ]

    def _marcar_todas(self) -> None:
        todas = len(self._listas_marcadas()) == len(LISTAS_IMOS)
        estado = Qt.CheckState.Unchecked if todas else Qt.CheckState.Checked
        for linha in range(len(LISTAS_IMOS)):
            self.tabela.item(linha, 0).setCheckState(estado)

    def _supervisor(self, texto: str, cor: str = tema.TEXTO_NORMAL) -> None:
        self.status_label.setStyleSheet(f"color: {cor};")
        self.status_label.setText(texto)

    def _atualizar(self) -> None:
        """Lê a ligação, a última gravação no iMos e o estado das listas."""
        self._supervisor("A ler a última gravação do desenho no iMos…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            try:
                if self._config is None:
                    with SessionLocal() as session:
                        self._config = carregar_config(session)
                self._encomenda = procurar_encomenda_imos(
                    self._config.ligacao, self._nome_enc, dir_id=self._dir_id
                )
            except Exception as erro:  # noqa: BLE001 - ligação/SQL: dizer porquê
                self._encomenda = None
                self.gravacao_label.setText("—")
                self._preencher_estados()
                self.gerar_button.setEnabled(False)
                self._supervisor(f"Não foi possível ler a encomenda no iMos: {erro}", tema.TEXTO_ERRO)
                return
        finally:
            QApplication.restoreOverrideCursor()

        encomenda = self._encomenda
        self.encomenda_label.setText(f"{encomenda.nome}  (ID {encomenda.proadmin_id} no iMos)")
        self.gravacao_label.setText(
            encomenda.ultima_gravacao.strftime("%d-%m-%Y %H:%M:%S")
            if encomenda.ultima_gravacao
            else "sem data no iMos"
        )
        self._preencher_estados()
        self.gerar_button.setEnabled(True)
        self._supervisor_estado()

    def _preencher_estados(self) -> None:
        try:
            self._estados = estado_listas(self._pasta_obra, self._nome_enc, self._encomenda)
        except OSError as erro:
            self._estados = []
            self._supervisor(f"Não consegui ler a pasta da obra: {erro}", tema.TEXTO_ERRO)
            return
        for linha, estado in enumerate(self._estados):
            if estado.caminho is None:
                na_pasta = "—"
            else:
                na_pasta = f"{_data(estado.gerada_em)} ({estado.origem})"
            item_pasta = QTableWidgetItem(na_pasta)
            item_pasta.setToolTip(
                str(estado.caminho) if estado.caminho else "Esta lista ainda não está na pasta da obra."
            )
            self.tabela.setItem(linha, 2, item_pasta)
            texto, cor = texto_situacao(estado, self._encomenda)
            item_situacao = QTableWidgetItem(texto)
            item_situacao.setForeground(QColor(cor))
            item_situacao.setToolTip(texto)
            self.tabela.setItem(linha, 3, item_situacao)
        self.tabela.resizeRowsToContents()

    def _supervisor_estado(self) -> None:
        desatualizadas = [e.lista.chave for e in self._estados if e.situacao == SITUACAO_DESATUALIZADA]
        em_falta = [e.lista.chave for e in self._estados if e.situacao == SITUACAO_EM_FALTA]
        aviso = self._encomenda.aviso if self._encomenda else ""
        if desatualizadas:
            texto = (
                "O desenho foi gravado no iMos depois de gerar: "
                + ", ".join(desatualizadas)
                + ". Marque-as e carregue em «Gerar listas marcadas»."
            )
            cor = tema.TEXTO_AVISO
        elif em_falta and len(em_falta) == len(self._estados):
            texto = "Ainda não há listas nesta obra. Marque as que precisa e carregue em «Gerar listas marcadas»."
            cor = tema.TEXTO_NORMAL
        elif em_falta:
            texto = "Faltam na pasta da obra: " + ", ".join(em_falta) + ". As restantes estão atualizadas."
            cor = tema.TEXTO_NORMAL
        else:
            texto = "Todas as listas da pasta da obra saíram da última gravação do desenho."
            cor = tema.TEXTO_OK
        if aviso:
            texto = f"{aviso} {texto}"
            cor = tema.TEXTO_AVISO
        self._supervisor(texto, cor)

    # ------------------------------------------------------------------
    def _gerar(self) -> None:
        listas = self._listas_marcadas()
        if not listas:
            self._supervisor("Marque pelo menos uma lista para gerar.", tema.TEXTO_AVISO)
            return
        if self._config is None:
            return
        self._a_trabalhar(True)
        self.progresso.setRange(0, len(listas))
        self.progresso.setValue(0)
        self._trabalho = _TrabalhoGeracao(
            self._config,
            pasta_obra=self._pasta_obra,
            nome_enc=self._nome_enc,
            dir_id=self._dir_id,
            listas=listas,
            parent=self,
        )
        self._trabalho.progresso.connect(self._ao_progresso)
        self._trabalho.terminado.connect(self._ao_terminar)
        self._trabalho.falhou.connect(self._ao_falhar)
        self._trabalho.start()

    def _a_trabalhar(self, ativo: bool) -> None:
        for botao in (self.todas_button, self.atualizar_button, self.gerar_button, self.fechar_button):
            botao.setEnabled(not ativo)
        self.tabela.setEnabled(not ativo)
        self.progresso.setVisible(ativo)

    def _ao_progresso(self, feitas: int, total: int, texto: str) -> None:
        self.progresso.setMaximum(max(total, 1))
        self.progresso.setValue(feitas)
        self._supervisor(texto)

    def _ao_falhar(self, mensagem: str) -> None:
        self._a_trabalhar(False)
        self._supervisor(f"As listas não foram geradas: {mensagem}", tema.TEXTO_ERRO)
        QMessageBox.warning(self, "Gerar listas iMOS", f"As listas não foram geradas.\n\n{mensagem}")

    def _ao_terminar(self, resultado: ResultadoGeracao) -> None:
        self._a_trabalhar(False)
        self.resultado = resultado
        self._encomenda = resultado.encomenda
        if resultado.encomenda.ultima_gravacao:
            self.gravacao_label.setText(resultado.encomenda.ultima_gravacao.strftime("%d-%m-%Y %H:%M:%S"))
        self._preencher_estados()

        geradas = resultado.geradas
        falhadas = resultado.falhadas
        linhas = [
            f"• {r.lista.chave}: gerada em {r.segundos:.0f} s"
            + (" (a anterior ficou guardada)" if r.anterior else "")
            for r in geradas
        ]
        linhas += [f"• {r.lista.chave}: NÃO gerada — {r.erro}" for r in falhadas]
        avisos = [f"• {r.lista.chave}: {a}" for r in geradas for a in r.avisos]
        if falhadas:
            self._supervisor(
                f"{len(geradas)} lista(s) gerada(s), {len(falhadas)} com erro — veja o resumo.",
                tema.TEXTO_ERRO,
            )
        else:
            self._supervisor(
                f"{len(geradas)} lista(s) gerada(s) a partir da gravação de "
                f"{_data(resultado.encomenda.ultima_gravacao)}. Já pode importá-las "
                "para a Lista Material.",
                tema.TEXTO_OK,
            )
        texto = "\n".join(linhas)
        if avisos:
            texto += "\n\nAvisos do relatório:\n" + "\n".join(avisos)
        caixa = QMessageBox.warning if falhadas else QMessageBox.information
        caixa(self, "Gerar listas iMOS", texto)

    def _abrir_pasta(self) -> None:
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._pasta_obra))):
            self._supervisor(f"Não foi possível abrir a pasta:\n{self._pasta_obra}", tema.TEXTO_ERRO)

    # Enquanto gera, a janela não fecha: a thread ainda está a escrever na obra.
    def _a_gerar(self) -> bool:
        return self._trabalho is not None and self._trabalho.isRunning()

    def reject(self) -> None:  # noqa: D102 - Esc / fechar
        if self._a_gerar():
            self._supervisor("Aguarde: as listas ainda estão a ser geradas.", tema.TEXTO_AVISO)
            return
        super().reject()

    def closeEvent(self, event) -> None:  # noqa: D102
        if self._a_gerar():
            self._supervisor("Aguarde: as listas ainda estão a ser geradas.", tema.TEXTO_AVISO)
            event.ignore()
            return
        super().closeEvent(event)

    @property
    def listas_geradas(self) -> int:
        return len(self.resultado.geradas) if self.resultado else 0
