"""Leitura (so-leitura) das materias-primas/artigos do PHC (tabela ST)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.phc_sql import build_connection_string, load_phc_config, run_select

FAMILIAS_MATERIAIS = ("FF00000", "FM00000", "FO00000")  # Ferragens, Madeiras, Orlas


def query_phc_materiais(session: Session) -> list[dict]:
    """Le os artigos de material (ativos) do PHC. SO-LEITURA (SELECT)."""
    familias = ", ".join(f"'{familia}'" for familia in FAMILIAS_MATERIAIS)
    query = (
        "SELECT ref AS Ref, design AS Descricao, familia AS Familia, "
        "faminome AS Familia_Nome, epcusto AS Preco_Custo, "
        "epvultimo AS Preco_Ultimo, "
        "forref AS Ref_Fornecedor, "
        "CONVERT(VARCHAR(10), udata, 104) AS Data_Preco, "
        "fornecedor AS Fornecedor, unidade AS Unidade, "
        "stock AS Stock, u_altura AS Altura, u_largura AS Largura, "
        "u_espess AS Espessura, obs AS Observacoes "
        "FROM ST WITH (NOLOCK) "
        f"WHERE inactivo = 0 AND familia IN ({familias}) "
        "ORDER BY familia, ref"
    )
    conn_str = build_connection_string(load_phc_config(session))
    return run_select(conn_str, query)
