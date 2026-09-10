"""Adaptadores dos catálogos de fornecedores.

Cada fornecedor envia o que quer, como quer: um xlsx da Emuca, dois PDFs da
Balbino & Faustino, um export do site da Casa Trend. Um **adaptador** por
fornecedor traduz esse formato para as duas formas de ``base.py`` —
``TabelaCatalogo`` e ``ArtigoCatalogo`` — e o ``importador`` escreve-as na base
``martelo_catalogos`` sem saber de quem vieram.

A ordem em que os adaptadores foram escritos segue o dinheiro, não a
dificuldade do formato: **Egger primeiro**, que é o que mais se gasta, depois
Sonae/Innovus, e a Finsa no fim.

Nada aqui escreve em matérias-primas — ver ``app/db/catalogos.py``.
"""

from app.services.catalogos.base import ArtigoCatalogo, TabelaCatalogo
from app.services.catalogos.importador import ResultadoImportacao, importar, importar_tabelas

__all__ = [
    "ArtigoCatalogo",
    "ResultadoImportacao",
    "TabelaCatalogo",
    "importar",
    "importar_tabelas",
]
