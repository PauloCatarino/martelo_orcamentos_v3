"""Fornecedores multimodais do piloto de roupeiros."""

from __future__ import annotations

import base64
import json
import os
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.domain.roupeiro_ia import (
    AnaliseRoupeiro,
    MedidaReconhecida,
    PedidoAnaliseRoupeiro,
    medida_para_mm,
)
from app.services.pdf_imagem_service import documento_pdf

LIMITE_PDF_BYTES = 50 * 1024 * 1024


def _schema_analise() -> dict:
    medida = {
        "type": "object",
        "properties": {
            "valor": {"type": ["number", "string", "null"]},
            "unidade": {"type": ["string", "null"]},
            "confianca": {"type": "number"},
            "texto_origem": {"type": ["string", "null"]},
        },
        "required": ["valor", "unidade", "confianca", "texto_origem"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "referencia": {"type": ["string", "null"]},
            "altura": medida,
            "largura": medida,
            "profundidade": medida,
            "caracteristicas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "codigo": {"type": "string"},
                        "quantidade": {"type": "number"},
                    },
                    "required": ["codigo", "quantidade"],
                    "additionalProperties": False,
                },
            },
            "restricoes": {"type": "array", "items": {"type": "string"}},
            "perguntas": {"type": "array", "items": {"type": "string"}},
            "confianca": {"type": "number"},
            "explicacao": {"type": "string"},
        },
        "required": ["referencia", "altura", "largura", "profundidade", "caracteristicas", "restricoes", "perguntas", "confianca", "explicacao"],
        "additionalProperties": False,
    }


def _prompt(pedido: PedidoAnaliseRoupeiro) -> str:
    perfil = json.dumps(pedido.perfil, ensure_ascii=False)
    catalogo = json.dumps(
        [{"codigo": m.codigo, "nome": m.nome, "caracteristicas": {k: str(v) for k, v in m.caracteristicas.items()}} for m in pedido.catalogo],
        ensure_ascii=False,
    )
    respostas = pedido.respostas_utilizador.strip()
    contexto_respostas = (
        "\nRespostas/correções fornecidas pelo utilizador às dúvidas da análise anterior: "
        f"{respostas}. Usa-as como informação confirmada pelo utilizador e assinala qualquer conflito com o desenho."
        if respostas
        else ""
    )
    return (
        "Analisa apenas o roupeiro assinalado no recorte. O objetivo principal é identificar R1/RP_01/etc., "
        "as divisões interiores e características funcionais que ajudam a escolher módulos: portas, gavetas, "
        "prateleiras, varões, maleiros, nichos, cantos, remates, estantes abertas, pilares e outras opções visíveis. "
        "As dimensões finais já pertencem ao item do orçamento e não devem ser usadas para repartir ou dimensionar "
        "os módulos; se leres medidas, devolve-as apenas como informação com confiança. Não inventes medidas nem "
        "preços. Respeita obrigatoriamente as entradas 'nao_quero'.\n"
        f"Página selecionada (base 1): {pedido.pagina}. Perfil privado: {perfil}. Catálogo informativo: {catalogo}."
        f"{contexto_respostas}"
    )


def _medida(dados: dict) -> MedidaReconhecida:
    valor = medida_para_mm(dados.get("valor"), dados.get("unidade"))
    return MedidaReconhecida(
        valor=valor,
        unidade="mm" if valor is not None else dados.get("unidade"),
        confianca=float(dados.get("confianca", 0)),
        texto_origem=dados.get("texto_origem"),
    )


def interpretar_analise(dados: dict) -> AnaliseRoupeiro:
    """Valida a forma mínima do JSON devolvido por qualquer fornecedor."""
    if not isinstance(dados, dict):
        raise ValueError("O fornecedor devolveu uma resposta que não é um objeto JSON.")
    for chave in ("altura", "largura", "profundidade", "caracteristicas"):
        if chave not in dados:
            raise ValueError(f"Resposta inválida: falta o campo {chave}.")
    caracteristicas_raw = dados["caracteristicas"]
    if isinstance(caracteristicas_raw, list):
        caracteristicas = {
            str(item["codigo"]).upper(): Decimal(str(item["quantidade"]))
            for item in caracteristicas_raw
        }
    elif isinstance(caracteristicas_raw, dict):
        # Compatibilidade com fornecedores locais que ainda devolvam um mapa.
        caracteristicas = {
            str(k).upper(): Decimal(str(v)) for k, v in caracteristicas_raw.items()
        }
    else:
        raise ValueError("Resposta inválida: características não são uma lista.")
    return AnaliseRoupeiro(
        referencia=dados.get("referencia"),
        altura=_medida(dados["altura"]),
        largura=_medida(dados["largura"]),
        profundidade=_medida(dados["profundidade"]),
        caracteristicas=caracteristicas,
        restricoes=tuple(dados.get("restricoes") or ()),
        perguntas=tuple(dados.get("perguntas") or ()),
        confianca=float(dados.get("confianca", 0)),
        explicacao=str(dados.get("explicacao") or ""),
        resultado_bruto=dados,
    )


