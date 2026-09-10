"""Ler os catálogos da base ``martelo_catalogos`` para quem os mostra.

Este módulo é o caminho de volta: os adaptadores da Fase 2 desmontaram o Excel
e escreveram artigos; aqui volta-se a montar o que o ecrã da Pesquisa IA e o
indexador precisam de ver. É de **leitura apenas** — nada aqui escreve.

Duas formas de olhar para os mesmos artigos:

* ``listar_artigos`` dá uma linha por artigo, como está na base: uma espessura,
  um preço. É o que o indexador quer, porque cada frase indexada tem de ter um
  preço só.
* ``listar_referencias`` volta a juntar as espessuras da mesma referência numa
  linha com uma coluna por espessura — a forma do Excel curado, que é como o
  Paulo está habituado a ver a tabela. O desdobramento da Fase 2 e este
  redobramento são inversos um do outro.

**Só as tabelas ativas contam.** Reimportar uma tabela desativa a anterior sem
a apagar; quem consulta vê a que vale hoje, e o histórico de preços continua
inteiro para quem o for procurar.
"""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalogos import FornArtigo, FornArtigoPreco, FornTabelaPreco
from app.utils.formatters import format_currency

#: Chave usada no dicionário de preços quando o artigo não tem espessura — uma
#: dobradiça ou um puxador. Sem isto os 9 827 artigos de ferragens entravam na
#: tabela sem preço nenhum à vista, que foi o que sempre aconteceu enquanto
#: isto se lia do Excel.
CHAVE_PRECO_UNITARIO = "Preço un."


@dataclass(frozen=True)
class ArtigoConsulta:
    """Um artigo de catálogo com o preço da tabela que vale hoje."""

    fornecedor: str
    fabricante: str | None
    tabela: str
    folha: str
    data_tabela: date | None
    chave_natural: str
    referencia: str
    descricao: str
    nome_design: str | None
    acabamento: str | None
    substrato: str | None
    substrato_origem: str | None
    espessura_mm: Decimal | None
    espessura: str | None
    familia: str | None
    seccao: str | None
    grupo: str | None
    #: O «Tipo Produto» da coluna do Excel — ver ``_tipo``.
    tipo: str
    unidade: str
    preco: Decimal | None
    artigo_id: int
    tabela_id: int
    #: Todos os preços que a tabela dá a esta referência nesta medida, quando
    #: são mais do que um. Vazio no caso normal. Ver ``_marcar_ambiguos``.
    precos_da_medida: tuple[Decimal, ...] = ()
    #: Falso quando existe outro preço mais alto para a mesma coisa e é esse
    #: que vale por decisão do Paulo.
    preco_a_considerar: bool = True

    @property
    def etiqueta_preco(self) -> str:
        """A chave deste preço na linha redobrada: ``19mm`` ou ``Preço un.``."""
        return self.espessura or CHAVE_PRECO_UNITARIO


@dataclass(frozen=True)
class LinhaReferencia:
    """Uma referência com todas as suas espessuras, como no Excel curado.

    Vive aqui, e não no ``placas_referencias_service`` que a mostra, porque é
    daqui que passou a vir. O serviço antigo continua a exportá-la para que
    nada de fora precise de saber que a origem mudou.
    """

    folha: str
    referencia: str
    st_acab: str
    nome_design: str
    grupo: str
    tipo: str
    fornecedor: str
    precos: dict[str, str]


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor).strip()


def _espessura(artigo: FornArtigo, atributos: dict) -> str | None:
    """A etiqueta da espessura — ``19mm`` — como o Excel a escrevia.

    Vem dos atributos porque foi o adaptador que a leu do cabeçalho; o
    ``espessura_mm`` é a garantia de que ela existe mesmo que os atributos
    tenham sido escritos por uma versão anterior.
    """
    etiqueta = _texto(atributos.get("espessura"))
    if etiqueta:
        return etiqueta
    if artigo.espessura_mm is None:
        return None
    numero = artigo.espessura_mm.normalize()
    inteiro = int(numero) if numero == numero.to_integral_value() else numero
    return f"{inteiro}mm"


def _tipo(artigo: FornArtigo, atributos: dict) -> str:
    """O «Tipo Produto» da coluna do Excel.

    O Egger guarda o texto inteiro nos atributos (a ``familia`` dele é só a
    primeira palavra, «Eurodekor»); os outros põem-no na ``familia``. A
    ``seccao`` fica em último porque em três dos adaptadores ela é o substrato
    de origem, que já tem coluna própria.
    """
    return (
        _texto(atributos.get("tipo_produto"))
        or _texto(artigo.familia)
        or _texto(artigo.seccao)
    )


