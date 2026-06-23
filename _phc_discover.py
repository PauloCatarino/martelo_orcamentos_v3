from app.db.session import SessionLocal
from app.services.phc_sql import build_connection_string, load_phc_config, run_select

q1 = (
    "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_NAME='ST' AND ("
    "COLUMN_NAME LIKE '%data%' OR COLUMN_NAME LIKE '%marg%' OR "
    "COLUMN_NAME LIKE '%desc%' OR COLUMN_NAME LIKE '%pcus%' OR "
    "COLUMN_NAME LIKE '%pvp%' OR COLUMN_NAME LIKE '%epv%' OR "
    "COLUMN_NAME LIKE '%prec%' OR COLUMN_NAME LIKE '%fabric%' OR "
    "COLUMN_NAME LIKE '%marca%' OR COLUMN_NAME LIKE 'u_%' ) "
    "ORDER BY COLUMN_NAME"
)
with SessionLocal() as s:
    conn = build_connection_string(load_phc_config(s))
    print("=== COLUNAS ST (data/marg/desc/preco/dims/fabricante) ===")
    for r in run_select(conn, q1):
        print(f"{r.get('COLUMN_NAME'):28} {r.get('DATA_TYPE')}")
