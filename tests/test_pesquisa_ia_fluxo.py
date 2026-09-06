"""Regressões da pesquisa por acabamento e do fluxo com fontes assíncronas."""
from types import SimpleNamespace
from time import monotonic, sleep
import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy.orm import sessionmaker
from app.domain.pesquisa_ia_consulta import corresponde, mesma_espessura, observacoes_relevantes
from app.services.woodstore_service import STOCK_SQL, estado_stock, query_woodstore
from app.services.phc_sql import assert_select_only


def test_pergunta_referencia_acabamento_e_espessura():
    assert corresponde("F500/ST20 | H1145/ST10", "Qual o preço de H1145/ST10 em 19 mm?")
    assert corresponde("H1145/ST10", "H1145 ST10")
    assert not corresponde("H11450/ST10", "H1145")
    assert not corresponde("U999/ST19", "U999/ST1")
    assert not corresponde("W1000/ST9 | U999/ST19", "U999/ST9")
    assert mesma_espessura(19, "H1145 em 19mm")
    assert not mesma_espessura(8, "H1145 em 19mm")
    assert observacoes_relevantes("F500/ST20 | H1145/ST10 | H1199/ST12", "H1145") == "H1145/ST10"


def test_woodstore_agrega_antes_de_juntar_e_preserva_divergencias():
    assert_select_only(STOCK_SQL)
    assert "SUM(Menge)" in STOCK_SQL and "COUNT(*)" in STOCK_SQL
    assert STOCK_SQL.count("GROUP BY Identnummer") == 2
    assert "WITH (NOLOCK)" not in STOCK_SQL
    assert estado_stock({"Disponivel": -1}) == "Divergência nas reservas"
    assert estado_stock({"Disponivel": 0}) == "Sem saldo disponível"
    assert estado_stock({"Disponivel": 1}) == "Saldo positivo"
    assert estado_stock({"Disponivel": None}) == "Por confirmar"


def test_woodstore_transporta_apenas_select_e_nao_expoe_credenciais(monkeypatch):
    from app.services import woodstore_service as mod
    for key, val in {"SERVER":"host", "NAME":"lagerdb", "UID":"reader", "PWD":"private-test"}.items():
        monkeypatch.setenv("WOODSTORE_DB_"+key, val)
    calls=[]
    def transport(conn, sql):
        calls.append((conn, sql))
        raise RuntimeError("private-test")
    monkeypatch.setattr(mod, "run_select", transport)
    with pytest.raises(RuntimeError) as err:
        query_woodstore(None)
    assert "private-test" not in str(err.value)
    assert "ApplicationIntent=ReadOnly" in calls[0][0]
    assert calls[0][1] == STOCK_SQL


@pytest.fixture
def page(monkeypatch):
    from app.ui.pages import pesquisa_ia_page as mod
    from app.core.session import app_session
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(app_session, "current_user", None)
    monkeypatch.setattr(mod, "ligar_persistencia_larguras", lambda *a, **k: False)
    monkeypatch.setattr(mod, "ligar_persistencia_splitter", lambda *a, **k: False)
    widget=mod.PesquisaIAPage()
    yield widget
    widget.hide()
    from app.ui.helpers.pesquisa_ia_fluxo import aguardar_pesquisas
    aguardar_pesquisas()
    app.processEvents()
    widget.deleteLater()
    app.processEvents()


def test_preferencia_isolada_por_utilizador(page, session, monkeypatch):
    from app.ui.helpers import pesquisa_ia_fluxo as fluxo
    from app.core.session import app_session
    from app.services.user_pref_service import UserPrefService
    monkeypatch.setattr(fluxo, "SessionLocal", sessionmaker(bind=session.get_bind()))
    monkeypatch.setattr(app_session, "current_user", SimpleNamespace(id=27))
    page._dono=27
    page.disposicao.setCurrentIndex(1)
    assert UserPrefService(session).obter_valor(27,"pesquisa_ia_disposicao") == "cima"
    assert UserPrefService(session).obter_valor(28,"pesquisa_ia_disposicao") is None
    page._dono=28
    monkeypatch.setattr(app_session, "current_user", SimpleNamespace(id=28))
    page.restaurar_disposicao()
    assert page.disposicao.currentData() == "lado"


def test_falha_preserva_stock_e_distingue_leitura_vazia(page):
    page._woodstore=[{"Referencia":"old","Disponivel":2}]
    page._fonte_recebida("woodstore",None,(None,"Sem ligação"))
    assert page._woodstore[0]["Referencia"] == "old"
    assert "falha de consulta" in page.fontes_status.text()
    page._fonte_recebida("woodstore",None,([],None))
    assert page._woodstore == []
    assert "woodstore" in page._leituras
    assert "woodstore" not in page._erros_fontes


