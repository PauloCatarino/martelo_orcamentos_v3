"""Regras do registo de horas (folha de horas): cálculo, feriados e resumos.

Vêm da app isolada «Registo de Horas · Lança Encanto» (PHP, out-2026), que
por sua vez copiava as folhas em papel — e o Paulo confirmou-as uma a uma:

* **dia útil**: saída − entrada − pausas (+ 2.º período) + acerto; até às
  horas normais do dia (8h) são normais e o resto é extra, escrito «8 + 3».
  Com menos de 8h a diferença desconta ao mês: «5 − 3»;
* **fim de semana, feriado e férias**: tudo o que se trabalhou é extra;
* **folga**: folga paga com horas extra — desconta as horas indicadas, «−8»;
* **cada mês fecha por si**: o saldo não passa para o mês seguinte;
* **subsídio de alimentação** (extra pago pela empresa, 10-10-2026): só nos
  dias fora do horário normal das 40 horas — sábado, domingo, feriado e dia
  de férias trabalhado —, 1,25 € por cada hora INTEIRA, até 10 € por dia.
  As horas extra de um dia útil não contam.

Várias entradas e saídas no mesmo dia (pedido do Paulo, 19-10-2026): cada
dia tem até 6 linhas Entrada/Saída — quem sai às 10h para uma consulta e volta
às 13h, ou sai às 17h e faz mais umas horas em casa à noite. As linhas são
postas pela ordem do dia; duas linhas que se sobrepõem são recusadas. O
«2.º período» de antes é agora a linha 2. Fins de semana, feriados e férias
também têm linhas (ou só o total de horas, como os dias antigos).

* **teletrabalho** (19-10-2026): dia útil feito parte em casa, parte na
  empresa, contado **pelo relógio**: dentro do horário habitual (das
  Definições, 08:00–17:00) são horas normais; antes ou depois é extra. O que
  faltar para as horas normais desconta ao mês — a não ser que se escreva em
  «Ausência justificada» (ex.: começou em casa e foi acabar o trabalho à
  empresa). As extra contam como as de um dia útil; não dá subsídio.

O «acerto» continua a existir para as pausas a mais e para o histórico que
veio da app antiga.

Tudo em minutos. Uma saída igual ou anterior à entrada é no dia seguinte
(«24h», «1h30 (+1)»). Sem base de dados e sem Qt: é aqui que os testes provam
que as contas batem com as da app antiga.
"""

from __future__ import annotations

import calendar
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, time, timedelta

# ---------------------------------------------------------------------------
# Tipos de dia
# ---------------------------------------------------------------------------
TIPO_UTIL = "util"
TIPO_TELETRABALHO = "teletrabalho"
TIPO_FIM_SEMANA = "fim_semana"
TIPO_FERIADO = "feriado"
TIPO_FERIAS = "ferias"
TIPO_FOLGA = "folga"
TIPOS = (
    TIPO_UTIL, TIPO_TELETRABALHO, TIPO_FIM_SEMANA, TIPO_FERIADO, TIPO_FERIAS, TIPO_FOLGA,
)
#: Os dias de trabalho com horário: 8h normais, acerto, jantar.
TIPOS_COM_HORARIO = frozenset({TIPO_UTIL, TIPO_TELETRABALHO})
#: Os dias fora do horário normal: tudo o que se trabalhou é extra.
TIPOS_FORA_DO_HORARIO = frozenset({TIPO_FIM_SEMANA, TIPO_FERIADO, TIPO_FERIAS})

NOMES_TIPOS = {
    TIPO_UTIL: "Dia útil",
    TIPO_TELETRABALHO: "Teletrabalho",
    TIPO_FIM_SEMANA: "Fim de semana",
    TIPO_FERIADO: "Feriado",
    TIPO_FERIAS: "Férias",
    TIPO_FOLGA: "Folga (desconta)",
}

AJUDA_TIPOS = {
    TIPO_UTIL: (
        "Até às horas normais do dia (8h) são horas normais; o resto conta como "
        "extra. Com menos horas, a diferença desconta ao mês."
    ),
    TIPO_TELETRABALHO: (
        "Parte do dia em casa, parte na empresa. Dentro do horário habitual são "
        "horas normais; antes ou depois conta como extra. O que faltar para as "
        "horas normais desconta ao mês, a não ser que o escreva em «Ausência "
        "justificada»."
    ),
    TIPO_FIM_SEMANA: "Todas as horas trabalhadas contam como extra.",
    TIPO_FERIADO: (
        "Todas as horas trabalhadas contam como extra. Deixe as horas vazias se "
        "não trabalhou."
    ),
    TIPO_FERIAS: (
        "Não conta horas. Se trabalhou, indique as entradas e saídas: contam como extra."
    ),
    TIPO_FOLGA: "Folga paga com horas extra: desconta as horas indicadas ao total do mês.",
}