class OpenAIVisionProvider:
    nome = "OPENAI"

    def __init__(self, modelo: str = "gpt-5.2", api_key: str | None = None, timeout: int = 120) -> None:
        self.modelo = modelo
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.timeout = timeout

    def analisar(self, pedido: PedidoAnaliseRoupeiro) -> AnaliseRoupeiro:
        caminho = Path(pedido.pdf_path)
        if not caminho.is_file():
            raise ValueError("O PDF selecionado não está acessível.")
        if caminho.stat().st_size > LIMITE_PDF_BYTES:
            raise ValueError("O PDF excede o limite de 50 MB do fornecedor OpenAI.")
        if not self.api_key:
            raise ValueError("A chave OPENAI_API_KEY não está configurada.")
        conteudo = [
            {
                "type": "input_file",
                "filename": caminho.name,
                "file_data": "data:application/pdf;base64," + base64.b64encode(caminho.read_bytes()).decode("ascii"),
                "detail": "high",
            },
            {"type": "input_text", "text": _prompt(pedido)},
        ]
        if pedido.recorte_png:
            conteudo.append(
                {
                    "type": "input_image",
                    "image_url": "data:image/png;base64," + base64.b64encode(pedido.recorte_png).decode("ascii"),
                    "detail": "high",
                }
            )
        payload = {
            "model": self.modelo,
            "input": [{"role": "user", "content": conteudo}],
            "text": {"format": {"type": "json_schema", "name": "analise_roupeiro", "strict": True, "schema": _schema_analise()}},
        }
        resposta = self._post("https://api.openai.com/v1/responses", payload, {"Authorization": f"Bearer {self.api_key}"})
        texto = resposta.get("output_text") or self._extrair_output_text(resposta)
        if not texto:
            raise ValueError("A OpenAI não devolveu a análise estruturada.")
        return interpretar_analise(json.loads(texto))

    def _post(self, url: str, payload: dict, headers: dict[str, str]) -> dict:
        if url == "https://api.openai.com/v1/responses":
            return self._post_openai(payload)
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Martelo-Orcamentos-V3/0.1",
                **headers,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detalhe = self._detalhe_erro_http(exc)
            raise ValueError(f"OpenAI recusou a análise ({exc.code}): {detalhe}") from exc
        except (URLError, TimeoutError) as exc:
            raise ValueError(f"Não foi possível contactar a OpenAI: {exc}") from exc

    def _post_openai(self, payload: dict) -> dict:
        """Executa Responses através do SDK oficial da OpenAI."""
        try:
            from openai import (
                APIConnectionError,
                APIStatusError,
                APITimeoutError,
                OpenAI,
            )
        except ImportError as exc:
            raise ValueError(
                "Falta o SDK OpenAI. Execute: pip install openai"
            ) from exc

        cliente = OpenAI(api_key=self.api_key, timeout=self.timeout)
        try:
            resposta = cliente.responses.create(**payload)
        except APIStatusError as exc:
            detalhe = self._detalhe_erro_sdk(exc)
            raise ValueError(
                f"OpenAI recusou a análise ({exc.status_code}): {detalhe}"
            ) from exc
        except (APIConnectionError, APITimeoutError) as exc:
            raise ValueError(f"Não foi possível contactar a OpenAI: {exc}") from exc
        return resposta.model_dump(mode="json")

    @staticmethod
    def _detalhe_erro_sdk(exc) -> str:
        corpo = getattr(exc, "body", None)
        partes: list[str] = []
        erro = corpo.get("error") if isinstance(corpo, dict) else None
        if not isinstance(erro, dict) and isinstance(corpo, dict):
            erro = corpo
        if isinstance(erro, dict):
            mensagem = str(erro.get("message") or "").strip()
            if mensagem:
                partes.append(mensagem)
            identificadores = [
                str(erro.get(chave)).strip()
                for chave in ("type", "code", "param")
                if erro.get(chave) not in (None, "")
            ]
            if identificadores:
                partes.append(" / ".join(identificadores))
        if not partes:
            partes.append(str(exc).strip() or "Pedido inválido")
        request_id = str(getattr(exc, "request_id", "") or "").strip()
        if request_id:
            partes.append(f"request_id={request_id}")
        return " | ".join(partes)

    @staticmethod
    def _detalhe_erro_http(exc: HTTPError) -> str:
        """Extrai a mensagem da API sem incluir dados de autenticação."""
        corpo = exc.read().decode("utf-8", errors="replace").strip()
        partes: list[str] = []
        if corpo:
            try:
                dados = json.loads(corpo)
            except json.JSONDecodeError:
                partes.append(corpo[:1500])
            else:
                erro = dados.get("error") if isinstance(dados, dict) else None
                if isinstance(erro, dict):
                    mensagem = str(erro.get("message") or "").strip()
                    if mensagem:
                        partes.append(mensagem)
                    identificadores = [
                        str(erro.get(chave)).strip()
                        for chave in ("type", "code", "param")
                        if erro.get(chave) not in (None, "")
                    ]
                    if identificadores:
                        partes.append(" / ".join(identificadores))
                else:
                    partes.append(corpo[:1500])
        if not partes:
            partes.append(
                str(getattr(exc, "reason", "") or "Pedido inválido").strip()
            )
        request_id = ""
        if getattr(exc, "headers", None) is not None:
            request_id = str(
                exc.headers.get("x-request-id")
                or exc.headers.get("X-Request-Id")
                or ""
            ).strip()
        if request_id:
            partes.append(f"request_id={request_id}")
        return " | ".join(partes)

    @staticmethod
    def _extrair_output_text(resposta: dict) -> str | None:
        for item in resposta.get("output", []):
            for conteudo in item.get("content", []):
                if conteudo.get("type") == "output_text" and conteudo.get("text"):
                    return conteudo["text"]
        return None


