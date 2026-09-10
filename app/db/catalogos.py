"""Base declarativa dos catálogos de fornecedores.

As tabelas de preços que os fornecedores enviam servem para **consultar** — a
Pesquisa IA responde ao utilizador em vez de ele andar por sites, telefonemas e
emails. As matérias-primas (``def_materias_primas``) são outra coisa: são o
registo de que dependem os orçamentos e o custeio, e estão a ser ligadas às
ferragens do iMos.

Por isso os catálogos vivem numa base própria — ``martelo_catalogos``, no mesmo
servidor MySQL dos orçamentos. A base dos catálogos reconstrói-se a partir dos
ficheiros de origem sempre que for preciso; a dos orçamentos não. Mantê-las
separadas é o que torna essa reconstrução inofensiva.

**Duas regras que não se atravessam:**

* nenhuma chave estrangeira liga os dois lados — o fornecedor fica aqui como
  texto, não como referência a ``def_fornecedores``;
* nada escreve em matérias-primas a partir de um catálogo. Passar um artigo
  pesquisado a matéria-prima é uma decisão do utilizador, no formulário do
  costume.

A ligação é a mesma (o ``SessionLocal``, com a conta MySQL de quem entrou na
app): estando as duas bases no mesmo servidor, as tabelas daqui são alcançadas
com o nome qualificado e não é preciso uma segunda ligação a acompanhar o
login. O que é preciso são privilégios — ver a migração ``20260910_112``.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase

from app.config.settings import settings

#: Nome da base dos catálogos. Vem do ``.env`` (``DB_CATALOGOS_NAME``) para que
#: um ambiente de testes ou de beta possa apontar para outro sítio.
SCHEMA_CATALOGOS = settings.DB_CATALOGOS_NAME


class CatalogosBase(DeclarativeBase):
    """Base dos modelos de catálogo.

    Deliberadamente separada da ``app.db.base.Base``: assim os catálogos nunca
    entram no ``metadata`` dos orçamentos, e um ``create_all`` de um lado nunca
    cria tabelas do outro.
    """


#: Usado pelo alembic (ver ``alembic/env.py``) e pelos testes.
catalogos_metadata = CatalogosBase.metadata
