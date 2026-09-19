"""Mensagens do Assistente quando um orçamento meu passa a Adjudicado/Não Adjudicado.

Regra pura: recebe o histórico (V2 + V3) já lido e devolve o texto. Decisões
do Paulo (19-09-2026):

* a mensagem é **só para o dono** do orçamento (o Utilizador da versão);
* **Adjudicado**: inspiradora e nunca igual — escolhe o facto mais marcante do
  histórico (primeiro trabalho com o cliente, maior do ano, ganho à 2.ª
  versão, n.º do ano) e acompanha com o gráfico do cliente;
* **Não Adjudicado**: tom SEMPRE positivo, só dados do cliente. Nada de
  «repensar se vale a pena este cliente» — foi ele próprio que o tirou;
* os números vêm todos do código; o texto é escolhido de um banco de frases.
"""

from __future__ import annotations

import random
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable

ADJUDICADO = "Adjudicado"
NAO_ADJUDICADO = "Não Adjudicado"

#: Ordem das barras do gráfico do cliente.
ESTADOS_GRAFICO = (
    "Adjudicado",
    "Enviado",
    "Não Adjudicado",
    "Falta Orçamentar",
    "Não Enviado",
    "Sem Interesse",
    "Cancelado",
    "Concluído",
)


def _chave(texto: object) -> str:
    base = unicodedata.normalize("NFKD", str(texto or "").strip())
    sem = "".join(c for c in base if not unicodedata.combining(c))
    return " ".join(sem.casefold().split())


_ESTADOS_POR_CHAVE = {_chave(estado): estado for estado in ESTADOS_GRAFICO}


def estado_canonico(estado: object) -> str:
    """«Nao Adjudicado», «Falta Orcamentar» (V2) → a grafia do V3."""
    return _ESTADOS_POR_CHAVE.get(_chave(estado), str(estado or "").strip())


def mesmo_nome(a: object, b: object) -> bool:
    return bool(_chave(a)) and _chave(a) == _chave(b)


@dataclass(frozen=True)
class OrcamentoHistorico:
    """Uma versão de orçamento, venha do V2 ou do V3."""

    numero: str
    versao: int
    cliente: str
    estado: str
    ano: int
    valor: Decimal | None
    utilizador: str
    origem: str = "V3"


def _por_orcamento(historico: Iterable[OrcamentoHistorico]) -> list[tuple[str, Decimal | None, OrcamentoHistorico]]:
    """Um resultado por nº de orçamento: ganho se alguma versão foi ganha."""
    grupos: dict[str, list[OrcamentoHistorico]] = {}
    for linha in historico:
        grupos.setdefault(linha.numero, []).append(linha)
    resultado = []
    for linhas in grupos.values():
        ganhas = [l for l in linhas if estado_canonico(l.estado) == ADJUDICADO]
        if ganhas:
            escolhida = max(ganhas, key=lambda l: l.versao)
        else:
            escolhida = max(linhas, key=lambda l: l.versao)
        resultado.append((estado_canonico(escolhida.estado), escolhida.valor, escolhida))
    return resultado


@dataclass(frozen=True)
class ResumoCliente:
    cliente: str
    por_estado: dict[str, int]
    total: int
    adjudicados: int
    valor_adjudicado: Decimal
    primeiro_ano: int | None


def resumo_cliente(historico: Iterable[OrcamentoHistorico], cliente: str) -> ResumoCliente:
    do_cliente = [l for l in historico if mesmo_nome(l.cliente, cliente)]
    resultados = _por_orcamento(do_cliente)
    contagem = Counter(estado for estado, _, _ in resultados)
    valor = sum(
        (v or Decimal("0") for estado, v, _ in resultados if estado == ADJUDICADO),
        Decimal("0"),
    )
    anos = [l.ano for l in do_cliente if l.ano]
    return ResumoCliente(
        cliente=cliente,
        por_estado={e: contagem[e] for e in ESTADOS_GRAFICO if contagem.get(e)},
        total=len(resultados),
        adjudicados=contagem.get(ADJUDICADO, 0),
        valor_adjudicado=valor,
        primeiro_ano=min(anos) if anos else None,
    )


