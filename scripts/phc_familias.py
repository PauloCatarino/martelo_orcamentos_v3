"""Lista (so-leitura) as familias de artigos do PHC, com nome e contagem."""

from __future__ import annotations

from app.db.session import SessionLocal
from app.services.phc_sql import build_connection_string, load_phc_config, run_select

QUERY = (
    "SELECT familia AS Familia, MAX(faminome) AS Nome, COUNT(*) AS N "
    "FROM ST WITH (NOLOCK) WHERE inactivo = 0 "
    "GROUP BY familia ORDER BY N DESC"
)


def main() -> None:
    with SessionLocal() as session:
        conn_str = build_connection_string(load_phc_config(session))
        for linha in run_select(conn_str, QUERY):
            print(linha)


if __name__ == "__main__":
    main()
