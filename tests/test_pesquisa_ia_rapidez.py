"""Pesquisa IA mais rápida (21-11-2026).

O registo do Ollama do Paulo mostrou que a demora não estava na pesquisa nem na
leitura do pedido (3–9 s), mas na ESCRITA: o llama3.2 entrava às vezes num ciclo
e escrevia sem fim (81 920 tokens em 1h03 a 18-11), e a pesquisa seguinte ficava
em fila atrás dessa resposta, porque o Ollama atende um pedido de cada vez.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from app.services import ollama_local
from app.services import pesquisa_ia_resposta_service as service_module


# ----- limite de escrita e modelo carregado -----


def test_opcoes_limitam_a_escrita_e_mantem_o_contexto() -> None:
    opcoes = ollama_local.opcoes_resposta("instruções", "pergunta")

    assert opcoes["num_predict"] == ollama_local.MAX_TOKENS_ESCRITOS
    # O que se pode escrever cabe na reserva do num_ctx: nada se corta.
    assert ollama_local.MAX_TOKENS_ESCRITOS <= ollama_local.TOKENS_RESPOSTA
    assert opcoes["num_ctx"] == 8192
    assert opcoes["temperature"] == 0


def _servico(monkeypatch) -> service_module.RespostaIAService:
    class _Definicoes:
        def __init__(self, session) -> None:
            pass

        def obter_valor(self, chave, default=None):
            return {"provedor_resposta_ia": "local", "modelo_local_ia": "llama3.2"}.get(
                chave, default
            )

    monkeypatch.setattr(service_module, "SystemSettingService", _Definicoes)
    return service_module.RespostaIAService(object())


class _Resposta:
    def __init__(self, pedacos: list[str]) -> None:
        self._linhas = [
            json.dumps({"message": {"content": p}, "done": False}).encode()
            for p in pedacos
        ] + [json.dumps({"message": {"content": ""}, "done": True}).encode()]
        self.fechada = False
        self.lidas = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.fechada = True
        return False

    def __iter__(self):
        for linha in self._linhas:
            self.lidas += 1
            yield linha


def test_pedido_leva_limite_e_keep_alive(monkeypatch) -> None:
    capturado = {}

    def _urlopen(req, timeout):  # noqa: ANN001
        capturado["payload"] = json.loads(req.data.decode("utf-8"))
        return _Resposta(["ok"])

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)
    assert "".join(_servico(monkeypatch).gerar_stream("MDF 22", "contexto")) == "ok"

    payload = capturado["payload"]
    assert payload["keep_alive"] == ollama_local.MANTER_CARREGADO
    assert payload["options"]["num_predict"] == ollama_local.MAX_TOKENS_ESCRITOS


# ----- travão de ciclos -----


def test_ciclo_e_cortado_e_a_ligacao_fechada(monkeypatch) -> None:
    linha = "- [PHC] FM00933: MDF STD CRU 2850X2100X22 | custo 9,10 €\n"
    resposta = _Resposta(["Conclusão:\n"] + [linha] * 500)
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: resposta)

    texto = "".join(_servico(monkeypatch).gerar_stream("MDF 22", "contexto"))

    assert texto.count("FM00933") == ollama_local.REPETICOES_MAX
    assert resposta.fechada
    assert resposta.lidas < 10


def test_linhas_curtas_e_vazias_repetidas_nao_cortam() -> None:
    # Medido a 21-11: «- Fornecedor: MADEIRAS» repete-se de artigo para artigo
    # numa resposta boa, e com o limite antigo (12 letras) era cortada a meio.
    pedacos = ["Preços:\n", "\n", "- 19 mm\n", "\n", "---\n", "---\n", "---\n"]
    for ref in ("FM00084", "FM00214", "FM00933", "FM00742"):
        pedacos += [f"- Referência: {ref}\n", "- Fornecedor: MADEIRAS\n", "- Unidade: MT2\n"]
    pedacos.append("fim")

    assert list(ollama_local.sem_ciclos(iter(pedacos))) == pedacos


def test_linha_partida_em_varios_pedacos_conta_inteira() -> None:
    pedacos = ["- [PHC] FM00933: MDF STD CRU ", "2850X2100X22 | custo 9,10 €\n"] * 5

    texto = "".join(ollama_local.sem_ciclos(iter(pedacos)))

    assert texto.count("9,10") == ollama_local.REPETICOES_MAX


# ----- contexto sem trechos repetidos -----


def test_trechos_iguais_de_ficheiros_duplicados_vao_uma_vez() -> None:
    from app.ui.pages.pesquisa_ia_page import trechos_diferentes

    tabela = "8 10 12\nMDF ST + 01,34 + 01,67"
    resultados = [
        SimpleNamespace(ficheiro="7_BF107_20241009 (1).pdf", trecho=tabela),
        SimpleNamespace(ficheiro="7_BF107_20241009.pdf", trecho=tabela + "  "),
        SimpleNamespace(ficheiro="7_Intasa.pdf", trecho="BRANCO 100GR MDF"),
    ]

    unicos = trechos_diferentes(resultados)

    assert [r.ficheiro for r in unicos] == ["7_BF107_20241009 (1).pdf", "7_Intasa.pdf"]


# ----- pergunta nova manda parar a resposta antiga -----


def test_worker_para_quando_lhe_pedem(monkeypatch) -> None:
    from PySide6.QtCore import QThread
    from app.ui.pages import pesquisa_ia_page as pagina

    class _Servico:
        def __init__(self, session) -> None:
            pass

        def gerar_stream(self, pergunta, contexto):
            for i in range(1000):
                yield f"linha {i}\n"

    class _Thread:
        def isInterruptionRequested(self) -> bool:
            return len(recebidos) >= 3

    recebidos: list[str] = []
    registos: list[tuple] = []
    monkeypatch.setattr(pagina, "RespostaIAService", _Servico)
    monkeypatch.setattr(pagina, "Session", lambda bind=None: _Contexto())
    monkeypatch.setattr(QThread, "currentThread", staticmethod(lambda: _Thread()))
    monkeypatch.setattr(pagina.diario_bordo, "registar_acao", lambda *a: registos.append(a))

    worker = pagina._RespostaWorker("MDF 22", "contexto")
    worker.pedaco.connect(recebidos.append)
    worker.run()

    assert len(recebidos) == 3
    assert "parada (pesquisa nova)" in registos[0][1]
    assert "1.ª palavra" in registos[0][1]


class _Contexto:
    def __enter__(self):
        return object()

    def __exit__(self, *_):
        return False
