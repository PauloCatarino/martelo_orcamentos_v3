"""O que um adaptador de fornecedor devolve, e as ferramentas para o construir.

Duas formas, e mais nada: uma ``TabelaCatalogo`` (o ficheiro que chegou) com os
seus ``ArtigoCatalogo`` (as coisas encomendáveis que estavam lá dentro). São
imutáveis e não sabem de SQLAlchemy — dá para as construir e verificar num
teste sem base de dados nenhuma, que é meia batalha em código de importação.

Duas decisões que vale a pena ler antes de escrever um adaptador novo:

**O hash é do conteúdo, não do ficheiro.** O ``12_Placas_Referencias_COMPLETO.xlsx``
tem treze separadores e cada um é uma tabela de um fornecedor diferente. Se o
hash fosse do ficheiro, importar o Egger e depois a Finsa do mesmo xlsx ia
bater na restrição de unicidade do ``ficheiro_hash`` como se fosse a mesma
tabela. Por isso o hash é das linhas que o adaptador leu — ver
``hash_conteudo``.

**Os avisos não são opcionais.** A falha que motivou este trabalho foi o leitor
antigo devolver zero linhas em silêncio quando um fornecedor escrevia ``Ref``
em vez de ``Referência``. Um adaptador que não sabe interpretar uma coluna
enche ``avisos`` — e um que não encontra linha nenhuma levanta
``FormatoInesperado``. Nunca, em nenhum caso, devolve uma tabela vazia como se
estivesse tudo bem.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation


class FormatoInesperado(RuntimeError):
    """O ficheiro não tem a forma que o adaptador esperava.

    Levantada em vez de devolver zero artigos: uma tabela de fornecedor que
    chega vazia é sempre um erro nosso, não um facto sobre o fornecedor.
    """


# ---------------------------------------------------------------------------
# As duas formas
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArtigoCatalogo:
    """Uma coisa encomendável, com o preço que a tabela lhe dava.

    Para placas isto é a combinação referência × substrato × espessura: um
    aglomerado de 19 mm e um de 8 mm da mesma referência são dois artigos, com
    preços próprios, e não duas colunas do mesmo.
    """

    #: O que o adaptador considera identificar o artigo dentro do fornecedor.
    #: É por ela que uma reimportação reconhece o que já cá estava.
    chave_natural: str
    referencia: str
    descricao: str
    unidade: str = "UN"
    nome_design: str | None = None
    familia: str | None = None
    seccao: str | None = None
    catalogo: str | None = None
    pagina: str | None = None
    grupo: str | None = None
    fabricante: str | None = None

    # --- placas ---
    substrato: str | None = None
    espessura_mm: Decimal | None = None
    acabamento: str | None = None
    formatos: str | None = None

    #: Nulo quando a tabela lista o artigo mas não lhe dá preço. Acontece.
    preco: Decimal | None = None
    desconto: Decimal | None = None

    atributos: dict[str, object] | None = None
    observacoes: str | None = None
    #: Referências alternativas: ``(tipo, valor)`` — ver ``FornArtigoAlias``.
    aliases: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class TabelaCatalogo:
    """Uma tabela de preços tal como chegou, já traduzida."""

    fornecedor: str
    nome: str
    artigos: tuple[ArtigoCatalogo, ...]
    fabricante: str | None = None
    referencia_tabela: str | None = None
    data_tabela: date | None = None
    ficheiro_origem: str | None = None
    ficheiro_hash: str | None = None
    moeda: str = "EUR"
    unidade_preco: str | None = None
    observacoes: str | None = None
    #: O que o adaptador não soube explicar. Ver a docstring do módulo.
    avisos: tuple[str, ...] = field(default_factory=tuple)

    @property
    def com_preco(self) -> int:
        return sum(1 for artigo in self.artigos if artigo.preco is not None)


# ---------------------------------------------------------------------------
# Ferramentas para os adaptadores
# ---------------------------------------------------------------------------


def normalizar(valor: object) -> str:
    """Minúsculas, sem acentos e sem espaços nas pontas.

    É o que permite reconhecer ``Referência``, ``REFERENCIA`` e ``Ref.`` como a
    mesma coisa — a comparação que faltava ao leitor antigo.
    """
    if valor is None:
        return ""
    texto_norm = unicodedata.normalize("NFKD", str(valor))
    texto_norm = "".join(c for c in texto_norm if not unicodedata.combining(c))
    return " ".join(texto_norm.lower().split())


def texto(valor: object) -> str | None:
    """O valor como texto aparado, ou ``None`` se não sobrar nada.

    O Excel enche células com espaços e com o texto ``"None"``; nenhum dos dois
    deve chegar à base como se fosse conteúdo.
    """
    if valor is None:
        return None
    limpo = str(valor).strip()
    if not limpo or limpo.lower() in {"none", "nan", "-", "--"}:
        return None
    return limpo


def numero(valor: object) -> Decimal | None:
    """Um número de tabela de preços, venha ele como for.

    Aceita ``7,94`` (vírgula portuguesa), ``1.234,56``, ``7.94 €`` e o que o
    openpyxl já devolve como float. Devolve ``None`` — nunca zero — quando não
    há número nenhum: zero é um preço, ausência não é.
    """
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        return Decimal(str(valor))

    limpo = str(valor).strip()
    if not limpo:
        return None
    limpo = re.sub(r"[^\d,.\-]", "", limpo)
    if not limpo or limpo in {"-", ".", ","}:
        return None
    # 1.234,56 -> 1234.56 ; 7,94 -> 7.94 ; 1,234.56 -> 1234.56
    if "," in limpo and "." in limpo:
        if limpo.rfind(",") > limpo.rfind("."):
            limpo = limpo.replace(".", "").replace(",", ".")
        else:
            limpo = limpo.replace(",", "")
    elif "," in limpo:
        limpo = limpo.replace(",", ".")
    try:
        return Decimal(limpo)
    except InvalidOperation:
        return None


def chave_natural(*partes: object) -> str:
    """Junta as partes que identificam o artigo, separadas por ``|``.

    As partes vazias caem fora, para a chave não mudar de forma só porque um
    fornecedor deixou de preencher uma coluna que não distinguia nada.
    """
    limpas = [str(p).strip() for p in partes if texto(p) is not None]
    if not limpas:
        raise ValueError("uma chave natural não pode ser vazia")
    return "|".join(limpas)


def hash_conteudo(linhas: Iterable[Sequence[object]]) -> str:
    """SHA-256 das linhas lidas, para a importação ser repetível sem estragos.

    O texto que se digere é canónico de propósito — células separadas por tabs,
    linhas por ``\\n``, ``None`` como vazio — para não depender do ``repr`` de
    nenhum tipo do Python: uma atualização do interpretador não deve fazer a
    mesma tabela parecer nova.
    """
    digest = hashlib.sha256()
    for linha in linhas:
        celulas = ["" if c is None else str(c) for c in linha]
        digest.update("\t".join(celulas).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def primeira_data(textos: Iterable[str]) -> date | None:
    """A primeira data que aparecer nas notas de uma tabela.

    As notas do separador dizem coisas como «atualizada a partir do PDF BF-82
    2026/04/20 (substitui tabela anterior de 2026/03/12)». A primeira é a desta
    tabela; a segunda é a da que ela substituiu — daí ficar-se pela primeira.
    """
    padrao = re.compile(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})")
    for linha in textos:
        achado = padrao.search(linha or "")
        if not achado:
            continue
        ano, mes, dia = (int(p) for p in achado.groups())
        try:
            return date(ano, mes, dia)
        except ValueError:
            continue
    return None


def primeira_referencia_tabela(textos: Iterable[str]) -> str | None:
    """O código que o fornecedor dá à tabela («BF-82»), se o escrever.

    Muitos não escrevem nenhum, e é por isso que devolve ``None`` sem se
    queixar em vez de inventar um.
    """
    # Uma letra chega: a Innovus chama «T-04» e «T-17» às tabelas dela, e com
    # duas letras no mínimo ficavam ambas sem código. As letras têm de estar
    # coladas ao hífen, senão um «WoodSide - 2026» passava por código.
    padrao = re.compile(r"\b([A-Z]{1,4}-\d{1,4}[A-Z]?)\b")
    for linha in textos:
        achado = padrao.search(linha or "")
        if achado:
            return achado.group(1)
    return None
