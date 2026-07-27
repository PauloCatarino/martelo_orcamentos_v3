"""Menu dedicado do IA Martelo, com mascote animada.

Um diálogo próprio (separado da pesquisa tradicional da Produção): o martelo
🔨 martela um prego na madeira 🪵 enquanto pensa e pára ao responder. A pesquisa
mostra a lista de obras AQUI (não mexe nos filtros da tabela); um duplo-clique
abre a obra na Produção. Pedidos sobre uma obra (texto/PDF/email) são tratados
pela página da Produção, através de callbacks.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QDate, QThread, QTime, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.datas import normalizar_data
from app.services.assistente_producao_service import AssistenteProducaoService
from app.ui import tema


class _MarteloAnimado(QWidget):
    """Mascote: o martelo martela um prego na madeira enquanto pensa."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(120, 96)

        madeira = QLabel("🪵", self)
        madeira.setStyleSheet("font-size: 30px;")
        madeira.adjustSize()
        madeira.move(46, 58)

        self._martelo = QLabel("🔨", self)
        self._martelo.setStyleSheet("font-size: 34px;")
        self._martelo.adjustSize()
        self._y_cima, self._y_baixo = 4, 26
        self._martelo.move(40, self._y_cima)

        self._timer = QTimer(self)
        self._timer.setInterval(130)
        self._timer.timeout.connect(self._tick)
        self._baixo = False

    def _tick(self) -> None:
        self._baixo = not self._baixo
        self._martelo.move(40, self._y_baixo if self._baixo else self._y_cima)

    def iniciar(self) -> None:
        self._timer.start()

    def parar(self) -> None:
        self._timer.stop()
        self._baixo = False
        self._martelo.move(40, self._y_cima)


class _IAWorker(QThread):
    """Corre a interpretação do IA Martelo fora da thread da UI."""

    concluido = Signal(object)  # ResultadoIA
    falhou = Signal(str)

    def __init__(self, pergunta, user_id, processos, ano_atual, hora_atual,
                 utilizador_nome, parent=None) -> None:
        super().__init__(parent)
        self._pergunta = pergunta
        self._user_id = user_id
        self._processos = processos
        self._ano_atual = ano_atual
        self._hora_atual = hora_atual
        self._utilizador_nome = utilizador_nome

    def run(self) -> None:  # noqa: D102 - QThread override
        try:
            with SessionLocal() as session:
                resultado = AssistenteProducaoService(session).responder_ia(
                    self._pergunta,
                    user_id=self._user_id,
                    processos=self._processos,
                    ano_atual=self._ano_atual,
                    hora_atual=self._hora_atual,
                    utilizador_nome=self._utilizador_nome,
                )
            self.concluido.emit(resultado)
        except Exception as exc:  # noqa: BLE001 - reportado à UI
            self.falhou.emit(str(exc))


