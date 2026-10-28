"""Aviso: o Escritório do Streamlit já avançou uma obra que aqui está em Desenho.

Quando o desenhador carrega em «Enviar para o Aprovisionamento» no Streamlit,
o modelo/versão sai do Desenho — e o Martelo, que não sabia, continuava a
dizer «Desenho». Este vigia dá por isso e propõe pôr a obra em **Produção**,
na mesma caixa do analisador de estados do PHC. Quem decide é a pessoa, linha
a linha; o Martelo nunca muda nada sozinho e nunca faz uma obra recuar.

Como é barato perguntar ao Streamlit «houve alguma coisa nova?» (o ``MAX(id)``
dos eventos), pergunta-se de cinco em cinco minutos; só quando a resposta muda
é que se vão buscar as versões. Cada pessoa vê só as suas obras.

As sugestões recusadas não voltam (só se a etapa mudar outra vez); «Ver
depois» guarda-as até ao dia seguinte.
"""

from __future__ import annotations

import json
from datetime import date

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core import diario_bordo
from app.db.session import SessionLocal
from app.domain import escritorio_streamlit as regras
from app.services import escritorio_streamlit_service as leitura
from app.services.producao_phc_sync_service import aplicar_estados
from app.services.user_pref_service import UserPrefService
from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

#: Preferência (por utilizador) com as sugestões já vistas:
#: ``{marca: "sempre" | "aaaa-mm-dd"}``.
CHAVE_VISTOS = "escritorio_streamlit_avisos_vistos"

#: Quantas marcas se guardam, no máximo (as mais antigas saem primeiro).
MAXIMO_VISTOS = 400

INTERVALO_MS = 5 * 60 * 1000

#: Depois do analisador do PHC (60 s), para não irem os dois ao mesmo tempo.
ATRASO_ARRANQUE_MS = 90 * 1000

TITULO = "Aviso do Escritório (Streamlit)"

APRESENTACAO = (
    "No Escritório do Streamlit, estas obras suas já saíram do Desenho — "
    "foram enviadas para o Aprovisionamento ou já estão libertadas para a fábrica.\n"
    "No Martelo continuam em Desenho. Marque as que quer passar a Produção; as "
    "que desmarcar ficam como estão e não volto a perguntar por elas."
)

DICA_VER_DEPOIS = "Fecha sem alterar nada. Volto a lembrar amanhã."


class _TrabalhoEscritorio(QObject):
    """Vive na thread de trabalho: o PowerShell demora e prendia a janela."""

    verificado = Signal(object, object)  # token, sugestões
    sem_novidades = Signal()
    falhou = Signal(str)

    def __init__(self, responsavel: str = "") -> None:
        super().__init__()
        self._responsavel = responsavel

    @Slot(object)
    def verificar(self, ultimo_token) -> None:
        try:
            with SessionLocal() as session:
                if ultimo_token is not None and leitura.ler_token(session) == ultimo_token:
                    self.sem_novidades.emit()
                    return
                token, sugestoes = leitura.levantar_sugestoes(
                    session, responsavel=self._responsavel or None
                )
        except Exception as erro:  # noqa: BLE001 - rede/SQL/config são externos
            self.falhou.emit(str(erro))
            return
        self.verificado.emit(token, sugestoes)


def ler_vistos(texto: object) -> dict[str, str]:
    try:
        dados = json.loads(str(texto or "{}"))
    except (TypeError, ValueError):
        return {}
    if not isinstance(dados, dict):
        return {}
    return {str(marca): str(valor) for marca, valor in dados.items()}


def juntar_vistos(vistos: dict[str, str], novos: dict[str, str], hoje: date) -> dict[str, str]:
    """Junta, deita fora os adiamentos de dias passados e corta no máximo."""
    resultado = {
        marca: valor
        for marca, valor in vistos.items()
        if valor == regras.VISTO_DE_VEZ or valor >= hoje.isoformat()
    }
    for marca, valor in novos.items():
        resultado.pop(marca, None)
        resultado[marca] = valor
    excesso = len(resultado) - MAXIMO_VISTOS
    if excesso > 0:
        for marca in list(resultado)[:excesso]:
            resultado.pop(marca)
    return resultado


