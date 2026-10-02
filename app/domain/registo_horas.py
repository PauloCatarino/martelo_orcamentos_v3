"""Regras do registo de horas (folha de horas): cálculo, feriados e resumos.

Vêm da app isolada «Registo de Horas · Lança Encanto» (PHP, out-2026), que
por sua vez copiava as folhas em papel — e o Paulo confirmou-as uma a uma:

* **dia útil**: saída − entrada − pausas (+ 2.º período) + acerto; até às
  horas normais do dia (8h) são normais e o resto é extra, escrito «8 + 3».
  Com menos de 8h a diferença desconta ao mês: «5 − 3»;
* **fim de semana, feriado e férias**: tudo o que se trabalhou é extra;
* **folga**: folga paga com horas extra — desconta as horas indicadas, «−8»;
* **cada mês fecha por si**: o saldo não passa para o mês seguinte.

O 2.º período é novo no Martelo: quem sai da empresa às 17h e trabalha mais
umas horas em casa à noite regista as duas partes, como nas duas colunas
Entrada/Saída da folha em papel. O «acerto» continua a existir para as pausas
a mais e para o histórico que veio da app antiga.

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
TIPO_FIM_SEMANA = "fim_semana"
TIPO_FERIADO = "feriado"
TIPO_FERIAS = "ferias"
TIPO_FOLGA = "folga"
TIPOS = (TIPO_UTIL, TIPO_FIM_SEMANA, TIPO_FERIADO, TIPO_FERIAS, TIPO_FOLGA)

NOMES_TIPOS = {
    TIPO_UTIL: "Dia útil",
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
    TIPO_FIM_SEMANA: "Todas as horas trabalhadas contam como extra.",
    TIPO_FERIADO: (
        "Todas as horas trabalhadas contam como extra. Deixe 0 se não trabalhou."
    ),
    TIPO_FERIAS: "Não conta horas. Se trabalhou, indique as horas: contam como extra.",
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


def tipo_por_defeito(dia: date) -> str:
    if feriado(dia):
        return TIPO_FERIADO
    return TIPO_FIM_SEMANA if e_fim_de_semana(dia) else TIPO_UTIL


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
    entrada: int | None = None
    saida: int | None = None
    entrada2: int | None = None
    saida2: int | None = None
    almoco: bool = True
    jantar: bool = False
    acerto: int = 0
    #: Fora dos dias úteis: horas trabalhadas (ou, na folga, horas a descontar).
    horas: int = 0


@dataclass(frozen=True)
class CalculoDia:
    trabalhado: int
    normais: int
    extra: int
    #: Saídas já com o dia seguinte somado (ex.: 1h30 → 25h30 = 1530).
    saida: int | None = None
    entrada2: int | None = None
    saida2: int | None = None


def _depois_de(hora: int, referencia: int) -> int:
    """A mesma hora do relógio, puxada para depois da referência."""
    while hora <= referencia:
        hora += MINUTOS_DIA
    return hora


def calcular_dia(
    dados: DadosDia,
    *,
    horas_normais: int = HORAS_NORMAIS_PADRAO,
    pausa: int = PAUSA_PADRAO,
) -> CalculoDia:
    """As contas da folha para um dia; ``ErroRegistoHoras`` se não fizer sentido."""
    if dados.tipo not in TIPOS:
        raise ErroRegistoHoras("Tipo de dia inválido.")

    if dados.tipo == TIPO_UTIL:
        if dados.entrada is None:
            raise ErroRegistoHoras("Indique a hora de entrada.")
        if dados.saida is None:
            raise ErroRegistoHoras("Indique a hora de saída.")
        if abs(dados.acerto) > MAX_ACERTO:
            raise ErroRegistoHoras("O acerto tem de estar entre −12 e 12 horas.")
        entrada = dados.entrada % MINUTOS_DIA
        saida = _depois_de(dados.saida % MINUTOS_DIA, entrada)
        trabalhado = saida - entrada
        entrada2 = saida2 = None
        if (dados.entrada2 is None) != (dados.saida2 is None):
            raise ErroRegistoHoras(
                "No 2.º período indique a entrada e a saída (ou deixe os dois vazios)."
            )
        if dados.entrada2 is not None and dados.saida2 is not None:
            entrada2 = _depois_de(dados.entrada2 % MINUTOS_DIA, saida - 1)
            saida2 = _depois_de(dados.saida2 % MINUTOS_DIA, entrada2)
            if saida2 - entrada > MINUTOS_DIA:
                raise ErroRegistoHoras(
                    "O 2.º período tem de começar depois da saída do 1.º "
                    "(e o dia não pode passar de 24 horas)."
                )
            trabalhado += saida2 - entrada2
        trabalhado += dados.acerto
        trabalhado -= pausa if dados.almoco else 0
        trabalhado -= pausa if dados.jantar else 0
        if trabalhado < 0:
            raise ErroRegistoHoras("Os descontos excedem as horas trabalhadas.")
        return CalculoDia(
            trabalhado=trabalhado,
            normais=min(trabalhado, horas_normais),
            extra=trabalhado - horas_normais,
            saida=saida,
            entrada2=entrada2,
            saida2=saida2,
        )

    if not 0 <= dados.horas <= MAX_HORAS_DIA:
        raise ErroRegistoHoras("Indique um número de horas entre 0 e 24.")
    if dados.horas == 0 and dados.tipo in (TIPO_FIM_SEMANA, TIPO_FOLGA):
        raise ErroRegistoHoras(
            "Indique as horas a descontar."
            if dados.tipo == TIPO_FOLGA
            else "Indique as horas trabalhadas."
        )
    if dados.tipo == TIPO_FOLGA:
        return CalculoDia(trabalhado=0, normais=0, extra=-dados.horas)
    return CalculoDia(trabalhado=dados.horas, normais=0, extra=dados.horas)


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


def horas_como_na_folha(tipo: str, normais: int, extra: int, trabalhado: int) -> str:
    """«8 + 3», «5 − 3», «8», «6», «−8»."""
    if tipo == TIPO_UTIL:
        if extra > 0:
            return f"{formatar_horas(normais)} + {formatar_horas(extra)}"
        if extra < 0:
            return f"{formatar_horas(normais)} {MENOS} {formatar_horas(-extra)}"
        return formatar_horas(normais)
    if tipo == TIPO_FOLGA:
        return f"{MENOS}{formatar_horas(-extra)}"
    return formatar_horas(trabalhado) if trabalhado > 0 else ""


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

    @property
    def horas_folha(self) -> str:
        return horas_como_na_folha(self.tipo, self.normais, self.extra, self.trabalhado)

    @property
    def horario(self) -> str:
        """«8h – 17h · 20h – 23h» nos dias úteis."""
        if self.tipo != TIPO_UTIL:
            return ""
        partes = [f"{formatar_hora(self.entrada)} – {formatar_hora(self.saida)}"]
        if self.entrada2 is not None and self.saida2 is not None:
            partes.append(f"{formatar_hora(self.entrada2)} – {formatar_hora(self.saida2)}")
        return " · ".join(partes)

    def observacoes_folha(self) -> str:
        partes = [etiqueta_do_dia(self.tipo, self.data)]
        if self.tipo == TIPO_UTIL:
            if self.acerto:
                partes.append(f"Acerto {formatar_total(self.acerto, com_mais=True)}")
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


def resumir_mes(dias: Iterable[LinhaDia]) -> ResumoMes:
    resumo = ResumoMes()
    for dia in dias:
        resumo.dias_registados += 1
        resumo.normais += dia.normais
        if dia.extra < 0:
            resumo.descontos += dia.extra
        elif dia.tipo == TIPO_UTIL:
            resumo.extra_uteis += dia.extra
        elif dia.tipo == TIPO_FIM_SEMANA:
            if dia.data.weekday() == 6:
                resumo.extra_domingos += dia.extra
            else:
                resumo.extra_sabados += dia.extra
        elif dia.tipo == TIPO_FERIADO:
            resumo.extra_feriados += dia.extra
        elif dia.tipo == TIPO_FERIAS:
            resumo.extra_ferias += dia.extra
        if dia.tipo == TIPO_UTIL:
            resumo.dias_uteis += 1
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
    linhas = "\n".join(f"• {rotulo}: {valor}" for rotulo, valor in resumo.linhas())
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
        return config
