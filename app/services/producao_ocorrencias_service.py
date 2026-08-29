"""Tickets da obra: registar, classificar, encaminhar e fechar.

Cada linha é um ticket — o que o cliente reportou, o que faltou, o que correu
mal — com tipo, responsável e estado, para nada se perder e para no fim do ano
se poder ver onde é que os erros aconteceram.

O texto e as fotos são acrescentados, não reescritos: o histórico é o que dá
valor ao registo quando é preciso discutir com um cliente.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import ocorrencia_tipos as tipos
from app.domain.ocorrencia_anexos import existe as anexo_existe
from app.domain.ocorrencia_relatorio import ObraRelatorio, TicketRelatorio
from app.models.producao import Producao
from app.models.producao_ocorrencia import ProducaoOcorrencia
from app.models.producao_ocorrencia_anexo import ProducaoOcorrenciaAnexo


#: Limite defensivo: um registo é uma nota, não um relatório.
MAX_TEXTO = 4000
MAX_ASSUNTO = 200


def listar_ocorrencias(
    session: Session,
    producao_id: int,
    *,
    tipo: str | None = None,
    estado: str | None = None,
    responsavel: str | None = None,
    texto: str | None = None,
    apenas_abertos: bool = False,
) -> list[ProducaoOcorrencia]:
    """List one obra's tickets, most recent first."""
    statement = (
        select(ProducaoOcorrencia)
        .where(ProducaoOcorrencia.producao_id == producao_id)
        .order_by(ProducaoOcorrencia.created_at.desc(), ProducaoOcorrencia.id.desc())
    )
    statement = _aplicar_filtros(
        statement,
        tipo=tipo,
        estado=estado,
        responsavel=responsavel,
        texto=texto,
        apenas_abertos=apenas_abertos,
    )
    return list(session.scalars(statement).all())


def listar_todas(
    session: Session,
    *,
    ano: int | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    responsavel: str | None = None,
    cliente: str | None = None,
    texto: str | None = None,
    apenas_abertos: bool = False,
) -> list[tuple[Producao, ProducaoOcorrencia]]:
    """All tickets across obras, newest first — para a lista global e o PDF."""
    statement = (
        select(Producao, ProducaoOcorrencia)
        .join(ProducaoOcorrencia, ProducaoOcorrencia.producao_id == Producao.id)
        .order_by(ProducaoOcorrencia.created_at.desc(), ProducaoOcorrencia.id.desc())
    )
    if ano is not None:
        # ``producao.ano`` é texto de 4 caracteres, não número.
        statement = statement.where(Producao.ano == str(ano))
    if cliente:
        statement = statement.where(Producao.nome_cliente.ilike(f"%{cliente.strip()}%"))
    statement = _aplicar_filtros(
        statement,
        tipo=tipo,
        estado=estado,
        responsavel=responsavel,
        texto=texto,
        apenas_abertos=apenas_abertos,
    )
    return [(obra, ticket) for obra, ticket in session.execute(statement).all()]


def _aplicar_filtros(
    statement,
    *,
    tipo: str | None,
    estado: str | None,
    responsavel: str | None,
    texto: str | None,
    apenas_abertos: bool,
):
    """Add the shared ticket filters to a select statement."""
    if tipo:
        statement = statement.where(ProducaoOcorrencia.tipo == tipo)
    if estado:
        statement = statement.where(ProducaoOcorrencia.estado == estado)
    elif apenas_abertos:
        statement = statement.where(
            ProducaoOcorrencia.estado.in_(tipos.ESTADOS_ABERTOS)
        )
    if responsavel:
        statement = statement.where(
            ProducaoOcorrencia.responsavel.ilike(f"%{responsavel.strip()}%")
        )
    if texto and texto.strip():
        procura = f"%{texto.strip()}%"
        statement = statement.where(
            ProducaoOcorrencia.texto.ilike(procura)
            | ProducaoOcorrencia.assunto.ilike(procura)
        )
    return statement


