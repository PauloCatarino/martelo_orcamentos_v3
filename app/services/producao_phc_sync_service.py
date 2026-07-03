"""Sync production states from PHC: detect differences and apply choices."""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.estado_producao import interpretar_ok
from app.models.producao import Producao
from app.services.encomendas_phc_service import query_phc_estado_debug_rows
from app.services.estado_producao_service import (
    TIPO_STREAMLIT,
    _ano_norm,
    _norm_streamlit,
    carregar_indice,
)
from app.services.streamlit_sql_service import query_encomendas_cliente_final

TIPO_PASTA_PHC = "Encomenda de Cliente"
_CAMPOS_PRODUCAO_INICIADA = ("bd_corte_ok", "bd_orla_ok", "bd_cnc_ok")


def _norm_num(valor) -> str:
    digits = re.sub(r"\D", "", str(valor or ""))
    return str(int(digits)) if digits else ""


def _norm_txt(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").strip())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().upper()


def _estado_phc_text(row: dict) -> str:
    return (
        str(row.get("Estado_PHC") or "").strip()
        or str(row.get("BO_Tabela1") or "").strip()
        or str(row.get("BI_Tabela1") or "").strip()
    )


def _map_phc_estado(texto) -> str | None:
    t = _norm_txt(texto)
    if not t:
        return None
    if "ARQUIV" in t:
        return "Arquivado"
    if "FINALIZ" in t:
        return "Finalizado"
    if "PRODUC" in t:
        return "Producao"
    if "DESENHO" in t:
        return "Desenho"
    return None


def _mapear_status_streamlit(status_raw) -> str | None:
    """Map Streamlit Status to a terminal production state."""
    t = _norm_txt(status_raw)
    if not t:
        return None
    if "ARQUIV" in t or re.search(r"(?<!\d)7(?!\d)", t):
        return "Arquivado"
    if "FINALIZ" in t or re.search(r"(?<!\d)5(?!\d)", t):
        return "Finalizado"
    return None


def _tem_producao_iniciada(linhas: list[dict]) -> bool:
    for linha in linhas or []:
        for campo in _CAMPOS_PRODUCAO_INICIADA:
            pct = interpretar_ok(linha.get(campo))
            if pct is not None and pct > 0:
                return True
    return False


def _filtrar_responsavel(processos, responsavel):
    if not responsavel:
        return list(processos)
    alvo = responsavel.strip().casefold()
    return [
        processo
        for processo in processos
        if (processo.responsavel or "").strip().casefold() == alvo
    ]


def detetar_diferencas_estado_phc(
    session: Session,
    *,
    responsavel=None,
) -> list[dict]:
    """Return production processes whose local state differs from PHC."""
    processos = (
        session.execute(
            select(Producao).where(
                Producao.tipo_pasta == TIPO_PASTA_PHC,
                Producao.num_enc_phc.is_not(None),
                Producao.ano.is_not(None),
            )
        )
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

    anos = sorted({str(p.ano).strip() for p in processos if str(p.ano or "").strip()})
    idx: dict[tuple[str, str], list[str]] = {}
    for ano in anos:
        for row in query_phc_estado_debug_rows(session, ano=ano, max_rows=0):
            chave = (str(row.get("Ano") or "").strip(), _norm_num(row.get("Enc_No")))
            if chave[0] and chave[1]:
                idx.setdefault(chave, []).append(_estado_phc_text(row))

    diffs = []
    for processo in processos:
        chave = (str(processo.ano).strip(), _norm_num(processo.num_enc_phc))
        sugerido = None
        phc_raw = ""
        for estado_phc in idx.get(chave, []):
            mapeado = _map_phc_estado(estado_phc)
            if mapeado:
                sugerido, phc_raw = mapeado, estado_phc
                break

        atual = (processo.estado or "").strip()
        if sugerido and sugerido != atual:
            diffs.append(
                {
                    "id": processo.id,
                    "codigo": (processo.codigo_processo or "").strip(),
                    "num_enc_phc": (processo.num_enc_phc or "").strip(),
                    "cliente": (processo.nome_cliente or "").strip(),
                    "estado_martelo": atual or "(sem estado)",
                    "estado_sugerido": sugerido,
                    "estado_phc_raw": phc_raw,
                }
            )

    diffs.sort(key=lambda d: d["codigo"].casefold())
    return diffs


def detetar_diferencas_estado_streamlit(
    session: Session,
    *,
    responsavel=None,
) -> list[dict]:
    """Return Cliente Final processes whose local state differs from Streamlit."""
    processos = (
        session.execute(
            select(Producao).where(
                Producao.tipo_pasta == TIPO_STREAMLIT,
                Producao.num_enc_phc.is_not(None),
                Producao.ano.is_not(None),
            )
        )
        .scalars()
        .all()
    )
    processos = _filtrar_responsavel(processos, responsavel)

    anos = sorted({_ano_norm(p.ano) for p in processos if _ano_norm(p.ano)})
    if not processos or not anos:
        return []

    status_idx: dict[tuple[str, str], object] = {}
    try:
        linhas_enc = query_encomendas_cliente_final(
            session,
            ano_minimo=int(min(anos)),
        )
    except Exception:
        linhas_enc = []
    for row in linhas_enc:
        ano = _ano_norm(row.get("Ano"))
        numero = _norm_streamlit(row.get("Numero"))
        if ano in anos and numero:
            status_idx[(ano, numero)] = row.get("Status")

    try:
        tp_idx = carregar_indice(session, anos_normais=[], anos_especiais=anos)
    except Exception:
        tp_idx = {}

    diffs = []
    for processo in processos:
        ano = _ano_norm(processo.ano)
        numero = _norm_streamlit(processo.num_enc_phc)
        status_raw = status_idx.get((ano, numero))
        sugerido = _mapear_status_streamlit(status_raw)
        if sugerido is None:
            linhas = tp_idx.get(("E", ano, numero), [])
            sugerido = "Producao" if _tem_producao_iniciada(linhas) else "Desenho"

        atual = (processo.estado or "").strip()
        if sugerido and sugerido != atual:
            status_texto = "" if status_raw is None else str(status_raw).strip()
            diffs.append(
                {
                    "id": processo.id,
                    "codigo": (processo.codigo_processo or "").strip(),
                    "num_enc_phc": (processo.num_enc_phc or "").strip(),
                    "cliente": (processo.nome_cliente or "").strip(),
                    "estado_martelo": atual or "(sem estado)",
                    "estado_sugerido": sugerido,
                    "estado_phc_raw": status_texto or "(sem dados)",
                    "fonte": "Streamlit",
                }
            )

    diffs.sort(key=lambda d: d["codigo"].casefold())
    return diffs


def aplicar_estados(
    session: Session,
    atualizacoes,
    *,
    current_user_id=None,
) -> int:
    """Apply selected state updates and commit them."""
    n = 0
    for proc_id, novo_estado in atualizacoes:
        processo = session.get(Producao, int(proc_id))
        if processo is None:
            continue
        processo.estado = novo_estado
        if current_user_id is not None:
            processo.updated_by_id = current_user_id
        n += 1
    session.commit()
    return n
