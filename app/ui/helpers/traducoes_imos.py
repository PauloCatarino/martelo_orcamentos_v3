"""Traduções do iX: onde estão os ficheiros e o aviso ao entrar no Martelo.

* O ``imos.msg`` é de cada PC: encontra-se sozinho (iX mais recente); quem o
  tiver noutro sítio escolhe-o e a escolha fica neste PC (``QSettings``).
* O Excel é igual para todos: fica nas Configurações gerais
  (``system_settings``); só o administrador o muda.
* O aviso (aprovado pelo Paulo a 10-10-2026): uma vez por dia e por PC, nos
  dias úteis, alguns minutos depois de abrir o Martelo, se este PC tiver
  traduções por aplicar — porque o Excel ganhou linhas novas, ou porque o iX
  foi reinstalado/atualizado e voltou aos textos de fábrica. Só pergunta: o
  ficheiro nunca é alterado sem a pessoa carregar em «Aplicar traduções».
  Cada pessoa pode desligá-lo na própria aba (fica na conta dela).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core import diario_bordo
from app.domain import agenda_diaria_phc
from app.services import imos_traducoes_service as servico

_ORG = "Lanca Encanto"
_APP = "Martelo Orcamentos V3"
CHAVE_CAMINHO_MSG = "imos_ix/caminho_imos_msg"
CHAVE_ULTIMO_AVISO = "imos_ix/ultimo_aviso_traducoes"
#: Preferência de cada pessoa: «1» avisa, «0» não.
PREF_AVISO = "imos_ix.aviso_traducoes"

TITULO_AVISO = "Traduções do iX por aplicar"
#: Depois dos outros avisos do arranque (PHC aos 30 s e 60 s, versão nova aos
#: 2 min), para as caixas não aparecerem umas em cima das outras.
ATRASO_ARRANQUE_MS = 3 * 60 * 1000
INTERVALO_RELOGIO_MS = 10 * 60 * 1000
HORA_AVISO = time(8, 0)


# --------------------------------------------------------------------------
# Caminhos
# --------------------------------------------------------------------------


def caminho_escolhido_neste_pc() -> str:
    try:
        return str(QSettings(_ORG, _APP).value(CHAVE_CAMINHO_MSG) or "").strip()
    except Exception:  # noqa: BLE001 - sem registo, procura-se sozinho
        return ""


def guardar_caminho_neste_pc(caminho: str) -> None:
    try:
        QSettings(_ORG, _APP).setValue(CHAVE_CAMINHO_MSG, caminho or "")
    except Exception:  # noqa: BLE001 - fica a procura automática
        pass


def caminho_imos_msg(
    *,
    escolhido: Callable[[], str] = caminho_escolhido_neste_pc,
    localizar: Callable[[], Path | None] = servico.localizar_imos_msg,
) -> tuple[Path | None, bool]:
    """(ficheiro, escolhido à mão?). Um caminho escolhido que já não existe é ignorado."""
    manual = escolhido()
    if manual and Path(manual).is_file():
        return Path(manual), True
    return localizar(), False


def caminho_excel(session) -> str:
    from app.services.system_setting_service import SystemSettingService

    valor = SystemSettingService(session).obter_valor(servico.CHAVE_EXCEL, "") or ""
    return valor.strip() or servico.EXCEL_PADRAO


def aviso_ligado(session, user_id: int | None) -> bool:
    if user_id is None:
        return False
    from app.services.user_pref_service import UserPrefService

    return (UserPrefService(session).obter_valor(user_id, PREF_AVISO, "1") or "1") != "0"


# --------------------------------------------------------------------------
# Aviso ao entrar
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class EstadoAviso:
    por_aplicar: int = 0
    versao: str = ""
    #: Porque não se conseguiu ver (sem iX, sem I:...): vai só para o diário.
    problema: str = ""
    ligado: bool = True


def ler_estado_aviso(user_id: int | None) -> EstadoAviso:
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        if not aviso_ligado(session, user_id):
            return EstadoAviso(ligado=False)
        excel = caminho_excel(session)
    msg, _manual = caminho_imos_msg()
    if msg is None:
        return EstadoAviso(problema="O iX CAD não está instalado neste PC.")
    try:
        lista = servico.ler_excel(excel)
        estados = servico.comparar(msg, lista)
    except servico.ErroTraducoes as erro:
        return EstadoAviso(problema=str(erro))
    return EstadoAviso(
        por_aplicar=servico.contar_por_aplicar(estados),
        versao=servico.versao_do_caminho(msg),
    )


def ler_ultimo_aviso() -> date | None:
    try:
        valor = QSettings(_ORG, _APP).value(CHAVE_ULTIMO_AVISO)
    except Exception:  # noqa: BLE001
        return None
    return agenda_diaria_phc.ler_data(str(valor) if valor else None)


def guardar_ultimo_aviso(dia: date) -> None:
    try:
        QSettings(_ORG, _APP).setValue(CHAVE_ULTIMO_AVISO, agenda_diaria_phc.escrever_data(dia))
    except Exception:  # noqa: BLE001
        pass


def perguntar_abrir(parent: QWidget | None, estado: EstadoAviso) -> bool:
    """A caixa do aviso. True = «Abrir IMOS IX»."""
    caixa = QMessageBox(parent)
    caixa.setIcon(QMessageBox.Icon.Information)
    caixa.setWindowTitle(TITULO_AVISO)
    versao = f" ({estado.versao})" if estado.versao else ""
    caixa.setText(
        f"O iX CAD deste PC{versao} tem {estado.por_aplicar} "
        f"{'texto' if estado.por_aplicar == 1 else 'textos'} diferente(s) do Excel "
        "das traduções da empresa."
    )
    caixa.setInformativeText(
        "Acontece quando se acrescentam linhas ao Excel ou quando o iX é "
        "reinstalado ou atualizado.\n\n«Abrir IMOS IX» leva-o ao menu, onde vê "
        "o que muda e aplica (é preciso fechar o iX CAD e o Organizer). Nada é "
        "alterado sem carregar em «Aplicar traduções».\n\n«Mais tarde»: volto a "
        "lembrar amanhã. Pode desligar este aviso no menu IMOS IX."
    )
    abrir = caixa.addButton("Abrir IMOS IX", QMessageBox.ButtonRole.AcceptRole)
    abrir.setToolTip("Ir ao menu IMOS IX › Traduções do iX")
    depois = caixa.addButton("Mais tarde", QMessageBox.ButtonRole.RejectRole)
    depois.setToolTip("Continuar a trabalhar; o aviso volta amanhã")
    # A caixa aparece sozinha: um Enter de quem estava a escrever não a aceita.
    caixa.setDefaultButton(depois)
    caixa.setEscapeButton(depois)
    caixa.exec()
    return caixa.clickedButton() is abrir


class _TrabalhoAviso(QObject):
    lido = Signal(object)
    falhou = Signal(str)

    def __init__(self, ler: Callable[[], EstadoAviso]) -> None:
        super().__init__()
        self._ler = ler

    @Slot()
    def ler(self) -> None:
        try:
            estado = self._ler()
        except Exception as erro:  # noqa: BLE001 - rede/base são externas
            self.falhou.emit(str(erro))
            return
        self.lido.emit(estado)


class AvisoTraducoesImos(QObject):
    """Agenda a verificação diária e mostra o aviso quando há traduções por aplicar."""

    pedir_leitura = Signal()

    def __init__(
        self,
        janela: QWidget | None = None,
        *,
        ativo: bool,
        user_id: int | None,
        abrir_menu: Callable[[], None],
        ler_estado: Callable[[], EstadoAviso] | None = None,
        perguntar: Callable[[QWidget | None, EstadoAviso], bool] = perguntar_abrir,
        ler_ultimo: Callable[[], date | None] = ler_ultimo_aviso,
        guardar_ultimo: Callable[[date], None] = guardar_ultimo_aviso,
        agora: Callable[[], datetime] = datetime.now,
    ) -> None:
        super().__init__(janela)
        self.ativo = bool(ativo)
        self._janela = janela
        self._abrir_menu = abrir_menu
        self._perguntar = perguntar
        self._ler_ultimo = ler_ultimo
        self._guardar_ultimo = guardar_ultimo
        self._agora = agora
        self._a_ler = False

        self._thread = QThread(self)
        self._trabalho = _TrabalhoAviso(ler_estado or (lambda: ler_estado_aviso(user_id)))
        self._trabalho.moveToThread(self._thread)
        self.pedir_leitura.connect(self._trabalho.ler)
        self._trabalho.lido.connect(self._ao_ler)
        self._trabalho.falhou.connect(self._ao_falhar)

        self._relogio = QTimer(self)
        self._relogio.setInterval(INTERVALO_RELOGIO_MS)
        self._relogio.timeout.connect(self.verificar_se_e_hora)
        if self.ativo:
            self._thread.start()
            aplicacao = QApplication.instance()
            if aplicacao is not None:
                aplicacao.aboutToQuit.connect(self.parar)
            self._relogio.start()
            QTimer.singleShot(ATRASO_ARRANQUE_MS, self.verificar_se_e_hora)

    @Slot()
    def verificar_se_e_hora(self) -> None:
        if not self.ativo or self._a_ler:
            return
        if not agenda_diaria_phc.deve_verificar(self._agora(), self._ler_ultimo(), hora=HORA_AVISO):
            return
        if QApplication.activeModalWidget() is not None:
            return  # há outra caixa aberta: tenta-se no próximo toque
        self._a_ler = True
        self.pedir_leitura.emit()

    @Slot(object)
    def _ao_ler(self, estado: EstadoAviso) -> None:
        self._a_ler = False
        self._guardar_ultimo(self._agora().date())
        if not estado.ligado:
            return
        if estado.problema:
            diario_bordo.registar_aviso(TITULO_AVISO, estado.problema)
            return
        if estado.por_aplicar <= 0:
            return
        diario_bordo.registar_acao(TITULO_AVISO, f"{estado.por_aplicar} por aplicar")
        if self._perguntar(self._janela, estado):
            self._abrir_menu()

    @Slot(str)
    def _ao_falhar(self, erro: str) -> None:
        self._a_ler = False
        self._guardar_ultimo(self._agora().date())
        diario_bordo.registar_erro(f"{TITULO_AVISO}: não foi possível verificar", erro)

    @Slot()
    def parar(self) -> None:
        self._relogio.stop()
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
