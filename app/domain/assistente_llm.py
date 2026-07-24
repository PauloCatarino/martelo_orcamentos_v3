"""Camada LLM do IA Martelo: o modelo propõe filtros, o código valida.

O modelo local (Ollama) percebe a pergunta em linguagem natural e devolve
**apenas JSON** com os filtros. Este módulo:

1. constrói as instruções (system) que ensinam o modelo a responder em JSON e a
   recusar temas fora do trabalho de mobiliário;
2. valida o JSON contra os **valores reais** da lista — o modelo nunca escolhe
   um cliente ou estado que não exista, por isso não pode inventar dados. O pior
   que faz é propor um filtro a menos, que cai para texto livre.

Se o modelo falhar ou não estiver disponível, o serviço volta ao cérebro
determinístico (:mod:`app.domain.assistente_intencao`).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from app.domain.assistente_intencao import Intencao, resolver_estado
from app.domain.pesquisa_texto import normalizar
from app.domain.producao_estados import ESTADOS_PRODUCAO

#: Campos de texto onde está o resumo da obra (contexto para o modelo).
_CAMPOS_RESUMO = (
    "Descrição artigos, Matérias usados, Descrição produção, Notas 1/2/3"
)

_INSTRUCOES = f"""És o «IA Martelo», assistente interno de uma empresa de \
mobiliário. Ajudas a encontrar OBRAS no menu Produção, traduzindo a pergunta \
em filtros. Respondes SEMPRE e SÓ com um objeto JSON, sem texto à volta.

Só trabalhas assuntos profissionais de mobiliário e produção. Se a pergunta \
tiver violência, linguagem imprópria ou for fora do trabalho, devolve \
{{"recusa": "Só posso ajudar em assuntos das obras e da produção."}}.

Campos JSON possíveis (usa só os que fizerem sentido):
- "termos": palavras de pesquisa livre (descrição do móvel, materiais, \
ferragens); procuram-se nos campos {_CAMPOS_RESUMO}.
- "estado": um de {list(ESTADOS_PRODUCAO)} (ex.: «na máquina»=Producao, \
«obra fechada»=Arquivado).
- "cliente": nome do cliente tal como aparece na pergunta.
- "responsavel": nome da pessoa responsável tal como aparece na pergunta.
- "so_atrasadas": true se pedir obras atrasadas / em atraso.
- "pergunta": se a pergunta for ambígua (ex.: um nome pode ser cliente OU \
pessoa), NÃO adivinhes — devolve aqui a pergunta de esclarecimento.

Não inventes valores. Se não tiveres a certeza de um filtro, deixa-o de fora."""


def construir_mensagens(pergunta: object, perfil_texto: str = "") -> tuple[str, str]:
    """Devolve (system, user) para o modelo local."""
    system = _INSTRUCOES
    if perfil_texto.strip():
        system += (
            "\n\nVocabulário deste utilizador (alcunhas e palavras ambíguas):\n"
            + perfil_texto.strip()
        )
    user = f'Pergunta: "{str(pergunta).strip()}"\nResponde só com o JSON.'
    return system, user


def extrair_json(texto: object) -> dict:
    """Extrai o primeiro objeto JSON de uma resposta do modelo, tolerante.

    Modelos pequenos às vezes embrulham o JSON em ```json ...``` ou texto; aqui
    apanha-se o primeiro bloco ``{...}`` equilibrado.
    """
    if not texto:
        return {}
    bruto = str(texto).strip()
    bruto = re.sub(r"^```(?:json)?", "", bruto).strip()
    bruto = re.sub(r"```$", "", bruto).strip()

    inicio = bruto.find("{")
    if inicio < 0:
        return {}
    profundidade = 0
    for fim in range(inicio, len(bruto)):
        if bruto[fim] == "{":
            profundidade += 1
        elif bruto[fim] == "}":
            profundidade -= 1
            if profundidade == 0:
                try:
                    dados = json.loads(bruto[inicio : fim + 1])
                except (ValueError, TypeError):
                    return {}
                return dados if isinstance(dados, dict) else {}
    return {}


def intencao_de_json(
    dados: dict,
    *,
    clientes: Iterable[str] = (),
    responsaveis: Iterable[str] = (),
) -> tuple[Intencao, str]:
    """Valida o JSON do modelo contra os valores reais e devolve (Intencao, recusa).

    Cliente/estado/responsável só entram se existirem mesmo; caso contrário são
    descartados (o modelo não pode inventar). ``recusa`` traz a mensagem quando
    o modelo recusou a pergunta.
    """
    if not isinstance(dados, dict):
        return Intencao(), ""

    recusa = _texto_ou_vazio(dados.get("recusa"))
    if recusa:
        return Intencao(), recusa

    pergunta = _texto_ou_vazio(dados.get("pergunta"))
    if pergunta:
        # Ambiguidade sinalizada pelo modelo: perguntar, não filtrar.
        return Intencao(perguntas=(pergunta,)), ""

    estado = resolver_estado(dados.get("estado")) if dados.get("estado") else None
    cliente = _casar_valor(dados.get("cliente"), clientes)
    responsavel = _casar_valor(dados.get("responsavel"), responsaveis)
    so_atrasadas = bool(dados.get("so_atrasadas"))
    termos = _texto_ou_vazio(dados.get("termos"))

    return (
        Intencao(
            termos=termos,
            estado=estado,
            cliente=cliente,
            responsavel=responsavel,
            so_atrasadas=so_atrasadas,
        ),
        "",
    )


def _texto_ou_vazio(valor: object) -> str:
    return str(valor).strip() if isinstance(valor, str) else ""


def _casar_valor(valor: object, valores: Iterable[str]) -> str | None:
    """Nome real que casa com o proposto pelo modelo (sem distinguir acentos)."""
    alvo = normalizar(valor)
    if not alvo:
        return None
    for existente in valores:
        if normalizar(existente) == alvo:
            return existente
    return None
