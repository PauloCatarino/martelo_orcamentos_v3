"""Tests for Pesquisa IA RAG answer generation service."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from app.services import pesquisa_ia_resposta_service as service_module


def _service(monkeypatch, valores: dict[str, str]) -> service_module.RespostaIAService:
    class _FakeSystemSettingService:
        def __init__(self, session) -> None:
            self.session = session

        def obter_valor(self, chave: str, default: str | None = None) -> str | None:
            return valores.get(chave, default)

    monkeypatch.setattr(
        service_module, "SystemSettingService", _FakeSystemSettingService
    )
    return service_module.RespostaIAService(object())


def test_resposta_local_exige_modelo_configurado(monkeypatch) -> None:
    servico = _service(
        monkeypatch,
        {"provedor_resposta_ia": "local", "modelo_local_ia": ""},
    )

    with pytest.raises(RuntimeError, match="Modelo local IA para resposta"):
        servico.gerar("pergunta", "contexto")


def test_resposta_local_chama_ollama(monkeypatch) -> None:
    capturado: dict[str, object] = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self) -> bytes:
            return json.dumps({"message": {"content": "Resposta local"}}).encode()

    def _fake_urlopen(req, timeout):  # noqa: ANN001
        capturado["timeout"] = timeout
        capturado["url"] = req.full_url
        capturado["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    servico = _service(
        monkeypatch,
        {"provedor_resposta_ia": "local", "modelo_local_ia": "llama3.1"},
    )

    resposta = servico.gerar("Que orlas existem?", "trecho")

    assert resposta == "Resposta local"
    assert capturado["timeout"] == 180
    assert capturado["url"] == "http://localhost:11434/api/chat"
    assert capturado["payload"]["model"] == "llama3.1"
    assert capturado["payload"]["messages"][0]["role"] == "system"
    assert "ARTIGOS" in capturado["payload"]["messages"][0]["content"]
    assert "espessura por linha" in capturado["payload"]["messages"][0]["content"]
    assert "Contexto fornecido" in capturado["payload"]["messages"][1]["content"]


def test_resposta_openai_usa_sdk(monkeypatch) -> None:
    capturado: dict[str, object] = {}

    class _FakeCompletions:
        def create(self, **kwargs):  # noqa: ANN001
            capturado.update(kwargs)
            message = SimpleNamespace(content="Resposta OpenAI")
            choice = SimpleNamespace(message=message)
            return SimpleNamespace(choices=[choice])

    class _FakeOpenAI:
        def __init__(self) -> None:
            self.chat = SimpleNamespace(
                completions=_FakeCompletions(),
            )

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    servico = _service(
        monkeypatch,
        {"provedor_resposta_ia": "openai", "modelo_openai_texto": "gpt-teste"},
    )

    resposta = servico.gerar("Pergunta", "Contexto")

    assert resposta == "Resposta OpenAI"
    assert capturado["model"] == "gpt-teste"
    assert capturado["messages"][0]["content"] == service_module.SYSTEM


def test_resposta_claude_usa_sdk_anthropic(monkeypatch) -> None:
    capturado: dict[str, object] = {}

    class _FakeMessages:
        def create(self, **kwargs):  # noqa: ANN001
            capturado.update(kwargs)
            bloco = SimpleNamespace(type="text", text="Resposta Claude")
            return SimpleNamespace(content=[bloco])

    class _FakeAnthropic:
        def __init__(self) -> None:
            self.messages = _FakeMessages()

    monkeypatch.setitem(
        sys.modules, "anthropic", SimpleNamespace(Anthropic=_FakeAnthropic)
    )
    servico = _service(
        monkeypatch,
        {"provedor_resposta_ia": "claude", "modelo_claude_ia": "claude-teste"},
    )

    resposta = servico.gerar("Pergunta", "Contexto")

    assert resposta == "Resposta Claude"
    assert capturado["model"] == "claude-teste"
    assert capturado["system"] == service_module.SYSTEM
    assert capturado["messages"][0]["role"] == "user"