class VerificadorEscritorioStreamlit(QObject):
    """Agenda a pergunta ao Streamlit e trata da conversa com o utilizador."""

    pedir_verificacao = Signal(object)

    #: Depois de gravar estados, para a lista de obras se voltar a carregar.
    estados_atualizados = Signal()

    #: Ids das obras que passaram a Produção (para o email ao cliente).
    obras_em_producao = Signal(list)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        user_id: int | None = None,
        responsavel: str = "",
        ativo: bool = True,
    ) -> None:
        super().__init__(parent)
        self._user_id = user_id
        self._responsavel = (responsavel or "").strip()
        self._ativo = ativo and user_id is not None
        self._a_trabalhar = False
        self._ultimo_token = None
        self._dia_da_volta: date | None = None
        self._ja_falhou = False

        self._thread = QThread(self)
        self._trabalho = _TrabalhoEscritorio(self._responsavel)
        self._trabalho.moveToThread(self._thread)
        self.pedir_verificacao.connect(self._trabalho.verificar)
        self._trabalho.verificado.connect(self._on_verificado)
        self._trabalho.sem_novidades.connect(self._on_sem_novidades)
        self._trabalho.falhou.connect(self._on_falhou)
        self._thread.start()

        aplicacao = QApplication.instance()
        if aplicacao is not None:
            aplicacao.aboutToQuit.connect(self.parar)

        self._relogio = QTimer(self)
        self._relogio.setInterval(INTERVALO_MS)
        self._relogio.timeout.connect(self.verificar)
        if self._ativo:
            self._relogio.start()
            QTimer.singleShot(ATRASO_ARRANQUE_MS, self.verificar)

    # ---- pergunta -----------------------------------------------------------
    @Slot()
    def verificar(self) -> None:
        if not self._ativo or self._a_trabalhar:
            return
        self._a_trabalhar = True
        # Uma volta completa por dia, mesmo sem nada novo no Streamlit: é
        # assim que o «Ver depois» de ontem volta a aparecer hoje.
        hoje = date.today()
        token = self._ultimo_token if self._dia_da_volta == hoje else None
        self._dia_da_volta = hoje
        self.pedir_verificacao.emit(token)

    # ---- vistos -------------------------------------------------------------
    def _vistos(self) -> dict[str, str]:
        try:
            with SessionLocal() as session:
                return ler_vistos(
                    UserPrefService(session).obter_valor(self._user_id, CHAVE_VISTOS)
                )
        except Exception:  # noqa: BLE001 - sem preferências, mostra-se tudo
            return {}

    def _guardar_vistos(self, novos: dict[str, str]) -> None:
        if not novos:
            return
        hoje = date.today()
        try:
            with SessionLocal() as session:
                UserPrefService(session).guardar_valor(
                    self._user_id,
                    CHAVE_VISTOS,
                    json.dumps(juntar_vistos(self._vistos(), novos, hoje)),
                )
        except Exception as erro:  # noqa: BLE001 - não vale a pena falhar por isto
            diario_bordo.registar_erro(f"{TITULO}: não guardou as recusas", str(erro))

    # ---- respostas da thread ------------------------------------------------
    @Slot()
    def _on_sem_novidades(self) -> None:
        self._a_trabalhar = False

    @Slot(object, object)
    def _on_verificado(self, token, sugestoes) -> None:
        self._ja_falhou = False
        self._ultimo_token = token
        hoje = date.today()
        mostrar = regras.por_mostrar(sugestoes or [], self._vistos(), hoje)
        if not mostrar:
            self._a_trabalhar = False
            return

        # Fica «a trabalhar» enquanto a caixa está aberta: o relógio não abre
        # uma segunda por cima da primeira.
        try:
            self._mostrar(mostrar, hoje)
        finally:
            self._a_trabalhar = False

    def _mostrar(self, sugestoes, hoje: date) -> None:
        caixa = ProducaoPhcSyncDialog(
            sugestoes,
            self._janela(),
            automatico=True,
            titulo=TITULO,
            apresentacao=APRESENTACAO,
            dica_ver_depois=DICA_VER_DEPOIS,
        )
        if not caixa.exec():
            self._guardar_vistos({s["marca"]: hoje.isoformat() for s in sugestoes})
            return

        escolhidas = {proc_id for proc_id, _estado in caixa.selecionados()}
        recusadas = {}
        for linha, sugestao in enumerate(sugestoes):
            if sugestao["id"] in escolhidas:
                continue
            # Escondida pelo filtro do responsável: não foi recusada, só não
            # se viu. Volta amanhã.
            escondida = caixa.table.isRowHidden(linha)
            recusadas[sugestao["marca"]] = (
                hoje.isoformat() if escondida else regras.VISTO_DE_VEZ
            )
        self._guardar_vistos(recusadas)
        if not escolhidas:
            return

        try:
            with SessionLocal() as session:
                quantas = aplicar_estados(
                    session,
                    [(proc_id, "Producao") for proc_id in escolhidas],
                    current_user_id=self._user_id,
                )
        except Exception as erro:  # noqa: BLE001 - base de dados
            diario_bordo.registar_erro(f"{TITULO}: não gravou", str(erro))
            QMessageBox.warning(
                self._janela(),
                TITULO,
                "Não consegui gravar os estados no Martelo.\n\n"
                "Mude o Estado à mão no menu Produção.",
            )
            return

        diario_bordo.registar_acao(
            "Aviso do Escritório: obras passadas a Produção", str(quantas)
        )
        self.estados_atualizados.emit()
        QMessageBox.information(
            self._janela(),
            TITULO,
            f"{quantas} obra(s) passada(s) a Produção no Martelo.",
        )
        self.obras_em_producao.emit(sorted(escolhidas))

    @Slot(str)
    def _on_falhou(self, erro: str) -> None:
        self._a_trabalhar = False
        # Em silêncio: corre sozinho e o servidor do Streamlit é um PC que pode
        # estar desligado. Fica no diário uma vez, não de cinco em cinco minutos.
        if not self._ja_falhou:
            diario_bordo.registar_erro(f"{TITULO}: o Streamlit não respondeu", erro)
        self._ja_falhou = True

    def _janela(self) -> QWidget | None:
        pai = self.parent()
        return pai if isinstance(pai, QWidget) else None

    # ---- fim ----------------------------------------------------------------
    @Slot()
    def parar(self) -> None:
        """Parar o relógio e fechar a thread (ao sair da aplicação)."""
        self._ativo = False
        self._relogio.stop()
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
