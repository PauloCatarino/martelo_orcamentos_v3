"""Pure rules for reading a supplier's answer to a price request.

The supplier gets a file with locked columns, but files come back in every
shape: columns moved, headers renamed, the sheet rebuilt by hand, numbers typed
as text. So the reading is deliberately forgiving about *form* and strict about
*meaning*: the ``Código`` is the only thing that decides which material a line
belongs to, and nothing is written to the catalog without a person saying yes.

The net price stays ours: the supplier sends the table price and the discount,
and we recompute the net with our own margin.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# Estado de cada linha lida, por ordem de gravidade para o utilizador.
ESTADO_ATUALIZA = "ATUALIZA"
ESTADO_SEM_ALTERACAO = "SEM ALTERAÇÃO"
ESTADO_DESCONTINUADO = "DESCONTINUADO"
ESTADO_ANOMALIA = "A CONFIRMAR"
ESTADO_DESCONHECIDO = "DESCONHECIDO"
ESTADO_SEM_RESPOSTA = "SEM RESPOSTA"

#: Variação a partir da qual o valor é assinalado para confirmação humana.
VARIACAO_SUSPEITA = Decimal("25")

#: Palavras com que um fornecedor costuma dizer que já não vende o artigo.
PALAVRAS_DESCONTINUADO = ("descontinuad", "esgotad", "fora de linha", "nao existe", "não existe")

# Cada campo aceita vários títulos: o fornecedor mexe nos cabeçalhos e o
# ficheiro tem de continuar a ser lido. A ordem importa — "preço tabela atual"
# não pode ser confundido com "preço tabela atualizado".
ALIASES = {
    "codigo": ("codigo", "refle", "referenciale", "referenciainterna"),
    "preco_novo": (
        "precotabelaatualizado",
        "precoatualizado",
        "preconovo",
        "novopreco",
        "precotabelanovo",
    ),
    "preco_atual": ("precotabelaatual", "precoatual"),
    "desconto": ("desconto", "descontopercentagem", "desc"),
    "nova_referencia": ("novareferencia", "novaref", "referencianova"),
    "nova_designacao": ("novadesignacao", "novadescricao", "designacaonova"),
    "observacoes": ("observacoes", "obs", "notas", "comentarios"),
    "designacao": ("designacao", "descricao"),
    "referencia_fornecedor": ("reffornecedor", "referenciafornecedor"),
}


@dataclass(frozen=True)
class PropostaPreco:
    """One line of the supplier's answer, ready to be judged."""

    linha: int
    codigo: str | None
    descricao: str | None
    preco_atual: Decimal | None
    preco_novo: Decimal | None
    desconto_novo: Decimal | None
    nova_referencia: str | None
    nova_designacao: str | None
    observacoes: str | None
    estado: str
    materia_prima_id: int | None = None
    variacao: Decimal | None = None
    detalhe: str | None = None

    @property
    def aplicavel(self) -> bool:
        """Se esta linha pode mesmo mudar alguma coisa no catálogo."""
        return self.estado in (ESTADO_ATUALIZA, ESTADO_ANOMALIA, ESTADO_DESCONTINUADO)

    @property
    def sugerido(self) -> bool:
        """Se vem marcada por omissão.

        Uma subida invulgar ou um artigo dado como descontinuado exigem que
        alguém olhe: ficam por marcar, mesmo sendo aplicáveis.
        """
        return self.estado == ESTADO_ATUALIZA


def normalizar_cabecalho(nome: object) -> str:
    """Título de coluna sem acentos, espaços nem maiúsculas."""
    if nome is None:
        return ""

    texto = unicodedata.normalize("NFKD", str(nome))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def mapear_colunas(cabecalhos) -> dict:
    """Descobrir em que coluna está cada campo, por título."""
    normalizados = [normalizar_cabecalho(cabecalho) for cabecalho in cabecalhos]
    mapa: dict[str, int | None] = {}

    for campo, aliases in ALIASES.items():
        indice = None
        for alias in aliases:
            if alias in normalizados:
                indice = normalizados.index(alias)
                break
        mapa[campo] = indice

    return mapa


def to_decimal(valor: object) -> Decimal | None:
    """Número escrito à mão, em qualquer feitio, para Decimal."""
    if valor is None or isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float, Decimal)):
        try:
            return Decimal(str(valor))
        except InvalidOperation:
            return None

    texto = str(valor).strip().replace("€", "").replace("%", "").replace(" ", "")
    if not texto:
        return None

    if "," in texto and "." in texto:
        # 1.234,56 vs 1,234.56
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    else:
        texto = texto.replace(",", ".")

    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def to_texto(valor: object) -> str | None:
    """Texto aparado, ou None quando vazio."""
    if valor is None:
        return None

    texto = str(valor).strip()
    return texto or None


