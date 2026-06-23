from app.db.session import SessionLocal
from app.services.phc_sql import build_connection_string, load_phc_config, run_select

q = (
    "SELECT TOP 8 ref AS Ref, forref AS ForRef, "
    "epv1 AS EPV1, epvultimo AS EPVUlt, epcusto AS EPCusto, "
    "marg1 AS Marg1, desci AS DescI, descii AS DescII, unidade AS Un, "
    "CONVERT(VARCHAR(10),datanovpv,104) AS d_novpv, "
    "CONVERT(VARCHAR(10),datar,104)     AS d_datar, "
    "CONVERT(VARCHAR(10),udata,104)     AS d_udata, "
    "CONVERT(VARCHAR(10),usrdata,104)   AS d_usrdata, "
    "CONVERT(VARCHAR(10),opendata,104)  AS d_opendata "
    "FROM ST WITH (NOLOCK) WHERE inactivo=0 AND familia='FM00000' AND epcusto>0 "
    "ORDER BY datar DESC"
)
with SessionLocal() as s:
    conn = build_connection_string(load_phc_config(s))
    rows = run_select(conn, q)
    for r in rows:
        print({k: r.get(k) for k in ["Ref","ForRef","EPV1","EPVUlt","EPCusto","Marg1","DescI","DescII","Un","d_novpv","d_datar","d_udata","d_usrdata","d_opendata"]})
