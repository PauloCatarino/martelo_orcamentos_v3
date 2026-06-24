"""Leitura (so-leitura) das encomendas do PHC (tabelas BI/BO/BO2/CL)."""

from __future__ import annotations

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