def diz_descontinuado(observacoes: str | None) -> bool:
    """Se o fornecedor está a dizer que o artigo acabou."""
    if not observacoes:
        return False

    texto = unicodedata.normalize("NFKD", observacoes.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return any(palavra in texto for palavra in PALAVRAS_DESCONTINUADO)


def variacao_percentual(atual: Decimal | None, novo: Decimal | None) -> Decimal | None:
    """De quanto mudou o preço, em percentagem."""
    if not atual or novo is None:
        return None

    return (novo - atual) / atual * Decimal(100)


def ler_respostas(
    cabecalhos,
    linhas,
    materias_por_codigo: dict,
    primeira_linha: int = 2,
    variacao_suspeita: Decimal = VARIACAO_SUSPEITA,
) -> list[PropostaPreco]:
    """Transformar o ficheiro devolvido numa lista de propostas.

    ``materias_por_codigo`` é o catálogo indexado por Ref LE (em maiúsculas).
    Nada aqui grava seja o que for: só diz o que *poderia* mudar e porquê.
    """
    mapa = mapear_colunas(cabecalhos)
    propostas = []

    for numero, linha in enumerate(linhas, start=primeira_linha):
        propostas.append(
            _proposta(numero, linha, mapa, materias_por_codigo, variacao_suspeita)
        )

    return [proposta for proposta in propostas if proposta is not None]


def _proposta(
    numero: int,
    linha,
    mapa: dict,
    materias_por_codigo: dict,
    variacao_suspeita: Decimal,
) -> PropostaPreco | None:
    """Ler uma linha do ficheiro do fornecedor."""

    def celula(campo: str):
        indice = mapa.get(campo)
        if indice is None or indice >= len(linha):
            return None
        return linha[indice]

    codigo = to_texto(celula("codigo"))
    preco_novo = to_decimal(celula("preco_novo"))
    desconto = to_decimal(celula("desconto"))
    observacoes = to_texto(celula("observacoes"))
    nova_referencia = to_texto(celula("nova_referencia"))
    nova_designacao = to_texto(celula("nova_designacao"))

    vazia = not any(
        (codigo, preco_novo, desconto, observacoes, nova_referencia, nova_designacao)
    )
    if vazia:
        return None

    materia = materias_por_codigo.get((codigo or "").upper())
    preco_atual = (
        getattr(materia, "preco_tabela", None)
        if materia is not None
        else to_decimal(celula("preco_atual"))
    )
    variacao = variacao_percentual(preco_atual, preco_novo)

    if materia is None:
        estado, detalhe = (
            ESTADO_DESCONHECIDO,
            "Este código não existe no catálogo — a linha é ignorada.",
        )
    elif diz_descontinuado(observacoes):
        estado, detalhe = (
            ESTADO_DESCONTINUADO,
            "O fornecedor diz que o artigo acabou: propõe-se desativá-lo.",
        )
    elif preco_novo is None and desconto is None:
        estado, detalhe = (ESTADO_SEM_RESPOSTA, "Ficou por preencher.")
    elif preco_novo is not None and preco_atual is not None and preco_novo == preco_atual:
        estado, detalhe = (ESTADO_SEM_ALTERACAO, "O preço mantém-se.")
    elif variacao is not None and abs(variacao) >= variacao_suspeita:
        estado, detalhe = (
            ESTADO_ANOMALIA,
            f"Variação de {variacao:.0f}% — confirme antes de aplicar.",
        )
    else:
        estado, detalhe = (ESTADO_ATUALIZA, None)

    return PropostaPreco(
        linha=numero,
        codigo=codigo,
        descricao=getattr(materia, "descricao", None) or to_texto(celula("designacao")),
        preco_atual=preco_atual,
        preco_novo=preco_novo,
        desconto_novo=desconto,
        nova_referencia=nova_referencia,
        nova_designacao=nova_designacao,
        observacoes=observacoes,
        estado=estado,
        materia_prima_id=getattr(materia, "id", None),
        variacao=variacao,
        detalhe=detalhe,
    )


def resumir(propostas) -> str:
    """Uma linha com o que o ficheiro traz."""
    if not propostas:
        return "O ficheiro não trazia nenhuma linha preenchida."

    contagem: dict[str, int] = {}
    for proposta in propostas:
        contagem[proposta.estado] = contagem.get(proposta.estado, 0) + 1

    partes = [f"{quantas} {estado.lower()}" for estado, quantas in contagem.items()]
    return f"{len(propostas)} linhas lidas — " + ", ".join(partes) + "."
