"""Leitura (SÓ-LEITURA) das propostas do PHC — tabela ``BO``, ``NDOS = 3``.

Serve para descobrir o número que o PHC atribuiu a uma proposta acabada de
criar, sem depender do ecrã (os campos do PHC são controlos OLE de Visual
FoxPro e não expõem texto ao Windows).

Estratégia — determinística e à prova de propostas criadas por outros
utilizadores ao mesmo tempo:

1. ANTES de criar: ler o maior ``OBRANO`` do ano (a "marca de água").
2. Criar a proposta pela automação da janela.
3. DEPOIS: procurar as propostas do ano com ``OBRANO`` acima da marca. Entre
   as candidatas escolhe-se a do cliente indicado (e a ref. cliente confirma).

⚠️ ``OBRANO`` **repete-se entre anos** (o nº 806 existe em 2022, 2023, 2024 e
2025), por isso todas as consultas filtram obrigatoriamente por ano — é isso
que torna o código do V3 ``<ano2><nº4>`` (ex.: ``260806``) não-ambíguo.

Todas as consultas passam por ``assert_select_only``: nunca escrevem no PHC.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services.phc_sql import (
    assert_select_only,
    build_connection_string,
    load_phc_config,
    run_select,
)

# Tipo de dossier "Proposta" no PHC (confirmado na base de dados real).
NDOS_PROPOSTA = 3


@dataclass(frozen=True)
class PropostaPhc:
    """Uma proposta lida do PHC."""

    numero: int
    ano: int
    num_cliente: str | None
    ref_cliente: str | None
    data: str | None
    #: Nome do destinatário gravado na proposta (``BO.NOME``). Nos clientes
    #: temporários é o único campo que distingue uma proposta da outra: todas
    #: ficam no cliente genérico 63, com nomes diferentes.
    nome: str | None = None


def _inteiro(valor) -> int | None:
    """Converter valores numéricos do SQL Server (numeric) para int."""
    if valor is None:
        return None
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def _texto(valor) -> str | None:
    normalizado = ("" if valor is None else str(valor)).strip()
    return normalizado or None


def build_query_max_obrano(ano: int) -> str:
    """Consulta do maior número de proposta já usado num ano."""
    return (
        "SELECT MAX(BO.OBRANO) AS Maximo "
        "FROM BO WITH (NOLOCK) "
        f"WHERE BO.NDOS = {NDOS_PROPOSTA} AND YEAR(BO.DATAOBRA) = {int(ano)}"
    )


def build_query_propostas_do_ano(
    *,
    ano: int,
    obrano_minimo: int | None = None,
    num_cliente: str | None = None,
    max_linhas: int = 50,
) -> str:
    """Consulta das propostas de um ano, opcionalmente acima de um número."""
    filtros = [
        f"BO.NDOS = {NDOS_PROPOSTA}",
        f"YEAR(BO.DATAOBRA) = {int(ano)}",
    ]
    if obrano_minimo is not None:
        filtros.append(f"BO.OBRANO > {int(obrano_minimo)}")
    if num_cliente:
        numero = _inteiro(num_cliente)
        if numero is not None:
            filtros.append(f"BO.NO = {numero}")

    return (
        f"SELECT TOP ({int(max_linhas)}) "
        "BO.OBRANO AS Numero, YEAR(BO.DATAOBRA) AS Ano, BO.NO AS Num_Cliente, "
        "LTRIM(RTRIM(BO.NOME)) AS Nome, "
        "LTRIM(RTRIM(BO.U_ORCC)) AS Ref_Cliente, "
        "CONVERT(VARCHAR(10), BO.DATAOBRA, 104) AS Data "
        "FROM BO WITH (NOLOCK) "
        f"WHERE {' AND '.join(filtros)} "
        "ORDER BY BO.OBRANO DESC"
    )


def build_query_dossiers_do_dia(*, data_iso: str) -> str:
    """Consulta dos dossiers criados a partir de uma data — QUALQUER tipo.

    Serve para detetar que o seletor do PHC estava noutro tipo (ex.: "Encomenda
    de Cliente") e foi criado o documento errado. O tipo não é legível no ecrã
    (é desenhado dentro do OLE), por isso só se deteta depois de gravar.

    Filtra por **data**, não por número: cada tipo de dossier tem a sua própria
    série de ``OBRANO`` (as Encomendas de Cliente já vão em 1329 enquanto as
    Propostas vão em 805), por isso comparar números entre tipos não faz
    sentido nenhum.

    ``data_iso`` no formato ``YYYYMMDD``.
    """
    dia = "".join(c for c in str(data_iso) if c.isdigit())[:8]
    if len(dia) != 8:
        raise ValueError("data_iso tem de ser YYYYMMDD")

    return (
        "SELECT TOP (50) BO.OBRANO AS Numero, BO.NDOS AS Ndos, "
        "LTRIM(RTRIM(BO.NMDOS)) AS Tipo, BO.NO AS Num_Cliente, "
        "LTRIM(RTRIM(BO.U_ORCC)) AS Ref_Cliente "
        "FROM BO WITH (NOLOCK) "
        f"WHERE BO.DATAOBRA >= '{dia}' "
        "ORDER BY BO.NDOS, BO.OBRANO DESC"
    )


def detetar_tipo_errado(
    linhas,
    *,
    num_cliente: str | None = None,
    ref_cliente: str | None = None,
) -> str | None:
    """Detetar um dossier criado com o tipo errado (não "Proposta").

    Devolve a descrição do dossier indevido, ou ``None`` se não houver sinal
    disso. Só considera dossiers do cliente/ref em questão — para não acusar
    documentos que outra pessoa criou legitimamente ao mesmo tempo.
    """
    esperado_cliente = _inteiro(num_cliente)
    ref = (ref_cliente or "").strip().casefold()

    for linha in linhas or []:
        ndos = _inteiro(linha.get("Ndos"))
        if ndos is None or ndos == NDOS_PROPOSTA:
            continue

        do_cliente = (
            esperado_cliente is not None
            and _inteiro(linha.get("Num_Cliente")) == esperado_cliente
        )
        mesma_ref = bool(
            ref and (_texto(linha.get("Ref_Cliente")) or "").casefold() == ref
        )
        if not (do_cliente or mesma_ref):
            continue

        tipo = _texto(linha.get("Tipo")) or f"NDOS {ndos}"
        numero = _inteiro(linha.get("Numero"))
        return f"{tipo} nº {numero}"

    return None


def build_query_linhas_proposta(*, ano: int, numero: int) -> str:
    """Consulta das linhas (artigos) de uma proposta — tabela ``BI``."""
    return (
        "SELECT BI.LORDEM AS Ordem, LTRIM(RTRIM(BI.DESIGN)) AS Designacao "
        "FROM BI WITH (NOLOCK) "
        "INNER JOIN BO WITH (NOLOCK) ON BO.BOSTAMP = BI.BOSTAMP "
        f"WHERE BO.NDOS = {NDOS_PROPOSTA} AND BO.OBRANO = {int(numero)} "
        f"AND YEAR(BO.DATAOBRA) = {int(ano)} "
        "ORDER BY BI.LORDEM"
    )


def verificar_proposta_gravada(
    proposta: PropostaPhc,
    designacoes: list[str],
    *,
    ref_cliente: str | None,
    designacao: str | None,
    nome_cliente: str | None = None,
) -> list[str]:
    """Confirmar que a proposta ficou no PHC como era pretendido.

    Rede de segurança para PCs com a grelha configurada de outra forma: o
    número de TABs pode cair num campo diferente e escrever no lugar errado
    sem dar erro. Como os campos do PHC são cegos ao Windows, esta é a única
    forma de detetar isso — comparando o que ficou gravado.

    Devolve a lista de avisos (vazia = tudo conforme).
    """
    avisos: list[str] = []

    # Cliente temporário: o nome é escrito à mão na janela que o PHC abre.
    # Se ficou "CONSUMIDOR FINAL", a janela não apareceu ou o nome perdeu-se —
    # e a proposta fica no PHC sem se saber de quem é.
    esperado_nome = (nome_cliente or "").strip()
    if esperado_nome:
        gravado_nome = (proposta.nome or "").strip()
        if gravado_nome.casefold() != esperado_nome.casefold():
            avisos.append(
                f"O Nome no PHC ficou {gravado_nome or '(vazio)'!r} em vez de "
                f"{esperado_nome!r}."
            )

    esperado_ref = (ref_cliente or "").strip()
    if esperado_ref:
        gravado_ref = (proposta.ref_cliente or "").strip()
        if gravado_ref.casefold() != esperado_ref.casefold():
            avisos.append(
                f"A Ref. Cliente no PHC ficou {gravado_ref or '(vazia)'!r} "
                f"em vez de {esperado_ref!r}."
            )

    esperada_designacao = (designacao or "").strip()
    if esperada_designacao:
        encontradas = [(d or "").strip() for d in designacoes if (d or "").strip()]
        if not encontradas:
            avisos.append(
                f"A proposta não tem nenhuma linha com a designação "
                f"{esperada_designacao!r}."
            )
        elif not any(
            d.casefold() == esperada_designacao.casefold() for d in encontradas
        ):
            avisos.append(
                f"A designação no PHC ficou {encontradas[0]!r} em vez de "
                f"{esperada_designacao!r}."
            )

    return avisos


def _linhas_para_propostas(linhas) -> list[PropostaPhc]:
    """Converter as linhas cruas do SELECT em ``PropostaPhc``."""
    propostas: list[PropostaPhc] = []
    for linha in linhas or []:
        numero = _inteiro(linha.get("Numero"))
        ano = _inteiro(linha.get("Ano"))
        if numero is None or ano is None:
            continue
        num_cliente = _inteiro(linha.get("Num_Cliente"))
        propostas.append(
            PropostaPhc(
                numero=numero,
                ano=ano,
                num_cliente=str(num_cliente) if num_cliente is not None else None,
                ref_cliente=_texto(linha.get("Ref_Cliente")),
                data=_texto(linha.get("Data")),
                nome=_texto(linha.get("Nome")),
            )
        )
    return propostas


def escolher_proposta_criada(
    candidatas: list[PropostaPhc],
    *,
    num_cliente: str | None = None,
    ref_cliente: str | None = None,
    nome_cliente: str | None = None,
) -> PropostaPhc | None:
    """Escolher, entre as candidatas, a proposta que acabou de ser criada.

    O cliente é um **requisito**, não uma preferência: propostas de outro
    cliente são descartadas. Sem isso arriscávamos mapear no V3 o número de
    uma proposta que outra pessoa criou ao mesmo tempo. Entre as do cliente
    certo, prefere a que tem o mesmo nome (conta para os clientes temporários,
    onde todas ficam no cliente genérico 63 e só o nome as distingue), depois
    a mesma ref. cliente e, em caso de empate, a de número mais baixo (a
    primeira criada depois da marca de água).

    O nome é preferência e não requisito de propósito: se o PHC o cortar por
    ser comprido, o número continua a ser encontrado — quem avisa da diferença
    é a :func:`verificar_proposta_gravada`.

    Devolve ``None`` quando não há nenhuma candidata segura — nesse caso o
    número deve ser confirmado por uma pessoa, nunca adivinhado.
    """
    if not candidatas:
        return None

    esperado_cliente = _inteiro(num_cliente)
    if esperado_cliente is not None:
        candidatas = [
            proposta
            for proposta in candidatas
            if _inteiro(proposta.num_cliente) == esperado_cliente
        ]
        if not candidatas:
            return None

    ref = (ref_cliente or "").strip().casefold()
    nome = (nome_cliente or "").strip().casefold()

    def pontuar(proposta: PropostaPhc) -> tuple[int, int, int]:
        mesmo_nome = bool(
            nome and (proposta.nome or "").strip().casefold() == nome
        )
        mesma_ref = bool(
            ref and (proposta.ref_cliente or "").strip().casefold() == ref
        )
        # Ordenar: nome igual primeiro, depois ref igual, depois nº mais baixo.
        return (0 if mesmo_nome else 1, 0 if mesma_ref else 1, proposta.numero)

    return sorted(candidatas, key=pontuar)[0]


# -- Execução (toca no SQL Server do PHC, só SELECT) ------------------------


def ler_max_obrano(session: Session, *, ano: int) -> int:
    """Maior número de proposta já usado no ano (0 se o ano estiver vazio)."""
    query = build_query_max_obrano(ano)
    assert_select_only(query)
    conn_str = build_connection_string(load_phc_config(session))
    linhas = run_select(conn_str, query)
    if not linhas:
        return 0
    return _inteiro(linhas[0].get("Maximo")) or 0


def listar_propostas_do_ano(
    session: Session,
    *,
    ano: int,
    obrano_minimo: int | None = None,
    num_cliente: str | None = None,
) -> list[PropostaPhc]:
    """Propostas de um ano (SÓ-LEITURA), opcionalmente acima de um número."""
    query = build_query_propostas_do_ano(
        ano=ano, obrano_minimo=obrano_minimo, num_cliente=num_cliente
    )
    assert_select_only(query)
    conn_str = build_connection_string(load_phc_config(session))
    return _linhas_para_propostas(run_select(conn_str, query))


def procurar_dossier_tipo_errado(
    session: Session,
    *,
    data_iso: str,
    num_cliente: str | None = None,
    ref_cliente: str | None = None,
) -> str | None:
    """Procurar um dossier criado hoje com o tipo errado (SÓ-LEITURA)."""
    query = build_query_dossiers_do_dia(data_iso=data_iso)
    assert_select_only(query)
    conn_str = build_connection_string(load_phc_config(session))
    linhas = run_select(conn_str, query)
    return detetar_tipo_errado(
        linhas, num_cliente=num_cliente, ref_cliente=ref_cliente
    )


def ler_designacoes_proposta(session: Session, *, ano: int, numero: int) -> list[str]:
    """Designações das linhas de uma proposta (SÓ-LEITURA)."""
    query = build_query_linhas_proposta(ano=ano, numero=numero)
    assert_select_only(query)
    conn_str = build_connection_string(load_phc_config(session))
    linhas = run_select(conn_str, query)
    return [
        texto
        for texto in ((_texto(linha.get("Designacao")) or "") for linha in linhas or [])
        if texto
    ]


def localizar_proposta_criada(
    session: Session,
    *,
    ano: int,
    obrano_base: int,
    num_cliente: str | None = None,
    ref_cliente: str | None = None,
    nome_cliente: str | None = None,
) -> PropostaPhc | None:
    """Localizar a proposta criada depois de ``obrano_base`` (SÓ-LEITURA).

    Devolve ``None`` se não houver uma correspondência segura para o cliente
    indicado — melhor pedir confirmação do que gravar o número errado.
    """
    candidatas = listar_propostas_do_ano(
        session, ano=ano, obrano_minimo=obrano_base, num_cliente=num_cliente
    )
    return escolher_proposta_criada(
        candidatas,
        num_cliente=num_cliente,
        ref_cliente=ref_cliente,
        nome_cliente=nome_cliente,
    )
