"""«Abrir no iX CAD» da Produção: perguntas, linha de estado e espera do arranque.

A parte do iMos/Windows está em ``app.services.imos_cad_service``; aqui fica só
o que é da interface. O iX CAD pode demorar mais de um minuto a arrancar, por
isso a espera é feita com um temporizador e o Martelo continua utilizável.

Uma encomenda acabada de criar pelo Martelo segue o mesmo caminho, com dois
passos a mais (fase E3): antes, a pasta e o desenho como o Organizer os
prepara; depois de a obra aparecer no iX CAD, a gravação com o `imosqsave`.
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
# Obra nova: depois de aparecer, tempo para o iMos acabar de a carregar antes
# de a gravar, e quanto tempo se espera que o separador dela fique o ativo.
ESPERA_ANTES_DE_GRAVAR_S = 3
ESPERA_SEPARADOR_ATIVO_S = 15
# O desenho novo grava em menos de um segundo (teste de 22-10-2026).
GRAVACAO_S = 60

FASES_OCUPADAS = ("arranque", "gravar", "gravacao")


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
        # Obra nova: depois de aberta, grava-se; guarda-se a data do desenho
        # antes do pedido para ver quando o iX CAD acabou de gravar.
        self._gravar = False
        self._gravado_antes: float | None = None
        self._temporizador = QTimer(self)
        self._temporizador.setInterval(INTERVALO_ESPERA_MS)
        self._temporizador.timeout.connect(self._tique)

    # ------------------------------------------------------------------
    @property
    def ocupado(self) -> bool:
        return self._temporizador.isActive() and self._fase in FASES_OCUPADAS

    def _avisar_ocupado(self) -> bool:
        """Um segundo pedido enquanto o iX CAD arranca ou grava não mexe em nada."""
        if not (self.ocupado and self._plano is not None):
            return False
        if self._fase == "arranque":
            self._mostrar_estado(
                f"O iX CAD ainda está a arrancar; a obra {self._plano.nome} abre "
                "assim que ele estiver pronto."
            )
        else:
            self._mostrar_estado(
                f"O Martelo ainda está a gravar a obra {self._plano.nome} no iX CAD. "
                "Espere um pouco."
            )
        return True

    def abrir_obra_nova(
        self,
        *,
        nome: str,
        dir_id: int | None,
        cfg: ImosConfig,
        pasta_imorder_martelo: str | None,
    ) -> None:
        """Encomenda acabada de criar: prepara o desenho, abre-a e grava-a.

        É o que hoje se faz à mão no Organizer e no iX CAD. Se a obra já tiver
        desenho, não se mexe nele: só se abre, como no «Abrir no iX CAD».
        """
        if self._avisar_ocupado():
            return
        instalacao = svc.localizar_instalacao()
        if instalacao is None:
            self._aviso("O iX CAD não está instalado neste PC.")
            return

        pasta_imorder = svc.pasta_imorder_a_usar(instalacao, pasta_imorder_martelo)
        try:
            copiado = svc.preparar_desenho_novo(
                pasta_imorder, nome, svc.modelo_desenho(instalacao)
            )
        except svc.ErroIxCad as erro:
            self._mostrar_estado(str(erro).split("\n", 1)[0])
            self._aviso(str(erro))
            return
        except OSError as erro:
            self._mostrar_estado("Não foi possível preparar a pasta da obra.")
            self._aviso(
                f"Não foi possível preparar a pasta da obra {nome}:\n{erro}\n\n"
                "Abra-a pelo iX Organizer."
            )
            return
        if copiado:
            diario_bordo.registar_acao(
                f"Preparou o desenho da obra nova ({svc.NOME_MODELO})", nome
            )
        self._abrir(
            nome=nome,
            dir_id=dir_id,
            cfg=cfg,
            instalacao=instalacao,
            pasta_imorder=pasta_imorder,
            gravar=copiado,
        )

    def abrir(
        self,
        *,
        nome: str,
        dir_id: int | None,
        cfg: ImosConfig,
        pasta_imorder_martelo: str | None,
    ) -> None:
        if self._avisar_ocupado():
            return

        instalacao = svc.localizar_instalacao()
        if instalacao is None:
            self._aviso("O iX CAD não está instalado neste PC.")
            return
        self._abrir(
            nome=nome,
            dir_id=dir_id,
            cfg=cfg,
            instalacao=instalacao,
            pasta_imorder=svc.pasta_imorder_a_usar(instalacao, pasta_imorder_martelo),
            gravar=False,
        )

    def _abrir(
        self,
        *,
        nome: str,
        dir_id: int | None,
        cfg: ImosConfig,
        instalacao: svc.InstalacaoIxCad,
        pasta_imorder: str,
        gravar: bool,
    ) -> None:
        self._gravar = gravar

        self._mostrar_estado("A confirmar a encomenda no iMos…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            plano = svc.preparar_abertura(
                cfg,
                nome,
                dir_id=dir_id,
                pasta_imorder=pasta_imorder,
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
            if self._gravar:
                # Obra nova: como o `LoadOrderInAcad` do Organizer, sem o aviso
                # de carregamento do iMos (foi assim que se testou a 22-10).
                svc.enviar_comando(
                    svc.COMANDO_SEM_AVISO_CARREGAR, esperar_s=svc.ESPERA_CANAL_LIVRE_S
                )
                time.sleep(svc.PAUSA_DEPOIS_SEM_AVISO_S)
                svc.enviar_comando(plano.comando, esperar_s=svc.ESPERA_CANAL_LIVRE_S)
            else:
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

        if self._fase == "gravar":
            self._tique_gravar(plano, decorrido)
            return
        if self._fase == "gravacao":
            self._tique_gravacao(plano, decorrido)
            return

        # Confirmação: o separador da obra apareceu no iX CAD?
        if f"{plano.nome}.DWG".upper() in svc.desenhos_abertos():
            if self._gravar:
                self._fase = "gravar"
                self._inicio = time.monotonic()
                self._mostrar_estado(f"Obra {plano.nome} aberta no iX CAD; a seguir é gravada…")
                return
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

    def _tique_gravar(self, plano: svc.PlanoAbertura, decorrido: float) -> None:
        """Obra nova aberta: pede a gravação, mas só se for o separador ativo.

        O `imosqsave` grava o desenho ativo; se entretanto o utilizador mudou
        de separador, gravava a obra errada — aí não se pede nada.
        """
        if decorrido < ESPERA_ANTES_DE_GRAVAR_S:
            return
        if svc.desenho_ativo() != f"{plano.nome}.DWG".upper():
            if decorrido > ESPERA_ANTES_DE_GRAVAR_S + ESPERA_SEPARADOR_ATIVO_S:
                self._parar(
                    f"Obra {plano.nome} aberta no iX CAD, mas não foi gravada: o "
                    "separador ativo é outro. Grave-a no iX CAD."
                )
            return
        self._gravado_antes = svc.momento_gravacao(plano.desenho)
        try:
            svc.enviar_comando(svc.COMANDO_GRAVAR, esperar_s=svc.ESPERA_CANAL_LIVRE_S)
        except svc.ErroIxCad as erro:
            razao = str(erro).split("\n", 1)[0]
            self._parar(
                f"Obra {plano.nome} aberta no iX CAD, mas não foi possível pedir a "
                f"gravação ({razao}). Grave-a no iX CAD."
            )
            return
        self._fase = "gravacao"
        self._inicio = time.monotonic()
        self._mostrar_estado(f"A gravar a obra {plano.nome} no iX CAD…")

    def _tique_gravacao(self, plano: svc.PlanoAbertura, decorrido: float) -> None:
        """A gravação acabou quando a data do desenho muda."""
        gravado = svc.momento_gravacao(plano.desenho)
        if gravado is not None and gravado != self._gravado_antes:
            diario_bordo.registar_acao("Abriu e gravou a obra nova no iX CAD", plano.nome)
            self._parar(f"Obra {plano.nome} aberta e gravada no iX CAD: pode desenhar.")
            return
        if decorrido > GRAVACAO_S:
            self._parar(
                f"Foi pedido ao iX CAD que gravasse a obra {plano.nome}, mas o desenho "
                "ainda não foi gravado. Veja no iX CAD se há alguma pergunta à "
                "espera e grave-a lá."
            )

    def _parar(self, estado: str) -> None:
        self._temporizador.stop()
        self._plano = None
        self._gravar = False
        self._mostrar_estado(estado)

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
