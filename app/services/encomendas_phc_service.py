"""Leitura (so-leitura) das encomendas do PHC (tabelas BI/BO/BO2/CL)."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.services.phc_sql import (
    assert_select_only,
    build_connection_string,
    load_phc_config,
    run_select,
)


def query_encomendas_phc(
    session: Session,
    *,
    ano_minimo: int,
    max_linhas: int = 0,
) -> list[dict]:
    """Le as encomendas (NDOS=1, nao anuladas) do PHC. SO-LEITURA (SELECT).

    ``ano_minimo`` filtra por ``BI.DATAOBRA >= '<ano>0101'``.
    ``max_linhas`` > 0 limita o resultado com ``TOP``; 0 = sem limite.
    As datas vem ja em "dd-mm-aaaa" do ``CONVERT(..., 104)``.

    Query portada do Martelo V2; passa pelo ``assert_select_only`` antes de
    ser executada com ``run_select`` (que tambem revalida).
    """
    ano = int(ano_minimo)
    top = ""
    if max_linhas and int(max_linhas) > 0:
        top = f"TOP ({int(max_linhas)}) "

    query = (
        f"SELECT {top}"
        "BI.NOME AS Cliente, CL.NOME2 AS Cliente_Abreviado, "
        "BI.OBRANO AS Enc_No, CL.NO AS Num_PHC, "
        "BI.REF AS Ref_PHC, BO2.TELEFONE AS Telefone, "
        "BO.U_ORCC AS Ref_Cliente, BI.DESIGN AS Descricao_Artigo, "
        "CONVERT(VARCHAR(10), BI.DATAOBRA, 104) AS Data_Encomenda, "
        "CONVERT(VARCHAR(10), BO.U_ENTREGA, 104) AS Data_Entrega "
        "FROM BI WITH (NOLOCK) "
        "INNER JOIN BO WITH (NOLOCK) ON BO.BOSTAMP = BI.BOSTAMP "
        "INNER JOIN BO2 WITH (NOLOCK) ON BO.BOSTAMP = BO2.BO2STAMP "
        "LEFT JOIN CL WITH (NOLOCK) ON CL.NOME = BI.NOME "
        f"WHERE BI.NDOS = 1 AND BO2.ANULADO = 0 AND BI.DATAOBRA >= '{ano}0101' "
        "ORDER BY BI.DATAOBRA DESC, BI.OBRANO DESC, BI.LORDEM DESC"
    )

    assert_select_only(query)
    conn_str = build_connection_string(load_phc_config(session))
    return run_select(conn_str, query)


def _build_phc_estado_debug_query(
    *,
    num_enc_phc=None,
    ano=None,
    min_year=None,
    max_rows=2000,
) -> str:
    """Build the read-only PHC status diagnostic SELECT."""
    filtros = [
        "BI.NDOS = 1",
        "LTRIM(RTRIM(BI.NMDOS)) = 'Encomenda de Cliente'",
    ]

    if num_enc_phc is not None and str(num_enc_phc).strip():
        enc_digits = re.sub(r"\D", "", str(num_enc_phc or ""))
        if not enc_digits:
            raise ValueError("Num Enc PHC invalido.")
        filtros.append(f"BI.OBRANO = {int(enc_digits)}")

    if ano is not None and str(ano).strip():
        try:
            ano_int = int(re.sub(r"\D", "", str(ano)))
        except Exception as exc:
            raise ValueError("Ano invalido.") from exc
        if ano_int < 1900 or ano_int > 2200:
            raise ValueError("Ano invalido.")
        filtros.append(f"BI.DATAOBRA >= '{ano_int:04d}-01-01'")
        filtros.append(f"BI.DATAOBRA < '{ano_int + 1:04d}-01-01'")
    elif min_year is not None and str(min_year).strip():
        try:
            min_year_int = int(re.sub(r"\D", "", str(min_year)))
        except Exception as exc:
            raise ValueError("Ano minimo invalido.") from exc
        if min_year_int < 1900 or min_year_int > 2200:
            raise ValueError("Ano minimo invalido.")
        filtros.append(f"BI.DATAOBRA >= '{min_year_int:04d}-01-01'")

    top = ""
    if max_rows is not None:
        try:
            max_rows_int = int(max_rows)
        except Exception as exc:
            raise ValueError("Maximo de linhas invalido.") from exc
        if max_rows_int < 0:
            raise ValueError("Maximo de linhas invalido.")
        if max_rows_int > 0:
            top = f"TOP ({max_rows_int}) "

    where = " AND ".join(filtros)
    return f"""
SELECT DISTINCT {top}
    YEAR(BI.DATAOBRA) AS Ano,
    BI.OBRANO AS Enc_No,
    LTRIM(RTRIM(BI.NOME)) AS BI_Nome,
    LTRIM(RTRIM(BO.NOME)) AS BO_Nome,
    LTRIM(RTRIM(CL.NOME)) AS CL_Nome,
    CAST(CL.NO AS VARCHAR(64)) AS Num_PHC,
    LTRIM(RTRIM(BI.NMDOC)) AS NMDoc,
    LTRIM(RTRIM(BI.TABELA1)) AS BI_Tabela1,
    LTRIM(RTRIM(BO.TABELA1)) AS BO_Tabela1,
    LTRIM(RTRIM(COALESCE(NULLIF(BO.TABELA1, ''), NULLIF(BI.TABELA1, ''), ''))) AS Estado_PHC,
    BI.FDATA AS FDataRaw,
    CONVERT(VARCHAR(10), BI.FDATA, 104) AS FData,
    CONVERT(VARCHAR(10), BI.DATAOBRA, 104) AS BI_DataObra,
    CONVERT(VARCHAR(10), BO.DATAOBRA, 104) AS BO_DataObra,
    BI.BOSTAMP AS BI_Bostamp,
    BO.BOSTAMP AS BO_Bostamp
FROM BI WITH (NOLOCK)
LEFT JOIN BO WITH (NOLOCK) ON BO.BOSTAMP = BI.BOSTAMP
LEFT JOIN CL WITH (NOLOCK) ON LTRIM(RTRIM(CL.NOME)) = LTRIM(RTRIM(BI.NOME))
WHERE {where}
ORDER BY FDataRaw DESC, Enc_No DESC, BI_Bostamp DESC
""".strip()


def query_phc_estado_debug_rows(
    session: Session,
    *,
    num_enc_phc=None,
    ano=None,
    min_year=None,
    max_rows=2000,
) -> list[dict]:
    """Read PHC order status diagnostic rows. SO-LEITURA (SELECT)."""
    query = _build_phc_estado_debug_query(
        num_enc_phc=num_enc_phc,
        ano=ano,
        min_year=min_year,
        max_rows=max_rows,
    )
    assert_select_only(query)
    conn_str = build_connection_string(load_phc_config(session))
    return run_select(conn_str, query)
