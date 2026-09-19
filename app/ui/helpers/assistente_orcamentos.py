"""Assistente dos Orçamentos: relógio das 8h30 e as ações da janela.

Só existe para quem tem o acesso «Assistente dos Orçamentos». Todos os dias
úteis, a partir das 8h30 (ou quando o Martelo abrir depois disso), abre a
janela do assistente **se** houver orçamentos da pessoa parados; se não
houver, não incomoda. A consulta é à base do Martelo (rápida): não precisa de
thread própria, ao contrário dos avisos do PHC.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtWidgets import QMessageBox, QWidget

from app.core.session import app_session
from app.core import diario_bordo
from app.db.session import SessionLocal
from app.domain import assistente_orcamentos as regra
from app.domain.clientes_emails import emails_envio_orcamentos
from app.domain.export_paths import subpasta_versao
from app.services.assistente_orcamentos_service import AssistenteOrcamentosService
from app.services.email_resposta_service import procurar_emails_do_cliente
from app.services.email_service import (
    carregar_email_config,
    enviar_email,
    get_email_log_path,
)
from app.services.orcamento_export_service import OrcamentoExportService
from app.services.orcamento_historico_service import OrcamentoHistoricoService
from app.ui.dialogs.assistente_orcamentos_dialog import AssistenteOrcamentosDialog
from app.ui.dialogs.email_orcamento_dialog import EmailOrcamentoDialog

#: O relógio só pergunta «já são horas?»; o resumo é uma vez por dia.
INTERVALO_RELOGIO_MS = 10 * 60 * 1000
#: Antes dos avisos do PHC (60 s), para não abrirem duas janelas ao mesmo tempo.
ATRASO_ARRANQUE_MS = 30 * 1000


class AssistenteOrcamentos(QObject):
    def __init__(
        self,
        janela: QWidget,
        *,
        user_id: int | None,
        nome: str = "",
        ativo: bool = False,
        pagina_orcamentos=None,
        mostrar_pagina=None,
    ) -> None:
        super().__init__(janela)
        self._janela = janela
        self._user_id = user_id
        self._nome = nome
        self._ativo = bool(ativo and user_id is not None)
        self._pagina = pagina_orcamentos
        self._mostrar_pagina = mostrar_pagina
        self._dialogo: AssistenteOrcamentosDialog | None = None

        self._relogio = QTimer(self)
        self._relogio.setInterval(INTERVALO_RELOGIO_MS)
        self._relogio.timeout.connect(self.verificar_se_e_hora)
        if self._ativo:
            self._relogio.start()
            QTimer.singleShot(ATRASO_ARRANQUE_MS, self.verificar_se_e_hora)

    @property
    def ativo(self) -> bool:
        return self._ativo

    # ---- agenda ----------------------------------------------------------
    @Slot()
    def verificar_se_e_hora(self) -> None:
        if not self._ativo:
            return
        agora = datetime.now()
        try:
            with SessionLocal() as session:
                servico = AssistenteOrcamentosService(session)
                if not regra.deve_mostrar(agora, servico.ultimo_resumo(self._user_id)):
                    return
                # Marca-se já: um erro não se repete de dez em dez minutos.
                servico.marcar_resumo(self._user_id, agora.date())
                resumo = servico.resumo(self._user_id, agora.date())
        except Exception as erro:  # noqa: BLE001 - base em baixo não pode parar o Martelo
            diario_bordo.registar_erro(f"Assistente dos Orçamentos: {erro}")
            return
        diario_bordo.registar_acao(
            "Assistente dos Orçamentos — resumo diário", f"{resumo.total} lembrete(s)"
        )
        if not resumo.vazio:
            self.abrir(automatico=True)

    def abrir(self, *, automatico: bool = False) -> None:
        if not self._ativo:
            return
        if self._dialogo is not None and self._dialogo.isVisible():
            self._dialogo.recarregar()
            self._dialogo.raise_()
            self._dialogo.activateWindow()
            return
        self._dialogo = AssistenteOrcamentosDialog(
            self, nome=self._nome, automatico=automatico, parent=self._janela
        )
        self._dialogo.show()

    # ---- ações pedidas pela janela --------------------------------------
    def resumo(self) -> regra.ResumoDiario:
        try:
            with SessionLocal() as session:
                return AssistenteOrcamentosService(session).resumo(self._user_id)
        except Exception as erro:  # noqa: BLE001
            diario_bordo.registar_erro(f"Assistente dos Orçamentos: {erro}")
            return regra.ResumoDiario()

    def adiar(self, versao_id: int) -> date | None:
        try:
            with SessionLocal() as session:
                return AssistenteOrcamentosService(session).adiar(self._user_id, versao_id)
        except Exception as erro:  # noqa: BLE001
            diario_bordo.registar_erro(f"Assistente dos Orçamentos (adiar): {erro}")
            return None

    def ver_na_lista(self, versao_id: int) -> bool:
        if self._pagina is None:
            return False
        if self._mostrar_pagina is not None:
            self._mostrar_pagina("orcamentos")
        return bool(self._pagina.mostrar_versao(versao_id))

    def mudar_estado(self, versao_id: int, estado: str) -> None:
        """Usa o seletor da lista: Adjudicado abre o Editar Orçamento, como lá."""
        if not self.ver_na_lista(versao_id):
            return
        diario_bordo.registar_acao(
            "Assistente dos Orçamentos — mudar estado", f"versão {versao_id} -> {estado}"
        )
        self._pagina.mudar_estado(self._pagina.table.currentRow(), estado)

    def email_seguimento(self, lembrete: regra.Lembrete) -> bool:
        diario_bordo.registar_acao(
            "Assistente dos Orçamentos — email de seguimento", lembrete.codigo
        )
        return preparar_email_seguimento(self._dialogo or self._janela, lembrete)


def preparar_email_seguimento(parent: QWidget, lembrete: regra.Lembrete) -> bool:
    """Abre o email de seguimento pronto a rever; só envia com «Enviar»."""
    try:
        with SessionLocal() as session:
            export = OrcamentoExportService(session)
            orcamento = export.orcamento_service.get_orcamento_by_versao_id(
                lembrete.versao_id
            )
            cliente = export.orcamento_service.get_cliente_da_versao(lembrete.versao_id)
            config = carregar_email_config(session)
            pasta = export.resolver_pasta_versao(lembrete.versao_id, criar=False)
    except Exception as erro:  # noqa: BLE001
        QMessageBox.critical(parent, "Email de seguimento", f"Não foi possível preparar o email:\n{erro}")
        return False
    if orcamento is None or cliente is None:
        QMessageBox.warning(parent, "Email de seguimento", "Orçamento ou cliente não encontrado.")
        return False

    versao = subpasta_versao(orcamento.numero_versao)
    anexos: list[str] = []
    emails_do_cliente: list[str] = []
    pasta_inicial = str(Path.home())
    if pasta is not None and Path(pasta).exists():
        pasta_inicial = str(pasta)
        # O PDF que seguiu da primeira vez, para o cliente não ter de o procurar.
        pdf = Path(pasta) / f"{orcamento.num_orcamento}_{versao}.pdf"
        if pdf.exists():
            anexos.append(str(pdf))
        if (config.metodo or "outlook").lower() == "outlook":
            emails_do_cliente = [
                str(caminho)
                for caminho in procurar_emails_do_cliente(Path(pasta), Path(pasta).parent)
            ]

    user = app_session.current_user
    remetente_email = getattr(user, "email", None)
    remetente_nome = getattr(user, "nome", None) or getattr(user, "username", None)
    dialogo = EmailOrcamentoDialog(
        parent,
        destinatario=emails_envio_orcamentos(cliente),
        cc=str(remetente_email or ""),
        assunto=regra.assunto_email_seguimento(
            orcamento.num_orcamento, versao, orcamento.obra or ""
        ),
        corpo=regra.corpo_email_seguimento(
            cliente=getattr(cliente, "nome", "") or "",
            num_orcamento=orcamento.num_orcamento,
            versao=versao,
            obra=orcamento.obra or "",
            ref_cliente=orcamento.ref_cliente or "",
            enviado_em=lembrete.enviado_em or lembrete.desde,
        ),
        anexos=anexos,
        pasta_inicial=pasta_inicial,
        tamanho_max_mb=config.tamanho_max_mb,
        emails_do_cliente=emails_do_cliente,
    )
    dialogo.setWindowTitle(f"Email de seguimento — orçamento {lembrete.codigo}")
    if not dialogo.exec():
        return False
    if not dialogo.destinatario():
        QMessageBox.warning(parent, "Email de seguimento", "Indique o destinatário antes de enviar.")
        return False
    try:
        enviar_email(
            dialogo.destinatario(),
            dialogo.assunto(),
            dialogo.corpo_html(),
            dialogo.anexos(),
            config=config,
            remetente_email=remetente_email,
            remetente_nome=remetente_nome,
            cc=dialogo.cc(),
            responder_a=dialogo.responder_a(),
        )
    except Exception as erro:  # noqa: BLE001
        QMessageBox.critical(
            parent,
            "Email de seguimento",
            f"Falha ao enviar o email:\n{erro}\n\nLog: {get_email_log_path()}",
        )
        return False
    try:
        with SessionLocal() as session:
            # Fica no histórico e recomeça a contagem dos 30 dias.
            OrcamentoHistoricoService(session).registar(
                lembrete.versao_id,
                "email",
                f"Email de seguimento enviado para {dialogo.destinatario()}",
            )
            session.commit()
    except Exception as erro:  # noqa: BLE001
        QMessageBox.warning(
            parent,
            "Email de seguimento",
            f"Email enviado, mas não foi possível registar no histórico:\n{erro}",
        )
    return True
