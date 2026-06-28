"""Pure formatting of multi-line item descriptions (phase P9)."""

from __future__ import annotations

from dataclasses import dataclass
import html

VERDE_DESTAQUE = "#0a5c0a"


@dataclass(frozen=True)
class LinhaDescricao:
    """One parsed line of an item description."""

    tipo: str
    texto: str


def parse_descricao(texto: str | None) -> list[LinhaDescricao]:
    """Parse a plain multi-line description into semantic lines."""
    if texto is None:
        return []

    linhas: list[LinhaDescricao] = []
    for linha in texto.split("\n"):
        conteudo = linha.lstrip("\t ").rstrip()
        if conteudo.startswith("- "):
            linhas.append(LinhaDescricao("traco", conteudo[2:].strip()))
        elif conteudo.startswith("* "):
            linhas.append(LinhaDescricao("estrela", conteudo[2:].strip()))
        elif conteudo:
            linhas.append(LinhaDescricao("titulo", conteudo))
        else:
            linhas.append(LinhaDescricao("vazia", ""))
    return linhas


def descricao_para_html(texto: str | None, *, com_cor: bool = True) -> str:
    """Convert a plain multi-line description to formatted HTML."""
    partes: list[str] = []
    for linha in parse_descricao(texto or ""):
        if linha.tipo == "traco":
            corpo = html.escape(linha.texto)
            partes.append(
                f'<div style="margin-left:18px; font-style:italic;">- {corpo}</div>'
            )
        elif linha.tipo == "estrela":
            corpo = html.escape(linha.texto)
            estilo = "margin-left:18px; font-style:italic;"
            if com_cor:
                estilo += f" color:{VERDE_DESTAQUE};"
            partes.append(f'<div style="{estilo}">{corpo}</div>')
        elif linha.tipo == "titulo":
            partes.append(
                f'<div style="font-weight:bold;">{html.escape(linha.texto)}</div>'
            )
        else:
            partes.append("<div>&nbsp;</div>")
    return "".join(partes)


def descricao_para_reportlab(texto: str | None, *, com_cor: bool = True) -> str:
    """Convert a plain multi-line description to ReportLab paragraph markup."""
    partes: list[str] = []
    for linha in parse_descricao(texto):
        esc = html.escape(linha.texto)
        if linha.tipo == "titulo":
            partes.append(f"<b>{esc}</b>")
        elif linha.tipo == "traco":
            partes.append(f"&nbsp;&nbsp;<i>- {esc}</i>")
        elif linha.tipo == "estrela":
            if com_cor:
                partes.append(
                    f'&nbsp;&nbsp;<i><font color="{VERDE_DESTAQUE}">{esc}</font></i>'
                )
            else:
                partes.append(f"&nbsp;&nbsp;<i>{esc}</i>")
        else:
            partes.append("&nbsp;")
    return "<br/>".join(partes)
