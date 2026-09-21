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
    #: Mês em que o orçamento foi criado (1-12); 0 quando não se sabe.
    mes: int = 0


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
    #: Último ano em que este cliente adjudicou alguma coisa ANTES desta.
    ultimo_ano_ganho: int | None = None


def resumo_cliente(
    historico: Iterable[OrcamentoHistorico],
    cliente: str,
    *,
    excluir_numero: str = "",
) -> ResumoCliente:
    do_cliente = [l for l in historico if mesmo_nome(l.cliente, cliente)]
    resultados = _por_orcamento(do_cliente)
    contagem = Counter(estado for estado, _, _ in resultados)
    valor = sum(
        (v or Decimal("0") for estado, v, _ in resultados if estado == ADJUDICADO),
        Decimal("0"),
    )
    anos = [l.ano for l in do_cliente if l.ano]
    anos_ganhos = [
        linha.ano
        for estado, _, linha in resultados
        if estado == ADJUDICADO and linha.ano and linha.numero != excluir_numero
    ]
    return ResumoCliente(
        cliente=cliente,
        por_estado={e: contagem[e] for e in ESTADOS_GRAFICO if contagem.get(e)},
        total=len(resultados),
        adjudicados=contagem.get(ADJUDICADO, 0),
        valor_adjudicado=valor,
        primeiro_ano=min(anos) if anos else None,
        ultimo_ano_ganho=max(anos_ganhos) if anos_ganhos else None,
    )


@dataclass(frozen=True)
class ResumoUtilizador:
    ano: int
    adjudicados: int
    valor_adjudicado: Decimal
    maior_outro: Decimal
    #: Adjudicações deste mês (pelo histórico de estados do V3).
    adjudicados_mes: int = 0
    mes: int = 0


def resumo_utilizador(
    historico: Iterable[OrcamentoHistorico],
    utilizador: str,
    ano: int,
    *,
    excluir_numero: str = "",
    adjudicados_mes: int = 0,
    mes: int = 0,
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
        adjudicados_mes=adjudicados_mes,
        mes=mes,
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
    "O cliente disse que sim: o trabalho de bastidores compensou.",
    "Mais madeira a entrar na fábrica por sua causa.",
    "Um orçamento bem feito vende-se sozinho — foi o que aconteceu aqui.",
    "Que belo resultado. A equipa da produção agradece o trabalho.",
    "Quando o orçamento está certo, o cliente nota. E notou.",
    "Somam-se as obras, soma-se a confiança de quem nos procura.",
    "Boa! O esforço de orçamentar com cuidado está a dar frutos.",
    "Está feito: hora de passar o testemunho à preparação.",
    "Cada «sim» destes é trabalho garantido para a casa.",
    "Parabéns pela persistência — é ela que fecha orçamentos.",
    "Um orçamento que sai da lista de espera e entra na lista de obras.",
    "Bem jogado. Este cliente fica a saber com quem pode contar.",
    "Mais uma vitória para juntar às deste ano.",
    "O seu nome está por trás desta obra. Parabéns!",
)

