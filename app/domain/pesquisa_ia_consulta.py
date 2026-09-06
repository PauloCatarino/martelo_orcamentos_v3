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
