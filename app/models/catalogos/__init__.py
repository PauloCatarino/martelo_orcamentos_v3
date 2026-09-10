"""Modelos dos catálogos de fornecedores (base ``martelo_catalogos``).

Este pacote **não** é importado por ``app.models``: os catálogos são uma base à
parte e não devem entrar no ``metadata`` dos orçamentos. Quem precisa deles
importa-os daqui de propósito — o alembic (``alembic/env.py``) e os serviços de
catálogo.
"""

from app.models.catalogos.forn_artigo import FornArtigo
from app.models.catalogos.forn_artigo_alias import FornArtigoAlias
from app.models.catalogos.forn_artigo_preco import FornArtigoPreco
from app.models.catalogos.forn_tabela_preco import FornTabelaPreco

__all__ = [
    "FornArtigo",
    "FornArtigoAlias",
    "FornArtigoPreco",
    "FornTabelaPreco",
]