ABERTURAS_NAO_ADJUDICADO = (
    "Nem todos os orçamentos se ganham — e o trabalho feito fica como experiência para o próximo.",
    "Desta vez o cliente escolheu outro caminho. O próximo orçamento é uma nova oportunidade.",
    "Faz parte do caminho: cada orçamento ensina alguma coisa.",
    "Obrigado pelo empenho neste orçamento. Vamos ao próximo com a mesma energia.",
    "Um «não» hoje não fecha a porta: os clientes voltam quando são bem atendidos.",
    "Continue com o mesmo cuidado — é ele que ganha os próximos.",
    "O trabalho não se perdeu: fica no Martelo para a próxima consulta deste cliente.",
    "Este não foi. Há mais orçamentos à espera de si, e esses podem ser.",
    "Quem orçamenta muito ouve «não» de vez em quando — faz parte de quem trabalha.",
    "O cliente ficou a conhecer o nosso trabalho. Isso também conta.",
    "Bola para a frente: o próximo orçamento merece a mesma atenção que deu a este.",
    "Sem dramas — a carteira de obras faz-se com uns sins e uns nãos.",
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


#: Contagens que merecem festa própria.
MARCOS_CONTAGEM = (10, 25, 50, 100, 150, 200, 250, 300, 400, 500)
#: Marcos de valor adjudicado no ano, em euros.
MARCOS_VALOR = (
    Decimal("25000"), Decimal("50000"), Decimal("100000"), Decimal("250000"),
    Decimal("500000"), Decimal("750000"), Decimal("1000000"),
)
#: A partir daqui a obra é grande o suficiente para se dizer.
VALOR_OBRA_GRANDE = Decimal("10000")
#: Enviado há tanto tempo que já ninguém contava com ele.
DIAS_ORCAMENTO_ANTIGO = 45

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def _texto_dias(dias: int) -> str:
    return "1 dia" if dias == 1 else f"{dias} dias"


def _marco_de_valor(utilizador: ResumoUtilizador, valor: Decimal) -> Decimal | None:
    """O marco de valor do ano que ESTE orçamento fez passar, se algum."""
    antes = utilizador.valor_adjudicado - valor
    for marco in MARCOS_VALOR:
        if antes < marco <= utilizador.valor_adjudicado:
            return marco
    return None


def destaques_adjudicado(
    orcamento: OrcamentoMudado, cliente: ResumoCliente, utilizador: ResumoUtilizador
) -> list[tuple[str, ...]]:
    """Os factos marcantes que se aplicam, do mais raro ao mais comum.

    Cada facto traz as maneiras de o dizer: escolhe-se sempre o PRIMEIRO facto
    (o mais marcante desta adjudicação) e varia-se só a maneira de o contar.
    Há sempre pelo menos um — o número do ano.
    """
    valor = Decimal(orcamento.valor or 0)
    ano = utilizador.ano
    opcoes: list[tuple[str, ...]] = []

    if utilizador.adjudicados in MARCOS_CONTAGEM:
        opcoes.append(
            (
                f"É o seu {_ordinal(utilizador.adjudicados)} orçamento adjudicado de "
                f"{ano}. Que número!",
                f"Chegou aos {utilizador.adjudicados} orçamentos adjudicados em {ano}!",
            )
        )
    marco = _marco_de_valor(utilizador, valor) if valor > 0 else None
    if marco is not None:
        opcoes.append(
            (
                f"Com este orçamento passou os {_euros(marco)} adjudicados em {ano}.",
                f"Os seus orçamentos ganhos em {ano} passaram hoje a barreira dos "
                f"{_euros(marco)}.",
            )
        )
    if cliente.adjudicados <= 1:
        primeiro = [
            f"É o primeiro trabalho ganho com o cliente {orcamento.cliente}. "
            "Um cliente novo é uma porta que se abre!",
            f"Primeira obra fechada com o cliente {orcamento.cliente} — há sempre "
            "uma primeira vez, e esta correu bem.",
        ]
        if cliente.total >= 3:
            primeiro.append(
                f"Ao fim de {cliente.total} orçamentos, é o primeiro que o cliente "
                f"{orcamento.cliente} fecha consigo. Valeu a pena insistir!"
            )
        opcoes.append(tuple(primeiro))
    elif cliente.ultimo_ano_ganho and cliente.ultimo_ano_ganho < ano:
        opcoes.append(
            (
                f"O cliente {orcamento.cliente} não fechava nada connosco desde "
                f"{cliente.ultimo_ano_ganho} — está de volta.",
                f"Desde {cliente.ultimo_ano_ganho} que o cliente {orcamento.cliente} "
                "não adjudicava nada. Recuperado!",
            )
        )
    if utilizador.adjudicados >= 3 and valor > 0 and valor > utilizador.maior_outro:
        opcoes.append(
            (
                f"É o seu maior orçamento adjudicado de {ano}: {_euros(valor)}.",
                f"Nunca tinha fechado tanto num orçamento este ano: {_euros(valor)}.",
            )
        )
    if valor >= VALOR_OBRA_GRANDE:
        opcoes.append(
            (
                f"Uma obra grande, de {_euros(valor)}. Bom trabalho!",
                f"{_euros(valor)} de obra — destas não aparecem todos os dias.",
            )
        )
    if orcamento.numero_versao >= 2:
        opcoes.append(
            (
                f"Ganho à {_ordinal(orcamento.numero_versao)} versão — a persistência "
                "compensou.",
                f"Foram precisas {orcamento.numero_versao} versões, mas o cliente "
                "acabou por dizer que sim.",
            )
        )
    if orcamento.dias_decisao is not None:
        dias = _texto_dias(orcamento.dias_decisao)
        if orcamento.dias_decisao == 0:
            opcoes.append(
                (
                    "O cliente decidiu no próprio dia em que recebeu o orçamento.",
                    "Enviado e fechado no mesmo dia. Não se pode pedir melhor.",
                )
            )
        elif orcamento.dias_decisao <= 7:
            opcoes.append(
                (
                    f"O cliente decidiu em {dias} — sinal de que acertou em cheio.",
                    f"Resposta do cliente em {dias}: raramente é tão rápido.",
                )
            )
        elif orcamento.dias_decisao >= DIAS_ORCAMENTO_ANTIGO:
            opcoes.append(
                (
                    f"Estava enviado há {dias} e o cliente acabou por voltar — ainda "
                    "bem que não desistiu dele.",
                    f"Depois de {dias} à espera, o cliente voltou e fechou.",
                )
            )
    if utilizador.adjudicados_mes >= 2 and utilizador.mes:
        mes = MESES[utilizador.mes - 1]
        opcoes.append(
            (
                f"É o seu {_ordinal(utilizador.adjudicados_mes)} orçamento adjudicado "
                f"em {mes}.",
                f"Já leva {utilizador.adjudicados_mes} orçamentos ganhos em {mes}.",
            )
        )
    elif utilizador.adjudicados_mes == 1 and utilizador.mes:
        mes = MESES[utilizador.mes - 1]
        opcoes.append(
            (
                f"É o primeiro adjudicado de {mes} — bom arranque de mês.",
                f"Abriu {mes} com um orçamento ganho.",
            )
        )
    opcoes.append(
        (
            f"É o seu {_ordinal(utilizador.adjudicados)} orçamento adjudicado em {ano}.",
            f"Mais um para a conta de {ano}: leva {utilizador.adjudicados} orçamentos "
            "ganhos.",
        )
    )
    return opcoes


def destaques_nao_adjudicado(
    cliente: ResumoCliente, utilizador: ResumoUtilizador
) -> list[tuple[str, ...]]:
    """Só coisas verdadeiras e positivas — nunca conselhos sobre o cliente."""
    opcoes: list[tuple[str, ...]] = []
    if utilizador.adjudicados:
        maneiras = [
            f"Em {utilizador.ano} já ganhou {utilizador.adjudicados} orçamento(s) — "
            "o próximo pode ser já a seguir.",
            f"Em {utilizador.ano} leva {_euros(utilizador.valor_adjudicado)} "
            "adjudicados. O trabalho está a dar resultado.",
        ]
        if utilizador.adjudicados_mes >= 1 and utilizador.mes:
            maneiras.append(
                f"Só em {MESES[utilizador.mes - 1]} já ganhou "
                f"{utilizador.adjudicados_mes} orçamento(s)."
            )
        opcoes.append(tuple(maneiras))
    if cliente.adjudicados >= 1:
        opcoes.append(
            (
                f"Este cliente já lhe adjudicou {cliente.adjudicados} orçamento(s) — "
                "este não foi, o próximo pode ser.",
                f"Com este cliente leva {cliente.adjudicados} obras ganhas; uma que "
                "não foi não muda isso.",
            )
        )
    opcoes.append(
        (
            "O orçamento fica guardado: se o cliente voltar, duplica-se para uma "
            "versão nova e está pronto.",
            "O próximo orçamento é uma nova oportunidade.",
        )
    )
    return opcoes


def _escolher_destaque(opcoes: list[tuple[str, ...]], semente: int) -> str:
    """O facto mais marcante, dito de uma das maneiras possíveis."""
    if not opcoes:
        return ""
    maneiras = opcoes[0]
    return maneiras[random.Random(semente + 1).randrange(len(maneiras))]


def destaque_adjudicado(
    orcamento: OrcamentoMudado, cliente: ResumoCliente, utilizador: ResumoUtilizador
) -> str:
    """O facto mais marcante desta adjudicação, na sua primeira maneira."""
    return destaques_adjudicado(orcamento, cliente, utilizador)[0][0]


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
            destaque=_escolher_destaque(
                destaques_adjudicado(orcamento, cliente, utilizador), semente
            ),
            factos=tuple(factos),
            grafico=dict(cliente.por_estado),
            cliente=orcamento.cliente,
        )

    factos = [linha_orcamento, *_factos_cliente(cliente)]
    destaque = _escolher_destaque(
        destaques_nao_adjudicado(cliente, utilizador), semente
    )
    return Mensagem(
        estado=NAO_ADJUDICADO,
        titulo=f"Desta vez não foi{', ' + primeiro if primeiro else ''}.",
        frase=_escolher(ABERTURAS_NAO_ADJUDICADO, semente, ultima_frase),
        destaque=destaque,
        factos=tuple(factos),
        grafico=dict(cliente.por_estado),
        cliente=orcamento.cliente,
    )


