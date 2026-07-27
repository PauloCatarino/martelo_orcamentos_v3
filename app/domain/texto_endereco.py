"""Limpar um endereço colado do chat, do Outlook ou de uma página.

Um endereço copiado traz muitas vezes um espaço invisível agarrado — um
espaço-duro, um zero-width, uma marca de direção. A olho nu o endereço parece
perfeito, e o Teams desiste de o reconhecer sem dizer porquê: abre a janela de
mensagem nova com o «Para:» vazio.
"""

from __future__ import annotations

import re


#: Espaços e marcas invisíveis que nunca fazem parte de um endereço:
#: espaço-duro, zero-width (space/non-joiner/joiner), word joiner, BOM e as
#: marcas de direção do Unicode.
_INVISIVEIS = re.compile(
    r"[\s ​-‏  ‪-‮⁠﻿]"
)


def limpar_endereco(email: object) -> str:
    """Return the address without invisible characters and outer spaces."""
    return _INVISIVEIS.sub("", str(email or "")).strip()


def endereco_suspeito(email: object) -> bool:
    """True quando o endereço tem caracteres que o Teams não vai reconhecer.

    Serve para avisar quem escreveu, em vez de o deixar às voltas a perguntar
    porque é que só aquela pessoa não funciona.
    """
    original = str(email or "")
    return bool(original.strip()) and limpar_endereco(original) != original.strip()
