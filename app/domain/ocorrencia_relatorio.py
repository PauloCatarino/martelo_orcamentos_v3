"""O que entra num relatório de ocorrências, já em forma de texto.

Módulo puro: recebe tickets, devolve linhas prontas a imprimir. Existe para o
gerador de PDF não precisar de saber nada de base de dados nem de Qt, e para os
títulos e o resumo do ano poderem ser testados sem abrir um PDF.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain import ocorrencia_tipos as tipos


@dataclass(frozen=True)
class TicketRelatorio:
    """One ticket as it goes on paper."""

    numero: int | None = None
    data: str = ""
    tipo: str = tipos.TIPO_PADRAO
    gravidade: str = tipos.GRAVIDADE_PADRAO
    origem: str = tipos.ORIGEM_PADRAO
    estado: str = tipos.ESTADO_PADRAO
    assunto: str = ""
    texto: str = ""
    responsavel: str = ""
    autor: str = ""
    #: "Enviado a X no Teams — 27-07-2026 12:26", já composto por quem monta.
    envio: str = ""
    resolucao: str = ""
    custo: str = ""
    fotos: tuple[str, ...] = ()

    @property
    def referencia(self) -> str:
        """Short ticket name: 'T3'."""
        return tipos.rotulo_ticket(self.numero)

    @property
    def e_erro_nosso(self) -> bool:
        """True when this ticket counts as our own mistake."""
        return tipos.e_erro_nosso(self.tipo)


@dataclass(frozen=True)
class ObraRelatorio:
    """One obra and its tickets."""

    codigo: str = ""
    cliente: str = ""
    ref_cliente: str = ""
    tickets: tuple[TicketRelatorio, ...] = field(default_factory=tuple)

    @property
    def identificacao(self) -> str:
        """Obra line for the report heading."""
        partes = [self.codigo or "Obra"]
        if self.cliente:
            partes.append(self.cliente)
        if self.ref_cliente:
            partes.append(f"Ref. {self.ref_cliente}")
        return "  ·  ".join(partes)


def contar_tickets(obras) -> int:
    """How many tickets there are in the whole report."""
    return sum(len(obra.tickets) for obra in obras or ())


def contar_fotos(obras) -> int:
    """How many photos there are in the whole report."""
    return sum(
        len(ticket.fotos) for obra in obras or () for ticket in obra.tickets
    )


def resumo_por_tipo(obras) -> dict[str, int]:
    """Ticket count by tipo, biggest first — é o quadro do fim do relatório."""
    contagem: dict[str, int] = {}
    for obra in obras or ():
        for ticket in obra.tickets:
            chave = tipos.normalizar_tipo(ticket.tipo)
            contagem[chave] = contagem.get(chave, 0) + 1
    return dict(
        sorted(contagem.items(), key=lambda par: (-par[1], par[0]))
    )


def contar_erros_nossos(obras) -> int:
    """Tickets that count as our own mistake (year-end analysis)."""
    return sum(
        1
        for obra in obras or ()
        for ticket in obra.tickets
        if ticket.e_erro_nosso
    )


def contar_por_resolver(obras) -> int:
    """Tickets still waiting for someone."""
    return sum(
        1
        for obra in obras or ()
        for ticket in obra.tickets
        if tipos.esta_aberto(ticket.estado)
    )


def titulo_relatorio(obras, *, uma_obra: bool) -> str:
    """Report title: one obra names it, many obras say how many."""
    lista = list(obras or ())
    if uma_obra and lista:
        return f"Ocorrências — {lista[0].codigo or 'obra'}"
    return "Ocorrências"


def subtitulo_relatorio(obras, *, ano=None, gerado_em: str = "") -> str:
    """One line saying what is in the report and how it was filtered."""
    lista = list(obras or ())
    total = contar_tickets(lista)
    partes = [f"{total} ticket(s)"]

    if len(lista) > 1:
        partes.append(f"{len(lista)} obra(s)")
    por_resolver = contar_por_resolver(lista)
    partes.append(f"{por_resolver} por resolver")
    erros = contar_erros_nossos(lista)
    partes.append(f"{erros} classificados como erro nosso")
    if ano:
        partes.append(f"ano {ano}")
    if gerado_em:
        partes.append(f"gerado em {gerado_em}")

    return "  ·  ".join(partes)


def linhas_resumo(obras) -> list[tuple[str, str, str]]:
    """Rows of the summary table: (tipo, quantos, é erro nosso?)."""
    return [
        (
            tipos.rotulo_tipo(chave),
            str(total),
            "Sim" if tipos.e_erro_nosso(chave) else "—",
        )
        for chave, total in resumo_por_tipo(obras).items()
    ]