@dataclass(frozen=True)
class ResumoUtilizador:
    ano: int
    adjudicados: int
    valor_adjudicado: Decimal
    maior_outro: Decimal


def resumo_utilizador(
    historico: Iterable[OrcamentoHistorico],
    utilizador: str,
    ano: int,
    *,
    excluir_numero: str = "",
) -> ResumoUtilizador:
    meus = [
        l for l in historico if mesmo_nome(l.utilizador, utilizador) and l.ano == ano
    ]
    ganhos = [
        (v or Decimal("0"), linha)
        for estado, v, linha in _por_orcamento(meus)
        if estado == ADJUDICADO
    ]
    outros = [v for v, linha in ganhos if linha.numero != excluir_numero]
    return ResumoUtilizador(
        ano=ano,
        adjudicados=len(ganhos),
        valor_adjudicado=sum((v for v, _ in ganhos), Decimal("0")),
        maior_outro=max(outros, default=Decimal("0")),
    )


@dataclass(frozen=True)
class OrcamentoMudado:
    codigo: str
    numero: str
    numero_versao: int
    cliente: str
    obra: str
    valor: Decimal | None
    estado: str
    #: Dias entre passar a Enviado e passar a este estado (None se não se sabe).
    dias_decisao: int | None = None
    #: Nome de quem mudou o estado, quando não foi o próprio.
    mudado_por: str = ""


@dataclass(frozen=True)
class Mensagem:
    estado: str
    titulo: str
    frase: str
    destaque: str
    factos: tuple[str, ...]
    grafico: dict[str, int] = field(default_factory=dict)
    cliente: str = ""


# ---- bancos de frases ------------------------------------------------------

ABERTURAS_ADJUDICADO = (
    "Mais um objetivo cumprido — o trabalho que pôs neste orçamento deu fruto.",
    "É assim que se constrói uma carteira de obras: um orçamento de cada vez.",
    "Bom trabalho! Cada adjudicação é a confiança de um cliente no nosso trabalho.",
    "Grande notícia para começar a pensar na produção.",
    "O detalhe com que orçamentou fez a diferença.",
    "Mais uma obra que vai sair das nossas máquinas graças a si.",
    "Este é daqueles dias que sabem bem. Continue assim!",
    "Orçamento fechado, cliente satisfeito — missão cumprida.",
)

ABERTURAS_NAO_ADJUDICADO = (
    "Nem todos os orçamentos se ganham — e o trabalho feito fica como experiência para o próximo.",
    "Desta vez o cliente escolheu outro caminho. O próximo orçamento é uma nova oportunidade.",
    "Faz parte do caminho: cada orçamento ensina alguma coisa.",
    "Obrigado pelo empenho neste orçamento. Vamos ao próximo com a mesma energia.",
    "Um «não» hoje não fecha a porta: os clientes voltam quando são bem atendidos.",
    "Continue com o mesmo cuidado — é ele que ganha os próximos.",
)


def _euros(valor: Decimal | None) -> str:
    numero = f"{Decimal(valor or 0):,.2f}"
    return numero.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def _ordinal(n: int) -> str:
    return f"{n}.º"


def _escolher(banco: tuple[str, ...], semente: int, evitar: str = "") -> str:
    gerador = random.Random(semente)
    indice = gerador.randrange(len(banco))
    if banco[indice] == evitar and len(banco) > 1:
        indice = (indice + 1) % len(banco)
    return banco[indice]


