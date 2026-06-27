"""Sync production states from PHC: detect differences and apply choices."""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.producao import Producao
from app.services.encomendas_phc_service import query_phc_estado_debug_rows

TIPO_PASTA_PHC = "Encomenda de Cliente"


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
        return "Produ\u00e7\u00e3o"
    if "DESENHO" in t:
        return "Desenho"
    return None


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
