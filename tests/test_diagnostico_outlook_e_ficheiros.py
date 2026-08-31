"""Mensagens de erro que dizem a CAUSA, e não uma lista de coisas a experimentar.

Vem do que aconteceu no PC da Andreia a 31-08-2026 (log do diário de bordo):

- o email não saiu e o aviso mandava "feche o Martelo e abra pelo atalho" — o
  que não resolve nada quando o Martelo está marcado no Windows para abrir
  sempre como administrador, que é para sempre e não só depois de instalar;
- o Resumo de Custos rebentou com "ERRO inesperado: [Errno 13] Permission
  denied", porque o ``PermissionError`` nem sequer estava a ser apanhado.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.services import email_service
from app.ui.pages.orcamento_relatorios_page import explicar_erro_de_ficheiro

ERRO_COM = "(-2146959355, 'A execução no servidor falhou', None, None)"


# ----- Outlook -----


def test_sem_outlook_classico_diz_que_o_novo_outlook_nao_serve(monkeypatch) -> None:
    monkeypatch.setattr(email_service, "_outlook_classico_instalado", lambda: False)

    mensagem = email_service._explicar_falha_do_outlook(ERRO_COM)

    assert "Outlook clássico" in mensagem
    assert "novo Outlook" in mensagem
    # Não manda desmarcar vistos que não existem.
    assert "administrador" not in mensagem.lower()


def test_marcado_para_abrir_como_admin_manda_desmarcar_o_visto(monkeypatch) -> None:
    monkeypatch.setattr(email_service, "_outlook_classico_instalado", lambda: True)
    monkeypatch.setattr(email_service, "_is_elevated", lambda: True)
    monkeypatch.setattr(
        email_service, "_marcado_para_abrir_como_administrador", lambda: True
    )
    monkeypatch.setattr(
        email_service, "_caminho_do_executavel", lambda: r"C:\Martelo\Martelo.exe"
    )

    mensagem = email_service._explicar_falha_do_outlook(ERRO_COM)

    assert "SEMPRE como administrador" in mensagem
    assert "Compatibilidade" in mensagem
    assert r"C:\Martelo\Martelo.exe" in mensagem
    # E diz porque é que o conselho antigo não chegava.
    assert "abrir pelo atalho não resolve" in mensagem


def test_elevado_sem_o_visto_continua_a_mandar_abrir_pelo_atalho(monkeypatch) -> None:
    monkeypatch.setattr(email_service, "_outlook_classico_instalado", lambda: True)
    monkeypatch.setattr(email_service, "_is_elevated", lambda: True)
    monkeypatch.setattr(
        email_service, "_marcado_para_abrir_como_administrador", lambda: False
    )

    mensagem = email_service._explicar_falha_do_outlook(ERRO_COM)

    assert "abra-o pelo atalho" in mensagem
    assert "Compatibilidade" in mensagem  # e o que fazer se voltar a acontecer


def test_sem_elevacao_nenhuma_nao_acusa_o_administrador(monkeypatch) -> None:
    monkeypatch.setattr(email_service, "_outlook_classico_instalado", lambda: True)
    monkeypatch.setattr(email_service, "_is_elevated", lambda: False)

    mensagem = email_service._explicar_falha_do_outlook(ERRO_COM)

    assert "ADMINISTRADOR" not in mensagem
    assert "Outlook está aberto" in mensagem


def test_o_detalhe_tecnico_vai_sempre_na_mensagem(monkeypatch) -> None:
    monkeypatch.setattr(email_service, "_outlook_classico_instalado", lambda: True)
    for elevado in (True, False):
        monkeypatch.setattr(email_service, "_is_elevated", lambda: elevado)
        monkeypatch.setattr(
            email_service, "_marcado_para_abrir_como_administrador", lambda: False
        )
        assert ERRO_COM in email_service._explicar_falha_do_outlook(ERRO_COM)


def test_deteccoes_do_windows_nao_rebentam_neste_pc() -> None:
    """Correm sempre, mesmo sem registo nenhum: devolvem um booleano e pronto."""
    assert isinstance(email_service._is_elevated(), bool)
    assert isinstance(email_service._marcado_para_abrir_como_administrador(), bool)
    assert isinstance(email_service._outlook_classico_instalado(), bool)
    assert email_service._caminho_do_executavel()


# ----- Ficheiros -----


def test_ficheiro_aberto_no_excel_diz_isso_e_nomeia_o_ficheiro() -> None:
    erro = PermissionError(13, "Permission denied")
    erro.filename = (
        r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\2026"
        r"\260869_CARP_MODEIRAS\01\Resumo_Custos_260869_01.xlsx"
    )

    mensagem = explicar_erro_de_ficheiro(erro)

    assert "Resumo_Custos_260869_01.xlsx" in mensagem
    assert "ABERTO" in mensagem
    assert "Excel" in mensagem
    assert "Errno 13" in mensagem  # o detalhe técnico não se perde


def test_ficheiro_aberto_sem_nome_ainda_da_uma_frase_util() -> None:
    mensagem = explicar_erro_de_ficheiro(PermissionError(13, "Permission denied"))

    assert "o ficheiro" in mensagem
    assert "ABERTO" in mensagem


def test_servidor_em_baixo_fala_do_servidor() -> None:
    assert "SERVER_LE" in explicar_erro_de_ficheiro(FileNotFoundError("x"))
    assert "rede" in explicar_erro_de_ficheiro(OSError("x"))


def test_erros_que_nao_sao_de_ficheiro_passam_tal_e_qual() -> None:
    assert explicar_erro_de_ficheiro(ValueError("Defina a pasta base")) == (
        "Defina a pasta base"
    )


@pytest.mark.parametrize(
    "metodo",
    [
        "_exportar_pdf",
        "_exportar_excel",
        "_exportar_phc",
        "_exportar_resumo_custos",
        "_exportar_plano_corte",
    ],
)
def test_todas_as_exportacoes_apanham_erros_de_ficheiro(metodo: str) -> None:
    """Sem isto, um ficheiro aberto no Excel sai como "ERRO inesperado"."""
    import inspect

    from app.ui.pages.orcamento_relatorios_page import OrcamentoRelatoriosPage

    fonte = inspect.getsource(getattr(OrcamentoRelatoriosPage, metodo))
    assert "OSError" in fonte
    assert "explicar_erro_de_ficheiro" in fonte
