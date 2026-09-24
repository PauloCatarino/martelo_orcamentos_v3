"""Contador do tempo ativo no iMos e na Lista Material (Excel).

Irmão do ``OrcamentoTempoTracker``, mas olha para janelas de OUTROS
programas: a cada 5 s vê qual é a janela da frente e há quanto tempo ninguém
mexe no rato ou no teclado. Conta só quando é o iMos ou uma Lista_Material e
houve atividade nos últimos 5 minutos — obras abertas e paradas, o PC
bloqueado ou a hora de almoço não contam.

Só funciona com o Martelo aberto nesse PC (minimizado serve). É uma medida do
tempo que uma obra leva em desenho e na passagem à produção, não um controlo
das pessoas; só o administrador a vê.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from time import monotonic

from PySide6.QtCore import QObject, QTimer

from app.core import diario_bordo
from app.core.janela_ativa import JanelaAtiva, ler_janela_ativa
from app.db.session import SessionLocal
from app.domain.tempo_atividade import incremento_tempo_ativo
from app.domain.tempo_programas import (
    LIMITE_INATIVIDADE_SEGUNDOS,
    identificar_janela,
)
from app.services.producao_tempo_atividade_service import (
    ProducaoTempoAtividadeService,
)

logger = logging.getLogger(__name__)

#: Quantos títulos por reconhecer se escrevem no diário por sessão.
_MAX_TITULOS_NO_DIARIO = 5


class TempoProgramasTracker(QObject):
    INTERVALO_TICK_MS = 5_000
    INTERVALO_GRAVACAO_SEGUNDOS = 60

    def __init__(
        self,
        parent: QObject | None,
        *,
        user_id: int | None,
        leitor=ler_janela_ativa,
        relogio=monotonic,
        hoje=date.today,
        iniciar: bool = True,
    ) -> None:
        super().__init__(parent)
        self._user_id = int(user_id) if user_id else None
        self._leitor = leitor
        self._relogio = relogio
        self._hoje = hoje
        self._ultimo_tick = relogio()
        self._desde_gravacao = 0.0
        #: (programa, encomenda, dia) → segundos ainda por gravar
        self._pendentes: dict[tuple[str, str, date], float] = defaultdict(float)
        self._titulos_vistos: set[str] = set()
        self._falha_anotada = False

        self._timer = QTimer(self)
        self._timer.setInterval(self.INTERVALO_TICK_MS)
        self._timer.timeout.connect(self._tick)
        if iniciar and self._user_id is not None:
            self._timer.start()

    def _tick(self) -> None:
        agora = self._relogio()
        intervalo = agora - self._ultimo_tick
        janela = self._ler()
        identificada = (
            identificar_janela(janela.processo, janela.titulo) if janela else None
        )
        incremento = incremento_tempo_ativo(
            agora=agora,
            ultimo_tick=self._ultimo_tick,
            ultima_atividade=(agora - janela.segundos_parado) if janela else None,
            contexto_ativo=identificada is not None and self._user_id is not None,
            aplicacao_ativa=True,
            limite_inatividade=LIMITE_INATIVIDADE_SEGUNDOS,
        )
        self._ultimo_tick = agora
        if identificada is not None and incremento > 0:
            chave = (identificada.programa, identificada.nome_encomenda, self._hoje())
            self._pendentes[chave] += incremento
        elif janela is not None and identificada is None:
            self._anotar_titulo_por_reconhecer(janela)

        self._desde_gravacao += max(0.0, intervalo)
        if self._desde_gravacao >= self.INTERVALO_GRAVACAO_SEGUNDOS:
            self._gravar_pendentes()

    def _ler(self) -> JanelaAtiva | None:
        try:
            return self._leitor()
        except Exception:  # noqa: BLE001 - nunca partir o Martelo por isto
            return None

    def _anotar_titulo_por_reconhecer(self, janela: JanelaAtiva) -> None:
        """Um desenho do iMos que não deu obra fica no diário (poucas vezes).

        É o sinal de que uma versão nova do iMos mudou o título da janela e a
        medição parou — sem isto, ninguém dava por nada.
        """
        if janela.processo != "imos.exe" or ".dwg" not in janela.titulo.lower():
            return
        if len(self._titulos_vistos) >= _MAX_TITULOS_NO_DIARIO:
            return
        if janela.titulo in self._titulos_vistos:
            return
        self._titulos_vistos.add(janela.titulo)
        diario_bordo.registar_acao(
            "Tempo de desenho: desenho do iMos sem obra reconhecida",
            janela.titulo,
        )

    def _gravar_pendentes(self) -> None:
        self._desde_gravacao = 0.0
        a_gravar = {
            chave: int(segundos)
            for chave, segundos in self._pendentes.items()
            if int(segundos) > 0
        }
        if not a_gravar or self._user_id is None:
            return
        try:
            with SessionLocal() as session:
                servico = ProducaoTempoAtividadeService(session)
                for (programa, nome, dia), segundos in a_gravar.items():
                    servico.adicionar_segundos(
                        self._user_id, programa, nome, dia, segundos
                    )
                session.commit()
        except Exception:  # noqa: BLE001 - fica para a próxima gravação
            # Uma vez por sessão: se a tabela ainda não existir nesta base (a
            # migração por aplicar), o diário não leva um erro por minuto.
            if not self._falha_anotada:
                self._falha_anotada = True
                logger.exception("Não foi possível gravar o tempo no iMos/Excel")
            return
        for chave, segundos in a_gravar.items():
            self._pendentes[chave] -= segundos
            if self._pendentes[chave] < 1:
                del self._pendentes[chave]

    def encerrar(self) -> None:
        """Gravar o que falta e parar (ao fechar ou mudar de utilizador)."""
        self._timer.stop()
        self._tick()
        self._gravar_pendentes()
