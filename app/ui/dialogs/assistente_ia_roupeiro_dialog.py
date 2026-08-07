"""Fluxo humano-no-circuito do piloto IA para Roupeiro Abrir."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QObject, QPoint, QRect, QSize, Qt, QThread, Signal, Slot
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHeaderView, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.db.session import SessionLocal
from app.domain.roupeiro_ia import AnaliseRoupeiro, PedidoAnaliseRoupeiro, ZonaDocumento
from app.services.def_modulo_service import DefModuloService
from app.services.ia_orcamento_service import IaOrcamentoService
from app.services.ia_perfil_service import listar_entradas
from app.services.roupeiro_combinador_service import RoupeiroCombinadorService
from app.services.roupeiro_vision_service import LocalVisionProvider, OpenAIVisionProvider
from app.services.system_setting_service import SystemSettingService
from app.services.pdf_imagem_service import documento_pdf
from app.services.orcamento_export_service import OrcamentoExportService
from app.models import OrcamentoItem


class _CropLabel(QLabel):
    """Pré-visualização simples com seleção retangular por arrasto."""

    def __init__(self) -> None:
        super().__init__("Escolha um PDF e uma página.")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(760, 420)
        self.setStyleSheet("border: 1px solid #9a8a7a; background: white;")
        self._origem: QPoint | None = None
        # A seleção vive nas coordenadas do pixmap, não nas do QLabel. Assim,
        # recentrar a imagem após uma alteração do layout não desloca o recorte.
        self._selecao = QRect()

    def _rect_pixmap_no_widget(self) -> QRect:
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            return QRect()
        return QRect(
            max(0, (self.width() - pixmap.width()) // 2),
            max(0, (self.height() - pixmap.height()) // 2),
            pixmap.width(),
            pixmap.height(),
        )

    def _ponto_no_pixmap(self, ponto: QPoint) -> QPoint | None:
        rect = self._rect_pixmap_no_widget()
        if rect.isNull() or not rect.contains(ponto):
            return None
        return ponto - rect.topLeft()

    def _ponto_no_pixmap_limitado(self, ponto: QPoint) -> QPoint:
        rect = self._rect_pixmap_no_widget()
        x = min(max(ponto.x(), rect.left()), rect.right())
        y = min(max(ponto.y(), rect.top()), rect.bottom())
        return QPoint(x, y) - rect.topLeft()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap() is not None:
            ponto = self._ponto_no_pixmap(event.position().toPoint())
            if ponto is not None:
                self._origem = ponto
                self._selecao = QRect(ponto, QSize())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._origem is not None:
            pixmap = self.pixmap()
            if pixmap is None:
                return
            ponto = self._ponto_no_pixmap_limitado(event.position().toPoint())
            self._selecao = QRect(self._origem, ponto).normalized().intersected(pixmap.rect())
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._origem is not None:
            pixmap = self.pixmap()
            if pixmap is None:
                self._origem = None
                return
            ponto = self._ponto_no_pixmap_limitado(event.position().toPoint())
            self._selecao = QRect(self._origem, ponto).normalized().intersected(pixmap.rect())
            self._origem = None
            self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._selecao.isNull():
            from PySide6.QtGui import QColor, QPainter, QPen
            painter = QPainter(self)
            painter.setPen(QPen(QColor("#d32f2f"), 2))
            painter.drawRect(self._selecao.translated(self._rect_pixmap_no_widget().topLeft()))

    def recorte_png(self) -> tuple[bytes | None, ZonaDocumento | None]:
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull() or self._selecao.width() < 10 or self._selecao.height() < 10:
            return None, None
        rect = self._selecao.intersected(pixmap.rect())
        if rect.isNull():
            return None, None
        recorte = pixmap.copy(rect)
        dados = QByteArray()
        buffer = QBuffer(dados)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        recorte.save(buffer, "PNG")
        buffer.close()
        zona = ZonaDocumento(
            pagina=0,
            x=rect.x() / pixmap.width(),
            y=rect.y() / pixmap.height(),
            largura=rect.width() / pixmap.width(),
            altura=rect.height() / pixmap.height(),
        )
        return bytes(dados), zona


class _VisionWorker(QObject):
    concluido = Signal(object)
    falhou = Signal(str)

    def __init__(self, provider, pedido) -> None:
        super().__init__()
        self.provider = provider
        self.pedido = pedido

    @Slot()
    def executar(self) -> None:
        try:
            self.concluido.emit(self.provider.analisar(self.pedido))
        except Exception as error:
            self.falhou.emit(str(error))


class AssistenteIaRoupeiroDialog(QDialog):
    def __init__(self, parent=None, *, item_id: int, user_id: int) -> None:
        super().__init__(parent)
        self.item_id = item_id
        self.user_id = user_id
        self.analise: AnaliseRoupeiro | None = None
        self.catalogo = []
        self.propostas = []
        self.proposta_ids: list[int] = []
        self.componentes_por_proposta: dict[int, list[int]] = {}
        self._respostas_analisadas = ""
        self._thread: QThread | None = None
        self._worker = None
        self.modulos_criados: list[int] = []
        self.setWindowTitle("Assistente IA — Roupeiro Abrir")
        self.setMinimumSize(1050, 820)

        self.pdf_input = QLineEdit()
        self.pdf_input.setReadOnly(True)
        self.pdf_input.setToolTip("PDF do pedido do cliente; a base de dados guarda apenas caminho e hash.")
        self.pdf_button = QPushButton("Escolher PDF…")
        self.pdf_button.setToolTip("Escolher o documento que contém o desenho do roupeiro.")
        self.pdf_button.clicked.connect(self._escolher_pdf)
        self.pagina_input = QSpinBox()
        self.pagina_input.setRange(1, 1)
        self.pagina_input.setToolTip("Página do PDF a mostrar e analisar como foco.")
        self.pagina_input.valueChanged.connect(self._render_pagina)
        linha_pdf = QHBoxLayout()
        linha_pdf.addWidget(self.pdf_input, 1)
        linha_pdf.addWidget(self.pdf_button)
        linha_pdf.addWidget(QLabel("Página"))
        linha_pdf.addWidget(self.pagina_input)

        self.preview = _CropLabel()
        self.instrucao = QLabel("Arraste um retângulo à volta de R1/R2/etc. O PDF completo é enviado apenas se confirmar uma análise em nuvem.")
        self.instrucao.setWordWrap(True)

        self.analisar_button = QPushButton("Analisar desenho")
        self.analisar_button.setToolTip("Enviar o documento ao fornecedor configurado e extrair medidas/características; não altera o orçamento.")
        self.analisar_button.clicked.connect(self._analisar)

        self.altura_input = self._spin_medida("Altura definida no item; altere-a na ficha do item.")
        self.largura_input = self._spin_medida("Largura definida no item; não é repartida pelos módulos.")
        self.profundidade_input = self._spin_medida("Profundidade definida no item; altere-a na ficha do item.")
        for spin in (self.altura_input, self.largura_input, self.profundidade_input):
            spin.setReadOnly(True)
        self.referencia_label = QLabel("—")
        self.perguntas_text = QPlainTextEdit("A análise ainda não foi executada.")
        self.perguntas_text.setReadOnly(True)
        self.perguntas_text.setMinimumHeight(105)
        self.perguntas_text.setMaximumHeight(145)
        self.perguntas_text.setToolTip(
            "Explicação, restrições e perguntas encontradas pela análise. Use a caixa seguinte para responder."
        )
        self.respostas_input = QPlainTextEdit()
        self.respostas_input.setPlaceholderText(
            "Ex.: portas de abrir; manter o varão; sem remate do lado esquerdo…"
        )
        self.respostas_input.setMinimumHeight(70)
        self.respostas_input.setMaximumHeight(95)
        self.respostas_input.setToolTip(
            "Responda às dúvidas ou corrija a leitura. Reanalise antes de gerar propostas."
        )
        self.respostas_input.textChanged.connect(self._respostas_alteradas)
        self.reanalisar_button = QPushButton("Reanalisar com respostas")
        self.reanalisar_button.setEnabled(False)
        self.reanalisar_button.setToolTip(
            "Enviar novamente o PDF e o mesmo recorte, incluindo as suas respostas como informação confirmada."
        )
        self.reanalisar_button.clicked.connect(self._analisar)
        respostas_widget = QWidget()
        respostas_layout = QVBoxLayout(respostas_widget)
        respostas_layout.setContentsMargins(0, 0, 0, 0)
        respostas_layout.addWidget(self.respostas_input)
        respostas_layout.addWidget(self.reanalisar_button, 0, Qt.AlignmentFlag.AlignRight)
        medidas_form = QFormLayout()
        medidas_form.addRow("Referência reconhecida", self.referencia_label)
        medidas_form.addRow("Altura do item (mm)", self.altura_input)
        medidas_form.addRow("Largura do item (mm)", self.largura_input)
        medidas_form.addRow("Profundidade do item (mm)", self.profundidade_input)
        medidas_form.addRow("Dúvidas / explicação", self.perguntas_text)
        medidas_form.addRow("As suas respostas", respostas_widget)

        self.propor_button = QPushButton("Gerar até 3 propostas")
        self.propor_button.setToolTip("Propor módulos pelas características lidas no PDF e pelo seu histórico.")
        self.propor_button.setEnabled(False)
        self.propor_button.clicked.connect(self._gerar_propostas)
        self.proposta_combo = QComboBox()
        self.proposta_combo.setToolTip("Escolha uma das três composições ordenadas.")
        self.proposta_combo.currentIndexChanged.connect(self._mostrar_proposta)
        self.modulos_table = QTableWidget(0, 3)
        self.modulos_table.setHorizontalHeaderLabels(["Ordem", "Módulo proposto", "Ações"])
        self.modulos_table.horizontalHeader().setStretchLastSection(False)
        self.modulos_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.modulos_table.verticalHeader().setVisible(False)
        self.modulos_table.verticalHeader().setDefaultSectionSize(36)
        self.modulos_table.setAlternatingRowColors(True)
        self.modulos_table.setColumnWidth(0, 85)
        self.modulos_table.setColumnWidth(2, 105)
        self.modulos_table.setMinimumHeight(210)
        self.modulos_table.setMaximumHeight(380)
        self.modulos_table.setToolTip(
            "Composição da proposta selecionada. Pode trocar ou remover módulos antes de confirmar."
        )

        self.rejeitar_button = QPushButton("Rejeitar proposta")
        self.rejeitar_button.setToolTip("Registar a rejeição só no seu histórico; não altera o orçamento.")
        self.rejeitar_button.clicked.connect(self._rejeitar)
        self.confirmar_button = QPushButton("Confirmar e inserir")
        self.confirmar_button.setToolTip("Inserir todos os módulos e recalcular numa única transação.")
        self.confirmar_button.clicked.connect(self._confirmar)
        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.setToolTip("Fechar sem alterar o orçamento.")
        self.cancelar_button.clicked.connect(self.reject)
        self.rejeitar_button.setEnabled(False)
        self.confirmar_button.setEnabled(False)

        self.status_label = QLabel("Escolha o PDF, a página e marque o roupeiro.")
        self.status_label.setWordWrap(True)
        acoes = QHBoxLayout()
        acoes.addWidget(self.analisar_button)
        acoes.addWidget(self.propor_button)
        acoes.addWidget(self.proposta_combo, 1)
        acoes.addWidget(self.rejeitar_button)
        acoes.addWidget(self.confirmar_button)
        acoes.addWidget(self.cancelar_button)

        detalhes = QWidget()
        detalhes_layout = QVBoxLayout(detalhes)
        detalhes_layout.setContentsMargins(0, 0, 0, 0)
        detalhes_layout.addLayout(medidas_form)
        detalhes_layout.addLayout(acoes)
        detalhes_layout.addWidget(self.modulos_table, 1)
        detalhes_layout.addWidget(self.status_label)

        separador = QSplitter(Qt.Orientation.Vertical)
        separador.setChildrenCollapsible(False)
        separador.addWidget(self.preview)
        separador.addWidget(detalhes)
        separador.setStretchFactor(0, 1)
        separador.setStretchFactor(1, 1)
        separador.setSizes([470, 570])

        layout = QVBoxLayout(self)
        layout.addLayout(linha_pdf)
        layout.addWidget(self.instrucao)
        layout.addWidget(separador, 1)
        self._ajustar_tamanho_inicial()
        self._carregar_contexto_item_e_pdf()

    def _ajustar_tamanho_inicial(self) -> None:
        """Usa quase toda a altura disponível sem ultrapassar o monitor."""
        screen = self.screen()
        if screen is None:
            self.resize(1200, 1000)
            return
        area = screen.availableGeometry()
        largura = min(1280, max(1100, int(area.width() * 0.78)))
        altura = min(area.height() - 30, max(900, int(area.height() * 0.94)))
        self.resize(largura, altura)

    @staticmethod
    def _spin_medida(tooltip: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0, 10000)
        spin.setDecimals(1)
        spin.setSpecialValueText("Por confirmar")
        spin.setToolTip(tooltip)
        return spin

    def _escolher_pdf(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(self, "Escolher pedido de orçamento", "", "PDF (*.pdf)")
        if not caminho:
            return
        self._usar_pdf(caminho)

    def _usar_pdf(self, caminho: str) -> None:
        """Carrega um PDF escolhido automaticamente ou manualmente."""
        self.pdf_input.setText(caminho)
        try:
            with documento_pdf(caminho) as doc:
                paginas = doc.pageCount()
        except Exception as error:
            self.status_label.setText(f"Não foi possível abrir o PDF: {error}")
            return
        self.pagina_input.setRange(1, max(1, paginas))
        self.pagina_input.setValue(1)
        self._render_pagina()

    def _carregar_contexto_item_e_pdf(self) -> None:
        """Lê dimensões do item e procura o pedido na pasta do orçamento."""
        try:
            with SessionLocal() as session:
                item = session.get(OrcamentoItem, self.item_id)
                if item is None:
                    self.status_label.setText("O item selecionado já não existe.")
                    return
                self.altura_input.setValue(float(item.altura or 0))
                self.largura_input.setValue(float(item.largura or 0))
                self.profundidade_input.setValue(float(item.profundidade or 0))
                pasta = OrcamentoExportService(session).resolver_pasta_versao(
                    item.orcamento_versao_id, criar=False
                )
            if pasta and pasta.is_dir():
                pdfs = list(pasta.glob("*.pdf"))
                if not pdfs and pasta.parent.is_dir():
                    pdfs = list(pasta.parent.glob("*.pdf"))
                pdfs.sort(
                    key=lambda p: (
                        "roup" not in p.name.casefold(),
                        "pedido" not in p.name.casefold(),
                        p.name.casefold(),
                    )
                )
                if pdfs:
                    self._usar_pdf(str(pdfs[0]))
                    self.status_label.setText(
                        f"PDF encontrado na pasta do orçamento: {pdfs[0].name}. Marque o roupeiro no desenho."
                    )
                    return
            self.status_label.setText(
                "Não encontrei um PDF na pasta do orçamento; escolha-o manualmente."
            )
        except Exception as error:
            self.status_label.setText(f"Não foi possível localizar a pasta do orçamento: {error}")

    def _render_pagina(self) -> None:
        caminho = self.pdf_input.text().strip()
        if not caminho:
            return
        try:
            with documento_pdf(caminho) as doc:
                indice = self.pagina_input.value() - 1
                pontos = doc.pagePointSize(indice)
                largura = 1400
                altura = max(1, round(largura * pontos.height() / pontos.width()))
                imagem = doc.render(indice, QSize(largura, altura))
            pixmap = QPixmap.fromImage(imagem).scaled(
                self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.preview.setPixmap(pixmap)
            self.preview._selecao = QRect()
        except Exception as error:
            self.status_label.setText(f"Não foi possível renderizar a página: {error}")

    def _respostas_alteradas(self) -> None:
        respostas = self.respostas_input.toPlainText().strip()
        alteradas = self.analise is not None and respostas != self._respostas_analisadas
        self.reanalisar_button.setEnabled(alteradas)
        if alteradas:
            self.propor_button.setEnabled(False)
            self.rejeitar_button.setEnabled(False)
            self.confirmar_button.setEnabled(False)
            self.status_label.setText(
                "As respostas foram alteradas. Reanalise o desenho para as considerar nas propostas."
            )
        elif self.analise is not None:
            self.propor_button.setEnabled(True)
            self.rejeitar_button.setEnabled(bool(self.propostas))
            self.confirmar_button.setEnabled(bool(self.propostas))

    def _analisar(self) -> None:
        caminho = self.pdf_input.text().strip()
        recorte, zona = self.preview.recorte_png()
        if not caminho or not Path(caminho).is_file():
            self.status_label.setText("Escolha um PDF acessível.")
            return
        if not recorte:
            self.status_label.setText("Marque primeiro a zona R1/R2/etc. por arrasto.")
            return
        with SessionLocal() as session:
            settings = SystemSettingService(session)
            fornecedor = (settings.obter_valor("provedor_visao_roupeiros", "openai") or "openai").lower()
            self.catalogo = DefModuloService(session).listar_elegiveis_roupeiro_abrir(self.user_id)
            perfil = tuple(
                {"tipo": e.tipo, "expressao": e.expressao, "significado": e.significado, "campos": e.campos}
                for e in listar_entradas(session, self.user_id)
            )
            if fornecedor == "local":
                modelo = settings.obter_valor("modelo_local_visao_roupeiros", "") or ""
                endpoint = settings.obter_valor("endpoint_local_visao_roupeiros", "http://localhost:11434") or "http://localhost:11434"
                if not modelo:
                    self.status_label.setText("Configure primeiro o modelo local de visão para roupeiros.")
                    return
                provider = LocalVisionProvider(modelo, endpoint)
            else:
                modelo = settings.obter_valor("modelo_openai_visao_roupeiros", "gpt-5.2") or "gpt-5.2"
                resposta = QMessageBox.warning(
                    self,
                    "Envio do PDF completo",
                    "Esta análise enviará o PDF completo à OpenAI, além do recorte marcado como foco. Pretende continuar?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if resposta != QMessageBox.StandardButton.Yes:
                    self.status_label.setText("Análise cancelada; nenhum dado do orçamento foi alterado.")
                    return
                provider = OpenAIVisionProvider(modelo)
        if zona:
            zona = replace(zona, pagina=self.pagina_input.value())
        pedido = PedidoAnaliseRoupeiro(
            pdf_path=caminho,
            item_id=self.item_id,
            user_id=self.user_id,
            pagina=self.pagina_input.value(),
            zona=zona,
            recorte_png=recorte,
            perfil=perfil,
            catalogo=tuple(self.catalogo),
            respostas_utilizador=self.respostas_input.toPlainText().strip(),
        )
        self._provider = provider
        self._pedido = pedido
        self.analisar_button.setEnabled(False)
        self.reanalisar_button.setEnabled(False)
        self.cancelar_button.setEnabled(False)
        self.status_label.setText("A analisar o documento… o orçamento permanece inalterado.")
        self._thread = QThread(self)
        self._worker = _VisionWorker(provider, pedido)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.executar)
        self._worker.concluido.connect(self._analise_concluida)
        self._worker.falhou.connect(self._analise_falhou)
        self._worker.concluido.connect(self._thread.quit)
        self._worker.falhou.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    @Slot(object)
    def _analise_concluida(self, analise: AnaliseRoupeiro) -> None:
        self.analise = analise
        self.referencia_label.setText(analise.referencia or "Não reconhecida")
        duvidas = list(analise.perguntas) + list(analise.restricoes)
        reconhecidas = (
            "Medidas eventualmente lidas no PDF (apenas informativas): "
            f"A={analise.altura.valor or '—'}, L={analise.largura.valor or '—'}, "
            f"P={analise.profundidade.valor or '—'} mm."
        )
        self.perguntas_text.setPlainText(
            (analise.explicacao + "\n" + reconhecidas + "\n" + "\n".join(duvidas)).strip()
        )
        self._respostas_analisadas = self.respostas_input.toPlainText().strip()
        self.propostas = []
        self.proposta_ids = []
        self.componentes_por_proposta = {}
        self.proposta_combo.clear()
        self.modulos_table.setRowCount(0)
        self.rejeitar_button.setEnabled(False)
        self.confirmar_button.setEnabled(False)
        self.propor_button.setEnabled(True)
        self.analisar_button.setEnabled(True)
        self.reanalisar_button.setEnabled(False)
        self.cancelar_button.setEnabled(True)
        self.status_label.setText(
            "Análise concluída. As dimensões continuam a ser as do item; reveja agora as propostas de módulos."
        )

    @Slot(str)
    def _analise_falhou(self, mensagem: str) -> None:
        self.analisar_button.setEnabled(True)
        self.reanalisar_button.setEnabled(
            self.analise is not None
            and self.respostas_input.toPlainText().strip() != self._respostas_analisadas
        )
        self.cancelar_button.setEnabled(True)
        self.status_label.setText(f"A análise falhou: {mensagem}")

    def _gerar_propostas(self) -> None:
        if self.analise is None:
            return
        medidas = [Decimal(str(spin.value())) for spin in (self.altura_input, self.largura_input, self.profundidade_input)]
        if any(v <= 0 for v in medidas):
            self.status_label.setText(
                "O item precisa de altura, largura e profundidade. Edite primeiro a ficha do item."
            )
            return
        with SessionLocal() as session:
            memoria = IaOrcamentoService(session)
            bonus = memoria.bonus_privado_modulos(self.user_id)
        self.propostas = RoupeiroCombinadorService().propor(
            medidas[1], self.catalogo, self.analise.caracteristicas, bonus_modulos=bonus
        )
        if not self.propostas:
            self.status_label.setText(
                "Ainda não existem módulos marcados como elegíveis para Roupeiro Abrir."
            )
            return
        try:
            with SessionLocal() as session:
                _analise_id, self.proposta_ids = IaOrcamentoService(session).registar_analise_e_propostas(
                    user_id=self.user_id,
                    item_id=self.item_id,
                    documento_path=self.pdf_input.text(),
                    pagina=self.pagina_input.value(),
                    zona=self._pedido.zona,
                    fornecedor=self._provider.nome,
                    modelo=self._provider.modelo,
                    analise=self.analise,
                    propostas=self.propostas,
                )
        except Exception as error:
            self.status_label.setText(f"Não foi possível guardar a análise privada: {error}")
            return
        self.proposta_combo.clear()
        self.componentes_por_proposta = {
            indice: [componente.def_modulo_id for componente in proposta.modulos]
            for indice, proposta in enumerate(self.propostas)
        }
        for indice, proposta in enumerate(self.propostas, 1):
            self.proposta_combo.addItem(f"Proposta {indice} — {proposta.pontuacao:.1f} pontos", indice - 1)
        self.rejeitar_button.setEnabled(True)
        self.confirmar_button.setEnabled(True)
        self._mostrar_proposta()

    def _mostrar_proposta(self) -> None:
        indice = self.proposta_combo.currentData()
        if indice is None or not self.propostas:
            return
        indice = int(indice)
        proposta = self.propostas[indice]
        componentes = self.componentes_por_proposta.get(indice, [])
        self.modulos_table.setRowCount(len(componentes))
        for row, modulo_id in enumerate(componentes):
            ordem_item = QTableWidgetItem(str(row + 1))
            ordem_item.setFlags(ordem_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.modulos_table.setItem(row, 0, ordem_item)
            combo = QComboBox()
            for modulo in self.catalogo:
                combo.addItem(f"{modulo.codigo} — {modulo.nome}", modulo.id)
            pos = combo.findData(modulo_id)
            combo.setCurrentIndex(pos if pos >= 0 else 0)
            combo.setToolTip("Pode trocar este módulo antes da confirmação.")
            combo.currentIndexChanged.connect(
                lambda _pos, proposta_indice=indice, linha=row, seletor=combo:
                self._trocar_modulo(proposta_indice, linha, seletor.currentData())
            )
            self.modulos_table.setCellWidget(row, 1, combo)
            remover = QPushButton("Remover")
            remover.setToolTip("Retirar este módulo apenas da composição em revisão.")
            remover.clicked.connect(
                lambda _checked=False, proposta_indice=indice, linha=row:
                self._remover_modulo(proposta_indice, linha)
            )
            self.modulos_table.setCellWidget(row, 2, remover)
        self.confirmar_button.setEnabled(bool(componentes))
        self.status_label.setText(proposta.explicacao)

    def _trocar_modulo(self, proposta_indice: int, linha: int, modulo_id) -> None:
        componentes = self.componentes_por_proposta.get(proposta_indice)
        if componentes is None or not 0 <= linha < len(componentes) or modulo_id is None:
            return
        componentes[linha] = int(modulo_id)

    def _remover_modulo(self, proposta_indice: int, linha: int) -> None:
        componentes = self.componentes_por_proposta.get(proposta_indice)
        if componentes is None or not 0 <= linha < len(componentes):
            return
        if len(componentes) == 1:
            self.status_label.setText("A composição deve manter pelo menos um módulo.")
            return
        componentes.pop(linha)
        self._mostrar_proposta()
        self.status_label.setText(
            "Módulo removido da composição em revisão; o orçamento continua inalterado."
        )

    def _componentes_editados(self) -> list[tuple[int, Decimal]]:
        indice = self.proposta_combo.currentData()
        if indice is None:
            return []
        return [
            (modulo_id, Decimal("0"))
            for modulo_id in self.componentes_por_proposta.get(int(indice), [])
        ]

    def _rejeitar(self) -> None:
        indice = self.proposta_combo.currentData()
        if indice is None:
            return
        motivo, ok = self._pedir_motivo()
        if not ok:
            return
        try:
            with SessionLocal() as session:
                IaOrcamentoService(session).rejeitar(self.proposta_ids[int(indice)], self.user_id, motivo)
        except Exception as error:
            self.status_label.setText(str(error))
            return
        self.status_label.setText("Rejeição registada apenas no seu histórico; o orçamento não foi alterado.")

    def _pedir_motivo(self) -> tuple[str, bool]:
        from PySide6.QtWidgets import QInputDialog
        return QInputDialog.getText(self, "Motivo da rejeição", "Motivo (opcional)")

    def _confirmar(self) -> None:
        indice = self.proposta_combo.currentData()
        if indice is None:
            return
        componentes = self._componentes_editados()
        largura_total = Decimal(str(self.largura_input.value()))
        resposta = QMessageBox.question(
            self,
            "Confirmar composição",
            "Inserir estes módulos, importar as estruturas e recalcular o item numa única transação?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        try:
            with SessionLocal() as session:
                service = IaOrcamentoService(session)
                proposta_id = self.proposta_ids[int(indice)]
                service.corrigir_componentes(proposta_id, self.user_id, componentes)
                self.modulos_criados = service.confirmar(
                    proposta_id=proposta_id,
                    user_id=self.user_id,
                    altura_mm=Decimal(str(self.altura_input.value())),
                    largura_mm=largura_total,
                    profundidade_mm=Decimal(str(self.profundidade_input.value())),
                    correcoes={
                        "interface": "módulos revistos; dimensões herdadas do item/custeio",
                        "respostas_utilizador": self.respostas_input.toPlainText().strip(),
                    },
                )
        except Exception as error:
            self.status_label.setText(f"Nada foi inserido. A operação foi revertida: {error}")
            return
        self.accept()