def contar_ocorrencias(session: Session, producao_id: int) -> int:
    """How many tickets this obra has."""
    return int(
        session.scalar(
            select(func.count())
            .select_from(ProducaoOcorrencia)
            .where(ProducaoOcorrencia.producao_id == producao_id)
        )
        or 0
    )


def contar_abertas(session: Session, producao_id: int) -> int:
    """How many tickets of this obra still need work."""
    return int(
        session.scalar(
            select(func.count())
            .select_from(ProducaoOcorrencia)
            .where(ProducaoOcorrencia.producao_id == producao_id)
            .where(ProducaoOcorrencia.estado.in_(tipos.ESTADOS_ABERTOS))
        )
        or 0
    )


def contagem_por_obra(session: Session, producao_ids=None) -> dict[int, int]:
    """Ticket count for many obras at once (one query)."""
    statement = select(
        ProducaoOcorrencia.producao_id, func.count()
    ).group_by(ProducaoOcorrencia.producao_id)
    if producao_ids is not None:
        ids = list(producao_ids)
        if not ids:
            return {}
        statement = statement.where(ProducaoOcorrencia.producao_id.in_(ids))
    return {int(pid): int(total) for pid, total in session.execute(statement).all()}


def proximo_numero(session: Session, producao_id: int) -> int:
    """Next ticket number inside this obra (T1, T2, …)."""
    maximo = session.scalar(
        select(func.max(ProducaoOcorrencia.numero)).where(
            ProducaoOcorrencia.producao_id == producao_id
        )
    )
    return int(maximo or 0) + 1


def assunto_sugerido(texto: str | None) -> str:
    """First line of the text, trimmed — serve de assunto quando não há um."""
    primeira = (texto or "").strip().splitlines()[0] if (texto or "").strip() else ""
    primeira = primeira.strip()
    if len(primeira) <= MAX_ASSUNTO:
        return primeira
    return primeira[: MAX_ASSUNTO - 1].rstrip() + "…"


