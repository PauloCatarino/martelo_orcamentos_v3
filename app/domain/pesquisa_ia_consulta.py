"""Interpretação determinística da pesquisa: referências, acabamentos e espessura."""
from __future__ import annotations
import re
import unicodedata


def normalizar(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def espessura_pedida(texto: str) -> float | None:
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*mm\b", texto, re.I)
    if not match:
        match = re.search(r"\bespessura\s+(\d+(?:[.,]\d+)?)\b", texto, re.I)
    return float(match[1].replace(",", ".")) if match else None


def termos(texto: str) -> list[str]:
    texto = re.sub(r"\b\d+(?:[.,]\d+)?\s*mm\b", " ", texto, flags=re.I)
    palavras = normalizar(texto).split()
    codigos = [p for p in palavras if re.fullmatch(r"[a-z]+\d+[a-z]*", p)]
    if codigos:
        return codigos  # 'qual o preço de H1145?' encontra o código, não a frase.
    ignoradas = set("qual quais o a os as de da do das dos em e para por um uma tem temos existe preco precos stock disponivel disponibilidade quanto custa mostrar procurar pesquisar mm gostaria saber preciso quero queria saber podes pode dizer diga me se ha no na nos nas armazem placas placa material materiais favor por com espessura".split())
    return [p for p in palavras if p not in ignoradas]


def corresponde(alvo: str, texto: str) -> bool:
    normal = normalizar(alvo)
    palavras = set(normal.split())
    # A referência e o acabamento têm de pertencer ao mesmo par, não a duas
    # entradas diferentes nas observações de um grupo de preço.
    pares = re.findall(r"\b([a-z]+\d+)\s+(st\d+|sm|sc|tf|ma|hg)\b", normalizar(texto))
    if any(not re.search(r"\b" + re.escape(ref + " " + st) + r"\b", normal)
           for ref, st in pares):
        return False
    return all((p in palavras if re.fullmatch(r"[a-z]+\d+[a-z]*", p) else p in normal)
               for p in termos(texto))


def mesma_espessura(valor, texto: str, filtro=None) -> bool:
    pedido = filtro or espessura_pedida(texto)
    if pedido is None:
        return True
    try:
        return abs(float(valor) - float(pedido)) < .001
    except (TypeError, ValueError):
        return False


def observacoes_relevantes(observacoes: str, texto: str) -> str:
    refs = termos(texto)
    partes = [p.strip() for p in (observacoes or "").split("|")]
    relevantes = [p for p in partes if corresponde(p, texto)] if refs else partes
    return " | ".join(relevantes)[:1800]


def valor_de_referencia(precos: dict[str, str], espessura=None) -> str:
    """O preço a mostrar na vista geral, de uma referência que tem vários.

    Uma referência de placa traz uma coluna de preço por espessura; uma
    ferragem traz um preço só. Na tabela «Todas» há **uma** célula para o
    valor, e o que lá estava era o grupo de preço — que para as 9 827 ferragens
    era a palavra «Grupo» e mais nada.

    A regra, por ordem: a espessura que a pesquisa pediu; o preço único, quando
    só há um; e senão o intervalo, do mais fino ao mais grosso, que é o que
    responde a «quanto custa isto, mais ou menos» sem inventar uma espessura
    que ninguém pediu.
    """
    if not precos:
        return "sem preço"
    if espessura is not None:
        etiqueta = f"{int(espessura)}mm" if float(espessura).is_integer() else f"{espessura}mm"
        if etiqueta in precos:
            return precos[etiqueta]
    valores = list(precos.values())
    if len(valores) == 1:
        return valores[0]
    return f"{valores[0]} a {valores[-1]}"


def referencia_com_acabamento(referencia: str, acabamento: str) -> str:
    """``W908/SM`` para uma placa, ``22.8000`` para uma dobradiça.

    Sem isto, as ferragens — que não têm acabamento — apareciam todas com uma
    barra pendurada no fim.
    """
    return f"{referencia}/{acabamento}" if acabamento else referencia


def grupo_ou_tipo(grupo: str, tipo: str) -> str:
    """O que a coluna «Tipo / unidade» diz de uma linha de catálogo.

    A coluna responde a «que espécie de coisa é esta», e cada família de
    artigos responde com o que tem:

    * uma **placa** responde com o grupo de preço — ``Grupo 0`` —, que é curto,
      e é por ele que se encontra a matéria-prima correspondente no V3;
    * uma **ferragem** não tem grupo nenhum, e responde com a família do
      catálogo — ``Casa Banho Tulhas Roupa``.

    O Casa Trend não preenche a coluna do grupo, e por isso as suas cinco mil
    linhas apareciam com a célula vazia, quando a folha tinha ali um nome para
    dar. Onde nem grupo nem tipo existem — a Emuca não tem coluna nenhuma
    disso — fica vazio, que é a verdade.
    """
    return (grupo or "").strip() or (tipo or "").strip()
