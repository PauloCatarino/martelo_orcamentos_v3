"""Falar com o Ollama que corre NESTE computador, e explicar quando não dá.

O Ollama é o programa que faz correr o modelo de linguagem (llama3.2 e afins).
Não vive no servidor: **está instalado em cada PC**, e o Martelo fala com ele em
``http://localhost:11434``. A definição do modelo (``modelo_local_ia``) é que é
partilhada, na base de dados — ou seja, o Martelo de toda a gente tenta usar o
modelo que lá está, mesmo nos computadores onde o Ollama não existe.

Quando não existe, o Python devolve isto:

    <urlopen error [WinError 10061] Nenhuma ligação pôde ser feita porque o
    computador de destino as recusou ativamente>

Foi o que apareceu à Andreia a 31-08-2026. Não diz o que falta nem o que fazer,
e ainda parece uma avaria da rede quando é só um programa que não está
instalado naquele PC. Este módulo troca essas mensagens por frases que dizem a
causa e o passo seguinte.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

#: O Ollama responde sempre na própria máquina, nesta porta.
URL_BASE = "http://localhost:11434"
URL_CHAT = f"{URL_BASE}/api/chat"
URL_MODELOS = f"{URL_BASE}/api/tags"


class OllamaIndisponivel(RuntimeError):
    """O Ollama não está a responder neste computador."""


class ModeloNaoInstalado(RuntimeError):
    """O Ollama responde, mas não tem o modelo que a definição pede."""


def pedido_chat(payload: dict) -> urllib.request.Request:
    """O pedido HTTP do ``/api/chat``, montado num sítio só."""
    return urllib.request.Request(
        URL_CHAT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


def modelos_instalados() -> list[str]:
    """Os modelos que este computador tem, ou lista vazia se não der."""
    try:
        with urllib.request.urlopen(URL_MODELOS, timeout=5) as resp:  # noqa: S310
            dados = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return []

    return [
        str(modelo.get("name") or "").strip()
        for modelo in dados.get("models", [])
        if modelo.get("name")
    ]


def explicar_falha(erro: Exception, modelo: str = "") -> Exception:
    """Traduzir uma falha do Ollama para uma frase que se possa agir.

    Devolve a exceção a levantar (não a levanta), para quem chama decidir.
    """
    if _e_ligacao_recusada(erro):
        return OllamaIndisponivel(
            "A resposta por IA não está disponível neste computador.\n\n"
            "Ela precisa do Ollama — o programa que faz correr o modelo de "
            "linguagem — instalado E a correr NESTE PC. O Ollama não vive no "
            "servidor: é preciso instalá-lo em cada computador que queira "
            "gerar respostas.\n\n"
            "O resto da Pesquisa IA (matérias-primas, artigos do PHC e "
            "catálogos) continua a funcionar sem ele — só a redação da "
            "resposta é que fica de fora.\n\n"
            f"Detalhe técnico: {erro}"
        )

    if _e_modelo_desconhecido(erro):
        instalados = modelos_instalados()
        tem = (
            "Modelos instalados neste PC: " + ", ".join(instalados)
            if instalados
            else "Este Ollama não tem modelo nenhum instalado."
        )
        return ModeloNaoInstalado(
            f"O Ollama está a correr, mas não tem o modelo «{modelo}».\n\n"
            f"{tem}\n\n"
            f"Instale-o com «ollama pull {modelo}» numa linha de comandos, ou "
            "mude a definição 'modelo_local_ia' em Configurações → Caminhos do "
            "Sistema para um dos modelos que já existem.\n\n"
            f"Detalhe técnico: {erro}"
        )

    return RuntimeError(f"O Ollama não respondeu como esperado.\n\n{erro}")


def _e_ligacao_recusada(erro: Exception) -> bool:
    """Ninguém do outro lado: o Ollama não está a correr aqui."""
    if isinstance(erro, urllib.error.HTTPError):
        return False
    if isinstance(erro, urllib.error.URLError):
        erro = erro.reason if isinstance(erro.reason, BaseException) else erro
    # 10061 é o número do Windows; ConnectionRefusedError cobre os outros.
    return isinstance(erro, (ConnectionRefusedError, TimeoutError)) or (
        getattr(erro, "errno", None) in (10061, 111)
    )


def _e_modelo_desconhecido(erro: Exception) -> bool:
    """O Ollama responde 404 quando lhe pedem um modelo que não tem."""
    return isinstance(erro, urllib.error.HTTPError) and erro.code == 404


def abrir(req: urllib.request.Request, *, timeout: int, modelo: str = "") -> Any:
    """``urlopen`` com as falhas já traduzidas."""
    try:
        return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310
    except (urllib.error.URLError, OSError) as erro:
        raise explicar_falha(erro, modelo) from erro
