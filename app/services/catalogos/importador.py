"""Escrever uma ``TabelaCatalogo`` na base ``martelo_catalogos``.

Isto não sabe de fornecedores nem de Excel: recebe o que um adaptador traduziu
e grava. O que sabe é como não fazer estragos ao repetir:

* **Uma tabela com o mesmo ``ficheiro_hash`` não entra duas vezes.** Reimportar
  o mesmo separador não faz nada e diz que não fez nada. É o que permite correr
  a importação sem medo, e o que faz a atualização de uma tabela gerar apenas
  as diferenças.
* **Os artigos reconhecem-se pela chave natural**, não pela posição no
  ficheiro. Um artigo que já cá esteja é atualizado na descrição e nos
  atributos; nunca é duplicado, e nunca é apagado só por ter saído da tabela
  nova — o histórico de preços dele continua a valer.
* **Os preços são acrescentados, nunca reescritos.** Uma linha por preço
  observado, ligada à tabela que o trouxe. É isso que responde a «quanto subiu
  este perfil desde a tabela de 2024».
* **A versão anterior da mesma tabela deixa de ser a que vale**
  (``ativa = False``), mas fica cá. Nada se apaga. «A mesma tabela» é o trio
  fornecedor + fabricante + nome, e é por isso que o ``nome`` que o adaptador
  dá **não leva o ano**: o ano está na ``data_tabela``, e um nome que mudasse
  todos os anos deixava as versões antigas ativas para sempre. A Balbino &
  Faustino vende três tabelas ao mesmo tempo — EGGER, Innovus Brancos e Innovus
  Decorativos — e nenhuma delas pode desativar as outras.

Nada aqui toca em ``def_materias_primas`` — ver ``app/db/catalogos.py``.

Quem chama é que faz ``commit``: assim uma importação de vários separadores
entra toda ou não entra nenhuma.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import String, select
from sqlalchemy.orm import Session

from app.models.catalogos import (
    FornArtigo,
    FornArtigoAlias,
    FornArtigoPreco,
    FornTabelaPreco,
)
from app.services.catalogos.base import ArtigoCatalogo, TabelaCatalogo

#: Campos do artigo que uma tabela nova pode corrigir. A chave natural não está
#: aqui de propósito: mudá-la faria um artigo novo, não uma correção.
CAMPOS_ATUALIZAVEIS = (
    "referencia",
    "descricao",
    "unidade",
    "nome_design",
    "familia",
    "seccao",
    "catalogo",
    "pagina",
    "grupo",
    "fabricante",
    "substrato",
    "espessura_mm",
    "acabamento",
    "formatos",
    "atributos",
    "observacoes",
)


@dataclass
class ResultadoImportacao:
    """O que aconteceu a uma tabela. Feito para se imprimir e se acreditar."""

    fornecedor: str
    nome: str
    tabela_id: int | None = None
    #: O hash já estava na base: não se escreveu nada.
    repetida: bool = False
    artigos_novos: int = 0
    artigos_atualizados: int = 0
    artigos_inalterados: int = 0
    precos_novos: int = 0
    aliases_novos: int = 0
    tabelas_desativadas: int = 0
    avisos: list[str] = field(default_factory=list)

    @property
    def artigos(self) -> int:
        return self.artigos_novos + self.artigos_atualizados + self.artigos_inalterados

    def resumo(self) -> str:
        if self.repetida:
            return (
                f"{self.fornecedor} · {self.nome}: já estava importada "
                f"(tabela {self.tabela_id}), nada a fazer"
            )
        return (
            f"{self.fornecedor} · {self.nome}: {self.artigos} artigos "
            f"({self.artigos_novos} novos, {self.artigos_atualizados} atualizados), "
            f"{self.precos_novos} preços"
        )


#: Limites de comprimento das colunas de texto, lidos do próprio modelo.
LIMITES: dict[str, int] = {
    coluna.name: coluna.type.length
    for coluna in FornArtigo.__table__.columns
    if isinstance(coluna.type, String) and coluna.type.length
}


class ValorGrandeDemais(ValueError):
    """Um campo não cabe na coluna.

    Vale a pena ter exceção própria: sem ela isto chegava como um ``DataError``
    do MySQL a meio de dezassete mil linhas, sem dizer que artigo nem que
    campo. É sempre um erro do adaptador — a coluna certa para um texto
    comprido é a ``descricao`` ou os ``atributos``, que não têm limite.
    """


def _valores(artigo: ArtigoCatalogo, tabela: TabelaCatalogo) -> dict[str, object]:
    """Os campos do modelo a partir da forma do adaptador."""
    valores = {campo: getattr(artigo, campo) for campo in CAMPOS_ATUALIZAVEIS}
    valores["fabricante"] = artigo.fabricante or tabela.fabricante

    for campo, limite in LIMITES.items():
        valor = valores.get(campo)
        if isinstance(valor, str) and len(valor) > limite:
            raise ValorGrandeDemais(
                f"{tabela.fornecedor} · {tabela.nome}: o campo {campo!r} do "
                f"artigo {artigo.chave_natural!r} tem {len(valor)} caracteres "
                f"e a coluna aceita {limite}: {valor[:80]!r}…"
            )
    if len(artigo.chave_natural) > LIMITES.get("chave_natural", 300):
        raise ValorGrandeDemais(
            f"{tabela.fornecedor} · {tabela.nome}: a chave natural tem "
            f"{len(artigo.chave_natural)} caracteres e a coluna aceita "
            f"{LIMITES['chave_natural']}: {artigo.chave_natural[:80]!r}…"
        )
    return valores


def importar(
    session: Session, tabela: TabelaCatalogo, *, forcar: bool = False
) -> ResultadoImportacao:
    """Grava uma tabela. Não faz ``commit`` — ver a docstring do módulo.

    Com ``forcar=True`` a tabela entra mesmo que o hash já esteja na base, o
    que serve para reimportar depois de se corrigir o adaptador. Continua a não
    apagar nada: fica uma tabela nova ao lado da antiga. Nesse caso a nova fica
    **sem** ``ficheiro_hash`` — a coluna é única e a linha antiga é que tem
    direito ao hash daquele conteúdo — e o hash vai para as ``observacoes``,
    para a reimportação continuar a ser rastreável.
    """
    resultado = ResultadoImportacao(
        fornecedor=tabela.fornecedor,
        nome=tabela.nome,
        avisos=list(tabela.avisos),
    )

    hash_a_gravar = tabela.ficheiro_hash
    observacoes = tabela.observacoes

    if tabela.ficheiro_hash:
        ja_existe = session.scalars(
            select(FornTabelaPreco).where(
                FornTabelaPreco.ficheiro_hash == tabela.ficheiro_hash
            )
        ).first()
        if ja_existe is not None:
            if not forcar:
                resultado.repetida = True
                resultado.tabela_id = ja_existe.id
                return resultado
            hash_a_gravar = None
            nota = (
                f"Reimportação forçada do mesmo conteúdo (hash "
                f"{tabela.ficheiro_hash}, já na tabela {ja_existe.id})."
            )
            observacoes = f"{observacoes}\n{nota}" if observacoes else nota
            resultado.avisos.append(nota)

    # A versão anterior da mesma tabela deixa de ser a que vale — e só ela.
    anteriores = session.scalars(
        select(FornTabelaPreco).where(
            FornTabelaPreco.fornecedor == tabela.fornecedor,
            FornTabelaPreco.fabricante == tabela.fabricante,
            FornTabelaPreco.nome == tabela.nome,
            FornTabelaPreco.ativa.is_(True),
        )
    ).all()
    for anterior in anteriores:
        anterior.ativa = False
        resultado.tabelas_desativadas += 1

    registo = FornTabelaPreco(
        fornecedor=tabela.fornecedor,
        fabricante=tabela.fabricante,
        nome=tabela.nome,
        referencia_tabela=tabela.referencia_tabela,
        data_tabela=tabela.data_tabela,
        ficheiro_origem=tabela.ficheiro_origem,
        ficheiro_hash=hash_a_gravar,
        moeda=tabela.moeda,
        unidade_preco=tabela.unidade_preco,
        observacoes=observacoes,
        ativa=True,
        importada_em=datetime.now(),
    )
    session.add(registo)
    session.flush()
    resultado.tabela_id = registo.id

    # Os artigos deste fornecedor de uma vez, em vez de uma consulta por linha:
    # a WoodSide sozinha traz 2 090 artigos.
    existentes = {
        artigo.chave_natural: artigo
        for artigo in session.scalars(
            select(FornArtigo).where(FornArtigo.fornecedor == tabela.fornecedor)
        )
    }

    vistos: set[str] = set()
    for artigo in tabela.artigos:
        if artigo.chave_natural in vistos:
            resultado.avisos.append(
                f"chave natural repetida no ficheiro, segunda ignorada: "
                f"{artigo.chave_natural}"
            )
            continue
        vistos.add(artigo.chave_natural)

        valores = _valores(artigo, tabela)
        registo_artigo = existentes.get(artigo.chave_natural)

        if registo_artigo is None:
            registo_artigo = FornArtigo(
                fornecedor=tabela.fornecedor,
                chave_natural=artigo.chave_natural,
                ativo=True,
                **valores,
            )
            session.add(registo_artigo)
            session.flush()
            existentes[artigo.chave_natural] = registo_artigo
            resultado.artigos_novos += 1
        else:
            mudou = False
            for campo, valor in valores.items():
                if getattr(registo_artigo, campo) != valor:
                    setattr(registo_artigo, campo, valor)
                    mudou = True
            if not registo_artigo.ativo:
                registo_artigo.ativo = True
                mudou = True
            if mudou:
                resultado.artigos_atualizados += 1
            else:
                resultado.artigos_inalterados += 1

        session.add(
            FornArtigoPreco(
                artigo_id=registo_artigo.id,
                tabela_preco_id=registo.id,
                referencia=artigo.referencia,
                valor=artigo.preco,
                moeda=tabela.moeda,
                unidade=artigo.unidade,
                desconto=artigo.desconto,
                valido_de=tabela.data_tabela,
            )
        )
        resultado.precos_novos += 1

        for tipo, valor_alias in artigo.aliases:
            existe = session.scalars(
                select(FornArtigoAlias).where(
                    FornArtigoAlias.artigo_id == registo_artigo.id,
                    FornArtigoAlias.tipo == tipo,
                    FornArtigoAlias.valor == valor_alias,
                )
            ).first()
            if existe is None:
                session.add(
                    FornArtigoAlias(
                        artigo_id=registo_artigo.id, tipo=tipo, valor=valor_alias
                    )
                )
                resultado.aliases_novos += 1

    session.flush()
    return resultado


def importar_tabelas(
    session: Session, tabelas: list[TabelaCatalogo], *, forcar: bool = False
) -> list[ResultadoImportacao]:
    """Importa várias tabelas pela ordem em que vêm."""
    return [importar(session, tabela, forcar=forcar) for tabela in tabelas]