class LocalVisionProvider(OpenAIVisionProvider):
    nome = "LOCAL"

    def __init__(self, modelo: str, endpoint: str = "http://localhost:11434", timeout: int = 180) -> None:
        super().__init__(modelo=modelo, api_key="local", timeout=timeout)
        self.endpoint = endpoint.rstrip("/")

    def analisar(self, pedido: PedidoAnaliseRoupeiro) -> AnaliseRoupeiro:
        if not Path(pedido.pdf_path).is_file():
            raise ValueError("O PDF selecionado não está acessível.")
        imagens = self._renderizar_paginas(pedido.pdf_path)
        if pedido.recorte_png:
            imagens.append(base64.b64encode(pedido.recorte_png).decode("ascii"))
        if not imagens:
            raise ValueError("O fornecedor local precisa do recorte renderizado da página.")
        payload = {
            "model": self.modelo,
            "stream": False,
            "format": _schema_analise(),
            "messages": [{"role": "user", "content": _prompt(pedido), "images": imagens}],
        }
        resposta = self._post(f"{self.endpoint}/api/chat", payload, {})
        texto = (resposta.get("message") or {}).get("content")
        if not texto:
            raise ValueError("O modelo local não devolveu conteúdo.")
        return interpretar_analise(json.loads(texto))

    @staticmethod
    def _renderizar_paginas(caminho: str) -> list[str]:
        """Renderiza todas as páginas para o fornecedor local (texto+imagem visual)."""
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize

        imagens: list[str] = []
        with documento_pdf(caminho) as documento:
            for pagina in range(documento.pageCount()):
                pontos = documento.pagePointSize(pagina)
                largura = 1400
                altura = max(1, round(largura * pontos.height() / pontos.width()))
                imagem = documento.render(pagina, QSize(largura, altura))
                dados = QByteArray()
                buffer = QBuffer(dados)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                imagem.save(buffer, "PNG")
                buffer.close()
                imagens.append(base64.b64encode(bytes(dados)).decode("ascii"))
        return imagens