def mes_de(valor: object) -> int:
    """Mês de uma data do V2 («2026-08-21», date ou datetime); 0 se não se sabe."""
    if isinstance(valor, date):
        return valor.month
    texto = str(valor or "")
    return int(texto[5:7]) if texto[5:7].isdigit() else 0


def ano_de(valor: object) -> int:
    """Ano de uma data do V2 (texto «2026-08-21», date ou datetime)."""
    if isinstance(valor, date):
        return valor.year
    texto = str(valor or "")
    return int(texto[:4]) if texto[:4].isdigit() else 0


# ---- «O seu trabalho»: o mês da própria pessoa -----------------------------

#: Quantos meses aparecem no gráfico do assistente.
MESES_NO_GRAFICO = 6


@dataclass(frozen=True)
class MesDeTrabalho:
    ano: int
    mes: int
    criados: int
    ganhos: int
    valor_ganho: Decimal

    @property
    def rotulo(self) -> str:
        return f"{MESES[self.mes - 1][:3]}/{str(self.ano)[2:]}"


@dataclass(frozen=True)
class ResumoMensal:
    ano: int
    mes: int
    criados: int
    ganhos: int
    valor_ganho: Decimal
    #: Quantos orçamentos passaram a Adjudicado DENTRO deste mês (histórico do
    #: V3), incluindo os criados em meses anteriores. None quando não se sabe.
    adjudicados_no_mes: int | None
    criados_no_ano: int
    ganhos_no_ano: int
    valor_ganho_no_ano: Decimal
    meses: tuple[MesDeTrabalho, ...]

    @property
    def mes_anterior(self) -> MesDeTrabalho | None:
        return self.meses[-2] if len(self.meses) >= 2 else None

    @property
    def vazio(self) -> bool:
        return not self.criados_no_ano and not self.ganhos_no_ano


