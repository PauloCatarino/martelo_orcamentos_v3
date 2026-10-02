"""«Abrir no iX CAD» da Produção: perguntas, linha de estado e espera do arranque.

A parte do iMos/Windows está em ``app.services.imos_cad_service``; aqui fica só
o que é da interface. O iX CAD pode demorar mais de um minuto a arrancar, por
isso a espera é feita com um temporizador e o Martelo continua utilizável.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core import diario_bordo
from app.services import imos_cad_service as svc
from app.services.imos_sql import ImosConfig, explicar_erro_ligacao

INTERVALO_ESPERA_MS = 1000
# Depois de pedir a obra, quanto tempo se procura o separador dela no iX CAD.
CONFIRMACAO_S = 45


class AbridorIxCad(QObject):
    """Abre obras no iX CAD a partir de uma página do Martelo."""

    def __init__(self, janela: QWidget, mostrar_estado: Callable[[str], None]) -> None:
        super().__init__(janela)
        self._janela = janela
        self._mostrar_estado = mostrar_estado
        self._plano: svc.PlanoAbertura | None = None
        self._fase = ""
        self._inicio = 0.0
        self._canal_desde = 0.0
        self._temporizador = QTimer(self)
        self._temporizador.setInterval(INTERVALO_ESPERA_MS)
        self._temporizador.timeout.connect(self._tique)

    # ------------------------------------------------------------------
    @property
    def ocupado(self) -> bool:
        return self._temporizador.isActive() and self._fase == "arranque"

    def abrir(
        self,
        *,
        nome: str,
        dir_id: int | None,
        cfg: ImosConfig,
        pasta_imorder_martelo: str | None,
    ) -> None:
        if self.ocupado and self._plano is not None:
            self._mostrar_estado(
                f"O iX CAD ainda está a arrancar; a obra {self._plano.nome} abre "
                "assim que ele estiver pronto."
            )
            return

        instalacao = svc.localizar_instalacao()
        if instalacao is None:
            self._aviso("O iX CAD não está instalado neste PC.")
            return

        self._mostrar_estado("A confirmar a encomenda no iMos…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            plano = svc.preparar_abertura(
                cfg,
                nome,
                dir_id=dir_id,
                pasta_imorder=svc.pasta_imorder_a_usar(instalacao, pasta_imorder_martelo),
            )
        except svc.ErroIxCad as erro:
            QApplication.restoreOverrideCursor()
            self._mostrar_estado(str(erro).split("\n", 1)[0])
            self._aviso(str(erro))
            return
        except ValueError as erro:
            # Nome que o iMos não aceita ou ligação sem utilizador/password:
            # a própria mensagem já diz o que está mal.
            QApplication.restoreOverrideCursor()
            self._mostrar_estado("Não foi possível confirmar a encomenda no iMos.")
            self._aviso(
                "Não foi possível confirmar no iMos que a encomenda existe, por "
                f"isso a obra não foi aberta.\n\n{erro}"
            )
            return
        except (RuntimeError, OSError, subprocess.SubprocessError) as erro:
            QApplication.restoreOverrideCursor()
            texto = (
                "Não foi possível confirmar no iMos que a encomenda existe, por "
                f"isso a obra não foi aberta.\n\n{explicar_erro_ligacao(erro)}"
            )
            self._mostrar_estado("Não foi possível ler o iMos.")
            self._aviso(texto)
            return
        QApplication.restoreOverrideCursor()

        if plano.ja_aberta_neste_pc:
            svc.trazer_para_frente()
            self._mostrar_estado(
                f"A obra {plano.nome} já está aberta no iX CAD: está no separador "
                f"{plano.nome}."
            )
            return

        avisos = plano.avisos()
        if avisos and not self._confirmar(
            "Antes de abrir a obra "
            f"{plano.nome}:\n\n• " + "\n• ".join(avisos) + "\n\nQuer abrir mesmo assim?"
        ):
            self._mostrar_estado(f"A obra {plano.nome} não foi aberta no iX CAD.")
            return

        estado = svc.estado_canal()
        if estado == svc.ESTADO_CANAL_SEM_ACESSO:
            self._aviso(svc.MENSAGEM_ELEVADO)
            self._mostrar_estado("O Martelo não consegue falar com o iX CAD.")
            return
        if estado == svc.ESTADO_CANAL_ATIVO:
            self._pedir(plano)
            return

        # iX CAD fechado: arranca-se como o Organizer e espera-se pelo canal.
        if svc.martelo_elevado():
            self._aviso(svc.MENSAGEM_ELEVADO)
            self._mostrar_estado("O iX CAD não foi aberto.")
            return
        if not self._confirmar(
            "O iX CAD não está aberto.\n\nQuer que o Martelo o abra agora e "
            f"depois abra a obra {plano.nome}? O iX CAD pode demorar um ou dois "
            "minutos a arrancar."
        ):
            self._mostrar_estado(f"A obra {plano.nome} não foi aberta no iX CAD.")
            return
        try:
            svc.arrancar_ix_cad(instalacao)
        except svc.ErroIxCad as erro:
            self._aviso(str(erro))
            self._mostrar_estado("O iX CAD não foi aberto.")
            return
        diario_bordo.registar_acao("Abriu o iX CAD para abrir uma obra", plano.nome)
        self._plano = plano
        self._fase = "arranque"
        self._inicio = time.monotonic()
        self._canal_desde = 0.0
        self._mostrar_estado(
            f"A abrir o iX CAD… a obra {plano.nome} abre assim que ele estiver pronto."
        )
        self._temporizador.start()

    # ------------------------------------------------------------------
    def _pedir(self, plano: svc.PlanoAbertura) -> None:
        """Envia o `imosopendwg` e fica a ver se o separador da obra aparece."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            svc.enviar_comando(plano.comando)
        except svc.ErroIxCad as erro:
            QApplication.restoreOverrideCursor()
            self._aviso(str(erro))
            self._mostrar_estado(f"A obra {plano.nome} não foi aberta no iX CAD.")
            self._temporizador.stop()
            return
        QApplication.restoreOverrideCursor()
        diario_bordo.registar_acao("Abriu a obra no iX CAD", plano.nome)
        svc.trazer_para_frente()
        self._plano = plano
        self._fase = "confirmacao"
        self._inicio = time.monotonic()
        self._mostrar_estado(f"Pedido enviado ao iX CAD: a abrir a obra {plano.nome}…")
        self._temporizador.start()

    def _tique(self) -> None:
        plano = self._plano
        if plano is None:
            self._temporizador.stop()
            return
        decorrido = time.monotonic() - self._inicio

        if self._fase == "arranque":
            if svc.estado_canal() != svc.ESTADO_CANAL_ATIVO:
                self._canal_desde = 0.0
                if decorrido > svc.ESPERA_ARRANQUE_S:
                    self._temporizador.stop()
                    self._plano = None
                    self._mostrar_estado(
                        f"O iX CAD não ficou pronto em {svc.ESPERA_ARRANQUE_S // 60} "
                        f"minutos. Quando estiver aberto, peça outra vez a obra "
                        f"{plano.nome}."
                    )
                return
            if not self._canal_desde:
                self._canal_desde = time.monotonic()
                self._mostrar_estado(
                    f"O iX CAD está quase pronto… a seguir abre a obra {plano.nome}."
                )
                return
            if time.monotonic() - self._canal_desde < svc.ESPERA_DEPOIS_DO_CANAL_S:
                return
            self._temporizador.stop()
            self._pedir(plano)
            return

        # Confirmação: o separador da obra apareceu no iX CAD?
        if f"{plano.nome}.DWG".upper() in svc.desenhos_abertos():
            self._temporizador.stop()
            self._plano = None
            self._mostrar_estado(f"Obra {plano.nome} aberta no iX CAD.")
            return
        if decorrido > CONFIRMACAO_S:
            self._temporizador.stop()
            self._plano = None
            self._mostrar_estado(
                f"O pedido foi enviado ao iX CAD, mas a obra {plano.nome} ainda não "
                "apareceu. Veja no iX CAD se há alguma pergunta à espera."
            )

    # ------------------------------------------------------------------
    def _aviso(self, texto: str) -> None:
        QMessageBox.warning(self._janela, svc.TITULO, texto)

    def _confirmar(self, texto: str) -> bool:
        resposta = QMessageBox.question(
            self._janela,
            svc.TITULO,
            texto,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return resposta == QMessageBox.StandardButton.Yes
