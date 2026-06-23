"""Geracao de resposta IA RAG a partir dos artigos e catalogos."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.system_setting_service import SystemSettingService

SYSTEM = (
    "\u00c9s um assistente interno de uma empresa de mobili\u00e1rio. "
    "Respondes em portugu\u00eas de "
    "Portugal, de forma direta, objetiva e \u00fatil. Usa a informa\u00e7\u00e3o "
    "dos ARTIGOS (mat\u00e9rias-primas "
    "do PHC/V3, com refer\u00eancia, fornecedor e pre\u00e7o) e dos TRECHOS "
    "de cat\u00e1logos fornecidos. "
    "Quando houver artigos relevantes, lista-os com refer\u00eancia, "
    "descri\u00e7\u00e3o e pre\u00e7o de custo. "
    "Cita a fonte (a refer\u00eancia do artigo, ou 'ficheiro \u00b7 local' "
    "do trecho). S\u00f3 se N\u00c3O houver "
    "mesmo nada relevante \u00e9 que dizes que n\u00e3o encontraste. "
    "Quando apresentares pre\u00e7os por espessura, mostra-os de forma "
    "organizada - uma espessura por linha no formato 'espessura - pre\u00e7o' "
    "(ex.: '8 mm - 11,37 \u20ac') -, nunca tudo misturado numa s\u00f3 linha. "
    "N\u00e3o inventes pre\u00e7os nem refer\u00eancias."
)


class RespostaIAService:
    def __init__(self, session: Session) -> None:
        svc = SystemSettingService(session)
        self._provedor = (
            svc.obter_valor("provedor_resposta_ia", "local") or "local"
        ).strip().lower()
        self._modelo_local = (svc.obter_valor("modelo_local_ia", "") or "").strip()
        self._modelo_openai = (
            svc.obter_valor("modelo_openai_texto", "gpt-4o-mini") or "gpt-4o-mini"
        ).strip()
        self._modelo_claude = (
            svc.obter_valor("modelo_claude_ia", "claude-opus-4-8")
            or "claude-opus-4-8"
        ).strip()

    def gerar(self, pergunta: str, contexto: str) -> str:
        prompt = f"Pergunta: {pergunta}\n\nContexto fornecido:\n{contexto}"
        if self._provedor == "openai":
            return self._openai(prompt)
        if self._provedor == "claude":
            return self._claude(prompt)
        return self._local(prompt)

    def _local(self, prompt: str) -> str:
        if not self._modelo_local:
            raise RuntimeError(
                "Defina 'Modelo local IA para resposta' (ex.: llama3.1) "
                "e tenha o Ollama a correr."
            )
        import json
        import urllib.request

        payload = {
            "model": self._modelo_local,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310
            dados = json.loads(resp.read().decode("utf-8"))
        return (dados.get("message", {}).get("content") or "").strip()

    def _openai(self, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Instale o SDK OpenAI: pip install openai") from exc
        cliente = OpenAI()
        resp = cliente.chat.completions.create(
            model=self._modelo_openai,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

    def _claude(self, prompt: str) -> str:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("Instale o SDK Anthropic: pip install anthropic") from exc
        cliente = anthropic.Anthropic()
        resposta = cliente.messages.create(
            model=self._modelo_claude or "claude-opus-4-8",
            max_tokens=2000,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            bloco.text for bloco in resposta.content if bloco.type == "text"
        ).strip()
