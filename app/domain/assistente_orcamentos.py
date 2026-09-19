"""Assistente dos Orçamentos: que orçamentos meus precisam de atenção hoje?

Regra pura (sem Qt nem base de dados). Todos os dias úteis, a partir das 8h30,
cada pessoa vê **os seus** orçamentos que ficaram parados:

* **Enviado** há mais de 30 dias sem nada de novo — o cliente ainda não deu
  resposta; o assistente oferece-se para preparar um email de seguimento;
* **Falta Orçamentar** há mais de 15 dias — ainda faz sentido orçamentar?

Decisões do Paulo (19-09-2026) que não se adivinham pelo código:

* manda a versão MAIS RECENTE de cada orçamento, e o dono é quem está no
  campo Utilizador dessa versão;
* se alguma versão do orçamento já está fechada (Adjudicado, Não Adjudicado,
  Cancelado, Sem Interesse, Concluído) o orçamento já teve resposta: não se
  lembra nada, mesmo que uma versão antiga tenha ficado em «Enviado»;
* o relógio do «Enviado» recomeça sempre que sai um email desse orçamento
  (o próprio email de seguimento conta);
* pouca informação de cada vez: o resumo do V2 mostrava tudo e deixou de ser
  lido. No máximo ``MAX_LINHAS`` por grupo.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Iterable

HORA_RESUMO = time(8, 30)
DIAS_SEM_RESPOSTA = 30
DIAS_FALTA_ORCAMENTAR = 15
DIAS_ADIAR = 7
MAX_LINHAS = 8

ESTADO_ENVIADO = "Enviado"
ESTADO_FALTA_ORCAMENTAR = "Falta Orçamentar"
#: Qualquer versão nestes estados quer dizer que o orçamento já teve resposta.
ESTADOS_FECHADOS = frozenset(
    {"Adjudicado", "Não Adjudicado", "Cancelado", "Sem Interesse", "Concluído"}
)

TIPO_SEM_RESPOSTA = "sem_resposta"
TIPO_FALTA_ORCAMENTAR = "falta_orcamentar"

APRESENTACAO = (
    "Sou o assistente dos Orçamentos. Todos os dias úteis, a partir das 8h30, "
    "mostro-lhe os seus orçamentos que ficaram parados: os enviados há mais de "
    f"{DIAS_SEM_RESPOSTA} dias sem resposta do cliente e os que estão em "
    f"«Falta Orçamentar» há mais de {DIAS_FALTA_ORCAMENTAR} dias. Não envio "
    "nem mudo nada sem a sua ordem."
)


@dataclass(frozen=True)
class VersaoOrcamento:
    orcamento_id: int
    versao_id: int
    numero_versao: int
    codigo: str
    estado: str
    dono_id: int | None
    cliente: str
    obra: str
    ref_cliente: str
    preco: Decimal | None
    criado_em: datetime
    #: Quando passou para o estado em que está (histórico); None = desde sempre.
    entrou_no_estado: datetime | None = None
    #: Último email registado no histórico desta versão.
    ultimo_email: datetime | None = None


@dataclass(frozen=True)
class Lembrete:
    tipo: str
    versao_id: int
    codigo: str
    cliente: str
    obra: str
    ref_cliente: str
    preco: Decimal | None
    desde: date
    dias: int
    #: Dia em que o orçamento passou a «Enviado» (para o email de seguimento).
    enviado_em: date | None = None


@dataclass(frozen=True)
class ResumoDiario:
    sem_resposta: tuple[Lembrete, ...] = ()
    falta_orcamentar: tuple[Lembrete, ...] = ()
    adiados: int = 0

    @property
    def vazio(self) -> bool:
        return not self.sem_resposta and not self.falta_orcamentar

    @property
    def total(self) -> int:
        return len(self.sem_resposta) + len(self.falta_orcamentar)


def deve_mostrar(agora: datetime, ultimo_resumo: date | None) -> bool:
    """Dia útil, já passou das 8h30 e ainda não se mostrou hoje."""
    if agora.weekday() > 4:
        return False
    if agora.time() < HORA_RESUMO:
        return False
    return ultimo_resumo != agora.date()


_ALVO_ESTADO = re.compile(r"(?:→|->)\s*(.+?)\s*(?:\(|$)")


def estado_alvo(descricao: str | None) -> str:
    """O estado de chegada de um evento «Estado: A → B (…)», ou ``""``."""
    encontrado = _ALVO_ESTADO.search(str(descricao or ""))
    return encontrado.group(1).strip() if encontrado else ""


def data_de_referencia(versao: VersaoOrcamento) -> datetime:
    """Desde quando conta o tempo parado desta versão."""
    referencia = versao.entrou_no_estado or versao.criado_em
    if versao.estado == ESTADO_ENVIADO and versao.ultimo_email is not None:
        referencia = max(referencia, versao.ultimo_email)
    return referencia


def levantar_lembretes(
    versoes: Iterable[VersaoOrcamento],
    *,
    dono_id: int,
    hoje: date,
    adiados: dict[int, date] | None = None,
) -> ResumoDiario:
    """Os orçamentos do ``dono_id`` que merecem um lembrete hoje."""
    adiados = adiados or {}
    por_orcamento: dict[int, list[VersaoOrcamento]] = {}
    for versao in versoes:
        por_orcamento.setdefault(versao.orcamento_id, []).append(versao)

    sem_resposta: list[Lembrete] = []
    falta: list[Lembrete] = []
    quantos_adiados = 0
    for grupo in por_orcamento.values():
        if any(versao.estado in ESTADOS_FECHADOS for versao in grupo):
            continue
        atual = max(grupo, key=lambda versao: (versao.numero_versao, versao.versao_id))
        if atual.dono_id != dono_id:
            continue
        if atual.estado == ESTADO_ENVIADO:
            limite, tipo, destino = DIAS_SEM_RESPOSTA, TIPO_SEM_RESPOSTA, sem_resposta
        elif atual.estado == ESTADO_FALTA_ORCAMENTAR:
            limite, tipo, destino = DIAS_FALTA_ORCAMENTAR, TIPO_FALTA_ORCAMENTAR, falta
        else:
            continue
        desde = data_de_referencia(atual).date()
        dias = (hoje - desde).days
        if dias < limite:
            continue
        adiado_ate = adiados.get(atual.versao_id)
        if adiado_ate is not None and hoje < adiado_ate:
            quantos_adiados += 1
            continue
        destino.append(
            Lembrete(
                tipo,
                atual.versao_id,
                atual.codigo,
                atual.cliente,
                atual.obra,
                atual.ref_cliente,
                atual.preco,
                desde,
                dias,
                (atual.entrou_no_estado or atual.criado_em).date()
                if tipo == TIPO_SEM_RESPOSTA
                else None,
            )
        )

    def ordenar(lista: list[Lembrete]) -> tuple[Lembrete, ...]:
        return tuple(sorted(lista, key=lambda item: (-item.dias, item.codigo)))

    return ResumoDiario(ordenar(sem_resposta), ordenar(falta), quantos_adiados)


# ---- «Lembrar daqui a 7 dias» (guardado nas preferências do utilizador) ----

def ler_adiados(texto: str | None) -> dict[int, date]:
    try:
        dados = json.loads(texto or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(dados, dict):
        return {}
    adiados: dict[int, date] = {}
    for chave, valor in dados.items():
        try:
            adiados[int(chave)] = date.fromisoformat(str(valor))
        except (TypeError, ValueError):
            continue
    return adiados


def adiar(adiados: dict[int, date], versao_id: int, hoje: date) -> dict[int, date]:
    """Junta o adiamento e deita fora os que já passaram."""
    novos = {chave: ate for chave, ate in adiados.items() if ate > hoje}
    novos[int(versao_id)] = hoje + timedelta(days=DIAS_ADIAR)
    return novos


def escrever_adiados(adiados: dict[int, date]) -> str:
    return json.dumps(
        {str(chave): ate.isoformat() for chave, ate in sorted(adiados.items())}
    )


# ---- Email de seguimento ---------------------------------------------------

def _saudacao(hora: int) -> str:
    if 6 <= hora < 13:
        return "Bom dia"
    if 13 <= hora < 20:
        return "Boa tarde"
    return "Boa noite"


def assunto_email_seguimento(num_orcamento: str, versao: str, obra: str) -> str:
    return f"Orçamento {num_orcamento}_{versao} - {obra}".strip(" -")


def corpo_email_seguimento(
    *,
    cliente: str,
    num_orcamento: str,
    versao: str,
    obra: str = "",
    ref_cliente: str = "",
    enviado_em: date,
    momento: datetime | None = None,
) -> str:
    """Email curto a perguntar se o cliente já analisou o orçamento."""
    agora = momento or datetime.now()
    obra_ref = " | ".join(
        parte
        for parte in (
            f"Obra: {html.escape(obra)}" if obra else "",
            f"Ref.: {html.escape(ref_cliente)}" if ref_cliente else "",
        )
        if parte
    )
    obra_ref_html = (
        f"<p style='margin:0 0 12px;'><b>{obra_ref}</b></p>" if obra_ref else ""
    )
    return (
        "<div style='font-family: Arial, sans-serif; color:#333;'>"
        f"<p style='margin:0 0 12px;'>{_saudacao(agora.hour)},</p>"
        f"<p style='margin:0 0 12px;'>Exmo(a). Sr(a). <b>{html.escape(cliente)}</b>,</p>"
        "<p style='margin:0 0 12px;'>No dia "
        f"{enviado_em.strftime('%d-%m-%Y')} enviámos o orçamento "
        f"<b>{html.escape(num_orcamento)}_{html.escape(versao)}</b>.</p>"
        f"{obra_ref_html}"
        "<p style='margin:0 0 12px;'>Gostaríamos de saber se já teve oportunidade "
        "de o analisar e se há alguma dúvida ou alteração que queira ver "
        "refletida.</p>"
        "<p style='margin:0 0 16px;'>Ficamos a aguardar o seu contacto.</p>"
        "<p style='margin:0 0 4px;'>Com os melhores cumprimentos,</p>"
        "<p style='margin:0;'>{{assinatura}}</p>"
        "</div>"
    )


def texto_dias(dias: int) -> str:
    return "1 dia" if dias == 1 else f"{dias} dias"