def test_catalogos_antigos_e_stream_antigo_nao_contaminam_nova_pergunta(page, monkeypatch):
    page.campo_pesquisa.definir_texto("H1145")
    page.aplicar_pesquisa()
    old=page.chave_consulta()
    page._consulta_resposta=old
    page.campo_pesquisa.definir_texto("U999")
    page._acrescentar_resposta("preço de H1145")
    assert page.resposta_text.toPlainText() == ""
    chamadas=[]
    monkeypatch.setattr(page,"pesquisar_catalogos",lambda: chamadas.append(True))
    page._fonte_recebida("catalogos",old,([SimpleNamespace(exato=True)],None))
    assert page._ultimos_catalogos == []
    assert chamadas


def test_fontes_corre_em_background_e_entrega_resultado(page):
    page._iniciar_fonte("woodstore", lambda: [{"Referencia":"X1","Disponivel":1}])
    limite=monotonic()+3
    while "woodstore" in page._jobs and monotonic()<limite:
        QApplication.processEvents()
        sleep(.005)
    assert page._woodstore[0]["Referencia"] == "X1"
    assert page.woodstore_table.rowCount() == 1


def test_resultados_de_fontes_sao_recebidos_na_thread_qt(page, monkeypatch):
    from PySide6.QtCore import QThread
    chamadas = []
    trabalho = []
    original = page._fonte_recebida
    def receber(*args):
        chamadas.append(QThread.currentThread())
        # Não tocar em widgets se esta regressão voltar: falhar como teste,
        # em vez de fazer o processo Qt abortar antes de reportar o erro.
        if QThread.currentThread() == page.thread():
            original(*args)
        else:
            page._jobs.pop(args[0], None)
    monkeypatch.setattr(page, "_fonte_recebida", receber)
    def consulta():
        trabalho.append(QThread.currentThread())
        return [{"Referencia": "X1", "Disponivel": 1}]
    page._iniciar_fonte("woodstore", consulta)
    limite = monotonic() + 3
    while not chamadas and monotonic() < limite:
        QApplication.processEvents()
        sleep(.005)
    assert chamadas == [page.thread()]
    assert trabalho and trabalho[0] != page.thread()
    assert page.woodstore_table.rowCount() == 1


def test_streaming_e_finalizacao_sao_recebidos_na_thread_qt(page, monkeypatch):
    from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
    chamadas = []
    class Emissor(QObject):
        pedaco = Signal(str)
        falha = Signal(str)
        terminou = Signal()
        @Slot()
        def run(self):
            self.pedaco.emit("resposta")
            self.falha.emit("erro de teste")
            self.terminou.emit()
    for nome in ("_acrescentar_resposta", "_resposta_falhou", "_resposta_concluida", "_finalizar_geracao"):
        monkeypatch.setattr(page, nome, lambda *args, nome=nome: chamadas.append((nome, QThread.currentThread())))
    t = QThread()
    e = Emissor()
    e.moveToThread(t)
    t.started.connect(e.run)
    r = page._receptor_pesquisa
    e.pedaco.connect(r.pedaco, Qt.ConnectionType.QueuedConnection)
    e.falha.connect(r.falhou, Qt.ConnectionType.QueuedConnection)
    e.terminou.connect(r.concluido, Qt.ConnectionType.QueuedConnection)
    e.terminou.connect(t.quit, Qt.ConnectionType.DirectConnection)
    t.finished.connect(r.finalizado, Qt.ConnectionType.QueuedConnection)
    t.finished.connect(e.deleteLater)
    t.start()
    assert t.wait(3000)
    limite = monotonic() + 3
    while len(chamadas) < 4 and monotonic() < limite:
        QApplication.processEvents()
        sleep(.005)
    assert len(chamadas) == 4
    assert all(thread == page.thread() for _, thread in chamadas)


def test_origem_resultado_e_disposicoes(page):
    page._woodstore=[{"Referencia":"X1","Material":"H1145/ST10","Espessura":19,"Disponivel":1}]
    page.aplicar_pesquisa()
    page.ver_origem_resultado(0,0)
    assert page.resultados_tabs.currentWidget() is page.woodstore_table
    from PySide6.QtCore import Qt
    page.disposicao.setCurrentIndex(1)
    assert page.tabelas_splitter.orientation() == Qt.Orientation.Vertical
    page.disposicao.setCurrentIndex(0)
    assert page.tabelas_splitter.orientation() == Qt.Orientation.Horizontal