def registar_ocorrencia(
    session: Session,
    *,
    producao_id: int,
    texto: str,
    assunto: str | None = None,
    tipo: str | None = None,
    gravidade: str | None = None,
    origem: str | None = None,
    estado: str | None = None,
    responsavel: str | None = None,
    responsavel_membro_id: int | None = None,
    custo_estimado=None,
    user_id: int | None = None,
    autor: str | None = None,
) -> ProducaoOcorrencia:
    """Open one ticket on this obra."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Escreva o que aconteceu antes de registar.")
    if len(texto) > MAX_TEXTO:
        raise ValueError(
            f"O registo é demasiado longo ({len(texto)} caracteres, "
            f"máximo {MAX_TEXTO})."
        )

    ocorrencia = ProducaoOcorrencia(
        producao_id=producao_id,
        user_id=user_id,
        autor=(autor or "").strip() or None,
        texto=texto,
        numero=proximo_numero(session, producao_id),
        assunto=(assunto or "").strip()[:MAX_ASSUNTO] or assunto_sugerido(texto),
        tipo=tipos.normalizar_tipo(tipo),
        gravidade=tipos.normalizar_gravidade(gravidade),
        origem=tipos.normalizar_origem(origem),
        estado=tipos.normalizar_estado(estado),
        responsavel=(responsavel or "").strip() or None,
        responsavel_membro_id=responsavel_membro_id,
        custo_estimado=_para_decimal(custo_estimado),
    )
    session.add(ocorrencia)
    session.flush()
    return ocorrencia


def atualizar_ocorrencia(
    session: Session,
    ocorrencia_id: int,
    *,
    user_id: int | None,
    is_admin: bool = False,
    **campos,
) -> ProducaoOcorrencia:
    """Edit a ticket — só o próprio autor ou um administrador.

    O ``estado`` fica de fora desta regra (ver :func:`mudar_estado`): quem
    resolve o problema raramente é quem o escreveu.
    """
    ocorrencia = _obter(session, ocorrencia_id)
    _exigir_autor(ocorrencia, user_id=user_id, is_admin=is_admin)

    if "texto" in campos:
        texto = (campos.pop("texto") or "").strip()
        if not texto:
            raise ValueError("Escreva o que aconteceu antes de gravar.")
        if len(texto) > MAX_TEXTO:
            raise ValueError(
                f"O registo é demasiado longo ({len(texto)} caracteres, "
                f"máximo {MAX_TEXTO})."
            )
        ocorrencia.texto = texto

    if "assunto" in campos:
        assunto = (campos.pop("assunto") or "").strip()[:MAX_ASSUNTO]
        ocorrencia.assunto = assunto or assunto_sugerido(ocorrencia.texto)

    normalizadores = {
        "tipo": tipos.normalizar_tipo,
        "gravidade": tipos.normalizar_gravidade,
        "origem": tipos.normalizar_origem,
    }
    for nome, normalizar in normalizadores.items():
        if nome in campos:
            setattr(ocorrencia, nome, normalizar(campos.pop(nome)))

    if "responsavel" in campos:
        ocorrencia.responsavel = (campos.pop("responsavel") or "").strip() or None
    if "responsavel_membro_id" in campos:
        ocorrencia.responsavel_membro_id = campos.pop("responsavel_membro_id")
    if "custo_estimado" in campos:
        ocorrencia.custo_estimado = _para_decimal(campos.pop("custo_estimado"))

    if campos:
        raise ValueError(f"Campos desconhecidos: {', '.join(sorted(campos))}.")

    session.flush()
    return ocorrencia


def mudar_estado(
    session: Session,
    ocorrencia_id: int,
    *,
    estado: str,
    autor: str | None = None,
    quando: datetime | None = None,
) -> ProducaoOcorrencia:
    """Move a ticket to another state; fechar guarda quem fechou e quando."""
    ocorrencia = _obter(session, ocorrencia_id)
    novo = tipos.normalizar_estado(estado)
    ocorrencia.estado = novo

    if novo == "resolvido":
        ocorrencia.resolvido_em = quando or datetime.now()
        ocorrencia.resolvido_por = (autor or "").strip() or None
    else:
        ocorrencia.resolvido_em = None
        ocorrencia.resolvido_por = None

    session.flush()
    return ocorrencia


def registar_envio(
    session: Session,
    ocorrencia_id: int,
    *,
    para: str,
    via: str = "teams",
    quando: datetime | None = None,
) -> ProducaoOcorrencia:
    """Record that the ticket was handed to someone — a prova de que foi avisado."""
    ocorrencia = _obter(session, ocorrencia_id)
    ocorrencia.enviado_em = quando or datetime.now()
    ocorrencia.enviado_para = (para or "").strip()[:255] or None
    ocorrencia.enviado_via = (via or "").strip()[:20] or None
    session.flush()
    return ocorrencia


def eliminar_ocorrencia(
    session: Session,
    ocorrencia_id: int,
    *,
    user_id: int | None,
    is_admin: bool = False,
) -> None:
    """Delete one ticket — só o próprio autor ou um administrador.

    Um diário onde qualquer pessoa apaga o que outra escreveu não serve para
    resolver discussões com clientes.
    """
    ocorrencia = _obter(session, ocorrencia_id)
    _exigir_autor(ocorrencia, user_id=user_id, is_admin=is_admin)
    session.delete(ocorrencia)
    session.flush()


# ---- anexos --------------------------------------------------------------
def listar_anexos(
    session: Session, ocorrencia_id: int
) -> list[ProducaoOcorrenciaAnexo]:
    """Files attached to one ticket, in the order they were added."""
    statement = (
        select(ProducaoOcorrenciaAnexo)
        .where(ProducaoOcorrenciaAnexo.ocorrencia_id == ocorrencia_id)
        .order_by(ProducaoOcorrenciaAnexo.ordem, ProducaoOcorrenciaAnexo.id)
    )
    return list(session.scalars(statement).all())


def registar_anexo(
    session: Session,
    *,
    ocorrencia_id: int,
    caminho: str,
    nome_original: str | None = None,
    legenda: str | None = None,
    user_id: int | None = None,
) -> ProducaoOcorrenciaAnexo:
    """Attach one already-copied file to a ticket."""
    caminho = (caminho or "").strip()
    if not caminho:
        raise ValueError("Caminho do anexo em falta.")

    proxima_ordem = int(
        session.scalar(
            select(func.max(ProducaoOcorrenciaAnexo.ordem)).where(
                ProducaoOcorrenciaAnexo.ocorrencia_id == ocorrencia_id
            )
        )
        or 0
    ) + 1

    anexo = ProducaoOcorrenciaAnexo(
        ocorrencia_id=ocorrencia_id,
        caminho=caminho[:1024],
        nome_original=(nome_original or "").strip()[:255] or None,
        legenda=(legenda or "").strip()[:255] or None,
        ordem=proxima_ordem,
        user_id=user_id,
    )
    session.add(anexo)
    session.flush()
    return anexo


def eliminar_anexo(session: Session, anexo_id: int) -> None:
    """Forget an attachment (o ficheiro fica na pasta da obra)."""
    anexo = session.get(ProducaoOcorrenciaAnexo, anexo_id)
    if anexo is None:
        raise ValueError("Anexo não encontrado.")
    session.delete(anexo)
    session.flush()


def contagem_anexos(session: Session, ocorrencia_ids) -> dict[int, int]:
    """How many files each ticket has (one query, for the list column)."""
    ids = list(ocorrencia_ids or [])
    if not ids:
        return {}
    statement = (
        select(ProducaoOcorrenciaAnexo.ocorrencia_id, func.count())
        .where(ProducaoOcorrenciaAnexo.ocorrencia_id.in_(ids))
        .group_by(ProducaoOcorrenciaAnexo.ocorrencia_id)
    )
    return {int(oid): int(total) for oid, total in session.execute(statement).all()}


# ---- análise -------------------------------------------------------------
def resumo_por_tipo(session: Session, *, ano: int | None = None) -> dict[str, int]:
    """Tickets by tipo — a base da avaliação de erros do fim do ano."""
    return _resumo(session, ProducaoOcorrencia.tipo, ano=ano)


def resumo_por_responsavel(
    session: Session, *, ano: int | None = None
) -> dict[str, int]:
    """Tickets by responsável."""
    return _resumo(session, ProducaoOcorrencia.responsavel, ano=ano)


def resumo_por_estado(session: Session, *, ano: int | None = None) -> dict[str, int]:
    """Tickets by estado."""
    return _resumo(session, ProducaoOcorrencia.estado, ano=ano)


def _resumo(session: Session, coluna, *, ano: int | None) -> dict[str, int]:
    statement = select(coluna, func.count()).group_by(coluna)
    if ano is not None:
        statement = statement.join(
            Producao, ProducaoOcorrencia.producao_id == Producao.id
        ).where(Producao.ano == str(ano))
    return {
        (chave or "—"): int(total)
        for chave, total in session.execute(statement).all()
    }


# ---- relatório -----------------------------------------------------------
def dados_para_relatorio(
    session: Session,
    *,
    producao_id: int | None = None,
    ano: int | str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    responsavel: str | None = None,
    apenas_abertos: bool = False,
    incluir_fotos: bool = True,
) -> list[ObraRelatorio]:
    """Build the report rows: one entry per obra, tickets inside, oldest first.

    Aqui a ordem inverte-se face à tabela do ecrã: num relatório lê-se a
    história da obra do princípio para o fim, e não do fim para o princípio.
    """
    if producao_id is not None:
        obra = session.get(Producao, producao_id)
        if obra is None:
            return []
        pares = [
            (obra, ticket)
            for ticket in listar_ocorrencias(
                session,
                producao_id,
                tipo=tipo,
                estado=estado,
                responsavel=responsavel,
                apenas_abertos=apenas_abertos,
            )
        ]
    else:
        pares = listar_todas(
            session,
            ano=ano,
            tipo=tipo,
            estado=estado,
            responsavel=responsavel,
            apenas_abertos=apenas_abertos,
        )

    agrupado: dict[int, list] = {}
    obras: dict[int, Producao] = {}
    for obra, ticket in pares:
        obras.setdefault(int(obra.id), obra)
        agrupado.setdefault(int(obra.id), []).append(ticket)

    relatorio: list[ObraRelatorio] = []
    for obra_id, tickets in agrupado.items():
        obra = obras[obra_id]
        tickets.sort(key=lambda t: (t.numero or 0, t.id))
        relatorio.append(
            ObraRelatorio(
                codigo=str(obra.codigo_processo or ""),
                cliente=str(obra.nome_cliente or ""),
                ref_cliente=str(obra.ref_cliente or ""),
                tickets=tuple(
                    _ticket_para_relatorio(ticket, incluir_fotos=incluir_fotos)
                    for ticket in tickets
                ),
            )
        )

    relatorio.sort(key=lambda obra: obra.codigo)
    return relatorio


def _ticket_para_relatorio(ticket, *, incluir_fotos: bool) -> TicketRelatorio:
    """Turn one ticket into the plain text the report needs."""
    envio = ""
    if ticket.enviado_em:
        # "aberto" e nao "enviado": o Martelo escreve o ticket na conversa,
        # mas quem carrega em Enter e' a pessoa (ver o dialogo das ocorrencias).
        via = (ticket.enviado_via or "chat").capitalize()
        envio = (
            f"{via} aberto para {ticket.enviado_para or '—'} em "
            f"{formatar_data(ticket.enviado_em)}"
        )

    resolucao = ""
    if ticket.resolvido_em:
        resolucao = (
            f"resolvido por {ticket.resolvido_por or '—'} em "
            f"{formatar_data(ticket.resolvido_em)}"
        )

    fotos: tuple[str, ...] = ()
    if incluir_fotos:
        fotos = tuple(
            str(anexo.caminho)
            for anexo in (ticket.anexos or [])
            if anexo.caminho and anexo_existe(anexo.caminho)
        )

    return TicketRelatorio(
        numero=ticket.numero,
        data=formatar_data(ticket.created_at),
        tipo=tipos.normalizar_tipo(ticket.tipo),
        gravidade=tipos.normalizar_gravidade(ticket.gravidade),
        origem=tipos.normalizar_origem(ticket.origem),
        estado=tipos.normalizar_estado(ticket.estado),
        assunto=str(ticket.assunto or ""),
        texto=str(ticket.texto or ""),
        responsavel=str(ticket.responsavel or ""),
        autor=str(ticket.autor or ""),
        envio=envio,
        resolucao=resolucao,
        custo=(
            f"{ticket.custo_estimado:.2f} €"
            if ticket.custo_estimado is not None
            else ""
        ),
        fotos=fotos,
    )


# ---- apoio ---------------------------------------------------------------
def _obter(session: Session, ocorrencia_id: int) -> ProducaoOcorrencia:
    ocorrencia = session.get(ProducaoOcorrencia, ocorrencia_id)
    if ocorrencia is None:
        raise ValueError("Registo não encontrado.")
    return ocorrencia


def _exigir_autor(
    ocorrencia: ProducaoOcorrencia, *, user_id: int | None, is_admin: bool
) -> None:
    if not is_admin and (user_id is None or ocorrencia.user_id != user_id):
        raise ValueError("Só quem escreveu o registo o pode alterar ou eliminar.")


def _para_decimal(valor) -> Decimal | None:
    """Accept text, number or nothing; anything unreadable becomes None."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor).replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        return None


def formatar_data(valor: datetime | None) -> str:
    """Return the ticket date as ``dd-mm-aaaa HH:MM``."""
    if valor is None:
        return ""
    try:
        return valor.strftime("%d-%m-%Y %H:%M")
    except AttributeError:
        return ""