def _mes_anterior(ano: int, mes: int) -> tuple[int, int]:
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def resumo_mensal(
    historico: Iterable[OrcamentoHistorico],
    utilizador: str,
    *,
    ano: int,
    mes: int,
    adjudicados_no_mes: int | None = None,
) -> ResumoMensal:
    """O trabalho do próprio, por mês de CRIAÇÃO do orçamento.

    A data de criação é a única que existe nos dois sítios (V3 e Arquivo V2);
    o número de adjudicações feitas dentro do mês vem à parte, do histórico de
    estados do V3, e é isso que ``adjudicados_no_mes`` traz.
    """
    meus = [linha for linha in historico if mesmo_nome(linha.utilizador, utilizador)]
    por_mes: dict[tuple[int, int], list[OrcamentoHistorico]] = {}
    for linha in meus:
        if linha.ano and linha.mes:
            por_mes.setdefault((linha.ano, linha.mes), []).append(linha)

    def resumo_do_mes(chave: tuple[int, int]) -> MesDeTrabalho:
        resultados = _por_orcamento(por_mes.get(chave, []))
        ganhos = [(v or Decimal("0")) for estado, v, _ in resultados if estado == ADJUDICADO]
        return MesDeTrabalho(
            ano=chave[0],
            mes=chave[1],
            criados=len(resultados),
            ganhos=len(ganhos),
            valor_ganho=sum(ganhos, Decimal("0")),
        )

    chaves: list[tuple[int, int]] = []
    atual = (ano, mes)
    for _ in range(MESES_NO_GRAFICO):
        chaves.append(atual)
        atual = _mes_anterior(*atual)
    chaves.reverse()
    meses = tuple(resumo_do_mes(chave) for chave in chaves)
    este = meses[-1]

    do_ano = [linha for linha in meus if linha.ano == ano]
    resultados_ano = _por_orcamento(do_ano)
    ganhos_ano = [
        (v or Decimal("0")) for estado, v, _ in resultados_ano if estado == ADJUDICADO
    ]
    return ResumoMensal(
        ano=ano,
        mes=mes,
        criados=este.criados,
        ganhos=este.ganhos,
        valor_ganho=este.valor_ganho,
        adjudicados_no_mes=adjudicados_no_mes,
        criados_no_ano=len(resultados_ano),
        ganhos_no_ano=len(ganhos_ano),
        valor_ganho_no_ano=sum(ganhos_ano, Decimal("0")),
        meses=meses,
    )