def destaque_adjudicado(
    orcamento: OrcamentoMudado, cliente: ResumoCliente, utilizador: ResumoUtilizador
) -> str:
    """O facto mais marcante desta adjudicação (o primeiro que se aplicar)."""
    if cliente.adjudicados <= 1:
        return (
            f"É o primeiro trabalho ganho com o cliente {orcamento.cliente}. "
            "Um cliente novo é uma porta que se abre!"
        )
    valor = Decimal(orcamento.valor or 0)
    if utilizador.adjudicados >= 3 and valor > 0 and valor > utilizador.maior_outro:
        return (
            f"É o seu maior orçamento adjudicado de {utilizador.ano}: {_euros(valor)}."
        )
    if orcamento.numero_versao >= 2:
        return (
            f"Ganho à {_ordinal(orcamento.numero_versao)} versão — a persistência "
            "compensou."
        )
    if orcamento.dias_decisao is not None and orcamento.dias_decisao <= 7:
        dias = "1 dia" if orcamento.dias_decisao == 1 else f"{orcamento.dias_decisao} dias"
        if orcamento.dias_decisao == 0:
            return "O cliente decidiu no próprio dia em que recebeu o orçamento."
        return f"O cliente decidiu em {dias} — sinal de que acertou em cheio."
    return (
        f"É o seu {_ordinal(utilizador.adjudicados)} orçamento adjudicado em "
        f"{utilizador.ano}."
    )


def _factos_cliente(cliente: ResumoCliente) -> list[str]:
    desde = f" desde {cliente.primeiro_ano}" if cliente.primeiro_ano else ""
    factos = [
        f"Com o cliente {cliente.cliente}{desde}: {cliente.total} orçamento(s), "
        f"{cliente.adjudicados} adjudicado(s)."
    ]
    if cliente.adjudicados and cliente.valor_adjudicado > 0:
        factos.append(f"Valor já adjudicado por este cliente: {_euros(cliente.valor_adjudicado)}.")
    return factos


def compor_mensagem(
    orcamento: OrcamentoMudado,
    cliente: ResumoCliente,
    utilizador: ResumoUtilizador,
    *,
    nome: str,
    semente: int,
    ultima_frase: str = "",
) -> Mensagem:
    primeiro = (nome or "").split()[0] if (nome or "").strip() else ""
    texto_obra = " ".join(str(orcamento.obra or "").split())
    if len(texto_obra) > 60:
        texto_obra = texto_obra[:59].rstrip() + "…"
    obra = f" — {texto_obra}" if texto_obra else ""
    valor = f" ({_euros(orcamento.valor)})" if orcamento.valor else ""
    linha_orcamento = f"Orçamento {orcamento.codigo} · {orcamento.cliente}{obra}{valor}"
    if orcamento.mudado_por:
        linha_orcamento += f" · estado mudado por {orcamento.mudado_por}"

    if orcamento.estado == ADJUDICADO:
        factos = [linha_orcamento, *_factos_cliente(cliente)]
        if utilizador.adjudicados:
            factos.append(
                f"Em {utilizador.ano} já ganhou {utilizador.adjudicados} orçamento(s), "
                f"{_euros(utilizador.valor_adjudicado)} no total."
            )
        return Mensagem(
            estado=ADJUDICADO,
            titulo=f"🎉 Parabéns{', ' + primeiro if primeiro else ''}!",
            frase=_escolher(ABERTURAS_ADJUDICADO, semente, ultima_frase),
            destaque=destaque_adjudicado(orcamento, cliente, utilizador),
            factos=tuple(factos),
            grafico=dict(cliente.por_estado),
            cliente=orcamento.cliente,
        )

    factos = [linha_orcamento, *_factos_cliente(cliente)]
    if utilizador.adjudicados:
        destaque = (
            f"Em {utilizador.ano} já ganhou {utilizador.adjudicados} orçamento(s) — "
            "o próximo pode ser já a seguir."
        )
    else:
        destaque = "O próximo orçamento é uma nova oportunidade."
    return Mensagem(
        estado=NAO_ADJUDICADO,
        titulo=f"Desta vez não foi{', ' + primeiro if primeiro else ''}.",
        frase=_escolher(ABERTURAS_NAO_ADJUDICADO, semente, ultima_frase),
        destaque=destaque,
        factos=tuple(factos),
        grafico=dict(cliente.por_estado),
        cliente=orcamento.cliente,
    )


def ano_de(valor: object) -> int:
    """Ano de uma data do V2 (texto «2026-08-21», date ou datetime)."""
    if isinstance(valor, date):
        return valor.year
    texto = str(valor or "")
    return int(texto[:4]) if texto[:4].isdigit() else 0