class IaMarteloDialog(QDialog):
    """Menu do IA Martelo (pesquisa + ações sobre uma obra)."""

    def __init__(
        self,
        parent=None,
        *,
        obter_processos: Callable[[], list],
        obter_user_id: Callable[[], int | None],
        on_abrir_obra: Callable[[int], None],
        on_resultado_obra: Callable[[object], None],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("IA Martelo")
        self.resize(560, 520)
        self._obter_processos = obter_processos
        self._obter_user_id = obter_user_id
        self._on_abrir_obra = on_abrir_obra
        self._on_resultado_obra = on_resultado_obra
        self._worker: _IAWorker | None = None

        layout = QVBoxLayout(self)

        topo = QHBoxLayout()
        self.mascote = _MarteloAnimado()
        topo.addWidget(self.mascote)
        titulo = QLabel(
            "<b>IA Martelo</b><br>Pergunte sobre as obras — pesquisa, ponto de "
            "situação, relatório PDF ou email ao cliente."
        )
        titulo.setWordWrap(True)
        topo.addWidget(titulo, stretch=1)
        layout.addLayout(topo)

        entrada = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText(
            "Ex.: as minhas obras atrasadas · relatório da obra 1134 · "
            "email da obra 800"
        )
        self.input.returnPressed.connect(self._perguntar)
        self.botao = QPushButton("Perguntar")
        self.botao.clicked.connect(self._perguntar)
        self.botao_ensinar = QPushButton("🎓 Ensinar o Martelo")
        self.botao_ensinar.setToolTip(
            "Abrir «Assistente — o meu perfil» para ensinar palavras, alcunhas e "
            "instruções ao Martelo (é aqui que se alimenta o conhecimento)."
        )
        self.botao_ensinar.clicked.connect(self._abrir_perfil)
        #: Palavra que a última pesquisa não conheceu (vai já escrita no perfil).
        self._palavra_a_ensinar = ""
        entrada.addWidget(self.input, stretch=1)
        entrada.addWidget(self.botao)
        entrada.addWidget(self.botao_ensinar)
        layout.addLayout(entrada)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 2px;"
        )
        layout.addWidget(self.status)

        self.resultados = QListWidget()
        self.resultados.setToolTip("Duplo-clique para abrir a obra na Produção.")
        self.resultados.itemDoubleClicked.connect(self._abrir_selecionada)
        layout.addWidget(self.resultados, stretch=1)

    # ---- pergunta --------------------------------------------------------
    def _perguntar(self) -> None:
        pergunta = self.input.text().strip()
        if not pergunta:
            return
        if self._worker is not None and self._worker.isRunning():
            return

        self.botao.setEnabled(False)
        self.status.setText("O Martelo está a martelar…")
        self.mascote.iniciar()

        user = app_session.current_user
        utilizador_nome = (
            getattr(user, "nome", None) or getattr(user, "username", None) or ""
        )
        worker = _IAWorker(
            pergunta,
            self._obter_user_id(),
            self._obter_processos(),
            QDate.currentDate().year(),
            QTime.currentTime().hour(),
            str(utilizador_nome),
            self,
        )
        worker.concluido.connect(self._concluido)
        worker.falhou.connect(self._falhou)
        worker.finished.connect(self._terminou)
        self._worker = worker
        worker.start()

    def _concluido(self, resultado) -> None:
        if getattr(resultado, "tipo", "") == "obra":
            # Texto/PDF/email tratados pela Produção (reutiliza tudo o que existe).
            self.resultados.clear()
            self.status.setText(resultado.aviso or "")
            self._on_resultado_obra(resultado)
            return

        # Pesquisa: mostrar as obras aqui.
        recusa = getattr(resultado, "recusa", "")
        intencao = getattr(resultado, "intencao", None)
        if recusa:
            self.resultados.clear()
            self.status.setText(recusa)
            return
        if intencao is not None and intencao.precisa_perguntar:
            self.resultados.clear()
            self.status.setText(" ".join(intencao.perguntas))
            return

        self._mostrar_obras(resultado)

    def _mostrar_obras(self, resultado) -> None:
        self.resultados.clear()
        for processo in resultado.obras:
            item = QListWidgetItem(self._descricao_obra(processo))
            item.setData(Qt.ItemDataRole.UserRole, getattr(processo, "id", None))
            self.resultados.addItem(item)
        frase = resultado.frase or ""
        sugestao = resultado.sugestao_perfil or ""
        self.status.setText(f"{frase} {sugestao}".strip())
        self._definir_palavra_a_ensinar(getattr(resultado, "palavra_a_ensinar", ""))

    def _definir_palavra_a_ensinar(self, palavra: str) -> None:
        """Guarda a palavra desconhecida e põe-na no botão de ensinar.

        Assim quem carrega no botão já encontra a palavra escrita no perfil —
        voltar a escrevê-la à mão é onde a maioria desiste de ensinar.
        """
        self._palavra_a_ensinar = (palavra or "").strip()
        self.botao_ensinar.setText(
            f"🎓 Ensinar «{self._palavra_a_ensinar}»"
            if self._palavra_a_ensinar
            else "🎓 Ensinar o Martelo"
        )

    @staticmethod
    def _descricao_obra(processo) -> str:
        codigo = str(getattr(processo, "codigo_processo", "") or "").strip()
        cliente = str(getattr(processo, "nome_cliente", "") or "").strip()
        estado = str(getattr(processo, "estado", "") or "").strip()
        entrega = normalizar_data(getattr(processo, "data_entrega", None)) or ""
        partes = [p for p in (codigo, cliente, estado) if p]
        if entrega:
            partes.append(f"entrega {entrega}")
        return "  ·  ".join(partes)

    def _abrir_selecionada(self, item: QListWidgetItem) -> None:
        processo_id = item.data(Qt.ItemDataRole.UserRole)
        if processo_id is not None:
            self._on_abrir_obra(int(processo_id))

    def _abrir_perfil(self) -> None:
        """Abre «Assistente — o meu perfil» para ensinar o Martelo.

        Se a última pesquisa esbarrou numa palavra desconhecida, ela vai já
        escrita e no quadro certo — só falta dizer o que significa.
        """
        from app.ui.pages.ia_perfil_page import IaPerfilPage

        palavra = getattr(self, "_palavra_a_ensinar", "")
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Assistente — o meu perfil")
        dialogo.resize(880, 600)
        col = QVBoxLayout(dialogo)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(
            IaPerfilPage(
                on_back=dialogo.accept,
                tipo_inicial="movel" if palavra else None,
                expressao_inicial=palavra,
            )
        )
        dialogo.exec()

    def _falhou(self, _erro: str) -> None:
        self.status.setText("Não foi possível interpretar a pergunta.")

    def _terminou(self) -> None:
        self.mascote.parar()
        self.botao.setEnabled(True)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
