"""Pesquisa unificada: trabalho em segundo plano e preferências pessoais."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import monotonic
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QMessageBox)
from sqlalchemy.orm import Session
from app.core.session import app_session
from app.db.session import SessionLocal
from app.services.user_pref_service import UserPrefService
from app.services.system_setting_service import SystemSettingService
from app.services.woodstore_service import query_woodstore, estado_stock
from app.domain.pesquisa_ia_consulta import (
    corresponde,
    mesma_espessura,
    observacoes_relevantes,
    referencia_com_acabamento,
    valor_de_referencia,
)
from app.utils.formatters import format_currency
from app.ui.widgets.combo_sem_scroll import ComboSemScroll

_ativos = set()
_ciclos = set()


class CicloPesquisa(QObject):
    """Manter worker e thread vivos até o Qt confirmar o fim da thread.

    Receber um resultado não significa que o worker já saiu de run(). Uma
    pesquisa seguinte pode começar antes disso. A limpeza fica na thread GUI,
    sem lambdas ligadas a objetos que já podem estar em destruição.
    """

    def __init__(self, thread, worker):
        super().__init__(QApplication.instance())
        self.thread_trabalho = thread
        self.worker = worker
        _ativos.add(thread)
        _ciclos.add(self)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self.finalizar, Qt.ConnectionType.QueuedConnection)

    @Slot()
    def finalizar(self):
        _ativos.discard(self.thread_trabalho)
        self.thread_trabalho.deleteLater()
        self.worker = None
        _ciclos.discard(self)
        self.deleteLater()


def aguardar_pesquisas():
    # As consultas são limitadas no transporte. Nunca destruir QThread a correr.
    for thread in list(_ativos):
        thread.requestInterruption()
        thread.quit()
    for thread in list(_ativos):
        thread.wait()


class FonteWorker(QObject):
    resultado = Signal(str, object, object)
    terminou = Signal()

    def __init__(self, fonte, token, tarefa):
        super().__init__()
        self.fonte, self.token, self.tarefa = fonte, token, tarefa

    @Slot()
    def run(self):
        try:
            dados = self.tarefa()
            self.resultado.emit(self.fonte, self.token, (dados, None))
        except Exception:
            self.resultado.emit(self.fonte, self.token, (None, "Não foi possível consultar esta fonte. Verifique a ligação/configuração."))
        finally:
            self.terminou.emit()


class ReceptorPesquisa(QObject):
    """Receber sinais numa instância QObject da thread da interface.

    O mixin Python não é um QObject: os seus @Slot não são registados de
    forma fiável pelo PySide6. Nunca o ligar diretamente a um worker.
    """

    def __init__(self, pagina):
        super().__init__(pagina)
        self.pagina = pagina

    @Slot(str, object, object)
    def fonte(self, nome, token, resultado):
        self.pagina._fonte_recebida(nome, token, resultado)

    @Slot(str)
    def pedaco(self, texto):
        self.pagina._acrescentar_resposta(texto)

    @Slot(str)
    def falhou(self, mensagem):
        self.pagina._resposta_falhou(mensagem)

    @Slot()
    def concluido(self):
        self.pagina._resposta_concluida()

    @Slot()
    def finalizado(self):
        self.pagina._finalizar_geracao()


class PesquisaIAFluxo:
    """Mixin da página: widgets permanecem exclusivamente na thread Qt."""

    def preparar_fluxo(self, layout, toolbar, linha_fichas):
        self._dono = getattr(app_session.current_user, "id", None)
        self._receptor_pesquisa = ReceptorPesquisa(self)
        self._jobs = {}
        self._leituras = {}
        self._erros_fontes = {}
        self._ultimas_tentativas = {}
        self._woodstore, self._woodstore_filtrados = [], []
        self._resposta_pendente = None
        self._consulta_resposta = None
        self._consulta_catalogos = ""
        self._cache_refs = None
        self._cache_cat = None
        self._ultima_consulta = None
        self._iniciado = False
        app = QApplication.instance()
        if not getattr(app, "_pesquisa_shutdown", False):
            app.aboutToQuit.connect(aguardar_pesquisas)
            app._pesquisa_shutdown = True
        self.carregar_button.setText("Atualizar fontes")
        self.carregar_button.setToolTip("Atualizar V3, PHC, tabelas dos fornecedores, índice dos catálogos e stock WoodStore por leitura.")
        self.carregar_button.clicked.disconnect()
        self.carregar_button.clicked.connect(self.atualizar_fontes)
        self.catalogos_button.hide()
        self.referencias_button.hide()
        for ficha in self.fichas.values():
            ficha.hide()  # Os separadores já selecionam e contam as fontes.
        self.resposta_button.setText("Pesquisar")
        self.resposta_button.setToolTip("Pesquisar todas as fontes e, se ativado, gerar uma resposta com as fontes disponíveis.")
        self.resposta_button.clicked.disconnect()
        self.resposta_button.clicked.connect(self.pesquisar_tudo)
        self.campo_pesquisa.pesquisar.connect(self.pesquisar_tudo)
        self.campo_pesquisa._input.setMaximumWidth(16777215)
        self.campo_pesquisa._input.setPlaceholderText("Ex.: Qual o preço de H1145/ST10 em 19 mm?")
        self.disposicao = ComboSemScroll()
        self.disposicao.addItem("Resposta ao lado", "lado")
        self.disposicao.addItem("Resposta por cima", "cima")
        self.disposicao.setToolTip("A disposição é guardada na sua conta de utilizador.")
        self.auto_resposta = QCheckBox("Responder ao pesquisar")
        self.auto_resposta.setChecked(True)
        self.auto_resposta.setToolTip("Gerar linguagem natural ao premir Pesquisar/Enter. Escrever apenas filtra os resultados.")
        self.espessura_input = ComboSemScroll()
        self.espessura_input.addItem("Todas as espessuras", None)
        for n in (3, 8, 10, 12, 16, 18, 19, 22, 25, 28, 30, 38):
            self.espessura_input.addItem(f"{n} mm", n)
        self.espessura_input.setToolTip("Filtrar por espessura. Uma espessura escrita na pergunta também é reconhecida.")
        controlos = QHBoxLayout()
        controlos.addWidget(self.disposicao)
        controlos.addWidget(self.espessura_input)
        controlos.addWidget(self.auto_resposta)
        controlos.addStretch()
        layout.insertLayout(2, controlos)
        self.fontes_status = QLabel("Fontes ainda não consultadas.")
        self.fontes_status.setWordWrap(True)
        layout.insertWidget(4, self.fontes_status)
        # Um único conjunto de resultados; separadores dão acesso às colunas
        # completas de cada fonte sem empilhar quatro tabelas no ecrã.
        self.resultados_tabs = QTabWidget()
        self.todas_table = QTableWidget(0, 6)
        self.todas_table.setHorizontalHeaderLabels(["Fonte", "Referência", "Descrição / correspondência", "Valor", "Tipo / unidade", "Origem"])
        self.todas_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.todas_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.todas_table.setAlternatingRowColors(True)
        self.todas_table.verticalHeader().hide()
        self.todas_table.setWordWrap(False)
        self.todas_table.horizontalHeader().setStretchLastSection(True)
        self.todas_table.cellDoubleClicked.connect(self.ver_origem_resultado)
        self.resultados_tabs.addTab(self.todas_table, "Todas")
        for nome, painel in (("V3", self.painel_v3), ("PHC", self.painel_phc),
                            ("Tabelas", self.painel_referencias), ("Catálogos", self.painel_catalogos)):
            self.resultados_tabs.addTab(painel, nome)
        self.woodstore_table = QTableWidget(0, 10)
        self.woodstore_table.setHorizontalHeaderLabels(["Ident / referência", "Comprimento", "Largura", "Espessura", "Material", "Código", "Quantidade (Lagen)", "Reservadas", "Saldo calculado", "Estado"])
        self.woodstore_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.woodstore_table.setAlternatingRowColors(True)
        self.woodstore_table.verticalHeader().hide()
        self.woodstore_table.setToolTip("Só leitura. Quantidade = contagem de registos Lagen; Reservadas = soma Menge. Saldo calculado não confirma pacotes, dimensões úteis ou autorização para consumir uma placa.")
        self.resultados_tabs.addTab(self.woodstore_table, "WoodStore")
        self.tabelas_splitter.addWidget(self.resultados_tabs)
        self.tabelas_splitter.setOrientation(Qt.Orientation.Horizontal)
        self.tabelas_splitter.setSizes([360, 850])
        self.painel_resposta.abrir(True)
        self.resposta_text.setPlaceholderText("Escreva uma referência ou pergunta e prima Pesquisar. Os resultados são apresentados mesmo sem o modelo IA disponível.")
        self.disposicao.currentIndexChanged.connect(self.guardar_disposicao)
        self.auto_resposta.toggled.connect(self.guardar_disposicao)
        self.espessura_input.currentIndexChanged.connect(self.aplicar_pesquisa)
        self._timer_fontes = QTimer(self)
        self._timer_fontes.setInterval(30_000)
        self._timer_fontes.timeout.connect(self.atualizar_se_necessario)
        self._timer_catalogos = QTimer(self)
        self._timer_catalogos.setSingleShot(True)
        self._timer_catalogos.setInterval(650)
        self._timer_catalogos.timeout.connect(self.pesquisar_catalogos)
        self._timer_filtro = QTimer(self)
        self._timer_filtro.setSingleShot(True)
        self._timer_filtro.setInterval(250)
        self._timer_filtro.timeout.connect(self.aplicar_pesquisa)
        self.campo_pesquisa.pesquisa_mudou.disconnect()
        self.campo_pesquisa.pesquisa_mudou.connect(self.agendar_pesquisa)
        self.aplicar_disposicao()

    def agendar_pesquisa(self, *_):
        # Invalidar já o contexto enquanto o debounce evita redesenhar milhares
        # de células a cada tecla. A resposta em curso deixa de ser exibida.
        self._consulta_resposta = None
        self._resposta_pendente = None
        self.resposta_text.clear()
        self._timer_filtro.start()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._iniciado:
            self._iniciado = True
            self.restaurar_disposicao()
            self.preparar_larguras_conta()
        self._timer_fontes.start()
        self.atualizar_se_necessario()

    def hideEvent(self, event):
        self.guardar_larguras_conta()
        self._timer_fontes.stop()
        self._timer_catalogos.stop()
        self._timer_filtro.stop()
        self._resposta_pendente = None
        super().hideEvent(event)

    def preparar_larguras_conta(self):
        import json
        self._tabelas_larguras = {n: getattr(self, n + "_table") for n in
            ("todas", "v3", "phc", "referencias", "catalogo", "woodstore")}
        self._timer_larguras = QTimer(self)
        self._timer_larguras.setSingleShot(True)
        self._timer_larguras.setInterval(700)
        self._timer_larguras.timeout.connect(self.guardar_larguras_conta)
        self._larguras_pendentes = False
        if self._dono is not None:
            try:
                with SessionLocal() as session:
                    raw = UserPrefService(session).obter_valor(self._dono, "pesquisa_ia_larguras", "{}")
                guardadas = json.loads(raw)
                for nome, tabela in self._tabelas_larguras.items():
                    for i in range(tabela.columnCount()):
                        chave = tabela.horizontalHeaderItem(i).text()
                        valor = guardadas.get(nome, {}).get(chave)
                        if isinstance(valor, int) and 20 <= valor <= 3000:
                            tabela.setColumnWidth(i, valor)
                            if nome in ("v3", "phc"):
                                setattr(self, "_" + nome + "_restaurado", True)
            except Exception:
                self.status_label.setText("Não foi possível ler as larguras guardadas.")
        for tabela in self._tabelas_larguras.values():
            tabela.horizontalHeader().sectionResized.connect(self._largura_alterada)

    def _largura_alterada(self, *_):
        self._larguras_pendentes = True
        self._timer_larguras.start()

    def guardar_larguras_conta(self):
        import json
        if not getattr(self, "_larguras_pendentes", False):
            return
        if self._dono is None or self._dono != getattr(app_session.current_user, "id", None):
            return
        dados = {nome: {t.horizontalHeaderItem(i).text(): t.columnWidth(i)
                 for i in range(t.columnCount())} for nome, t in self._tabelas_larguras.items()}
        try:
            with SessionLocal() as session:
                UserPrefService(session).guardar_valor(self._dono, "pesquisa_ia_larguras", json.dumps(dados))
            self._larguras_pendentes = False
        except Exception:
            self.status_label.setText("Não foi possível gravar as larguras na sua conta.")

    def restaurar_disposicao(self):
        if self._dono is None:
            return
        try:
            with SessionLocal() as session:
                svc = UserPrefService(session)
                modo = svc.obter_valor(self._dono, "pesquisa_ia_disposicao", "lado")
                auto = svc.obter_valor(self._dono, "pesquisa_ia_auto_resposta", "1")
            self.disposicao.blockSignals(True)
            self.auto_resposta.blockSignals(True)
            self.disposicao.setCurrentIndex(max(0, self.disposicao.findData(modo)))
            self.auto_resposta.setChecked(auto == "1")
            self.disposicao.blockSignals(False)
            self.auto_resposta.blockSignals(False)
            self.aplicar_disposicao()
        except Exception:
            self.status_label.setText("Não foi possível ler a sua disposição guardada.")

    def aplicar_disposicao(self):
        lado = self.disposicao.currentData() == "lado"
        self.tabelas_splitter.setOrientation(Qt.Orientation.Horizontal if lado else Qt.Orientation.Vertical)
        self.tabelas_splitter.insertWidget(0, self.resultados_tabs if lado else self.painel_resposta)
        self.tabelas_splitter.setStretchFactor(0, 3 if lado else 1)
        self.tabelas_splitter.setStretchFactor(1, 1 if lado else 3)
        self.tabelas_splitter.setSizes([850, 360] if lado else [220, 650])

    def guardar_disposicao(self, *_):
        self.aplicar_disposicao()
        if self._dono is None or self._dono != getattr(app_session.current_user, "id", None):
            return
        try:
            with SessionLocal() as session:
                svc = UserPrefService(session)
                svc.guardar_valor(self._dono, "pesquisa_ia_disposicao", self.disposicao.currentData())
                svc.guardar_valor(self._dono, "pesquisa_ia_auto_resposta", "1" if self.auto_resposta.isChecked() else "0")
        except Exception:
            self.status_label.setText("Disposição aplicada, mas não foi possível gravá-la na sua conta.")

    def _iniciar_fonte(self, fonte, tarefa, token=None):
        if fonte in self._jobs:
            return
        self._ultimas_tentativas[fonte] = monotonic()
        thread = QThread(QApplication.instance())
        worker = FonteWorker(fonte, token, tarefa)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.resultado.connect(self._receptor_pesquisa.fonte, Qt.ConnectionType.QueuedConnection)
        worker.terminou.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        CicloPesquisa(thread, worker)
        self._jobs[fonte] = (thread, worker)
        thread.start()
        self.mostrar_estado_fontes()

    def ler_fonte(self, fonte, consulta):
        # Capturar o engine do login atual: um relogin não muda a ligação de
        # uma consulta que já estava na fila. Resultados são locais à página.
        engine = SessionLocal.kw.get("bind")
        def run():
            with Session(bind=engine) as session:
                return consulta(session)
        self._iniciar_fonte(fonte, run)

    def atualizar_fontes(self, *_):
        self.carregar_v3()
        self.carregar_phc()
        self.carregar_referencias()
        self.ler_fonte("woodstore", query_woodstore)
        self.pesquisar_catalogos()

    def atualizar_se_necessario(self):
        if self._dono is None or not self.isVisible() or self._dono != getattr(app_session.current_user, "id", None):
            return
        for fonte, tempo, load in (("v3", 30, self.carregar_v3), ("phc", 300, self.carregar_phc),
                                   ("placas", 60, self.carregar_referencias),
                                   ("woodstore", 60, lambda: self.ler_fonte("woodstore", query_woodstore))):
            if monotonic() - self._ultimas_tentativas.get(fonte, -1000) >= tempo:
                load()
        self.mostrar_estado_fontes()

    @Slot(str, object, object)
    def _fonte_recebida(self, fonte, token, resultado):
        self._jobs.pop(fonte, None)
        if self._dono != getattr(app_session.current_user, "id", None):
            return
        dados, erro = resultado
        if erro:
            self._erros_fontes[fonte] = erro
        else:
            self._erros_fontes.pop(fonte, None)
            self._leituras[fonte] = datetime.now()
            if fonte == "catalogos":
                if token == self.chave_consulta():
                    self._ultimos_catalogos = dados
                    self._texto_catalogos = self.campo_pesquisa.texto().strip()
                    self._consulta_catalogos = token
                    self._preencher_catalogos(dados)
            else:
                setattr(self, {"v3": "_v3", "phc": "_phc", "placas": "_referencias_todas", "woodstore": "_woodstore"}[fonte], dados)
        self.aplicar_pesquisa()
        self.mostrar_estado_fontes()
        if fonte == "catalogos" and token != self.chave_consulta() and self.campo_pesquisa.texto().strip():
            self.pesquisar_catalogos()
        if self._resposta_pendente == self.chave_consulta() and not self._jobs:
            self._timer_catalogos.stop()
            self._resposta_pendente = None
            self.gerar_resposta()

    def mostrar_estado_fontes(self):
        partes = []
        for fonte in ("v3", "phc", "placas", "catalogos", "woodstore"):
            ultimo = self._leituras.get(fonte)
            estado = "a consultar…" if fonte in self._jobs else "falha de consulta" if fonte in self._erros_fontes else "disponível" if ultimo else "por consultar"
            partes.append(f"{fonte.upper()}: {estado}" + (f" · leitura {ultimo:%H:%M:%S}" if ultimo else ""))
        self.fontes_status.setText("  |  ".join(partes))
        self.fontes_status.setToolTip("Em caso de falha conservam-se os últimos dados e a hora da leitura. WoodStore: saldo = contagem Lagen − soma Menge das reservas; confirmar divergências e pacotes no armazém.")

    def chave_consulta(self):
        return (self.campo_pesquisa.texto().strip(), self.espessura_input.currentData())

    def pesquisar_tudo(self, *_):
        if not self.campo_pesquisa.texto().strip():
            self.status_label.setText("Escreva uma referência ou pergunta.")
            return
        self._timer_catalogos.stop()
        self._timer_filtro.stop()
        self.aplicar_pesquisa()
        self.atualizar_se_necessario()
        self._timer_catalogos.stop()
        self.pesquisar_catalogos()
        if self.auto_resposta.isChecked():
            self._resposta_pendente = self.chave_consulta()
            if not self._jobs:
                self._resposta_pendente = None
                self.gerar_resposta()

    def atualizar_resultados_unificados(self):
        texto, esp = self.chave_consulta()
        if self._ultima_consulta != self.chave_consulta():
            self._ultima_consulta = self.chave_consulta()
            self._resposta_pendente = None
            self.resposta_text.clear()
            self._consulta_resposta = None
            if texto and self.isVisible():
                self._timer_catalogos.start()
        self._woodstore_filtrados = [r for r in self._woodstore if corresponde(" ".join(str(r.get(k) or "") for k in ("Referencia", "Material", "Codigo")), texto) and mesma_espessura(r.get("Espessura"), texto, esp)]
        self.woodstore_table.setRowCount(len(self._woodstore_filtrados))
        for i, r in enumerate(self._woodstore_filtrados):
            vals = [str(r.get(k) if r.get(k) is not None else "") for k in ("Referencia", "Comprimento", "Largura", "Espessura", "Material", "Codigo", "Quantidade", "Reservadas", "Disponivel")]
            self._escrever_linha(self.woodstore_table, i, vals + [estado_stock(r)])
        linhas = []
        for m in self._v3_filtrados:
            linhas.append(("V3", m.ref_le, m.descricao, format_currency(m.preco_liquido), f"Líquido / {m.unidade}", observacoes_relevantes(m.observacoes or "", texto), self.painel_v3))
        for r in self._phc_filtrados:
            linhas.append(("PHC", r.get("Ref"), r.get("Descricao"), format_currency(r.get("Preco_Custo")), f"Custo / {r.get('Unidade', '')}", str(r.get("Data_Preco") or ""), self.painel_phc))
        for r in self._referencias_filtradas:
            # A coluna do valor tinha aqui o grupo de preco. Numa placa isso
            # ainda dizia alguma coisa; nas 9 827 ferragens que entraram com a
            # Fase 3 dizia so' "Grupo " -- e o preco delas, que existe e e' o
            # que se procura, nao aparecia em lado nenhum.
            linhas.append(("Tabelas", referencia_com_acabamento(r.referencia, r.st_acab),
                           r.nome_design, valor_de_referencia(r.precos, esp),
                           r.grupo, r.folha, self.painel_referencias))
        for r in self._ultimos_catalogos:
            linhas.append(("Catálogos", r.ficheiro, r.trecho[:240], "Exato" if r.exato else "Aproximação", r.fornecedor, r.local, self.painel_catalogos))
        for r in self._woodstore_filtrados:
            linhas.append(("WoodStore", r.get("Referencia"), r.get("Material"), str(r.get("Disponivel")), estado_stock(r), r.get("Codigo"), self.woodstore_table))
        total = len(linhas)
        self._linhas_unificadas = linhas[:300]
        self.todas_table.setRowCount(len(self._linhas_unificadas))
        for i, linha in enumerate(self._linhas_unificadas):
            for j, value in enumerate(linha[:6]):
                item = QTableWidgetItem(str(value or ""))
                item.setToolTip(str(value or ""))
                self.todas_table.setItem(i, j, item)
        self.resultados_tabs.setTabText(0, f"Todas ({min(total, 300)} de {total})" if total > 300 else f"Todas ({total})")
        self.todas_table.setToolTip("Duplo clique para ver a origem. A vista geral apresenta até 300 resultados; os separadores mostram cada fonte completa. Refine a pesquisa para encontrar o artigo.")
        self.resultados_tabs.setTabText(5, f"WoodStore ({len(self._woodstore_filtrados)})")
        for index, nome, quantidade in ((1,"V3",len(self._v3_filtrados)),(2,"PHC",len(self._phc_filtrados)),
                (3,"Tabelas",len(self._referencias_filtradas)),(4,"Catálogos",len(self._ultimos_catalogos))):
            self.resultados_tabs.setTabText(index,f"{nome} ({quantidade})")

    def ver_origem_resultado(self, row, _column):
        linha = self._linhas_unificadas[row]
        self.resultados_tabs.setCurrentWidget(linha[-1])
        if hasattr(linha[-1], "abrir"):
            linha[-1].abrir(True)