def frases_do_mes(resumo: ResumoMensal) -> list[str]:
    """As linhas que o assistente mostra em «O seu trabalho»."""
    mes = MESES[resumo.mes - 1]
    linhas: list[str] = []
    if resumo.criados:
        linha = f"Em {mes} criou {resumo.criados} orçamento(s)"
        if resumo.ganhos:
            linha += (
                f" e {resumo.ganhos} desses já foram adjudicados "
                f"({_euros(resumo.valor_ganho)})"
            )
        linhas.append(linha + ".")
    else:
        linhas.append(f"Ainda não criou orçamentos em {mes}.")
    if resumo.adjudicados_no_mes:
        linhas.append(
            f"Fechou {resumo.adjudicados_no_mes} orçamento(s) em {mes}, contando os "
            "que vinham de meses anteriores."
        )
    anterior = resumo.mes_anterior
    if anterior is not None and anterior.criados:
        diferenca = resumo.criados - anterior.criados
        if diferenca > 0:
            linhas.append(
                f"São mais {diferenca} do que em {MESES[anterior.mes - 1]} "
                f"({anterior.criados})."
            )
        elif diferenca < 0:
            linhas.append(
                f"Em {MESES[anterior.mes - 1]} tinha criado {anterior.criados}."
            )
        else:
            linhas.append(f"Os mesmos que em {MESES[anterior.mes - 1]}.")
    if resumo.criados_no_ano:
        linhas.append(
            f"No total de {resumo.ano}: {resumo.criados_no_ano} orçamentos criados, "
            f"{resumo.ganhos_no_ano} ganhos ({_euros(resumo.valor_ganho_no_ano)})."
        )
    return linhas