MENOS = "−"
MINUTOS_DIA = 24 * 60
HORAS_NORMAIS_PADRAO = 8 * 60
PAUSA_PADRAO = 60
HORAS_FOLGA_PADRAO = 8 * 60
#: Limites que a app antiga já usava.
MAX_HORAS_DIA = 24 * 60
MAX_ACERTO = 12 * 60
MAX_AUSENCIA = 12 * 60
#: Linhas Entrada/Saída num dia.
MAX_PERIODOS = 6
#: Um intervalo entre linhas que apanhe pelo menos meia hora entre as 12h e as
#: 15h já é o almoço: a janela desliga «Descontar almoço» sozinha.
ALMOCO_DESDE = 12 * 60
ALMOCO_ATE = 15 * 60
ALMOCO_MINIMO = 30

#: Subsídio de alimentação extra (regra do Paulo, 10-10-2026), em cêntimos:
#: 1,25 € por hora inteira, no máximo 10 € por dia (8 horas ou mais).
SUBSIDIO_CENTIMOS_POR_HORA = 125
SUBSIDIO_MAXIMO_DIA_CENTIMOS = 1000
#: Os dias fora do horário normal. O dia útil não entra, mesmo com horas
#: extra; a folga desconta, não é trabalho.
TIPOS_COM_SUBSIDIO = frozenset({TIPO_FIM_SEMANA, TIPO_FERIADO, TIPO_FERIAS})
ROTULO_SUBSIDIO = "Subsídio de alimentação"

#: O registo oficial começa a 1 de outubro de 2026 (decisão do Paulo); o que
#: está antes é histórico das folhas em papel e nunca aparece «por registar».
INICIO_REGISTO_PADRAO = date(2026, 10, 1)

#: Envio à contabilidade: dia 2 de cada mês, às 9h20, com as horas do mês
#: anterior.
DIA_ENVIO = 2
HORA_ENVIO = time(9, 20)
EMAIL_CONTABILIDADE_PADRAO = "financeiro@lancaencanto.pt"
#: O lembrete dos dias por registar olha, no máximo, para estes dias atrás.
JANELA_LEMBRETE_DIAS = 62

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)
SEMANA = (
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
)
SEMANA_CURTO = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


class ErroRegistoHoras(ValueError):
    """Um dia que não se pode guardar; a mensagem é para o utilizador ler."""


