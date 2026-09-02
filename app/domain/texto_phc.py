"""Quebra de linhas para a coluna Designacao do Excel do PHC.

O PHC corta a designacao aos 55 caracteres por linha: o que passar disso
desaparece na importacao, sem aviso nenhum. Aqui parte-se o texto ANTES de
gravar, e parte-se por PALAVRAS -- cortar a meio de "CORREDIÇA" daria uma
designacao que ninguem percebe do outro lado.

Puro de proposito: e' a regra que decide o que o cliente le' no PHC.
"""

from __future__ import annotations

#: Quantos caracteres cabem numa linha da designacao do PHC.
MAX_CARACTERES_LINHA = 55


def quebrar_designacao(texto, *, limite: int = MAX_CARACTERES_LINHA) -> list[str]:
    """Parte ``texto`` em linhas de, no maximo, ``limite`` caracteres.

    Parte por espacos. Uma palavra maior do que o limite (uma referencia
    comprida, por exemplo) e' cortada a` forca -- vale mais entrar cortada do
    que fazer a linha estourar o limite e ser truncada pelo PHC.

    O prefixo de lista ("- ", "* ") vem ja' no texto e conta para o limite; as
    linhas seguintes da mesma frase ficam alinhadas por baixo dele.
    """
    limpo = str(texto or "").strip()
    if not limpo:
        return []
    if limite < 1:
        raise ValueError("O limite de caracteres tem de ser pelo menos 1.")

    linhas: list[str] = []
    atual = ""
    for palavra in limpo.split():
        while len(palavra) > limite:
            # Palavra maior do que a linha inteira: parte-se onde der.
            if atual:
                linhas.append(atual)
                atual = ""
            linhas.append(palavra[:limite])
            palavra = palavra[limite:]
        if not atual:
            atual = palavra
        elif len(atual) + 1 + len(palavra) <= limite:
            atual = f"{atual} {palavra}"
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas
