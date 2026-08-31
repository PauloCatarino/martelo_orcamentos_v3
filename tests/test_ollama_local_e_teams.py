"""Dois problemas do PC da Andreia na 1.0.9 (31-08-2026).

1. Pesquisa IA → "Gerar resposta IA" respondia com
   ``<urlopen error [WinError 10061] Nenhuma ligação pôde ser feita porque o
   computador de destino as recusou ativamente>``. Não diz o que falta nem o
   que fazer, e parece uma avaria de rede quando é só o Ollama que não está
   instalado NAQUELE computador.

2. Ocorrências → "Enviar para Teams" dizia "Teams aberto na conversa de Andreia
   com o ticket escrito" e gravava o envio no ticket — mas o que apareceu no
   ecrã foi a janela do Windows "Como quer abrir isto?" e não saiu mensagem
   nenhuma.
"""

from __future__ import annotations

import inspect
import os
import urllib.error

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.services import ollama_local


def _recusada() -> urllib.error.URLError:
    """A falha exata que apareceu no PC da Andreia."""
    return urllib.error.URLError(
        ConnectionRefusedError(
            10061,
            "Nenhuma ligação pôde ser feita porque o computador de destino "
            "as recusou ativamente",
        )
    )


# ----- 1. Ollama -----


def test_ligacao_recusada_explica_que_falta_o_ollama_neste_pc() -> None:
    erro = ollama_local.explicar_falha(_recusada(), "llama3.2")

    assert isinstance(erro, ollama_local.OllamaIndisponivel)
    texto = str(erro)
    assert "Ollama" in texto
    assert "NESTE PC" in texto
    # Diz que o resto da Pesquisa IA continua a servir — é o que evita o
    # "a Pesquisa IA não funciona" quando só a redação é que ficou de fora.
    assert "continua a funcionar" in texto
    # E não esconde o detalhe técnico de quem o quiser ver.
    assert "10061" in texto


def test_erro_de_ligacao_sem_url_error_tambem_e_reconhecido() -> None:
    erro = ollama_local.explicar_falha(ConnectionRefusedError(10061, "recusou"))

    assert isinstance(erro, ollama_local.OllamaIndisponivel)


def test_modelo_em_falta_diz_qual_e_e_como_instalar(monkeypatch) -> None:
    monkeypatch.setattr(
        ollama_local, "modelos_instalados", lambda: ["llama3.1:8b", "mistral"]
    )
    http = urllib.error.HTTPError(
        ollama_local.URL_CHAT, 404, "not found", hdrs=None, fp=None
    )

    erro = ollama_local.explicar_falha(http, "llama3.2")

    assert isinstance(erro, ollama_local.ModeloNaoInstalado)
    texto = str(erro)
    assert "llama3.2" in texto
    assert "llama3.1:8b" in texto and "mistral" in texto
    assert "ollama pull llama3.2" in texto
    assert "modelo_local_ia" in texto


def test_ollama_sem_modelo_nenhum_diz_isso(monkeypatch) -> None:
    monkeypatch.setattr(ollama_local, "modelos_instalados", lambda: [])
    http = urllib.error.HTTPError(
        ollama_local.URL_CHAT, 404, "not found", hdrs=None, fp=None
    )

    assert "não tem modelo nenhum" in str(
        ollama_local.explicar_falha(http, "llama3.2")
    )


def test_outras_falhas_nao_se_disfarcam_de_ollama_em_falta() -> None:
    http = urllib.error.HTTPError(
        ollama_local.URL_CHAT, 500, "boom", hdrs=None, fp=None
    )

    erro = ollama_local.explicar_falha(http, "llama3.2")

    assert not isinstance(erro, ollama_local.OllamaIndisponivel)
    assert not isinstance(erro, ollama_local.ModeloNaoInstalado)


def test_listar_modelos_nao_rebenta_sem_ollama(monkeypatch) -> None:
    def _falha(*_a, **_k):
        raise _recusada()

    monkeypatch.setattr(ollama_local.urllib.request, "urlopen", _falha)

    assert ollama_local.modelos_instalados() == []


def test_abrir_traduz_a_falha(monkeypatch) -> None:
    def _falha(*_a, **_k):
        raise _recusada()

    monkeypatch.setattr(ollama_local.urllib.request, "urlopen", _falha)
    pedido = ollama_local.pedido_chat({"model": "llama3.2"})

    with pytest.raises(ollama_local.OllamaIndisponivel):
        ollama_local.abrir(pedido, timeout=5, modelo="llama3.2")


@pytest.mark.parametrize(
    "modulo",
    [
        "app.services.pesquisa_ia_resposta_service",
        "app.services.assistente_producao_service",
    ],
)
def test_quem_fala_com_o_ollama_passa_pelo_tradutor(modulo: str) -> None:
    """Senão o WinError 10061 volta a chegar cru ao ecrã."""
    import importlib

    fonte = inspect.getsource(importlib.import_module(modulo))
    assert "ollama_local.abrir" in fonte
    assert "urllib.request.urlopen" not in fonte
    assert "http://localhost:11434/api/chat" not in fonte


# ----- 2. Teams -----


def test_envio_para_teams_pede_confirmacao_antes_de_dar_por_enviado() -> None:
    from app.ui.dialogs.ocorrencias_obra_dialog import OcorrenciasObraDialog

    fonte = inspect.getsource(OcorrenciasObraDialog._enviar_teams)

    # A confirmação vem DEPOIS de abrir o link e ANTES de registar o envio.
    assert "_confirmar_teams_abriu" in fonte
    assert fonte.index("abrir_chat_teams") < fonte.index("_confirmar_teams_abriu")
    assert fonte.index("_confirmar_teams_abriu") < fonte.index("registar_envio")


def test_quando_o_teams_nao_abriu_nao_se_grava_nada() -> None:
    from app.ui.dialogs.ocorrencias_obra_dialog import OcorrenciasObraDialog

    fonte = inspect.getsource(OcorrenciasObraDialog._enviar_teams)
    depois_da_pergunta = fonte[fonte.index("_confirmar_teams_abriu"):]
    ramo_nao = depois_da_pergunta[: depois_da_pergunta.index("return") + len("return")]

    # No ramo do "não": copia o texto e sai, sem registar.
    assert "clipboard" in ramo_nao
    assert "registar_envio" not in ramo_nao
    assert "NÃO registado" in ramo_nao


def test_a_pergunta_fala_da_janela_do_windows() -> None:
    """É a janela que a Andreia viu; sem a nomear, ninguém liga uma à outra."""
    from app.ui.dialogs.ocorrencias_obra_dialog import OcorrenciasObraDialog

    fonte = inspect.getsource(OcorrenciasObraDialog._confirmar_teams_abriu)
    assert "Como quer abrir isto?" in fonte
    assert "Enter no Teams" in fonte
