"""Read a price list that came as a PDF instead of the attachment we sent.

Some suppliers answer with their own list, as a PDF, and nobody is going to
retype two hundred lines by hand. A PDF has no columns — only text laid out in
lines — so this reads line by line and looks, in each one, for a reference we
know and a price. What it cannot recognise it drops in silence: better to bring
back fewer lines that are right than many that were invented.

The result comes out in the same shape as a worksheet (headers + rows), so
everything downstream — the reading rules, the anomaly warnings and the review
screen — works exactly as with the Excel answer. And, as always, nothing is
written to the catalog without a person ticking the line.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from app.domain.pedido_precos import (
    COLUNA_CODIGO,
    COLUNA_DESCONTO,
    COLUNA_DESIGNACAO,
    COLUNA_OBSERVACOES,
    COLUNA_PRECO_NOVO,
)
from app.domain.resposta_fornecedor import PADRAO_REF_LE, to_decimal

#: Os cabeçalhos que fabricamos para o resto do circuito ler como sempre.
CABECALHOS_PDF = (
    COLUNA_CODIGO,
    COLUNA_DESIGNACAO,
    COLUNA_PRECO_NOVO,
    COLUNA_DESCONTO,
    COLUNA_OBSERVACOES,
)

#: Um número com cara de preço: 24,87 · 1.234,56 · 24.87 · 15
PADRAO_NUMERO = re.compile(r"^[+-]?\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d+)?$|^[+-]?\d+(?:[.,]\d+)?$")

#: Percentagens só são lidas como desconto quando vêm escritas com o sinal.
PADRAO_PERCENTAGEM = re.compile(r"^([+-]?\d+(?:[.,]\d+)?)\s*%$")


def e_pdf(caminho: str | Path) -> bool:
    """Se este ficheiro é um PDF (pelo nome)."""
    return Path(caminho).suffix.lower() == ".pdf"


def ler_pdf(
    caminho: str | Path,
    reconhecer: Callable[[str], bool] | None = None,
) -> tuple[list, list, int]:
    """Ler um PDF e devolver (cabeçalhos, linhas, número da primeira linha).

    ``reconhecer`` diz se um pedaço de texto é uma referência que conhecemos —
    a nossa Ref LE ou a referência do fornecedor. Sem ela, só as linhas com
    algo com a cara de uma Ref LE são aproveitadas.
    """
    linhas = []
    for texto in _linhas_do_pdf(caminho):
        linha = interpretar_linha(texto, reconhecer)
        if linha is not None:
            linhas.append(linha)

    return list(CABECALHOS_PDF), linhas, 1


def interpretar_linha(
    texto: str,
    reconhecer: Callable[[str], bool] | None = None,
) -> tuple | None:
    """O que se consegue tirar de uma linha de texto de um PDF.

    Devolve None quando a linha não tem os dois ingredientes obrigatórios: uma
    referência que reconheçamos e um preço.
    """
    palavras = texto.split()
    if len(palavras) < 2:
        return None

    indice_ref = _indice_da_referencia(palavras, reconhecer)
    if indice_ref is None:
        return None

    desconto, indice_desconto = _desconto(palavras)
    preco, indice_preco = _preco(palavras, indice_ref, indice_desconto)
    if preco is None:
        return None

    fim = min(indice for indice in (indice_preco, indice_desconto) if indice is not None)
    designacao = " ".join(palavras[indice_ref + 1 : fim]).strip(" -:·")

    return (
        palavras[indice_ref].strip(" .,;:"),
        designacao or None,
        preco,
        desconto,
        f"Lido do PDF: {texto.strip()}",
    )


def _indice_da_referencia(
    palavras: list, reconhecer: Callable[[str], bool] | None
) -> int | None:
    """Em que palavra está a referência do artigo."""
    if reconhecer is not None:
        for indice, palavra in enumerate(palavras):
            if reconhecer(palavra.strip(" .,;:")):
                return indice

    for indice, palavra in enumerate(palavras):
        if PADRAO_REF_LE.match(palavra.strip(" .,;:").upper()):
            return indice

    return None


def _desconto(palavras: list) -> tuple:
    """O desconto, quando vem escrito com o sinal de percentagem."""
    for indice in range(len(palavras) - 1, -1, -1):
        encontrado = PADRAO_PERCENTAGEM.match(palavras[indice])
        if encontrado:
            return to_decimal(encontrado.group(1)), indice

    return None, None


def _preco(palavras: list, indice_ref: int, indice_desconto: int | None) -> tuple:
    """O preço é o último número da linha que não seja o desconto."""
    for indice in range(len(palavras) - 1, indice_ref, -1):
        if indice == indice_desconto:
            continue
        bruto = palavras[indice].replace("€", "").strip(" .,;:")
        if not PADRAO_NUMERO.match(bruto):
            continue
        valor = to_decimal(bruto)
        if valor is not None and valor > 0:
            return valor, indice

    return None, None


def _linhas_do_pdf(caminho: str | Path) -> list:
    """O texto do PDF, linha a linha, página a página."""
    from pypdf import PdfReader

    leitor = PdfReader(str(caminho))
    linhas: list = []
    for pagina in leitor.pages:
        texto = pagina.extract_text() or ""
        linhas.extend(linha for linha in texto.splitlines() if linha.strip())

    return linhas


def resumo_da_leitura(linhas, total_texto: int | None = None) -> str:
    """Uma linha a dizer o que se conseguiu tirar do PDF."""
    if not linhas:
        return (
            "Não foi possível reconhecer nenhuma linha neste PDF. Se o ficheiro "
            "for uma imagem digitalizada, o texto não pode ser lido."
        )

    aviso = (
        f"{len(linhas)} linhas reconhecidas no PDF. A leitura de um PDF é sempre "
        "um palpite: confirme os preços antes de aplicar."
    )
    if total_texto:
        return f"{aviso} ({total_texto} linhas de texto no ficheiro.)"

    return aviso
