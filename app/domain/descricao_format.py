"""Pure formatting of multi-line item descriptions to HTML (phase P9)."""

from __future__ import annotations

import html

VERDE_DESTAQUE = "#0a5c0a"


def descricao_para_html(texto: str | None, *, com_cor: bool = True) -> str:
    """Convert a plain multi-line description to formatted HTML.

    - 1.ª/linhas sem prefixo: título a **bold**;
    - linha `- …` (após tabs/espaços): itálico, indentada, com marcador `-`;
    - linha `* …`: itálico + verde (sem o `*`);
    - linha vazia: espaço.
    """
    partes: list[str] = []
    for linha in (texto or "").split("\n"):
        conteudo = linha.lstrip("\t ").rstrip()
        if conteudo.startswith("- "):
            corpo = html.escape(conteudo[2:].strip())
            partes.append(
                f'<div style="margin-left:18px; font-style:italic;">- {corpo}</div>'
            )
        elif conteudo.startswith("* "):
            corpo = html.escape(conteudo[2:].strip())
            estilo = "margin-left:18px; font-style:italic;"
            if com_cor:
                estilo += f" color:{VERDE_DESTAQUE};"
            partes.append(f'<div style="{estilo}">{corpo}</div>')
        elif conteudo:
            partes.append(f'<div style="font-weight:bold;">{html.escape(conteudo)}</div>')
        else:
            partes.append("<div>&nbsp;</div>")
    return "".join(partes)
