"""Regras puras do tempo ativo no iMos e no Excel da Lista Material.

Nem o iMos nem o Excel guardam o tempo de trabalho: a base do iMos só regista
as gravações de cada encomenda (sem utilizador), e o Excel não guarda tempo de
edição no ficheiro (verificado a 24-09-2026). Quem sabe o que está a ser
trabalhado é a janela em primeiro plano:

    iX CAD 2025 - [0406_01_26_JF_VIVA.dwg]
    Lista_Material_1599_01_26_TEMPO_PLURAL.xlsm - Excel

Em ambos está o nome da encomenda no iMos, o mesmo que o Martelo dá à obra
(``gerar_nome_enc_imos_ix``). É por ele que o tempo chega à linha certa da
Produção.
"""

from __future__ import annotations

import re
from typing import NamedTuple

PROGRAMA_IMOS = "imos"
PROGRAMA_EXCEL = "excel"

#: Sem rato nem teclado há mais do que isto, deixa de contar. No desenho
#: passa-se tempo a olhar e a pensar sem mexer no rato (decisão do Paulo).
LIMITE_INATIVIDADE_SEGUNDOS = 300.0

#: Nome de encomenda iMos: ``1599_01_26_TEMPO_PLURAL`` ou ``_263_01_26_RUI_…``.
#: Um desenho solto (``Drawing1.dwg``) ou um de orçamento (``ORC_260881_…``)
#: não é obra de produção e fica de fora.
_NOME_ENCOMENDA = re.compile(r"^_?\d{3,4}_\d{2}_\d{2}_\S.*$")
_DESENHO_IMOS = re.compile(r"\[([^\]]*?)\.dwg\b", re.IGNORECASE)
_LISTA_MATERIAL = re.compile(r"Lista_Material_(.+?)\.xls[a-z]?\b", re.IGNORECASE)

#: Tamanho da coluna na base; os nomes do iMos têm no máximo 30.
TAMANHO_NOME = 80


class JanelaIdentificada(NamedTuple):
    programa: str
    nome_encomenda: str


def identificar_janela(processo: str, titulo: str) -> JanelaIdentificada | None:
    """Que encomenda está a ser trabalhada nesta janela, se for iMos ou Excel.

    ``processo`` é o nome do executável (``imos.exe``); quando o Windows não o
    deixar ler vem vazio, e decide o título.
    """
    exe = (processo or "").strip().lower()
    texto = (titulo or "").strip()
    if not texto:
        return None

    if exe == "imos.exe" or (not exe and texto.lower().startswith("ix cad")):
        encontrado = _DESENHO_IMOS.search(texto)
        if encontrado:
            return _so_se_for_encomenda(PROGRAMA_IMOS, encontrado.group(1))
        return None

    if exe == "excel.exe" or (not exe and texto.lower().endswith("- excel")):
        encontrado = _LISTA_MATERIAL.search(texto)
        if encontrado:
            return _so_se_for_encomenda(PROGRAMA_EXCEL, encontrado.group(1))
    return None


def _so_se_for_encomenda(programa: str, bruto: str) -> JanelaIdentificada | None:
    # O iMos pode mostrar o caminho inteiro do desenho: fica só o nome.
    nome = re.split(r"[\\/]", bruto.strip())[-1].strip()
    if not _NOME_ENCOMENDA.match(nome):
        return None
    return JanelaIdentificada(programa, nome[:TAMANHO_NOME])


def chave_encomenda(nome: str | None) -> str:
    """Forma de comparar nomes (o Windows e o iMos não ligam a maiúsculas)."""
    return " ".join(str(nome or "").split()).casefold()
