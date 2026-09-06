"""Consulta WoodStore/Homag. SQL fixo, exclusivamente SELECT; nunca escreve."""
from __future__ import annotations

import os
from sqlalchemy.orm import Session
from app.services.phc_sql import connection_value, run_select
from app.services.system_setting_service import SystemSettingService

# Agregar antes dos joins evita multiplicar stock pelas linhas de reserva.
# Lagen representa posições/camadas: manter a contagem usada na consulta de
# referência, distinguindo-a de pacotes e de uma promessa de stock utilizável.
STOCK_SQL = """SELECT
 LTRIM(RTRIM(i.Identnummer)) AS Referencia,
 i.Laenge AS Comprimento, i.Breite AS Largura, i.Dicke AS Espessura,
 i.Dekor AS Material, i.Materialcode AS Codigo,
 COALESCE(l.Quantidade,0) AS Quantidade,
 COALESCE(r.Reservadas,0) AS Reservadas,
 COALESCE(l.Quantidade,0)-COALESCE(r.Reservadas,0) AS Disponivel
 FROM dbo.Ident i
 LEFT JOIN (SELECT Identnummer,COUNT(*) AS Quantidade
            FROM dbo.Lagen GROUP BY Identnummer) l ON l.Identnummer=i.Identnummer
 LEFT JOIN (SELECT Identnummer,SUM(Menge) AS Reservadas
            FROM dbo.AAusReservierung GROUP BY Identnummer) r ON r.Identnummer=i.Identnummer
 ORDER BY i.Identnummer"""


def query_woodstore(session: Session) -> list[dict]:
    svc = SystemSettingService(session)
    def value(key, default=""):
        return (os.getenv("WOODSTORE_DB_" + key.upper()) or
                svc.obter_valor("woodstore_db_" + key, default) or default).strip()
    cfg = {k: value(k, v) for k, v in {
        "server": "10.101.50.1", "name": "lagerdb", "uid": "", "pwd": "",
    }.items()}
    if not cfg["uid"] or not cfg["pwd"]:
        raise RuntimeError("Configure a ligação WoodStore em Caminhos do Sistema (grupo WoodStore).")
    def quoted(k):
        return connection_value(cfg[k], k, origem="WoodStore")
    conn = (f"Server={quoted('server')};Database={quoted('name')};"
            f"User ID={quoted('uid')};Password={quoted('pwd')};"
            "ApplicationIntent=ReadOnly;Encrypt=False;TrustServerCertificate=True;Connection Timeout=8;")
    try:
        return run_select(conn, STOCK_SQL)
    except Exception as exc:
        # Não propagar a saída do processo: pode incluir a configuração.
        raise RuntimeError("WoodStore sem ligação ou consulta recusada. Verifique a rede e a configuração.") from None


def estado_stock(linha: dict) -> str:
    saldo = linha.get("Disponivel")
    if saldo is None:
        return "Por confirmar"
    if saldo < 0:
        return "Divergência nas reservas"
    return "Saldo positivo" if saldo > 0 else "Sem saldo disponível"