def _consulta_base():
    return (
        select(FornTabelaPreco, FornArtigo, FornArtigoPreco)
        .join(FornArtigoPreco, FornArtigoPreco.tabela_preco_id == FornTabelaPreco.id)
        .join(FornArtigo, FornArtigo.id == FornArtigoPreco.artigo_id)
        .where(FornTabelaPreco.ativa.is_(True), FornArtigo.ativo.is_(True))
        .order_by(FornTabelaPreco.id, FornArtigo.id, FornArtigoPreco.id)
    )


def listar_artigos(session: Session) -> list[ArtigoConsulta]:
    """Um artigo por linha, com o preço da tabela ativa que o trouxe."""
    linhas: list[ArtigoConsulta] = []
    for tabela, artigo, preco in session.execute(_consulta_base()).all():
        atributos = artigo.atributos or {}
        linhas.append(
            ArtigoConsulta(
                fornecedor=tabela.fornecedor,
                fabricante=artigo.fabricante or tabela.fabricante,
                tabela=tabela.nome,
                folha=_texto(atributos.get("folha")),
                data_tabela=tabela.data_tabela,
                chave_natural=artigo.chave_natural,
                referencia=_texto(artigo.referencia),
                descricao=_texto(artigo.descricao),
                nome_design=artigo.nome_design,
                acabamento=artigo.acabamento,
                substrato=artigo.substrato,
                substrato_origem=atributos.get("substrato_origem"),
                espessura_mm=artigo.espessura_mm,
                espessura=_espessura(artigo, atributos),
                familia=artigo.familia,
                seccao=artigo.seccao,
                grupo=artigo.grupo,
                tipo=_tipo(artigo, atributos),
                unidade=preco.unidade or artigo.unidade or "UN",
                preco=preco.valor,
                artigo_id=artigo.id,
                tabela_id=tabela.id,
            )
        )
    return _marcar_ambiguos(linhas)


def _medida(artigo: ArtigoConsulta) -> tuple:
    """A mesma coisa, comprada da mesma maneira: referência, acabamento,
    substrato de origem e espessura. Não entra o design nem a descrição."""
    return (
        artigo.folha,
        artigo.fornecedor,
        artigo.referencia,
        _texto(artigo.acabamento),
        _texto(artigo.substrato_origem),
        _texto(artigo.espessura),
    )


def _marcar_ambiguos(linhas: list[ArtigoConsulta]) -> list[ArtigoConsulta]:
    """Onde a tabela dá dois preços à mesma coisa, vale o mais caro.

    É uma decisão do Paulo, tomada em setembro de 2026, e a razão é simples:
    validar cada caso com o fornecedor custa mais do que a diferença, e
    orçamentar pelo preço de baixo é a única das duas hipóteses em que se perde
    dinheiro. **Nada se esconde**: os dois preços continuam na base e os dois
    aparecem na tabela do ecrã; o que esta marca decide é qual deles a resposta
    IA cita quando tem de citar um.

    Acontece em dois sítios, e por motivos diferentes. Na Finsa a referência
    ``688B`` com o acabamento ``YOKU`` é ao mesmo tempo *CARYA WOOD* (Grupo 3) e
    *TIVOLI ASH* (Grupo 2) — 72 combinações de substrato e espessura, com todo o
    ar de gralha na tabela de origem. No BLUM o mesmo artigo aparece em duas
    secções do PDF com preços diferentes — 71 casos, e aí a diferença é
    provavelmente real (embalagem, contexto), o que não muda a conclusão.
    """
    por_medida: dict[tuple, list[int]] = defaultdict(list)
    for indice, linha in enumerate(linhas):
        if linha.preco is not None:
            por_medida[_medida(linha)].append(indice)

    marcados = list(linhas)
    for indices in por_medida.values():
        precos = {linhas[indice].preco for indice in indices}
        if len(precos) < 2:
            continue
        ordenados = tuple(sorted(precos))
        for indice in indices:
            marcados[indice] = replace(
                linhas[indice],
                precos_da_medida=ordenados,
                preco_a_considerar=linhas[indice].preco == ordenados[-1],
            )
    return marcados


def _grupo(artigo: ArtigoConsulta) -> str:
    """A coluna «Grupo» — grupo de preço nas placas, secção do catálogo nas
    ferragens.

    A ``seccao`` só serve de reserva para quem não tem espessura. Nos três
    adaptadores de placas a ``seccao`` guarda o substrato de origem, que já tem
    o seu sítio na coluna do tipo; usá-la aqui enchia a coluna «Grupo» dos
    Innovus com «Aglomerado de partículas hidrófugo» quando a tabela não lhes
    dá grupo nenhum.
    """
    if artigo.grupo:
        return _texto(artigo.grupo)
    return "" if artigo.espessura else _texto(artigo.seccao)


