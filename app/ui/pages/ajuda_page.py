"""Centro de Ajuda local, com catálogo, leitor de guias e ficha de teste."""

from __future__ import annotations

import html
from collections.abc import Callable

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtTextToSpeech import QTextToSpeech, QVoice
from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QStackedLayout,
    QTextEdit,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.ui import tema
from app.ui.ajuda import GuiaAjuda, carregar_guias
from app.ui.widgets.barra_cabecalho import BarraCabecalho


class AjudaPage(QWidget):
    """Mostra os tutoriais incluídos e recolhe feedback do piloto."""

    def __init__(self, on_back: Callable[[], None] | None = None) -> None:
        super().__init__()
        self._on_back = on_back
        self._guias = {guia.id: guia for guia in carregar_guias()}
        self._guia_atual: GuiaAjuda | None = None
        self._passo_atual = 0

        # A narração é gerada localmente pelo motor de voz do Windows: não há
        # ficheiros, internet nem credenciais para distribuir. Usa duas vozes
        # instaladas quando existirem; se só houver uma voz PT, diferencia os
        # dois narradores por ritmo e tom.
        motor = "winrt" if "winrt" in QTextToSpeech.availableEngines() else ""
        self._narrador = QTextToSpeech(motor, self) if motor else QTextToSpeech(self)
        self._narrador.setVolume(0.9)
        self._narrador.stateChanged.connect(self._estado_narracao_alterado)
        self._narrador.errorOccurred.connect(self._erro_narracao)
        self._vozes = self._escolher_vozes()
        self._narracao_ativa = False
        self._avanco_automatico = True
        self._indice_fala = 0

        self._stack = QStackedLayout(self)
        self._catalogo = self._criar_catalogo()
        self._leitor = self._criar_leitor()
        self._stack.addWidget(self._catalogo)
        self._stack.addWidget(self._leitor)

    def abrir_guia(self, guia_id: str) -> bool:
        """Abre diretamente um guia; devolve False se não existir."""
        guia = self._guias.get(guia_id)
        if guia is None:
            return False
        self._guia_atual = guia
        self._passo_atual = 0
        self._avanco_automatico = True
        self._mostrar_passo()
        self._stack.setCurrentWidget(self._leitor)
        QTimer.singleShot(250, self._iniciar_narracao_do_passo)
        return True

    def mostrar_catalogo(self) -> None:
        """Volta ao catálogo e pára uma narração que esteja a tocar."""
        self._parar_narracao()
        self._stack.setCurrentWidget(self._catalogo)

    def _criar_catalogo(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(
            BarraCabecalho(
                "Ajuda",
                ["Guias práticos para trabalhar no Martelo V3"],
            )
        )

        introducao = QLabel(
            "Escolha um guia. Os exemplos são fictícios e o guia não altera "
            "os seus dados. Pode acompanhar a explicação lendo a transcrição."
        )
        introducao.setWordWrap(True)
        layout.addWidget(introducao)

        catalogo = QGroupBox("Guias disponíveis")
        catalogo_layout = QVBoxLayout(catalogo)
        if not self._guias:
            catalogo_layout.addWidget(QLabel("Ainda não há guias disponíveis."))
        for guia in self._guias.values():
            cartao = QFrame()
            cartao.setStyleSheet(
                f"QFrame {{ background: {tema.BEGE_CLARO}; border: 1px solid "
                f"{tema.CINZA_CASTANHO}; border-radius: 6px; }}"
            )
            linha = QHBoxLayout(cartao)
            texto = QLabel(
                f"<b>{html.escape(guia.titulo)}</b><br>{html.escape(guia.resumo)}"
                f"<br><small>{len(guia.passos)} passos · versão {guia.versao}</small>"
            )
            texto.setWordWrap(True)
            abrir = QPushButton("Abrir guia")
            abrir.setToolTip(f"Abrir o guia “{guia.titulo}”.")
            abrir.clicked.connect(lambda _=False, guia_id=guia.id: self.abrir_guia(guia_id))
            linha.addWidget(texto, stretch=1)
            linha.addWidget(abrir)
            catalogo_layout.addWidget(cartao)
        layout.addWidget(catalogo)

        layout.addWidget(self._criar_ficha_feedback())
        layout.addStretch()
        return pagina

    def _criar_ficha_feedback(self) -> QGroupBox:
        caixa = QGroupBox("Ficha de recolha — piloto")
        formulario = QFormLayout(caixa)
        self.feedback_nome = QLineEdit()
        self.feedback_nome.setPlaceholderText("Nome ou código do participante")
        self.feedback_nome.setToolTip("Identificação opcional de quem experimentou o guia.")
        self.feedback_resultado = QButtonGroup(self)
        resultado_widget = QWidget()
        resultado_layout = QHBoxLayout(resultado_widget)
        resultado_layout.setContentsMargins(0, 0, 0, 0)
        self.feedback_concluiu = QRadioButton("Concluiu sem ajuda")
        self.feedback_nao_concluiu = QRadioButton("Precisou de ajuda")
        self.feedback_resultado.addButton(self.feedback_concluiu, 1)
        self.feedback_resultado.addButton(self.feedback_nao_concluiu, 0)
        resultado_layout.addWidget(self.feedback_concluiu)
        resultado_layout.addWidget(self.feedback_nao_concluiu)
        self.feedback_dificuldade = QLineEdit()
        self.feedback_dificuldade.setPlaceholderText("Ex.: passo 3 — escolher cliente")
        self.feedback_dificuldade.setToolTip("Indique o passo ou assunto que causou mais dificuldade.")
        self.feedback_sugestoes = QTextEdit()
        self.feedback_sugestoes.setFixedHeight(70)
        self.feedback_sugestoes.setToolTip("Registe sugestões para melhorar o guia.")
        self.feedback_estado = QLabel("")
        self.feedback_estado.setStyleSheet(f"color: {tema.TEXTO_OK};")
        copiar = QPushButton("Copiar ficha")
        copiar.setToolTip("Copiar o feedback para enviar à equipa do Martelo.")
        copiar.clicked.connect(self._copiar_feedback)
        formulario.addRow("Participante", self.feedback_nome)
        formulario.addRow("Resultado", resultado_widget)
        formulario.addRow("Maior dificuldade", self.feedback_dificuldade)
        formulario.addRow("Sugestões", self.feedback_sugestoes)
        formulario.addRow("", copiar)
        formulario.addRow("", self.feedback_estado)
        return caixa

    def _criar_leitor(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        topo = QHBoxLayout()
        self.voltar_catalogo_button = QPushButton("← Fechar guia")
        self.voltar_catalogo_button.setToolTip("Fechar este guia e voltar ao catálogo de ajuda.")
        self.voltar_catalogo_button.clicked.connect(self.mostrar_catalogo)
        self.leitor_titulo = QLabel()
        self.leitor_titulo.setStyleSheet(f"color: {tema.CASTANHO_ESCURO}; font-size: 18px; font-weight: bold;")
        topo.addWidget(self.voltar_catalogo_button)
        topo.addWidget(self.leitor_titulo, stretch=1)
        layout.addLayout(topo)

        self.progresso = QLabel()
        self.progresso.setStyleSheet(f"color: {tema.CASTANHO_MEDIO}; font-weight: bold;")
        layout.addWidget(self.progresso)
        self.imagem = QLabel()
        self.imagem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imagem.setMinimumHeight(260)
        self.imagem.setStyleSheet(f"background: {tema.BEGE_CLARO}; border: 1px solid {tema.CINZA_CASTANHO};")
        layout.addWidget(self.imagem)
        self.passo_titulo = QLabel()
        self.passo_titulo.setStyleSheet(f"color: {tema.CASTANHO_ESCURO}; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.passo_titulo)
        self.explicacao = QLabel()
        self.explicacao.setWordWrap(True)
        layout.addWidget(self.explicacao)

        transcricao_caixa = QGroupBox("Conversa dos narradores — transcrição")
        transcricao_caixa.setMaximumHeight(145)
        transcricao_caixa.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        transcricao_layout = QVBoxLayout(transcricao_caixa)
        self.transcricao = QTextBrowser()
        self.transcricao.setOpenExternalLinks(False)
        self.transcricao.setFixedHeight(78)
        transcricao_layout.addWidget(self.transcricao)
        layout.addWidget(transcricao_caixa)

        controlos = QHBoxLayout()
        self.anterior = QPushButton("← Anterior")
        self.anterior.setToolTip("Mostrar o passo anterior do guia.")
        self.anterior.clicked.connect(lambda: self._mudar_passo(-1))
        self.seguinte = QPushButton("Seguinte →")
        self.seguinte.setToolTip("Mostrar o passo seguinte do guia.")
        self.seguinte.clicked.connect(lambda: self._mudar_passo(1))
        self.repetir_audio = QPushButton("🔊 Repetir narração")
        self.repetir_audio.setToolTip("Ouvir novamente a conversa deste passo.")
        self.repetir_audio.clicked.connect(self._repetir_narracao)
        self.automatico_button = QPushButton("⏸ Pausar guia")
        self.automatico_button.setToolTip(
            "Pausar a narração e o avanço automático para explorar manualmente."
        )
        self.automatico_button.clicked.connect(self._alternar_automatico)
        self.audio_estado = QLabel()
        self.audio_estado.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")
        controlos.addWidget(self.anterior)
        controlos.addWidget(self.seguinte)
        controlos.addStretch()
        controlos.addWidget(self.audio_estado)
        controlos.addWidget(self.repetir_audio)
        controlos.addWidget(self.automatico_button)
        layout.addLayout(controlos)
        return pagina

    def _mostrar_passo(self) -> None:
        if self._guia_atual is None:
            return
        passo = self._guia_atual.passos[self._passo_atual]
        total = len(self._guia_atual.passos)
        self.leitor_titulo.setText(self._guia_atual.titulo)
        self.progresso.setText(f"Passo {self._passo_atual + 1} de {total}")
        self.passo_titulo.setText(passo.titulo)
        self.explicacao.setText(passo.explicacao)
        self.transcricao.setHtml("<br>".join(
            f"<b>{html.escape(fala.narrador)}:</b> {html.escape(fala.texto)}"
            for fala in passo.falas
        ))
        pixmap = QPixmap(str(passo.imagem))
        if pixmap.isNull():
            self.imagem.setPixmap(QPixmap())
            self.imagem.setText("Não foi possível carregar a ilustração deste passo.")
        else:
            self.imagem.setText("")
            self.imagem.setPixmap(
                pixmap.scaled(860, 330, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        narracao_disponivel = bool(self._narrador.availableVoices())
        self.repetir_audio.setEnabled(narracao_disponivel)
        if narracao_disponivel:
            self.audio_estado.setText("Narração local pronta")
        else:
            self.audio_estado.setText("Voz do Windows indisponível — leia a transcrição")
        self.anterior.setEnabled(self._passo_atual > 0)
        self.seguinte.setEnabled(self._passo_atual < total - 1)
        self._atualizar_botao_automatico()

    def _mudar_passo(self, delta: int) -> None:
        if self._guia_atual is None:
            return
        novo = self._passo_atual + delta
        if 0 <= novo < len(self._guia_atual.passos):
            # Os botões manuais dão controlo completo ao utilizador: a voz e o
            # avanço automático param até este escolher retomar o guia.
            self._avanco_automatico = False
            self._parar_narracao()
            self._passo_atual = novo
            self._mostrar_passo()

    def _repetir_narracao(self) -> None:
        """Repete a conversa do passo, sem reativar o avanço automático."""
        self._parar_narracao()
        self._iniciar_narracao_do_passo(avancar_no_fim=False)

    def _alternar_automatico(self) -> None:
        """Pausa/retoma a apresentação narrada automaticamente."""
        if self._narracao_ativa or self._avanco_automatico:
            self._avanco_automatico = False
            self._parar_narracao()
            self.audio_estado.setText("Guia em pausa — use os botões ou retome o automático")
        else:
            self._avanco_automatico = True
            self._iniciar_narracao_do_passo()
        self._atualizar_botao_automatico()

    def _iniciar_narracao_do_passo(self, *, avancar_no_fim: bool | None = None) -> None:
        """Inicia a conversa sintetizada do diapositivo corrente."""
        if self._guia_atual is None:
            return
        if not self._narrador.availableVoices():
            return
        if avancar_no_fim is not None:
            self._avanco_automatico = avancar_no_fim
        self._narracao_ativa = True
        self._indice_fala = 0
        self.audio_estado.setText("Marta e João estão a explicar este passo…")
        self._atualizar_botao_automatico()
        self._falar_proxima_linha()

    def _falar_proxima_linha(self) -> None:
        if not self._narracao_ativa or self._guia_atual is None:
            return
        falas = self._guia_atual.passos[self._passo_atual].falas
        if self._indice_fala >= len(falas):
            self._narracao_ativa = False
            self._atualizar_botao_automatico()
            self._agendar_proximo_passo()
            return
        fala = falas[self._indice_fala]
        self._indice_fala += 1
        voz, tom, ritmo = self._perfil_narrador(fala.narrador)
        self._narrador.setVoice(voz)
        self._narrador.setPitch(tom)
        self._narrador.setRate(ritmo)
        self._narrador.say(fala.texto)

    def _estado_narracao_alterado(self, estado: QTextToSpeech.State) -> None:
        if not self._narracao_ativa:
            return
        if estado == QTextToSpeech.State.Ready:
            self._falar_proxima_linha()

    def _agendar_proximo_passo(self) -> None:
        if not self._avanco_automatico or self._guia_atual is None:
            self.audio_estado.setText("Narração concluída — use os botões para continuar")
            return
        guia_id, passo_atual = self._guia_atual.id, self._passo_atual
        if passo_atual == len(self._guia_atual.passos) - 1:
            self._avanco_automatico = False
            self.audio_estado.setText("Guia concluído — use Anterior para rever")
            self._atualizar_botao_automatico()
            return
        QTimer.singleShot(1200, lambda: self._avancar_automaticamente(guia_id, passo_atual))

    def _avancar_automaticamente(self, guia_id: str, passo_atual: int) -> None:
        if (
            self._avanco_automatico
            and self._guia_atual is not None
            and self._guia_atual.id == guia_id
            and self._passo_atual == passo_atual
        ):
            self._passo_atual += 1
            self._mostrar_passo()
            self._iniciar_narracao_do_passo()

    def _parar_narracao(self) -> None:
        self._narracao_ativa = False
        if self._narrador.state() != QTextToSpeech.State.Ready:
            self._narrador.stop()

    def _atualizar_botao_automatico(self) -> None:
        if self._narracao_ativa or self._avanco_automatico:
            self.automatico_button.setText("⏸ Pausar guia")
            self.automatico_button.setToolTip(
                "Pausar a narração e o avanço automático para explorar manualmente."
            )
        else:
            self.automatico_button.setText("▶ Retomar automático")
            self.automatico_button.setToolTip(
                "Ouvir este passo e continuar automaticamente para o seguinte."
            )

    def _escolher_vozes(self) -> dict[str, QVoice]:
        vozes = self._narrador.availableVoices()
        if not vozes:
            return {}
        feminina = next(
            (voz for voz in vozes if voz.gender() == QVoice.Gender.Female), vozes[0]
        )
        masculina = next(
            (voz for voz in vozes if voz.gender() == QVoice.Gender.Male), feminina
        )
        return {"Marta": feminina, "João": masculina}

    def _perfil_narrador(self, nome: str) -> tuple[QVoice, float, float]:
        voz = self._vozes.get(nome) or self._narrador.availableVoices()[0]
        # Quando o Windows só disponibiliza uma voz PT, o segundo perfil fica
        # intencionalmente mais grave e pausado, mantendo a conversa distinta.
        if nome == "João":
            return voz, -0.32, -0.12
        return voz, 0.12, -0.04

    def _erro_narracao(self, _motivo, mensagem: str) -> None:
        self._narracao_ativa = False
        self._avanco_automatico = False
        self.audio_estado.setText(
            f"Não foi possível reproduzir a narração: {mensagem or 'motor de voz indisponível'}"
        )
        self._atualizar_botao_automatico()

    def _copiar_feedback(self) -> None:
        resultado = self.feedback_resultado.checkedId()
        texto_resultado = {1: "Concluiu sem ajuda", 0: "Precisou de ajuda"}.get(resultado, "Não indicado")
        ficha = (
            "Piloto Ajuda — Criar um orçamento\n"
            f"Participante: {self.feedback_nome.text().strip() or 'Não indicado'}\n"
            f"Resultado: {texto_resultado}\n"
            f"Maior dificuldade: {self.feedback_dificuldade.text().strip() or 'Não indicada'}\n"
            f"Sugestões: {self.feedback_sugestoes.toPlainText().strip() or 'Sem sugestões'}"
        )
        QGuiApplication.clipboard().setText(ficha)
        self.feedback_estado.setText("Ficha copiada. Pode agora enviá-la à equipa.")
