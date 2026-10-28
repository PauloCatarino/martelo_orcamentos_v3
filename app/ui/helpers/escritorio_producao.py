"""Produção → Escritório do Streamlit: o envio para o Aprovisionamento, na UI.

Serve dois caminhos da página Produção:

- o **Gravar**, quando a obra passa de Desenho a Produção — o Martelo grava
  como sempre e, no fim, avança o modelo/versão no Streamlit. O Streamlit
  nunca impede nem desfaz o Gravar: o pior que acontece é ficar por enviar;
- **Funções › Enviar para o Aprovisionamento**, para repetir só esse passo
  (o Streamlit estava desligado, a obra já estava em Produção…).

As regras estão em :mod:`app.domain.escritorio_streamlit`; aqui ficam só as
caixas de mensagem e a ordem das coisas.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.core import diario_bordo
from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain import escritorio_streamlit as regras
from app.domain.escritorio_streamlit import Avaliacao
from app.services import escritorio_streamlit_escrita as escrita
from app.services import escritorio_streamlit_service as leitura

TITULO = "Escritório (Streamlit)"

#: Para onde se manda quem quer repetir o passo.
COMO_REPETIR = "Tente de novo em Funções › Enviar para o Aprovisionamento."


@dataclass(frozen=True)
class PreparacaoEnvio:
    """O que se decidiu ANTES de gravar, para fazer DEPOIS de gravar."""

    avaliacao: Avaliacao | None = None
    #: Texto para a linha de estado quando não se envia.
    mensagem: str = ""
    enviar: bool = False
    #: Caixa a mostrar depois de gravar: "" (nenhuma), "info" ou "aviso".
    caixa: str = ""
    #: O porquê, para essa caixa.
    porque: str = ""


def escrita_ligada() -> bool:
    try:
        with SessionLocal() as session:
            return leitura.escrita_ativa(session)
    except Exception:  # noqa: BLE001 - sem definições, fica desligado
        return False


def avaliar_obra(dados: Mapping[str, object]) -> tuple[Avaliacao | None, str]:
    """Ler o Streamlit para esta obra. Devolve ``(avaliação, "")`` ou ``(None, erro)``."""
    try:
        chave = regras.chave_versao(
            dados.get("ano"),
            dados.get("num_enc_phc"),
            dados.get("versao_obra"),
            dados.get("versao_plano"),
        )
    except ValueError as erro:
        return None, str(erro)

    utilizador = app_session.current_user
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        with SessionLocal() as session:
            avaliacao = leitura.avaliar(
                session,
                chave,
                martelo_username=getattr(utilizador, "username", "") or "",
                martelo_nome=getattr(utilizador, "nome", "") or "",
            )
    except Exception as erro:  # noqa: BLE001 - rede, PowerShell, SQL: tudo externo
        diario_bordo.registar_erro(f"{TITULO}: leitura falhou", str(erro))
        return None, leitura.explicar_erro_leitura(erro)
    finally:
        QApplication.restoreOverrideCursor()
    return avaliacao, ""


def confirmar_avisos(parent: QWidget | None, avaliacao: Avaliacao, *, botao_nao: str) -> bool:
    """Os avisos do Streamlit (sem plano de corte…) não impedem: pedem um clique."""
    caixa = QMessageBox(parent)
    caixa.setIcon(QMessageBox.Icon.Warning)
    caixa.setWindowTitle(TITULO)
    caixa.setText(
        f"{avaliacao.chave.descricao}: antes de seguir para o Aprovisionamento, "
        "o Streamlit avisa:"
    )
    caixa.setInformativeText("\n".join(f"• {aviso}" for aviso in avaliacao.avisos))
    enviar = caixa.addButton("Enviar mesmo assim", QMessageBox.ButtonRole.AcceptRole)
    enviar.setToolTip(
        "Envia na mesma para o Aprovisionamento; os avisos ficam registados no "
        "histórico do Escritório."
    )
    nao = caixa.addButton(botao_nao, QMessageBox.ButtonRole.RejectRole)
    nao.setToolTip("Não envia nada ao Streamlit. Pode enviar mais tarde em Funções.")
    caixa.setDefaultButton(nao)
    caixa.exec()
    return caixa.clickedButton() is enviar


def preparar_no_gravar(parent: QWidget | None, dados: Mapping[str, object]) -> PreparacaoEnvio | None:
    """Antes de gravar uma obra que entra em Produção. ``None`` = não fazer nada
    (o envio está desligado neste Martelo)."""
    if not escrita_ligada():
        return None
    avaliacao, erro = avaliar_obra(dados)
    if avaliacao is None:
        return PreparacaoEnvio(
            mensagem=f"Escritório: não enviado — {erro}",
            caixa="aviso",
            porque=erro,
        )
    if not avaliacao.pronto:
        return PreparacaoEnvio(
            avaliacao=avaliacao,
            mensagem=f"Escritório: {avaliacao.mensagem}",
            caixa="" if avaliacao.discreta else "info",
            porque=avaliacao.mensagem,
        )
    if avaliacao.avisos and not confirmar_avisos(
        parent, avaliacao, botao_nao="Só gravar no Martelo"
    ):
        return PreparacaoEnvio(
            avaliacao=avaliacao,
            mensagem="Escritório: não enviado para o Aprovisionamento (escolheu só gravar no Martelo).",
        )
    return PreparacaoEnvio(avaliacao=avaliacao, enviar=True)


def concluir_no_gravar(parent: QWidget | None, preparacao: PreparacaoEnvio, *, pasta: str) -> str:
    """Depois de gravar: avisa do que ficou por fazer, ou envia. Devolve o texto
    para a linha de estado."""
    if preparacao.caixa == "aviso":
        QMessageBox.warning(
            parent,
            TITULO,
            "A obra ficou gravada no Martelo, mas não consegui falar com o "
            f"Escritório do Streamlit.\n\n{preparacao.porque}\n\n{COMO_REPETIR}",
        )
    elif preparacao.caixa == "info":
        QMessageBox.information(
            parent,
            TITULO,
            "A obra ficou gravada no Martelo, mas não seguiu para o "
            f"Aprovisionamento:\n\n{preparacao.porque}",
        )
    if not preparacao.enviar or preparacao.avaliacao is None:
        return preparacao.mensagem
    return executar_envio(parent, preparacao.avaliacao, pasta=pasta)


def executar_envio(parent: QWidget | None, avaliacao: Avaliacao, *, pasta: str) -> str:
    """Gravar no Streamlit. Devolve o texto para a linha de estado."""
    command_id = regras.novo_command_id()
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        with SessionLocal() as session:
            resultado = escrita.enviar(session, avaliacao, command_id=command_id, pasta=pasta)
    except Exception as erro:  # noqa: BLE001 - rede, PowerShell, SQL: tudo externo
        QApplication.restoreOverrideCursor()
        diario_bordo.registar_erro("Enviar para o Aprovisionamento", str(erro))
        QMessageBox.warning(
            parent,
            TITULO,
            "Não foi possível avançar no Escritório (erro técnico). Nada foi "
            f"gravado no Streamlit.\n\n{escrita.explicar_erro_escrita(erro)}\n\n"
            + COMO_REPETIR,
        )
        return "Escritório: não foi possível avançar (erro técnico) — nada foi gravado no Streamlit."
    QApplication.restoreOverrideCursor()

    if resultado.resultado == escrita.JA_REGISTADO:
        return "Escritório: este clique já estava registado."
    if resultado.resultado == escrita.CONFLITO:
        QMessageBox.warning(
            parent,
            TITULO,
            "Outra pessoa alterou este modelo/versão entretanto. Nada foi gravado "
            "no Streamlit.\n\nVeja no Streamlit em que etapa ele está.",
        )
        return "Escritório: outra pessoa alterou este modelo/versão entretanto — nada foi gravado."

    diario_bordo.registar_acao(
        "Enviou para o Aprovisionamento (Streamlit)", avaliacao.chave.bd_key
    )
    if resultado.espelho_erro:
        # O avanço ficou; só a linha do Histórico do Tempos de Produção falhou.
        diario_bordo.registar_aviso(
            "Escritório: linha do histórico não gravada", resultado.espelho_erro
        )
    mensagem = f"Escritório: {regras.mensagem_sucesso(avaliacao.chave)}"
    if resultado.libertada:
        QMessageBox.information(parent, TITULO, regras.MENSAGEM_LIBERTADA)
        mensagem += " Material só do cliente: ficou logo libertado para a fábrica."
    return mensagem