def _chave_linha(artigo: ArtigoConsulta) -> tuple:
    """O que faz duas espessuras serem a mesma referência do Excel.

    É a chave natural do adaptador **sem a espessura**, e é assim de propósito:
    a chave natural é a única definição de identidade que existe, e cada
    adaptador escolheu a sua com o cuidado que os dados obrigaram. Reconstruí-la
    aqui a partir dos campos visíveis dava sempre uma versão pobre — o BLUM
    distingue artigos pela secção do PDF, que a tabela nem mostra, e 55
    referências perdiam metade dos preços sem nada dizer.

    Todos os adaptadores põem a espessura no fim da chave. Se por acaso não
    estiver lá, **não se junta nada**: a linha fica sozinha, que é um erro que
    se vê, em vez de um preço que desaparece.
    """
    sufixo = f"|{artigo.espessura}"
    if artigo.espessura and artigo.chave_natural.endswith(sufixo):
        return (artigo.folha, artigo.fornecedor, artigo.chave_natural[: -len(sufixo)])
    return (artigo.folha, artigo.fornecedor, artigo.chave_natural)


@dataclass(frozen=True)
class GrupoReferencia:
    """Uma referência com as suas espessuras, antes de virar linha de tabela.

    O ``principal`` é o artigo por onde a referência se apresenta — o primeiro
    que apareceu, e todos os campos dele são iguais nos irmãos, tirando a
    espessura e o preço. O ``por_etiqueta`` tem um artigo por espessura, com a
    etiqueta que o cabeçalho do Excel usava (``19mm``), ou a chave do preço
    unitário quando não há espessura nenhuma.
    """

    principal: ArtigoConsulta
    por_etiqueta: dict[str, ArtigoConsulta]

    @property
    def etiquetas(self) -> list[str]:
        return list(self.por_etiqueta)

    @property
    def tem_ambiguidade(self) -> bool:
        return any(
            artigo.precos_da_medida for artigo in self.por_etiqueta.values()
        )


def agrupar_por_referencia(artigos: list[ArtigoConsulta]) -> list[GrupoReferencia]:
    """Volta a juntar as espessuras que a Fase 2 desdobrou.

    Quando a mesma espessura da mesma referência aparece em duas tabelas
    ativas, vale a mais recente: os artigos vêm ordenados por tabela e o último
    escreve por cima. É o mesmo critério de quem abre a tabela mais nova em
    cima da mesa.
    """
    principais: OrderedDict[tuple, ArtigoConsulta] = OrderedDict()
    por_etiqueta: dict[tuple, dict[str, ArtigoConsulta]] = {}
    for artigo in artigos:
        chave = _chave_linha(artigo)
        principais.setdefault(chave, artigo)
        por_etiqueta.setdefault(chave, {})
        por_etiqueta[chave][artigo.etiqueta_preco] = artigo
    return [
        GrupoReferencia(principal=artigo, por_etiqueta=por_etiqueta[chave])
        for chave, artigo in principais.items()
    ]


def listar_referencias(session: Session) -> list[LinhaReferencia]:
    """As referências com uma coluna por espessura — a forma do Excel curado."""
    return [
        LinhaReferencia(
            folha=grupo.principal.folha,
            referencia=grupo.principal.referencia,
            st_acab=_texto(grupo.principal.acabamento),
            nome_design=_texto(grupo.principal.nome_design)
            or grupo.principal.descricao,
            grupo=_grupo(grupo.principal),
            tipo=grupo.principal.tipo,
            fornecedor=grupo.principal.fornecedor,
            precos={
                etiqueta: format_currency(artigo.preco)
                for etiqueta, artigo in grupo.por_etiqueta.items()
                if artigo.preco is not None
            },
        )
        for grupo in agrupar_por_referencia(listar_artigos(session))
    ]


def assinatura_catalogos(session: Session) -> tuple[int, str]:
    """Um carimbo que muda quando a base muda, para quem guarda em cache.

    Conta os preços e vê a última importação: qualquer importação nova mexe num
    dos dois. Substitui a data do ficheiro Excel, que deixou de ser a origem.
    """
    total = session.scalar(select(func.count()).select_from(FornArtigoPreco)) or 0
    ultima: datetime | None = session.scalar(
        select(func.max(FornTabelaPreco.importada_em))
    )
    return total, ultima.isoformat() if ultima else ""


def esta_vazia(session: Session) -> bool:
    """Verdade se ainda ninguém correu a importação."""
    return not session.scalar(
        select(FornTabelaPreco.id).where(FornTabelaPreco.ativa.is_(True)).limit(1)
    )
