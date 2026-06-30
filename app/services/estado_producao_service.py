"""Serviço SQL (só-leitura) do Estado de Produção — chão de fábrica (PD2).

Lê o Streamlit (SQL Server, READ-ONLY) — ``CadernoEncargos[_]`` + ``TemposProducao[_]``
(JOIN por ``bd_key``) — nos dois universos (normais e especiais ``_``), agrupa as
linhas por encomenda (ano + nº), liga cada encomenda às obras do Martelo (tabela
``producao``) e calcula o estado por setor com o domínio puro PD1
(:mod:`app.domain.estado_producao`). NÃO é a UI (isso é o PD3).

Mapeamento das tabelas (confirmado por sonda à BD, INFORMATION_SCHEMA):
- ``CadernoEncargos`` (``CadernoEncargos_`` nos especiais) tem a IDENTIFICAÇÃO:
  ``bd_key, bd_ano, bd_n_encomenda, bd_modelo, bd_versao, bd_cliente, bd_existe_montagem``.
- ``TemposProducao`` (``TemposProducao_`` nos especiais) tem os ``*_ok`` + quantidades
  + ``bd_tempo_embalamento_minutos`` (e ``bd_key`` para o JOIN).

READ-ONLY absoluto: todas as queries passam por ``assert_select_only`` antes de
correr. Sem Qt — é camada de serviço, testável.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.estado_producao import EstadoProducao, estado_producao_encomenda
from app.services import producao_precos_service as precos
from app.services import streamlit_sql_service as st
from app.services.phc_sql import assert_select_only, run_select
from app.services.producao_service import ProducaoService

TIPO_PHC = "Encomenda de Cliente"
TIPO_STREAMLIT = "Encomenda de Cliente Final"

# Colunas por tabela (ver sonda no docstring): ce = CadernoEncargos, tp = TemposProducao.
_COLS_CE = (
    "bd_key",
    "bd_ano",
    "bd_n_encomenda",
    "bd_modelo",
    "bd_versao",
    "bd_cliente",
    "bd_existe_montagem",
)
_COLS_TP = (
    "bd_stock_ok",
    "bd_preparacao_placas_ok",
    "bd_corte_ok",
    "bd_orla_ok",
    "bd_cnc_ok",
    "bd_montagem_ok",
    "bd_embalagem_ok",
    "bd_expedicao_ok",
    "bd_operacoes_corte_quantidade",
    "bd_operacoes_orla_quantidade",
    "bd_operacoes_cnc_quantidade",
    "bd_tempo_embalamento_minutos",
)


def _norm_num(valor) -> str:
    """Só dígitos, sem zeros à esquerda ("0237" -> "237")."""
    digits = re.sub(r"\D", "", str(valor or ""))
    return str(int(digits)) if digits else ""


def _norm_streamlit(valor) -> str:
    """Número especial normalizado ("58" -> "_058"; "_058" -> "_058")."""
    raw = str(valor or "").strip()
    digits = re.sub(r"\D", "", raw)
    return "_" + digits.zfill(3) if digits else raw


def _ano_norm(valor) -> str:
    """Só os dígitos do ano ("2026" -> "2026")."""
    return re.sub(r"\D", "", str(valor or ""))


@dataclass(frozen=True)
class EstadoProducaoObra:
    """Estado de produção de UMA obra do Martelo (ligada ao Streamlit)."""

    id: int
    codigo: str
    ano: str
    num_enc: str
    cliente: str
    enc_phc: str               # nº encomenda PHC (vazio se obra Streamlit)
    enc_streamlit: str         # nº encomenda Streamlit "_NNN" (vazio se obra PHC)
    ref_cliente: str           # referência do cliente
    responsavel: str
    estado_local: str          # Producao.estado
    fonte: str                 # "Streamlit" (normais) | "Streamlit _" (especiais)
    preco_externo: float | None  # preço na fonte externa (PHC/Streamlit) ou None
    fonte_preco: str           # "PHC" | "Streamlit" | ""
    estado: EstadoProducao     # resultado do PD1
    encontrado: bool           # houve linhas no Streamlit p/ esta encomenda
    concluido_sem_preco: bool  # 100% mas sem preço externo (ver método)


def _build_query(*, especial: bool, anos: list[str]) -> str:
    """Monta a query de um universo (normais ou especiais ``_``)."""
    tabela_ce = "dbo.CadernoEncargos_" if especial else "dbo.CadernoEncargos"
    tabela_tp = "dbo.TemposProducao_" if especial else "dbo.TemposProducao"
    colunas = [f"ce.{c} AS {c}" for c in _COLS_CE]
    colunas += [f"tp.{c} AS {c}" for c in _COLS_TP]
    # ``anos`` já vem saneado a dígitos em :func:`_query_universo` (sem injeção).
    anos_in = ", ".join(f"'{ano}'" for ano in anos)
    return (
        "SELECT " + ", ".join(colunas) + " "
        f"FROM {tabela_ce} ce WITH (NOLOCK) "
        f"LEFT JOIN {tabela_tp} tp WITH (NOLOCK) ON tp.bd_key = ce.bd_key "
        f"WHERE CAST(ce.bd_ano AS VARCHAR(8)) IN ({anos_in})"
    )


def _query_universo(session: Session, *, especial: bool, anos) -> list[dict]:
    """Corre a query de um universo e acrescenta a chave derivada de montagem."""
    anos_limpos = sorted({a for a in (_ano_norm(x) for x in anos or []) if a})
    if not anos_limpos:
        return []

    query = _build_query(especial=especial, anos=anos_limpos)
    assert_select_only(query)
    conn = st.build_connection_string(st.load_streamlit_config(session))
    linhas = run_select(conn, query)
    for linha in linhas:
        # O PD1 espera tem_montagem_ativa (1/0), derivado de bd_existe_montagem='1'.
        linha["tem_montagem_ativa"] = (
            1 if str(linha.get("bd_existe_montagem") or "").strip() == "1" else 0
        )
    return linhas


def carregar_indice(
    session: Session,
    *,
    anos_normais,
    anos_especiais,
) -> dict[tuple[str, str, str], list[dict]]:
    """Junta os dois universos num índice agrupado por encomenda.

    Chave: ``("N", ano, _norm_num(nº))`` (normais) ou
    ``("E", ano, _norm_streamlit(nº))`` (especiais). Uma encomenda tem várias
    ``bd_key`` -> várias linhas.
    """
    indice: dict[tuple[str, str, str], list[dict]] = {}

    for linha in _query_universo(session, especial=False, anos=anos_normais):
        ano = _ano_norm(linha.get("bd_ano"))
        num = _norm_num(linha.get("bd_n_encomenda"))
        if ano and num:
            indice.setdefault(("N", ano, num), []).append(linha)

    for linha in _query_universo(session, especial=True, anos=anos_especiais):
        ano = _ano_norm(linha.get("bd_ano"))
        num = _norm_streamlit(linha.get("bd_n_encomenda"))
        if ano and num:
            indice.setdefault(("E", ano, num), []).append(linha)

    return indice


def estado_producao_por_processo(
    session: Session,
    processos=None,
    *,
    responsavel=None,
) -> list[EstadoProducaoObra]:
    """Devolve o estado de produção de cada obra, ligado ao Streamlit.

    ``concluido_sem_preco`` (aviso "⚠️ Concluído sem preço") usa o preço EXTERNO
    por tipo de encomenda (PHC ou Streamlit, via ``precos.precos_externos``): 100%
    concluído mas sem preço na fonte. ``precos_externos`` é resiliente — se uma
    fonte estiver offline, os preços dessa fonte ficam vazios (None).
    """
    if processos is None:
        processos = ProducaoService(session).listar_processos()

    if responsavel:
        alvo = responsavel.strip().casefold()
        processos = [
            processo
            for processo in processos
            if (processo.responsavel or "").strip().casefold() == alvo
        ]

    mapa_precos = precos.precos_externos(session, processos)

    anos_normais = sorted(
        {
            str(processo.ano).strip()
            for processo in processos
            if (processo.tipo_pasta or "") == TIPO_PHC and str(processo.ano or "").strip()
        }
    )
    anos_especiais = sorted(
        {
            str(processo.ano).strip()
            for processo in processos
            if (processo.tipo_pasta or "") == TIPO_STREAMLIT
            and str(processo.ano or "").strip()
        }
    )

    indice = carregar_indice(
        session, anos_normais=anos_normais, anos_especiais=anos_especiais
    )

    resultados: list[EstadoProducaoObra] = []
    for processo in processos:
        tipo = processo.tipo_pasta or ""
        if tipo == TIPO_STREAMLIT:
            chave = ("E", _ano_norm(processo.ano), _norm_streamlit(processo.num_enc_phc))
            fonte = "Streamlit _"
        else:
            chave = ("N", _ano_norm(processo.ano), _norm_num(processo.num_enc_phc))
            fonte = "Streamlit"

        num_enc = (processo.num_enc_phc or "").strip()
        enc_phc = num_enc if tipo == TIPO_PHC else ""
        enc_streamlit = num_enc if tipo == TIPO_STREAMLIT else ""
        ref_cliente = (processo.ref_cliente or "").strip()

        linhas = indice.get(chave, [])
        estado = estado_producao_encomenda(linhas)

        preco_externo = mapa_precos.get(processo.id)
        fonte_preco = (
            "PHC" if tipo == TIPO_PHC
            else ("Streamlit" if tipo == TIPO_STREAMLIT else "")
        )
        sem_preco = preco_externo is None or preco_externo <= 0
        concluido_sem_preco = (
            estado.total_setores > 0 and estado.global_pct >= 100 and sem_preco
        )

        resultados.append(
            EstadoProducaoObra(
                id=processo.id,
                codigo=(processo.codigo_processo or "").strip(),
                ano=str(processo.ano or "").strip(),
                num_enc=num_enc,
                cliente=(processo.nome_cliente or "").strip(),
                enc_phc=enc_phc,
                enc_streamlit=enc_streamlit,
                ref_cliente=ref_cliente,
                responsavel=(processo.responsavel or "").strip(),
                estado_local=(processo.estado or "").strip(),
                fonte=fonte,
                preco_externo=preco_externo,
                fonte_preco=fonte_preco,
                estado=estado,
                encontrado=bool(linhas),
                concluido_sem_preco=concluido_sem_preco,
            )
        )

    # Mantém a ordem de ``processos`` (listar_processos -> created_at DESC, mais
    # recente no topo), consistente com a lista da Produção e o dashboard.
    return resultados