# ---------------------------------------------------------------------------
# Feriados nacionais
# ---------------------------------------------------------------------------
def domingo_de_pascoa(ano: int) -> date:
    """Algoritmo de Meeus/Jones/Butcher (calendário gregoriano)."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741 - nome do algoritmo
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(ano, mes, dia + 1)


_CACHE_FERIADOS: dict[int, dict[date, str]] = {}


def feriados_do_ano(ano: int) -> dict[date, str]:
    """Feriados nacionais de Portugal (os mesmos da app antiga)."""
    if ano not in _CACHE_FERIADOS:
        pascoa = domingo_de_pascoa(ano)
        _CACHE_FERIADOS[ano] = {
            date(ano, 1, 1): "Ano Novo",
            pascoa - timedelta(days=2): "Sexta-feira Santa",
            pascoa: "Páscoa",
            date(ano, 4, 25): "Dia da Liberdade",
            date(ano, 5, 1): "Dia do Trabalhador",
            pascoa + timedelta(days=60): "Corpo de Deus",
            date(ano, 6, 10): "Dia de Portugal",
            date(ano, 8, 15): "Assunção de Nossa Senhora",
            date(ano, 10, 5): "Implantação da República",
            date(ano, 11, 1): "Dia de Todos os Santos",
            date(ano, 12, 1): "Restauração da Independência",
            date(ano, 12, 8): "Imaculada Conceição",
            date(ano, 12, 25): "Natal",
        }
    return _CACHE_FERIADOS[ano]


def feriado(dia: date) -> str:
    """Nome do feriado nacional deste dia, ou ``""``."""
    return feriados_do_ano(dia.year).get(dia, "")


def e_fim_de_semana(dia: date) -> bool:
    return dia.weekday() >= 5


def tipo_por_defeito(dia: date, habitual: str = TIPO_UTIL) -> str:
    """O tipo com que um dia novo abre; de segunda a sexta é o das Definições."""
    if feriado(dia):
        return TIPO_FERIADO
    if e_fim_de_semana(dia):
        return TIPO_FIM_SEMANA
    return habitual if habitual in TIPOS_COM_HORARIO else TIPO_UTIL


def e_dia_de_trabalho(dia: date) -> bool:
    """Segunda a sexta e não feriado: os dias que se esperam registados."""
    return not e_fim_de_semana(dia) and not feriado(dia)


# ---------------------------------------------------------------------------
# Cálculo de um dia
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DadosDia:
    """O que se escreve na folha para um dia."""

    tipo: str
    #: A 1.ª linha Entrada/Saída (e a 2.ª, o antigo «2.º período»). Com
    #: ``periodos`` preenchido, estes quatro campos não contam.
    entrada: int | None = None
    saida: int | None = None
    entrada2: int | None = None
    saida2: int | None = None
    almoco: bool = True
    jantar: bool = False
    acerto: int = 0
    #: Fim de semana, feriado e férias sem linhas: o total de horas trabalhadas
    #: (na folga, as horas a descontar).
    horas: int = 0
    #: As linhas Entrada/Saída, pela ordem em que estão na janela; uma linha
    #: com as duas horas vazias não conta.
    periodos: tuple[tuple[int | None, int | None], ...] = ()
    #: Teletrabalho: horas fora, dentro do horário, que não descontam.
    ausencia: int = 0


@dataclass(frozen=True)
class CalculoDia:
    trabalhado: int
    normais: int
    #: Extra do dia já com o que falta descontado (negativo = desconta).
    extra: int
    #: Saídas já com o dia seguinte somado (ex.: 1h30 → 25h30 = 1530).
    saida: int | None = None
    entrada2: int | None = None
    saida2: int | None = None
    #: As linhas pela ordem do dia, com as saídas do dia seguinte somadas.
    periodos: tuple[tuple[int, int], ...] = ()
    #: Teletrabalho: o que faltou para as horas normais (já tirado a ``extra``).
    falta: int = 0
    ausencia: int = 0
    #: Teletrabalho: minutos feitos antes ou depois do horário habitual.
    fora_horario: int = 0

    @property
    def extra_feito(self) -> int:
        """As horas extra feitas, antes de descontar o que faltou."""
        return self.extra + self.falta if self.falta else max(self.extra, 0)

    @property
    def desconto(self) -> int:
        """O que desconta ao mês (0 ou negativo)."""
        return -self.falta if self.falta else min(self.extra, 0)


def _depois_de(hora: int, referencia: int) -> int:
    """A mesma hora do relógio, puxada para depois da referência."""
    while hora <= referencia:
        hora += MINUTOS_DIA
    return hora


def periodos_pedidos(dados: DadosDia) -> list[tuple[int | None, int | None]]:
    """As linhas Entrada/Saída do dia (as antigas ``entrada``/``entrada2`` também)."""
    if dados.periodos:
        return [(e, s) for e, s in dados.periodos]
    pedidos: list[tuple[int | None, int | None]] = []
    if dados.tipo in TIPOS_COM_HORARIO or dados.entrada is not None or dados.saida is not None:
        pedidos.append((dados.entrada, dados.saida))
    if dados.entrada2 is not None or dados.saida2 is not None:
        pedidos.append((dados.entrada2, dados.saida2))
    return pedidos


def ordenar_periodos(
    pedidos: Iterable[tuple[int | None, int | None]],
) -> list[tuple[int, int]]:
    """Linhas → períodos pela ordem do dia; ``ErroRegistoHoras`` se não fizerem sentido.

    Linhas com as duas horas vazias saltam-se. Uma saída igual ou anterior à
    entrada é no dia seguinte, e só a última linha do dia a pode ter: duas
    linhas que se sobrepõem são recusadas (a hora estaria contada duas vezes).
    """
    pedidos = list(pedidos)
    cheias: list[tuple[int, int, int]] = []
    for numero, (entrada, saida) in enumerate(pedidos, start=1):
        if entrada is None and saida is None:
            continue
        if entrada is None or saida is None:
            if len(pedidos) == 1:
                raise ErroRegistoHoras(
                    "Indique a hora de entrada." if entrada is None else "Indique a hora de saída."
                )
            raise ErroRegistoHoras(
                f"Na linha {numero} indique a entrada e a saída (ou deixe as duas vazias)."
            )
        cheias.append((entrada % MINUTOS_DIA, saida % MINUTOS_DIA, numero))
    if len(cheias) > MAX_PERIODOS:
        raise ErroRegistoHoras(f"No máximo {MAX_PERIODOS} entradas e saídas por dia.")
    cheias.sort(key=lambda linha: (linha[0], linha[2]))
    periodos: list[tuple[int, int]] = []
    numeros: list[int] = []
    for entrada, saida, numero in cheias:
        saida = _depois_de(saida, entrada)
        if periodos and entrada < periodos[-1][1]:
            fim = min(periodos[-1][1], saida)
            raise ErroRegistoHoras(
                f"As linhas {numeros[-1]} e {numero} sobrepõem-se: das "
                f"{hora_texto(entrada)} às {hora_texto(fim)} estaria contado duas vezes."
            )
        periodos.append((entrada, saida))
        numeros.append(numero)
    if periodos and periodos[-1][1] - periodos[0][0] > MINUTOS_DIA:
        raise ErroRegistoHoras("O dia não pode passar de 24 horas.")
    return periodos


def intervalo_almoco(periodos: Iterable[tuple[int, int]]) -> tuple[int, int] | None:
    """O intervalo entre duas linhas que já é o almoço (12h–15h), ou ``None``."""
    lista = list(periodos)
    for (_e1, saida), (entrada, _s2) in zip(lista, lista[1:]):
        dentro = min(entrada, ALMOCO_ATE) - max(saida, ALMOCO_DESDE)
        if dentro >= ALMOCO_MINIMO:
            return saida, entrada
    return None


def _dentro_do_horario(periodos: Iterable[tuple[int, int]], horario: tuple[int, int]) -> int:
    inicio, fim = horario
    fim = _depois_de(fim, inicio) if fim <= inicio else fim
    return sum(max(0, min(s, fim) - max(e, inicio)) for e, s in periodos)


def _calculo(
    trabalhado: int, normais: int, extra: int, periodos: list[tuple[int, int]], **extras
) -> CalculoDia:
    return CalculoDia(
        trabalhado=trabalhado,
        normais=normais,
        extra=extra,
        saida=periodos[0][1] if periodos else None,
        entrada2=periodos[1][0] if len(periodos) > 1 else None,
        saida2=periodos[1][1] if len(periodos) > 1 else None,
        periodos=tuple(periodos),
        **extras,
    )


def calcular_dia(
    dados: DadosDia,
    *,
    horas_normais: int = HORAS_NORMAIS_PADRAO,
    pausa: int = PAUSA_PADRAO,
    horario: tuple[int, int] = (8 * 60, 17 * 60),
) -> CalculoDia:
    """As contas da folha para um dia; ``ErroRegistoHoras`` se não fizer sentido.

    ``horario`` é o horário habitual da pessoa (Definições): só o Teletrabalho
    o usa, para separar as horas normais das extra pelo relógio.
    """
    if dados.tipo not in TIPOS:
        raise ErroRegistoHoras("Tipo de dia inválido.")

    if dados.tipo == TIPO_FOLGA:
        if not 0 <= dados.horas <= MAX_HORAS_DIA:
            raise ErroRegistoHoras("Indique um número de horas entre 0 e 24.")
        if dados.horas == 0:
            raise ErroRegistoHoras("Indique as horas a descontar.")
        return CalculoDia(trabalhado=0, normais=0, extra=-dados.horas)

    pedidos = periodos_pedidos(dados)
    com_linhas = any(e is not None or s is not None for e, s in pedidos)

    if dados.tipo in TIPOS_FORA_DO_HORARIO:
        if not com_linhas:
            # Só o total de horas (como os dias antigos).
            if not 0 <= dados.horas <= MAX_HORAS_DIA:
                raise ErroRegistoHoras("Indique um número de horas entre 0 e 24.")
            if dados.horas == 0 and dados.tipo == TIPO_FIM_SEMANA:
                raise ErroRegistoHoras("Indique as horas trabalhadas.")
            return CalculoDia(trabalhado=dados.horas, normais=0, extra=dados.horas)
        periodos = ordenar_periodos(pedidos)
        trabalhado = sum(s - e for e, s in periodos) - (pausa if dados.almoco else 0)
        if trabalhado < 0:
            raise ErroRegistoHoras("Os descontos excedem as horas trabalhadas.")
        return _calculo(trabalhado, 0, trabalhado, periodos)

    # Dia útil e teletrabalho.
    if abs(dados.acerto) > MAX_ACERTO:
        raise ErroRegistoHoras("O acerto tem de estar entre −12 e 12 horas.")
    periodos = ordenar_periodos(pedidos or [(None, None)])
    if not periodos:
        raise ErroRegistoHoras("Indique a hora de entrada e a de saída.")
    soma = sum(s - e for e, s in periodos)
    almoco = pausa if dados.almoco else 0
    jantar = pausa if dados.jantar else 0
    trabalhado = soma + dados.acerto - almoco - jantar
    if trabalhado < 0:
        raise ErroRegistoHoras("Os descontos excedem as horas trabalhadas.")

    if dados.tipo == TIPO_UTIL:
        return _calculo(
            trabalhado, min(trabalhado, horas_normais), trabalhado - horas_normais, periodos
        )

    # Teletrabalho: pelo relógio.
    if not 0 <= dados.ausencia <= MAX_AUSENCIA:
        raise ErroRegistoHoras("A ausência justificada tem de estar entre 0 e 12 horas.")
    dentro = _dentro_do_horario(periodos, horario)
    fora = soma - dentro
    # O almoço sai das horas do horário; o jantar, das de fora.
    tira = min(almoco, dentro)
    dentro, fora = dentro - tira, fora - (almoco - tira)
    tira = min(jantar, fora)
    fora, dentro = fora - tira, dentro - (jantar - tira)
    if dados.acerto > 0:
        # Um acerto positivo enche primeiro as horas normais; o resto é extra.
        enche = min(dados.acerto, max(0, horas_normais - dentro))
        dentro, fora = dentro + enche, fora + dados.acerto - enche
    else:
        dentro += dados.acerto
    # O que ficou negativo de um lado sai do outro (os dois somam o trabalhado).
    if dentro < 0:
        dentro, fora = 0, fora + dentro
    elif fora < 0:
        dentro, fora = dentro + fora, 0
    feito = fora + max(0, dentro - horas_normais)
    normais = min(dentro + dados.ausencia, horas_normais)
    falta = max(0, horas_normais - dentro - dados.ausencia)
    return _calculo(
        trabalhado,
        normais,
        feito - falta,
        periodos,
        falta=falta,
        ausencia=dados.ausencia,
        fora_horario=max(fora, 0),
    )


def subsidio_alimentacao(tipo: str, trabalhado: int) -> int:
    """Cêntimos de subsídio de alimentação de um dia.

    Só fora do horário normal (fim de semana, feriado, férias trabalhadas):
    1,25 € por hora inteira — 2h30 dá 2,50 € —, até 10 € por dia.
    """
    if tipo not in TIPOS_COM_SUBSIDIO or trabalhado <= 0:
        return 0
    horas_inteiras = int(trabalhado) // 60
    return min(horas_inteiras * SUBSIDIO_CENTIMOS_POR_HORA, SUBSIDIO_MAXIMO_DIA_CENTIMOS)


def formatar_euros(centimos: int) -> str:
    """Cêntimos → «21,88 €», «1.250,00 €» (como os preços nos menus)."""
    euros, resto = divmod(abs(int(centimos)), 100)
    sinal = MENOS if centimos < 0 else ""
    return f"{sinal}{euros:,}".replace(",", ".") + f",{resto:02d} €"


# ---------------------------------------------------------------------------
# Escrita das horas (como na folha em papel)
# ---------------------------------------------------------------------------
def formatar_horas(minutos: int) -> str:
    """Minutos → «3» ou «2h30» (sem sinal)."""
    total = abs(int(round(minutos)))
    h, m = divmod(total, 60)
    return f"{h}h{m:02d}" if m else str(h)


def formatar_total(minutos: int, com_mais: bool = False) -> str:
    """Minutos → «61h», «2h30», «−3h»; «+2h» com ``com_mais``."""
    sinal = MENOS if minutos < 0 else ("+" if com_mais and minutos > 0 else "")
    h, m = divmod(abs(int(round(minutos))), 60)
    return f"{sinal}{h}h{m:02d}" if m else f"{sinal}{h}h"


def formatar_hora(minutos: int | None) -> str:
    """Hora do relógio: «8h», «17h30», «24h», «1h30 (+1)»."""
    if minutos is None:
        return ""
    seguinte = minutos > MINUTOS_DIA
    relogio = minutos - MINUTOS_DIA if seguinte else minutos
    h, m = divmod(relogio, 60)
    texto = f"{h}h{m:02d}" if m else f"{h}h"
    return texto + (" (+1)" if seguinte else "")


def hora_texto(minutos: int | None) -> str:
    """Hora do relógio para um campo: 1530 → «01:30»."""
    if minutos is None:
        return ""
    h, m = divmod(minutos % MINUTOS_DIA, 60)
    return f"{h:02d}:{m:02d}"


def ler_hora(texto: str | None) -> int | None:
    """«8», «8:30», «08h30», «17h» → minutos; ``None`` se vazio/inválido."""
    valor = (texto or "").strip().lower().replace(" ", "")
    if not valor:
        return None
    encontrado = re.fullmatch(r"(\d{1,2})(?:[:h.](\d{2})?)?h?", valor)
    if not encontrado:
        return None
    horas = int(encontrado.group(1))
    minutos = int(encontrado.group(2) or 0)
    if horas > 24 or minutos > 59 or (horas == 24 and minutos):
        return None
    return horas * 60 + minutos


def horas_como_na_folha(
    tipo: str, normais: int, extra: int, trabalhado: int, falta: int = 0
) -> str:
    """«8 + 3», «5 − 3», «8», «6», «−8».

    No teletrabalho pode haver horas extra (fora do horário) e horas em falta
    no mesmo dia: a folha mostra «6 + 3» e o que falta segue na coluna Extra.
    """
    if tipo in TIPOS_COM_HORARIO:
        feito = extra + falta if falta else max(extra, 0)
        if feito > 0:
            return f"{formatar_horas(normais)} + {formatar_horas(feito)}"
        if extra < 0:
            return f"{formatar_horas(normais)} {MENOS} {formatar_horas(-extra)}"
        return formatar_horas(normais)
    if tipo == TIPO_FOLGA:
        return f"{MENOS}{formatar_horas(-extra)}"
    return formatar_horas(trabalhado) if trabalhado > 0 else ""


def texto_periodos(periodos: Iterable[tuple[int, int]], *, maiusculas: bool = False) -> str:
    """«8h – 10h · 13h – 17h · 20h – 23h» (no PDF, «8H – 10H …»)."""
    partes = []
    for entrada, saida in periodos:
        texto = f"{formatar_hora(entrada)} – {formatar_hora(saida)}"
        partes.append(texto.upper() if maiusculas else texto)
    return " · ".join(partes)


def etiqueta_do_dia(tipo: str, dia: date) -> str:
    """O que vai para as observações da folha: «Sábado», «Feriado», «Férias»…"""
    if tipo == TIPO_UTIL:
        return ""
    if tipo == TIPO_FIM_SEMANA:
        return {5: "Sábado", 6: "Domingo"}.get(dia.weekday(), "Fim de semana")
    if tipo == TIPO_FOLGA:
        return "Folga"
    return NOMES_TIPOS[tipo]


def nome_mes(ano: int, mes: int) -> str:
    return f"{MESES[mes - 1]} de {ano}"


def titulo_dia(dia: date) -> str:
    """«Terça-feira, 30 de setembro de 2026»."""
    return (
        f"{SEMANA[dia.weekday()].capitalize()}, {dia.day} de "
        f"{MESES[dia.month - 1]} de {dia.year}"
    )


def sem_acentos(texto: str) -> str:
    normal = unicodedata.normalize("NFD", texto or "")
    sem = "".join(ch for ch in normal if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^A-Za-z0-9]+", "_", sem).strip("_").upper()


def nome_ficheiro_folha(nome: str, ano: int, mes: int) -> str:
    """Como as folhas digitalizadas: ``HORAS_PAULO_CATARINO_SETEMBRO_2026.pdf``."""
    return f"HORAS_{sem_acentos(nome) or 'COLABORADOR'}_{sem_acentos(MESES[mes - 1])}_{ano}.pdf"


# ---------------------------------------------------------------------------
# O mês
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LinhaDia:
    """Um dia guardado, já com as contas feitas (é o que a base devolve)."""

    data: date
    tipo: str
    entrada: int | None = None
    saida: int | None = None
    entrada2: int | None = None
    saida2: int | None = None
    almoco: bool = False
    jantar: bool = False
    acerto: int = 0
    horas: int = 0
    trabalhado: int = 0
    normais: int = 0
    extra: int = 0
    observacoes: str = ""
    origem: str = "martelo"
    #: Todas as linhas Entrada/Saída (desde 19-10-2026); vazio nos dias que só
    #: têm ``entrada``/``entrada2`` (os antigos) ou só o total de horas.
    periodos: tuple[tuple[int, int], ...] = ()
    #: Teletrabalho: ausência justificada e o que faltou para as horas normais.
    ausencia: int = 0
    falta: int = 0

    @property
    def lista_periodos(self) -> tuple[tuple[int, int], ...]:
        """As linhas do dia; nos dias antigos, a entrada/saída e o 2.º período."""
        if self.periodos:
            return self.periodos
        lista = []
        if self.entrada is not None and self.saida is not None:
            lista.append((self.entrada, self.saida))
        if self.entrada2 is not None and self.saida2 is not None:
            lista.append((self.entrada2, self.saida2))
        return tuple(lista)

    @property
    def so_total(self) -> bool:
        """Fim de semana, feriado ou férias registado só com o total de horas."""
        return self.tipo in TIPOS_FORA_DO_HORARIO and not self.lista_periodos and self.horas > 0

    @property
    def extra_feito(self) -> int:
        """As horas extra feitas, antes de descontar o que faltou."""
        return self.extra + self.falta if self.falta else max(self.extra, 0)

    @property
    def desconto(self) -> int:
        """O que este dia desconta ao mês (0 ou negativo)."""
        return -self.falta if self.falta else min(self.extra, 0)

    @property
    def extra_partes(self) -> tuple[int, ...]:
        """O que vai para a coluna Extra: «+3h · −2h» no teletrabalho com falta."""
        if self.falta and self.extra_feito > 0:
            return (self.extra_feito, -self.falta)
        return (self.extra,) if self.extra else ()

    @property
    def horas_folha(self) -> str:
        return horas_como_na_folha(
            self.tipo, self.normais, self.extra, self.trabalhado, self.falta
        )

    @property
    def subsidio(self) -> int:
        """Subsídio de alimentação do dia, em cêntimos (0 nos dias úteis)."""
        return subsidio_alimentacao(self.tipo, self.trabalhado)

    @property
    def subsidio_folha(self) -> str:
        """«5,00 €» na folha; vazio quando o dia não tem subsídio."""
        return formatar_euros(self.subsidio) if self.subsidio else ""

    @property
    def horario(self) -> str:
        """«8h – 10h · 13h – 17h · 20h – 23h»: todas as linhas do dia."""
        if self.tipo == TIPO_FOLGA:
            return ""
        return texto_periodos(self.lista_periodos)

    def observacoes_folha(self) -> str:
        partes = [etiqueta_do_dia(self.tipo, self.data)]
        if self.tipo in TIPOS_COM_HORARIO:
            if self.acerto:
                partes.append(f"Acerto {formatar_total(self.acerto, com_mais=True)}")
            if self.ausencia:
                partes.append(f"Ausência justificada {formatar_total(self.ausencia)}")
            if self.jantar:
                partes.append("Desc. jantar")
        partes.append(self.observacoes)
        return " – ".join(p for p in partes if p)


@dataclass
class ResumoMes:
    """Totais do mês, separados como a contabilidade os precisa."""

    normais: int = 0
    extra_uteis: int = 0
    extra_sabados: int = 0
    extra_domingos: int = 0
    extra_feriados: int = 0
    extra_ferias: int = 0
    descontos: int = 0
    dias_registados: int = 0
    dias_uteis: int = 0
    dias_ferias: int = 0
    dias_feriado: int = 0
    dias_folga: int = 0
    #: Dias de teletrabalho (também contam nos ``dias_uteis``).
    dias_teletrabalho: int = 0
    #: Subsídio de alimentação do mês, em cêntimos.
    subsidio: int = 0

    @property
    def extra_positivo(self) -> int:
        return (
            self.extra_uteis
            + self.extra_sabados
            + self.extra_domingos
            + self.extra_feriados
            + self.extra_ferias
        )

    @property
    def total_extra(self) -> int:
        """O que conta para pagar: extras menos descontos. Cada mês fecha por si."""
        return self.extra_positivo + self.descontos

    def linhas(self) -> list[tuple[str, str]]:
        """Rótulo → valor, pela ordem do relatório."""
        return [
            ("Horas normais", formatar_total(self.normais)),
            ("Horas extra em dias úteis", formatar_total(self.extra_uteis)),
            ("Horas extra aos sábados", formatar_total(self.extra_sabados)),
            ("Horas extra aos domingos", formatar_total(self.extra_domingos)),
            ("Horas extra em feriados", formatar_total(self.extra_feriados)),
            ("Horas extra em férias", formatar_total(self.extra_ferias)),
            ("Descontos (dias com menos horas e folgas)", formatar_total(self.descontos)),
            ("Total de horas extra", formatar_total(self.total_extra)),
        ]

    def linha_subsidio(self) -> tuple[str, str]:
        """O subsídio vem à parte das horas: é dinheiro, não entra no total."""
        return (ROTULO_SUBSIDIO, formatar_euros(self.subsidio))

    def linhas_relatorio(self) -> list[tuple[str, str]]:
        """As horas e, no fim, o subsídio — para o email e a folha em PDF."""
        return [*self.linhas(), self.linha_subsidio()]


def resumir_mes(dias: Iterable[LinhaDia]) -> ResumoMes:
    resumo = ResumoMes()
    for dia in dias:
        resumo.dias_registados += 1
        resumo.normais += dia.normais
        resumo.subsidio += dia.subsidio
        # O teletrabalho pode ter extra e falta no mesmo dia: cada uma no seu sítio.
        resumo.descontos += dia.desconto
        feito = dia.extra_feito
        if dia.tipo in TIPOS_COM_HORARIO:
            resumo.extra_uteis += feito
        elif dia.tipo == TIPO_FIM_SEMANA:
            if dia.data.weekday() == 6:
                resumo.extra_domingos += feito
            else:
                resumo.extra_sabados += feito
        elif dia.tipo == TIPO_FERIADO:
            resumo.extra_feriados += feito
        elif dia.tipo == TIPO_FERIAS:
            resumo.extra_ferias += feito
        if dia.tipo in TIPOS_COM_HORARIO:
            resumo.dias_uteis += 1
            if dia.tipo == TIPO_TELETRABALHO:
                resumo.dias_teletrabalho += 1
        elif dia.tipo == TIPO_FERIAS:
            resumo.dias_ferias += 1
        elif dia.tipo == TIPO_FERIADO:
            resumo.dias_feriado += 1
        elif dia.tipo == TIPO_FOLGA:
            resumo.dias_folga += 1
    return resumo


def dias_do_mes(ano: int, mes: int) -> list[date]:
    return [date(ano, mes, d) for d in range(1, calendar.monthrange(ano, mes)[1] + 1)]


def mes_anterior(ano: int, mes: int) -> tuple[int, int]:
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def mes_seguinte(ano: int, mes: int) -> tuple[int, int]:
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def dias_em_falta(
    registados: Iterable[date], *, desde: date, ate: date
) -> list[date]:
    """Dias úteis entre ``desde`` (incl.) e ``ate`` (excl.) sem nada registado."""
    feitos = set(registados)
    dias: list[date] = []
    dia = desde
    while dia < ate:
        if e_dia_de_trabalho(dia) and dia not in feitos:
            dias.append(dia)
        dia += timedelta(days=1)
    return dias


def lista_de_dias(dias: list[date]) -> str:
    """«segunda 29/09, terça 30/09 e quarta 01/10»."""
    textos = [f"{SEMANA[d.weekday()].split('-')[0]} {d:%d/%m}" for d in dias]
    if len(textos) <= 1:
        return "".join(textos)
    return ", ".join(textos[:-1]) + " e " + textos[-1]


# ---------------------------------------------------------------------------
# Agenda: lembrete diário e envio do mês à contabilidade
# ---------------------------------------------------------------------------
def momento_envio(ano: int, mes: int) -> datetime:
    """Quando sai o mês ``ano/mes``: dia 2 do mês seguinte, às 9h20."""
    ano_seg, mes_seg = mes_seguinte(ano, mes)
    return datetime.combine(date(ano_seg, mes_seg, DIA_ENVIO), HORA_ENVIO)


def meses_por_enviar(
    agora: datetime,
    *,
    inicio_registo: date,
    enviados: Iterable[tuple[int, int]],
    com_registos: Iterable[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Meses do registo oficial que já deviam ter seguido e ainda não seguiram.

    Só conta meses com dias registados: um mês vazio (férias longas, conta
    nova) não tem nada para mandar à contabilidade. O mais antigo vem primeiro.
    """
    feitos = set(enviados)
    com_dados = set(com_registos)
    meses: list[tuple[int, int]] = []
    ano, mes = inicio_registo.year, inicio_registo.month
    while momento_envio(ano, mes) <= agora:
        if (ano, mes) in com_dados and (ano, mes) not in feitos:
            meses.append((ano, mes))
        ano, mes = mes_seguinte(ano, mes)
    return meses


