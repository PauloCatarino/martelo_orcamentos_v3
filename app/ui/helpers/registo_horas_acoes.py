"""Ações do Registo de Horas usadas pela página e pelos avisos automáticos.

Gerar a folha do mês em PDF e enviá-la à contabilidade (depois de a pessoa
confirmar no diálogo). Ficam aqui para o botão da página e o aviso do dia 2
fazerem exatamente o mesmo.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core import diario_bordo
from app.db.session import SessionLocal
from app.domain import registo_horas as regra
from app.services.email_service import carregar_email_config, enviar_email, get_email_log_path
from app.services.registo_horas_pdf import gerar_folha_pdf
from app.services.registo_horas_service import RegistoHorasService
from app.services.system_setting_service import SystemSettingService
from app.ui.dialogs.registo_horas_definicoes_dialog import pasta_pdf_padrao
from app.ui.dialogs.registo_horas_envio_dialog import (
    ACAO_ENVIAR,
    RegistoHorasEnvioDialog,
)

TITULO = "Registo de Horas"
#: O mesmo logótipo dos PDFs dos orçamentos.
LOGO = "LE_Logotipo.png"


def pasta_folhas(config: regra.ConfigHoras) -> Path:
    return Path(config.pasta_pdf) if config.pasta_pdf else pasta_pdf_padrao()


def nome_na_folha(config: regra.ConfigHoras, nome_conta: str) -> str:
    return config.nome_folha or nome_conta or "Colaborador"


def _caminho_logo(session) -> Path | None:
    pasta = SystemSettingService(session).obter_valor("pasta_base_dados_orcamento")
    if not pasta:
        return None
    caminho = Path(pasta) / LOGO
    try:
        return caminho if caminho.is_file() else None
    except OSError:  # servidor fora de alcance: a folha sai sem logótipo
        return None


def em_falta_no_mes(
    servico: RegistoHorasService,
    user_id: int,
    ano: int,
    mes: int,
    config: regra.ConfigHoras,
    hoje: date,
) -> list[date]:
    """Dias úteis do mês sem registo (só no registo oficial e até ontem)."""
    dias = regra.dias_do_mes(ano, mes)
    desde = max(dias[0], config.inicio_registo)
    ate = min(date.fromordinal(dias[-1].toordinal() + 1), hoje)
    if desde >= ate:
        return []
    feitos = servico.datas_registadas(user_id, desde, ate)
    return regra.dias_em_falta(feitos, desde=desde, ate=ate)


def gerar_folha(
    user_id: int, nome_conta: str, ano: int, mes: int, *, hoje: date | None = None
) -> Path:
    """Escreve a folha do mês na pasta das folhas e devolve o caminho."""
    hoje = hoje or date.today()
    with SessionLocal() as session:
        servico = RegistoHorasService(session)
        config = servico.config(user_id)
        dias = servico.listar_mes(user_id, ano, mes)
        em_falta = em_falta_no_mes(servico, user_id, ano, mes, config, hoje)
        logo = _caminho_logo(session)
    nome = nome_na_folha(config, nome_conta)
    pasta = pasta_folhas(config)
    destino = pasta / regra.nome_ficheiro_folha(nome, ano, mes)
    try:
        return gerar_folha_pdf(
            destino, nome=nome, ano=ano, mes=mes, dias=dias, em_falta=em_falta, logo=logo
        )
    except PermissionError:
        # A folha anterior está aberta no leitor de PDF: escreve-se ao lado.
        alternativo = destino.with_name(f"{destino.stem}_{datetime.now():%H%M%S}.pdf")
        return gerar_folha_pdf(
            alternativo, nome=nome, ano=ano, mes=mes, dias=dias, em_falta=em_falta, logo=logo
        )


def abrir_ficheiro(caminho: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(caminho)))


def enviar_mes(
    parent: QWidget,
    *,
    user_id: int,
    nome_conta: str,
    email_conta: str,
    ano: int,
    mes: int,
    automatico: bool = False,
) -> str | None:
    """Mostra o mês, e envia-o se a pessoa confirmar. Devolve a ação escolhida."""
    hoje = date.today()
    try:
        with SessionLocal() as session:
            servico = RegistoHorasService(session)
            config = servico.config(user_id)
            dias = servico.listar_mes(user_id, ano, mes)
            em_falta = em_falta_no_mes(servico, user_id, ano, mes, config, hoje)
            ja_enviado = servico.ultimo_envio(user_id, ano, mes)
            destinatario = servico.email_contabilidade()
    except Exception as erro:  # noqa: BLE001
        diario_bordo.registar_erro(f"Registo de Horas (envio): {erro}")
        QMessageBox.warning(parent, TITULO, f"Não foi possível ler as horas do mês:\n{erro}")
        return None
    nome = nome_na_folha(config, nome_conta)

    def _ver_pdf() -> None:
        try:
            abrir_ficheiro(gerar_folha(user_id, nome_conta, ano, mes, hoje=hoje))
        except Exception as erro:  # noqa: BLE001
            QMessageBox.warning(parent, TITULO, f"Não foi possível gerar a folha:\n{erro}")

    dialogo = RegistoHorasEnvioDialog(
        parent,
        nome=nome,
        ano=ano,
        mes=mes,
        dias=dias,
        em_falta=em_falta,
        destinatario=destinatario,
        ja_enviado=ja_enviado,
        automatico=automatico,
        ver_pdf=_ver_pdf,
    )
    dialogo.exec()
    acao = dialogo.acao
    if acao != ACAO_ENVIAR:
        diario_bordo.registar_acao(
            "Registo de Horas — envio do mês", f"{ano}-{mes:02d}: {acao or 'cancelado'}"
        )
        return acao

    destino = dialogo.destinatario()
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        folha = gerar_folha(user_id, nome_conta, ano, mes, hoje=hoje)
        with SessionLocal() as session:
            # A cópia geral dos orçamentos (email_copia) não deve receber horas
            # de ninguém: segue só para a contabilidade e para o próprio.
            config_email = replace(carregar_email_config(session), copia="")
        enviar_email(
            destino,
            dialogo.assunto(),
            dialogo.mensagem_html(),
            [str(folha)],
            config=config_email,
            remetente_email=email_conta or None,
            remetente_nome=nome,
        )
    except Exception as erro:  # noqa: BLE001
        QApplication.restoreOverrideCursor()
        diario_bordo.registar_erro(f"Registo de Horas: falha ao enviar {ano}-{mes:02d}: {erro}")
        QMessageBox.critical(
            parent,
            TITULO,
            f"O email não foi enviado:\n{erro}\n\nLog: {get_email_log_path()}",
        )
        return None
    QApplication.restoreOverrideCursor()
    try:
        with SessionLocal() as session:
            RegistoHorasService(session).registar_envio(
                user_id,
                ano,
                mes,
                destinatario=destino,
                resumo=regra.resumir_mes(dias),
                ficheiro=str(folha),
            )
    except Exception as erro:  # noqa: BLE001
        QMessageBox.warning(
            parent,
            TITULO,
            "O email seguiu, mas não foi possível registar o envio no Martelo "
            f"(o aviso do mês pode voltar a aparecer):\n{erro}",
        )
    diario_bordo.registar_acao("Registo de Horas — mês enviado", f"{ano}-{mes:02d} para {destino}")
    QMessageBox.information(
        parent,
        TITULO,
        f"As horas de {regra.nome_mes(ano, mes)} seguiram para {destino}.\n\n"
        f"A folha ficou guardada em:\n{folha}",
    )
    return ACAO_ENVIAR