def test_worker_e_preservado_entre_resultado_e_fim_da_thread(page, monkeypatch):
    import threading
    import weakref
    from PySide6.QtCore import QObject, Signal, Slot
    from app.ui.helpers import pesquisa_ia_fluxo as mod
    libertar = threading.Event()
    class WorkerLento(QObject):
        resultado = Signal(str, object, object)
        terminou = Signal()
        def __init__(self, fonte, token, tarefa):
            super().__init__()
            self.fonte, self.token = fonte, token
        @Slot()
        def run(self):
            self.resultado.emit(self.fonte, self.token, ([], None))
            libertar.wait(3)
            self.terminou.emit()
    monkeypatch.setattr(mod, "FonteWorker", WorkerLento)
    page._iniciar_fonte("woodstore", lambda: [])
    thread, worker = page._jobs["woodstore"]
    ref = weakref.ref(worker)
    del worker
    try:
        limite = monotonic() + 2
        while "woodstore" in page._jobs and monotonic() < limite:
            QApplication.processEvents()
            sleep(.005)
        assert "woodstore" not in page._jobs
        assert thread.isRunning()
        assert any(c.worker is ref() for c in mod._ciclos)
    finally:
        libertar.set()
        assert thread.wait(3000)
        QApplication.processEvents()
    assert thread not in mod._ativos


def test_pesquisas_sucessivas_com_acabamento_e_espessura(page, session, monkeypatch):
    from app.models import DefMateriaPrima
    from app.repositories.def_materia_prima_repository import DefMateriaPrimaRepository
    session.add_all([
        DefMateriaPrima(ref_le="PLC0066",descricao="AGL MLM EGGER GRUPO 5 19MM",
                        espessura=19,observacoes="F500/ST20 | H1145/ST10",ativo=True),
        DefMateriaPrima(ref_le="PLC0067",descricao="AGL MLM EGGER GRUPO 5 08MM",
                        espessura=8,observacoes="F500/ST20 | H1145/ST10",ativo=True),
    ])
    session.flush()
    page._v3=DefMateriaPrimaRepository(session).list_all()
    monkeypatch.setattr(page, "atualizar_se_necessario", lambda: None)
    monkeypatch.setattr(page, "pesquisar_catalogos", lambda: page._iniciar_fonte("catalogos",lambda: [],page.chave_consulta()))
    respostas=[]
    monkeypatch.setattr(page, "_iniciar_geracao", lambda pergunta, contexto: respostas.append((pergunta,contexto)))
    for pergunta in ["H1145", "O preço H1145/ST10 19mm"] * 5:
        page.campo_pesquisa.definir_texto(pergunta)
        page.pesquisar_tudo()
        limite=monotonic()+3
        while page._jobs and monotonic()<limite:
            QApplication.processEvents()
            sleep(.005)
        QApplication.processEvents()
        assert respostas[-1][0]==pergunta
        assert len(page._v3_filtrados)==(1 if "19mm" in pergunta else 2)
    assert "PLC0066" in respostas[-1][1]
    assert "PLC0067" not in respostas[-1][1]


def test_frase_natural_preserva_acabamento_e_espessura_decimal():
    assert corresponde("AGL B3768/SC 19MM", "Gostaria de saber o preço B3768/SC 19mm")
    assert not corresponde("AGL B3768/MA 19MM", "preço B3768/SC 19mm")
    assert mesma_espessura(0.8, "espessura 0,8")


def test_resumo_estavel_preserva_restos_e_escapa_html():
    from app.domain.pesquisa_ia_resumo import resumo_fontes, comentario_html
    rows = [{"Referencia":"PLACA", "Disponivel":0}, {"Referencia":"RESTO", "Disponivel":1}]
    html = resumo_fontes([], [], rows, [], [])
    assert html.index("1. MATÉRIAS") < html.index("2. PHC") < html.index("3. WOODSTORE")
    assert "RESTO" in html and "saldo calculado 1" in html
    assert 'font-size:14pt' in html
    assert "<strong>stock</strong>" in comentario_html("**stock** <script>")
    assert "<script>" not in comentario_html("**stock** <script>")


def test_larguras_guardadas_na_conta_e_preservadas_ao_pesquisar(page, session, monkeypatch):
    import json
    from app.ui.helpers import pesquisa_ia_fluxo as fluxo
    from app.core.session import app_session
    from app.services.user_pref_service import UserPrefService
    monkeypatch.setattr(fluxo, "SessionLocal", sessionmaker(bind=session.get_bind()))
    monkeypatch.setattr(app_session, "current_user", SimpleNamespace(id=27))
    page._dono = 27
    page.preparar_larguras_conta()
    page.todas_table.setColumnWidth(2, 317)
    page.woodstore_table.setColumnWidth(1, 177)
    page.guardar_larguras_conta()
    prefs = UserPrefService(session)
    saved = json.loads(prefs.obter_valor(27, "pesquisa_ia_larguras"))
    assert 317 in saved["todas"].values()
    assert 177 in saved["woodstore"].values()
    assert prefs.obter_valor(28, "pesquisa_ia_larguras") is None
    page.atualizar_resultados_unificados()
    assert page.todas_table.columnWidth(2) == 317