def deve_lembrar_hoje(hoje: date, ultimo_lembrete: date | None) -> bool:
    """O lembrete dos dias por registar aparece uma vez por dia."""
    return ultimo_lembrete != hoje


# ---------------------------------------------------------------------------
# Email à contabilidade
# ---------------------------------------------------------------------------
def assunto_email(nome: str, ano: int, mes: int) -> str:
    return f"Registo de horas — {nome} — {nome_mes(ano, mes)}"


def corpo_email(nome: str, ano: int, mes: int, resumo: ResumoMes) -> str:
    """Texto simples, editável no diálogo antes de enviar."""
    linhas = "\n".join(
        f"• {rotulo}: {valor}" for rotulo, valor in resumo.linhas_relatorio()
    )
    return (
        "Bom dia,\n\n"
        f"Segue em anexo o registo de horas de {nome} referente a "
        f"{nome_mes(ano, mes)}.\n\n"
        f"{linhas}\n\n"
        "Cumprimentos,\n"
        f"{nome}"
    )


# ---------------------------------------------------------------------------
# Definições de cada pessoa
# ---------------------------------------------------------------------------
@dataclass
class ConfigHoras:
    """O horário e os avisos de uma pessoa (vai para as ``user_prefs``)."""

    #: Nome na folha e no email; vazio = o nome da conta.
    nome_folha: str = ""
    entrada_habitual: int = 8 * 60
    saida_habitual: int = 17 * 60
    horas_normais_dia: int = HORAS_NORMAIS_PADRAO
    pausa_almoco: int = PAUSA_PADRAO
    descontar_almoco: bool = True
    lembrete_diario: bool = True
    envio_mensal: bool = True
    inicio_registo: date = field(default=INICIO_REGISTO_PADRAO)
    #: Onde ficam as folhas em PDF; vazio = Documentos\Registo de Horas.
    pasta_pdf: str = ""
    #: Tipo com que abrem os dias novos de segunda a sexta (util | teletrabalho).
    tipo_habitual: str = TIPO_UTIL

    @property
    def horario(self) -> tuple[int, int]:
        """O horário habitual, que separa as horas normais das extra no teletrabalho."""
        return (self.entrada_habitual, self.saida_habitual)

    def para_json(self) -> str:
        dados = asdict(self)
        dados["inicio_registo"] = self.inicio_registo.isoformat()
        return json.dumps(dados, ensure_ascii=False)

    @classmethod
    def de_json(cls, texto: str | None) -> "ConfigHoras":
        """Lê o que estiver guardado; o que faltar ou vier estragado fica no padrão."""
        config = cls()
        try:
            dados = json.loads(texto) if texto else {}
        except (TypeError, ValueError):
            return config
        if not isinstance(dados, Mapping):
            return config
        for campo in fields(cls):
            if campo.name not in dados:
                continue
            valor = dados[campo.name]
            atual = getattr(config, campo.name)
            try:
                if isinstance(atual, bool):
                    valor = bool(valor)
                elif isinstance(atual, int):
                    valor = int(valor)
                elif isinstance(atual, date):
                    valor = date.fromisoformat(str(valor))
                else:
                    valor = str(valor or "")
            except (TypeError, ValueError):
                continue
            setattr(config, campo.name, valor)
        if config.tipo_habitual not in TIPOS_COM_HORARIO:
            config.tipo_habitual = TIPO_UTIL
        return config
