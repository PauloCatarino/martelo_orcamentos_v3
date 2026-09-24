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


# ----- 1b. PC do Pedro (23-09-2026): demora e erros do próprio Ollama -----


@pytest.mark.parametrize(
    "erro",
    [TimeoutError("timed out"), urllib.error.URLError(TimeoutError("timed out"))],
)
def test_demora_nao_se_disfarca_de_ollama_por_instalar(erro) -> None:
    """O Ollama acabado de instalar demora a carregar o modelo; não está em falta."""
    explicado = ollama_local.explicar_falha(erro, "llama3.2", 180)

    assert isinstance(explicado, ollama_local.OllamaLento)
    assert not isinstance(explicado, ollama_local.OllamaIndisponivel)
    texto = str(explicado)
    assert "está neste PC" in texto
    assert "180 segundos" in texto
    assert "llama3.2" in texto
    assert "timed out" in texto


def _http_500(corpo: bytes) -> urllib.error.HTTPError:
    import io

    return urllib.error.HTTPError(
        ollama_local.URL_CHAT, 500, "Internal Server Error", hdrs=None,
        fp=io.BytesIO(corpo),
    )


def test_falta_de_memoria_diz_o_que_fazer() -> None:
    erro = _http_500(
        b'{"error":"model requires more system memory (5.6 GiB) '
        b'than is available (3.1 GiB)"}'
    )

    explicado = ollama_local.explicar_falha(erro, "llama3.2")

    assert isinstance(explicado, ollama_local.OllamaRespondeuErro)
    texto = str(explicado)
    assert "memória livre" in texto and "llama3.2" in texto
    # A frase do próprio Ollama não se perde.
    assert "5.6 GiB" in texto


def test_outro_erro_do_ollama_mostra_o_que_ele_disse() -> None:
    erro = _http_500(b'{"error":"llama runner process has terminated"}')

    texto = str(ollama_local.explicar_falha(erro, "llama3.2"))

    assert "llama runner process has terminated" in texto
    assert "HTTP Error 500" not in texto


class _RespostaFalsa:
    def __init__(self, linhas, falha: Exception | None = None) -> None:
        self._linhas = linhas
        self._falha = falha

    def __iter__(self):
        yield from self._linhas
        if self._falha:
            raise self._falha


def test_streaming_devolve_os_pedacos_de_texto() -> None:
    resp = _RespostaFalsa([
        b'{"message":{"content":"Ol"},"done":false}\n',
        b"\n",
        b'{"message":{"content":"\xc3\xa1"},"done":false}\n',
        b'{"message":{"content":""},"done":true}\n',
        b'{"message":{"content":"depois do fim"}}\n',
    ])

    assert list(ollama_local.pedacos_chat(resp, timeout=180)) == ["Ol", "á"]


def test_erro_a_meio_do_streaming_nao_passa_em_silencio() -> None:
    resp = _RespostaFalsa([
        b'{"message":{"content":"Ol"},"done":false}\n',
        b'{"error":"model requires more system memory than is available"}\n',
    ])

    with pytest.raises(ollama_local.OllamaRespondeuErro, match="memória livre"):
        list(ollama_local.pedacos_chat(resp, timeout=180, modelo="llama3.2"))


def test_demora_a_meio_do_streaming_e_explicada() -> None:
    resp = _RespostaFalsa(
        [b'{"message":{"content":"Ol"},"done":false}\n'],
        falha=TimeoutError("timed out"),
    )

    with pytest.raises(ollama_local.OllamaLento, match="180 segundos"):
        list(ollama_local.pedacos_chat(resp, timeout=180, modelo="llama3.2"))


def test_resposta_da_pesquisa_ia_usa_o_leitor_de_streaming() -> None:
    from app.services.pesquisa_ia_resposta_service import RespostaIAService

    fonte = inspect.getsource(RespostaIAService._local_stream)
    assert "ollama_local.pedacos_chat" in fonte


# ----- 1c. Pedidos cortados pelo início (registo do Ollama do Paulo, 24-09) -----


def test_pedido_pequeno_tem_espaco_folgado() -> None:
    # Acima dos 4096 do Ollama por omissão, que cortava 45 de 125 pedidos reais
    # quase no limite.
    assert ollama_local.contexto_para("instruções", "pergunta curta") == 8192


def test_o_maior_pedido_real_cabe_inteiro_com_a_resposta() -> None:
    # 6807 tokens a ~2,4 caracteres cada: o maior pedido visto no registo.
    texto = "x" * int(6807 * 2.42)

    num_ctx = ollama_local.contexto_para(texto)

    assert num_ctx >= 6807 + ollama_local.TOKENS_RESPOSTA
    assert num_ctx in ollama_local.CONTEXTOS


def test_contexto_nao_cresce_sem_limite() -> None:
    assert ollama_local.contexto_para("x" * 1_000_000) == max(ollama_local.CONTEXTOS)


@pytest.mark.parametrize("metodo", ["_local", "_local_stream"])
def test_pesquisa_ia_pede_o_contexto_a_medida(monkeypatch, metodo) -> None:
    import json

    from app.services.pesquisa_ia_resposta_service import RespostaIAService

    enviados = []

    def _abrir(req, **_k):
        enviados.append(json.loads(req.data.decode("utf-8")))
        raise RuntimeError("parar aqui")

    monkeypatch.setattr(ollama_local, "abrir", _abrir)
    servico = RespostaIAService.__new__(RespostaIAService)
    servico._modelo_local = "llama3.2"
    prompt = "Contexto fornecido:\n" + "V3 | H3170 ST12 | 24,50 €\n" * 700

    with pytest.raises(RuntimeError, match="parar aqui"):
        resultado = getattr(servico, metodo)(prompt)
        list(resultado) if metodo == "_local_stream" else resultado

    num_ctx = enviados[0]["options"]["num_ctx"]
    assert num_ctx == ollama_local.contexto_para(
        enviados[0]["messages"][0]["content"], prompt
    )
    assert num_ctx > 4096


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
