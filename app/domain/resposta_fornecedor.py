"""Pure rules for reading a supplier's answer to a price request.

The supplier gets a file with locked columns, but files come back in every
shape: columns moved, headers renamed, the sheet rebuilt by hand, numbers typed
as text. So the reading is deliberately forgiving about *form* and strict about
*meaning*: the ``Código`` is the only thing that decides which material a line
belongs to, and nothing is written to the catalog without a person saying yes.

The net price stays ours: the supplier sends the table price and the discount,
and we recompute the net with our own margin.

Finding the columns happens in three passes, from the most trustworthy to the
least: the exact title, a title that merely resembles it, and — only when the
title says nothing — the *contents* of the column. Whatever was found by
contents is reported as such, so the person reviewing knows what to look at
twice.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
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

#: Desconto acima do qual deixa de ser um desconto e passa a ser um engano.
DESCONTO_MAXIMO = Decimal("95")

#: Fatores típicos de uma vírgula fora do sítio (24,87 escrito 2487).
FATORES_DECIMAIS = (Decimal(100), Decimal(1000))

#: Palavras com que um fornecedor costuma dizer que já não vende o artigo.
PALAVRAS_DESCONTINUADO = ("descontinuad", "esgotad", "fora de linha", "nao existe", "não existe")

#: Uma Ref LE nossa: três a quatro letras e quatro dígitos (PLC0052).
PADRAO_REF_LE = re.compile(r"^[A-Z]{2,4}\d{3,5}$")

# Como cada coluna foi encontrada — vai para a nota que o utilizador lê.
ORIGEM_TITULO = "titulo"
ORIGEM_PARECIDO = "parecido"
ORIGEM_CONTEUDO = "conteudo"

# Cada campo aceita vários títulos: o fornecedor mexe nos cabeçalhos e o
# ficheiro tem de continuar a ser lido. A ordem importa — "preço tabela atual"
# não pode ser confundido com "preço tabela atualizado".
ALIASES = {
    "codigo": ("codigo", "refle", "referenciale", "referenciainterna", "nossaref",
               "nossareferencia"),
    "preco_novo": (
        "precotabelaatualizado",
        "precoatualizado",
        "preconovo",
        "novopreco",
        "precotabelanovo",
        "precotabela",
        "precounitario",
        "precolista",
        "pvp",
    ),
    "preco_atual": ("precotabelaatual", "precoatual"),
    "desconto": ("desconto", "descontopercentagem", "desc", "descontos", "abatimento"),
    "nova_referencia": ("novareferencia", "novaref", "referencianova"),
    "nova_designacao": ("novadesignacao", "novadescricao", "designacaonova"),
    "observacoes": ("observacoes", "obs", "notas", "comentarios", "nota"),
    "designacao": ("designacao", "descricao", "artigodescricao", "denominacao"),
    "referencia_fornecedor": ("reffornecedor", "referenciafornecedor", "refforn",
                              "vossaref", "vossareferencia", "codigofornecedor"),
}

#: Na 2.ª passagem só se aceitam títulos longos: "desc" apanharia "descrição".
MINIMO_ALIAS_PARECIDO = 6

# A ordem por que se procura, para os títulos mais específicos ficarem com a
# coluna antes dos genéricos ("preço tabela atualizado" antes de "desconto").
ORDEM_CAMPOS = (
    "codigo",
    "preco_novo",
    "preco_atual",
    "desconto",
    "nova_referencia",
    "nova_designacao",
    "referencia_fornecedor",
    "designacao",
    "observacoes",
)


@dataclass(frozen=True)
class MapaColunas:
    """Em que coluna ficou cada campo, e como lá se chegou.

    Comporta-se como o dicionário simples que era antes (``mapa["codigo"]``),
    mas guarda também a proveniência de cada coluna: uma coluna reconhecida
    pelo conteúdo é um palpite e tem de ser dita ao utilizador.
    """

    campos: dict
    origens: dict

    def __getitem__(self, campo: str):
        return self.campos.get(campo)

    def get(self, campo: str, default=None):
        valor = self.campos.get(campo)
        return default if valor is None else valor

    def adivinhados(self) -> tuple:
        """Campos que só foram encontrados a olhar para os valores."""
        return tuple(
            campo
            for campo, origem in self.origens.items()
            if origem == ORIGEM_CONTEUDO
        )

    def renomeados(self) -> tuple:
        """Campos cujo título não era o nosso, mas parecia."""
        return tuple(
            campo
            for campo, origem in self.origens.items()
            if origem == ORIGEM_PARECIDO
        )

    def notas(self, cabecalhos=None) -> list:
        """O que dizer ao utilizador sobre a leitura das colunas."""
        cabecalhos = list(cabecalhos or [])

        def titulo(campo: str) -> str:
            indice = self.campos.get(campo)
            if indice is None or indice >= len(cabecalhos):
                return f"coluna {(indice or 0) + 1}"
            return str(cabecalhos[indice] or f"coluna {indice + 1}")

        notas = []
        for campo in self.renomeados():
            notas.append(
                f"«{titulo(campo)}» foi lida como {NOMES_CAMPOS.get(campo, campo)}."
            )
        for campo in self.adivinhados():
            notas.append(
                f"«{titulo(campo)}» não tinha título conhecido; foi reconhecida "
                f"pelos valores como {NOMES_CAMPOS.get(campo, campo)} — confirme."
            )
        if self.campos.get("codigo") is None:
            notas.append(
                "Não há coluna com o nosso código: as linhas são reconhecidas "
                "pela referência do fornecedor."
            )
        return notas


#: Como cada campo se chama para quem lê o aviso.
NOMES_CAMPOS = {
    "codigo": "o nosso código",
    "preco_novo": "o preço novo",
    "preco_atual": "o preço atual",
    "desconto": "o desconto",
    "designacao": "a designação",
    "referencia_fornecedor": "a referência do fornecedor",
    "nova_referencia": "a nova referência",
    "nova_designacao": "a nova designação",
    "observacoes": "as observações",
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
    avisos: tuple = ()

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


def mapear_colunas(cabecalhos, linhas=None) -> MapaColunas:
    """Descobrir em que coluna está cada campo.

    Primeiro pelo título exato, depois por um título parecido e, só para o que
    ficar por encontrar, pelos valores das ``linhas``.
    """
    normalizados = [normalizar_cabecalho(cabecalho) for cabecalho in cabecalhos]
    campos: dict = {campo: None for campo in ALIASES}
    origens: dict = {}
    usados: set = set()

    for campo in ORDEM_CAMPOS:
        indice = _por_titulo_exato(ALIASES[campo], normalizados, usados)
        if indice is not None:
            campos[campo], origens[campo] = indice, ORIGEM_TITULO
            usados.add(indice)

    for campo in ORDEM_CAMPOS:
        if campos[campo] is not None:
            continue
        indice = _por_titulo_parecido(campo, normalizados, usados)
        if indice is not None:
            campos[campo], origens[campo] = indice, ORIGEM_PARECIDO
            usados.add(indice)

    if linhas:
        _pelo_conteudo(campos, origens, usados, list(linhas))

    return MapaColunas(campos=campos, origens=origens)


def _por_titulo_exato(aliases, normalizados, usados) -> int | None:
    for alias in aliases:
        for indice, titulo in enumerate(normalizados):
            if titulo == alias and indice not in usados:
                return indice
    return None


def _por_titulo_parecido(campo: str, normalizados, usados) -> int | None:
    """Um título que não é o nosso mas diz o mesmo ("Preço Un. (€)")."""
    for alias in ALIASES[campo]:
        if len(alias) < MINIMO_ALIAS_PARECIDO:
            continue
        for indice, titulo in enumerate(normalizados):
            if indice in usados or not titulo:
                continue
            if alias not in titulo and titulo not in alias:
                continue
            if campo == "preco_atual" and ("atualizado" in titulo or "novo" in titulo):
                # "preço tabela atualizado" é o preço novo, não o que temos.
                continue
            if campo == "preco_novo" and titulo.endswith("atual"):
                continue
            if len(titulo) < 3:
                continue
            return indice
    return None


def _pelo_conteudo(campos: dict, origens: dict, usados: set, linhas: list) -> None:
    """Último recurso: olhar para os valores das colunas por identificar."""
    total = len(linhas)
    if not total:
        return

    largura = max(len(linha) for linha in linhas)

    if campos.get("codigo") is None:
        indice = _coluna_de_codigos(linhas, largura, usados)
        if indice is not None:
            campos["codigo"], origens["codigo"] = indice, ORIGEM_CONTEUDO
            usados.add(indice)

    if campos.get("preco_novo") is None:
        numericas = [
            indice
            for indice in range(largura)
            if indice not in usados and _e_coluna_de_numeros(linhas, indice)
        ]
        # Só quando não há dúvida: uma única coluna de números por explicar.
        if len(numericas) == 1:
            campos["preco_novo"], origens["preco_novo"] = numericas[0], ORIGEM_CONTEUDO
            usados.add(numericas[0])


def _valores_da_coluna(linhas, indice: int) -> list:
    valores = []
    for linha in linhas:
        if indice < len(linha):
            valor = linha[indice]
            if valor not in (None, ""):
                valores.append(valor)
    return valores


def _coluna_de_codigos(linhas, largura: int, usados: set) -> int | None:
    """A coluna em que a maioria dos valores tem a cara de uma Ref LE."""
    melhor, melhor_taxa = None, Decimal("0.6")
    for indice in range(largura):
        if indice in usados:
            continue
        valores = _valores_da_coluna(linhas, indice)
        if not valores:
            continue
        certos = sum(
            1 for valor in valores if PADRAO_REF_LE.match(str(valor).strip().upper())
        )
        taxa = Decimal(certos) / Decimal(len(valores))
        if taxa >= melhor_taxa:
            melhor, melhor_taxa = indice, taxa
    return melhor


def _e_coluna_de_numeros(linhas, indice: int) -> bool:
    valores = _valores_da_coluna(linhas, indice)
    if not valores:
        return False
    return all(to_decimal(valor) is not None for valor in valores)


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


def avisos_do_valor(
    preco_atual: Decimal | None,
    preco_novo: Decimal | None,
    desconto: Decimal | None,
    variacao: Decimal | None,
    variacao_suspeita: Decimal = VARIACAO_SUSPEITA,
) -> list:
    """O que há de estranho nesta linha, dito por palavras.

    Não decide nada: só junta as razões para alguém olhar antes de gravar. Um
    preço errado aqui entra em todos os orçamentos feitos a seguir.
    """
    avisos: list = []

    if preco_novo is not None and preco_novo <= 0:
        avisos.append(
            "O preço vem a zero ou negativo — o material sairia sem custo nos "
            "orçamentos."
        )

    if desconto is not None:
        if desconto < 0 or desconto > DESCONTO_MAXIMO:
            avisos.append(
                f"Desconto de {_percentagem(desconto)}% está fora do normal "
                f"(0 a {_percentagem(DESCONTO_MAXIMO)}%)."
            )
        elif 0 < desconto < 1:
            avisos.append(
                f"Desconto escrito {_percentagem(desconto)} — quis dizer "
                f"{_percentagem(desconto * Decimal(100))}%?"
            )

    fator = _fator_decimal(preco_atual, preco_novo)
    if fator:
        avisos.append(
            f"O preço vem {fator} — parece uma vírgula fora do sítio."
        )
    elif variacao is not None and abs(variacao) >= variacao_suspeita:
        sinal = "acima" if variacao > 0 else "abaixo"
        avisos.append(
            f"Variação de {abs(variacao):.0f}% {sinal} do preço atual — confirme "
            "antes de aplicar."
        )

    return avisos


def _percentagem(valor: Decimal) -> str:
    """Uma percentagem escrita como se escreve cá: 20, 7,5, 0,2."""
    return format(float(valor), "g").replace(".", ",")


def _fator_decimal(atual: Decimal | None, novo: Decimal | None) -> str | None:
    """Se o preço novo é ~100x ou ~1000x o atual (ou o contrário)."""
    if not atual or not novo or atual <= 0 or novo <= 0:
        return None

    razao = novo / atual
    for fator in FATORES_DECIMAIS:
        if abs(razao - fator) <= fator / Decimal(10):
            return f"{fator:g} vezes maior"
        if abs(razao - Decimal(1) / fator) <= Decimal(1) / fator / Decimal(10):
            return f"{fator:g} vezes menor"
    return None


def ler_respostas(
    cabecalhos,
    linhas,
    materias_por_codigo: dict,
    primeira_linha: int = 2,
    variacao_suspeita: Decimal = VARIACAO_SUSPEITA,
    materias_por_referencia: dict | None = None,
    mapa: MapaColunas | None = None,
) -> list:
    """Transformar o ficheiro devolvido numa lista de propostas.

    ``materias_por_codigo`` é o catálogo indexado por Ref LE (em maiúsculas) e
    ``materias_por_referencia`` pela referência do fornecedor, para quando o
    fornecedor responde com a lista dele em vez do nosso anexo.

    Nada aqui grava seja o que for: só diz o que *poderia* mudar e porquê.
    """
    linhas = list(linhas)
    mapa = mapa or mapear_colunas(cabecalhos, linhas)
    propostas = []

    for numero, linha in enumerate(linhas, start=primeira_linha):
        proposta = _proposta(
            numero,
            linha,
            mapa,
            materias_por_codigo,
            materias_por_referencia or {},
            variacao_suspeita,
        )
        if proposta is not None:
            propostas.append(proposta)

    return _marcar_repetidos(propostas)


def _marcar_repetidos(propostas: list) -> list:
    """Duas linhas para o mesmo material são sempre para olhar.

    Acontece quando o fornecedor junta a lista dele por baixo da nossa: fica lá
    o mesmo artigo duas vezes, com preços diferentes.
    """
    contagem: dict = {}
    for proposta in propostas:
        # Só contam as linhas que propõem alguma coisa: uma linha em branco
        # repetida não é um conflito, é apenas uma linha em branco.
        if proposta.materia_prima_id is not None and proposta.aplicavel:
            contagem[proposta.materia_prima_id] = (
                contagem.get(proposta.materia_prima_id, 0) + 1
            )

    repetidos = {chave for chave, quantas in contagem.items() if quantas > 1}
    if not repetidos:
        return propostas

    finais = []
    for proposta in propostas:
        if proposta.materia_prima_id not in repetidos or not proposta.aplicavel:
            finais.append(proposta)
            continue

        aviso = "O ficheiro traz mais do que uma linha para este material."
        finais.append(
            replace(
                proposta,
                estado=ESTADO_ANOMALIA,
                avisos=proposta.avisos + (aviso,),
                detalhe=aviso,
            )
        )

    return finais


def _proposta(
    numero: int,
    linha,
    mapa,
    materias_por_codigo: dict,
    materias_por_referencia: dict,
    variacao_suspeita: Decimal,
) -> PropostaPreco | None:
    """Ler uma linha do ficheiro do fornecedor."""

    def celula(campo: str):
        indice = mapa.get(campo)
        if indice is None or indice >= len(linha):
            return None
        return linha[indice]

    codigo = to_texto(celula("codigo"))
    ref_fornecedor = to_texto(celula("referencia_fornecedor"))
    bruto_preco = celula("preco_novo")
    preco_novo = to_decimal(bruto_preco)
    desconto = to_decimal(celula("desconto"))
    observacoes = to_texto(celula("observacoes"))
    nova_referencia = to_texto(celula("nova_referencia"))
    nova_designacao = to_texto(celula("nova_designacao"))

    vazia = not any(
        (codigo, ref_fornecedor, preco_novo, desconto, observacoes,
         nova_referencia, nova_designacao)
    )
    if vazia:
        return None

    materia = _material_da_linha(
        codigo, ref_fornecedor, materias_por_codigo, materias_por_referencia
    )
    preco_atual = (
        getattr(materia, "preco_tabela", None)
        if materia is not None
        else to_decimal(celula("preco_atual"))
    )
    variacao = variacao_percentual(preco_atual, preco_novo)
    avisos = avisos_do_valor(
        preco_atual, preco_novo, desconto, variacao, variacao_suspeita
    )

    ilegivel = preco_novo is None and to_texto(bruto_preco) is not None
    if ilegivel:
        avisos.insert(
            0, f"Não percebi o valor «{to_texto(bruto_preco)}» escrito no preço."
        )

    estado, detalhe = _estado_da_linha(
        materia, observacoes, preco_novo, desconto, preco_atual, avisos, ilegivel
    )

    return PropostaPreco(
        linha=numero,
        codigo=codigo or getattr(materia, "ref_le", None),
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
        avisos=tuple(avisos),
    )


def _material_da_linha(
    codigo: str | None,
    ref_fornecedor: str | None,
    materias_por_codigo: dict,
    materias_por_referencia: dict,
):
    """Achar o material: pelo nosso código e, se não der, pela referência dele."""
    materia = materias_por_codigo.get((codigo or "").upper())
    if materia is not None:
        return materia

    # O código pode ser a referência do fornecedor, quando ele responde com a
    # lista dele: as duas hipóteses são tentadas contra o mesmo índice.
    for candidato in (ref_fornecedor, codigo):
        if candidato:
            materia = materias_por_referencia.get(candidato.strip().upper())
            if materia is not None:
                return materia

    return None


def _estado_da_linha(
    materia,
    observacoes: str | None,
    preco_novo: Decimal | None,
    desconto: Decimal | None,
    preco_atual: Decimal | None,
    avisos: list,
    ilegivel: bool,
) -> tuple:
    """O que fazer com esta linha, e porquê."""
    if materia is None:
        return (
            ESTADO_DESCONHECIDO,
            "Este código não existe no catálogo — a linha é ignorada.",
        )

    if diz_descontinuado(observacoes):
        return (
            ESTADO_DESCONTINUADO,
            "O fornecedor diz que o artigo acabou: propõe-se desativá-lo.",
        )

    if preco_novo is None and desconto is None:
        if ilegivel:
            return (ESTADO_ANOMALIA, avisos[0])
        return (ESTADO_SEM_RESPOSTA, "Ficou por preencher.")

    desconto_atual = getattr(materia, "desconto", None)
    sem_mudanca = (
        preco_novo is not None
        and preco_atual is not None
        and preco_novo == preco_atual
        and (desconto is None or desconto == desconto_atual)
    )
    if sem_mudanca:
        return (ESTADO_SEM_ALTERACAO, "O preço mantém-se.")

    if avisos:
        return (ESTADO_ANOMALIA, avisos[0])

    return (ESTADO_ATUALIZA, None)


def resumir(propostas) -> str:
    """Uma linha com o que o ficheiro traz."""
    if not propostas:
        return "O ficheiro não trazia nenhuma linha preenchida."

    contagem: dict = {}
    for proposta in propostas:
        contagem[proposta.estado] = contagem.get(proposta.estado, 0) + 1

    partes = [f"{quantas} {estado.lower()}" for estado, quantas in contagem.items()]
    return f"{len(propostas)} linhas lidas — " + ", ".join(partes) + "."
