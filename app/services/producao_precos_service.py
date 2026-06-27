"""Validate Martelo prices against PHC/Streamlit external selling prices."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.producao import Producao
from app.services import phc_sql
from app.services import streamlit_sql_service as st

TIPO_PHC = "Encomenda de Cliente"
TIPO_STREAMLIT = "Encomenda de Cliente Final"
TOLERANCIA = 1.0


def _norm_num(valor) -> str:
    digits = re.sub(r"\D", "", str(valor or ""))
    return str(int(digits)) if digits else ""


def _norm_streamlit(valor) -> str:
    raw = str(valor or "").strip()
    digits = re.sub(r"\D", "", raw)
    return "_" + digits.zfill(3) if digits else raw


def _query_phc_totais(session, anos) -> dict[tuple[str, str], float]:
    conn = phc_sql.build_connection_string(phc_sql.load_phc_config(session))
    totais: dict[tuple[str, str], float] = {}
    for ano in anos:
        ano_int = int(re.sub(r"\D", "", str(ano)) or "0")
        if ano_int <= 0:
            continue
        query = (
            "SELECT BO.OBRANO AS enc, BO.etotaldeb AS total "
            "FROM BO WITH (NOLOCK) "
            f"WHERE BO.NDOS = 1 AND BO.DATAOBRA >= '{ano_int}-01-01' "
            f"AND BO.DATAOBRA < '{ano_int + 1}-01-01'"
        )
        phc_sql.assert_select_only(query)
        for row in phc_sql.run_select(conn, query):
            enc = _norm_num(row.get("enc"))
            if not enc:
                continue
            try:
                total = float(row.get("total") or 0)
            except (TypeError, ValueError):
                total = 0.0
            totais[(str(ano_int), enc)] = total
    return totais


def _query_streamlit_totais(session) -> dict[str, float]:
    conn = st.build_connection_string(st.load_streamlit_config(session))
    query = (
        "SELECT E.Numero AS numero, SUM(I.ValorVenda) AS total "
        "FROM dbo.Encomendas E WITH (NOLOCK) "
        "LEFT JOIN dbo.ItensEncomenda I WITH (NOLOCK) ON I.EncomendaId = E.Id "
        "GROUP BY E.Numero"
    )
    phc_sql.assert_select_only(query)
    totais: dict[str, float] = {}
    for row in phc_sql.run_select(conn, query):
        numero = _norm_streamlit(row.get("numero"))
        if not numero:
            continue
        try:
            total = float(row.get("total") or 0)
        except (TypeError, ValueError):
            total = 0.0
        totais[numero] = total
    return totais


def detetar_diferencas_preco(session: Session, *, responsavel=None) -> list[dict]:
    """Return production processes whose Martelo price differs from external price."""
    processos = (
        session.execute(select(Producao).where(Producao.num_enc_phc.is_not(None)))
        .scalars()
        .all()
    )
    if responsavel:
        alvo = responsavel.strip().casefold()
        processos = [
            processo
            for processo in processos
            if (processo.responsavel or "").strip().casefold() == alvo
        ]

    anos = sorted(
        {
            str(processo.ano).strip()
            for processo in processos
            if (processo.tipo_pasta or "") == TIPO_PHC
            and str(processo.ano or "").strip()
        }
    )
    tem_streamlit = any(
        (processo.tipo_pasta or "") == TIPO_STREAMLIT for processo in processos
    )
    phc_tot = _query_phc_totais(session, anos) if anos else {}
    st_tot = _query_streamlit_totais(session) if tem_streamlit else {}

    diffs = []
    for processo in processos:
        externo = None
        fonte = ""
        if (processo.tipo_pasta or "") == TIPO_PHC:
            externo = phc_tot.get(
                (str(processo.ano).strip(), _norm_num(processo.num_enc_phc))
            )
            fonte = "PHC"
        elif (processo.tipo_pasta or "") == TIPO_STREAMLIT:
            externo = st_tot.get(_norm_streamlit(processo.num_enc_phc))
            fonte = "Streamlit"

        if externo is None or externo <= 0:
            continue

        martelo = float(processo.preco_total) if processo.preco_total is not None else None
        sem_preco = martelo is None
        if not sem_preco and abs(martelo - externo) < TOLERANCIA:
            continue

        diffs.append(
            {
                "id": processo.id,
                "codigo": (processo.codigo_processo or "").strip(),
                "num_enc": (processo.num_enc_phc or "").strip(),
                "cliente": (processo.nome_cliente or "").strip(),
                "fonte": fonte,
                "preco_martelo": martelo,
                "preco_externo": round(externo, 2),
                "default_check": sem_preco,
            }
        )

    diffs.sort(key=lambda d: ((not d["default_check"]), d["codigo"].casefold()))
    return diffs


def aplicar_precos(session, atualizacoes, *, current_user_id=None) -> int:
    """Apply selected prices and commit them."""
    n = 0
    for proc_id, novo_preco in atualizacoes:
        processo = session.get(Producao, int(proc_id))
        if processo is None:
            continue
        try:
            processo.preco_total = Decimal(str(novo_preco))
        except (InvalidOperation, ValueError):
            continue
        if current_user_id is not None:
            processo.updated_by_id = current_user_id
        n += 1
    session.commit()
    return n
