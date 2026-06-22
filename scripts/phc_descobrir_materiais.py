"""Descoberta (SO-LEITURA) das tabelas de materiais/artigos no PHC.

Corre queries SELECT em INFORMATION_SCHEMA para identificar tabelas candidatas a
"materias-primas/artigos" (com colunas de referencia, descricao, familia e preco)
e lista as colunas das mais provaveis. Nao escreve nada no PHC.
"""

from __future__ import annotations

from app.db.session import SessionLocal
from app.services.phc_sql import build_connection_string, load_phc_config, run_select

QUERY_CANDIDATAS = """
SELECT c.TABLE_NAME AS Tabela,
       COUNT(*) AS N_Colunas,
       MAX(CASE WHEN c.COLUMN_NAME LIKE '%REF%' THEN 1 ELSE 0 END) AS Tem_Ref,
       MAX(CASE WHEN c.COLUMN_NAME LIKE '%DESIGN%' THEN 1 ELSE 0 END) AS Tem_Design,
       MAX(CASE WHEN c.COLUMN_NAME LIKE '%FAMILIA%' THEN 1 ELSE 0 END) AS Tem_Familia,
       MAX(CASE WHEN (c.COLUMN_NAME LIKE '%EPV%' OR c.COLUMN_NAME LIKE '%PVP%'
                      OR c.COLUMN_NAME LIKE '%PRECO%' OR c.COLUMN_NAME LIKE '%CUSTO%')
                THEN 1 ELSE 0 END) AS Tem_Preco
FROM INFORMATION_SCHEMA.COLUMNS c
GROUP BY c.TABLE_NAME
HAVING MAX(CASE WHEN c.COLUMN_NAME LIKE '%REF%' THEN 1 ELSE 0 END) = 1
   AND MAX(CASE WHEN c.COLUMN_NAME LIKE '%DESIGN%' THEN 1 ELSE 0 END) = 1
ORDER BY Tem_Preco DESC, Tem_Familia DESC, c.TABLE_NAME
""".strip()


def _colunas_de(conn_str: str, tabela: str) -> list[dict]:
    query = (
        "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME = '{tabela}' ORDER BY ORDINAL_POSITION"
    )
    return run_select(conn_str, query)


def main() -> None:
    with SessionLocal() as session:
        cfg = load_phc_config(session)
        conn_str = build_connection_string(cfg)

        print("=== Tabelas candidatas a materiais/artigos (tem REF + DESIGN) ===")
        candidatas = run_select(conn_str, QUERY_CANDIDATAS)
        for linha in candidatas:
            print(linha)

        nomes = [str(c.get("Tabela")) for c in candidatas[:3]]
        if "ST" not in nomes:
            nomes.append("ST")
        for tabela in nomes:
            print(f"\n=== Colunas de {tabela} ===")
            try:
                for col in _colunas_de(conn_str, tabela):
                    print(col)
            except Exception as exc:  # noqa: BLE001
                print(f"(nao foi possivel ler {tabela}: {exc})")


if __name__ == "__main__":
    main()
