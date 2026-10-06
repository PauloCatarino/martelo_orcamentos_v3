"""Copia para a imos_LE (base oficial) só o que o Output batch DV_Roupeiros usa.

Pedido do Paulo (06-10-2026), no fim da etapa dos roupeiros: passar para a imos_LE o batch
DV_Roupeiros e tudo aquilo de que ele precisa, e NADA do DV_Desenhos_Obra (nem DV_Planta,
DV_Alcado, DV_Alcado_Frentes, DV_Corte_Lateral, as etiquetas de obra, a tabela, a moldura
DV_A3_Obra).

Copia as linhas TAL COMO ESTÃO na imos_LE_TESTES (com as afinações que o Paulo fez no Element
Manager), não as regera a partir do configurar_dv.py. O conjunto sai do próprio batch:
- o batch DV_Roupeiros (CMSOUTPUTBATCH + CMSOUTPUTITEM);
- a moldura e as regras que o JSON da saída "Drawing views" nomeia (layout, cotagem, etiquetas);
- o corte lateral dos roupeiros (DV_Roup_Corte_Lateral: não está no batch, usa-se à mão);
- as condições que essas regras usam;
- cada elemento na pasta DV_Desenhos da sua árvore (cria-a se não existir).

Segurança: o SQL corre numa transação, com THROW se a base não for a imos_LE, e só apaga e
escreve linhas com estes nomes exatos (todos DV_*). As condições levam um CONDITIONID novo (é
uma identidade). Os blocos (I:\\Library\\AttDWG), os estilos (imosBlocks.dwg / IMOS.dwt) e as
etiquetas das vistas (config\\DrawingFlags) são ficheiros: não passam por aqui.

Uso (a partir da pasta principal do Martelo, por causa do .env):
    python scripts/imos_drawing_views/publicar_roupeiros.py           # mostra o conjunto e o SQL
    python scripts/imos_drawing_views/publicar_roupeiros.py --aplicar # escreve na imos_LE
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from configurar_dv import _PS, BASE_TESTES, PASTA, lit, lista, _so_dv  # noqa: E402

BASE_OFICIAL = "imos_LE"
BATCH = "DV_Roupeiros"
EXTRA_CORTE = ["DV_Roup_Corte_Lateral"]
T = f"{BASE_TESTES}.dbo"

# (tabela principal, tabelas filhas com NAME, pasta, tipo do nó)
COTAGEM = {"DIMPLAN": 486, "DIMELEV": 487, "DIMSECTSIDE": 494}


def _cfg(base: str) -> dict:
    from app.db.session import SessionLocal
    from app.services import imos_sql

    with SessionLocal() as s:
        cfg = dict(imos_sql.load_imos_config(s))
    cfg["database"] = base
    return cfg


def _select(cfg: dict, sql: str) -> list[dict]:
    from app.services import imos_sql

    return imos_sql.run_imos_select(cfg, sql)


def conjunto(cfg_t: dict) -> dict:
    """Lê na TESTES o que o batch usa."""
    item = _select(cfg_t, f"SELECT PARAM_3 FROM dbo.CMSOUTPUTITEM WHERE BATCHNAME = {lit(BATCH)}")
    if len(item) != 1:
        raise SystemExit(f"Esperava 1 saída no batch {BATCH} da {BASE_TESTES}, há {len(item)}.")
    d = json.loads(item[0]["PARAM_3"])["submittaldrawingdefinition"]
    vp, va = d["planview"], d["elevation"]
    c = {
        "molduras": sorted({vp["layout"], va["layout"]}),
        "DIMPLAN": [vp["dimensioning"]],
        "DIMELEV": [va["dimensioning"]],
        "DIMSECTSIDE": EXTRA_CORTE,
        "LABELLING": sorted({vp["annotation"], va["annotation"]}),
    }
    conds = set()
    for pref in COTAGEM:
        for r in _select(cfg_t, f"SELECT DISTINCT CONDITION FROM dbo.{pref}LINES WHERE NAME IN ({lista(c[pref])})"):
            conds.add(r["CONDITION"])
    for r in _select(cfg_t, f"SELECT DISTINCT CONDITION FROM dbo.LABELLING WHERE NAME IN ({lista(c['LABELLING'])})"):
        conds.add(r["CONDITION"])
    c["condicoes"] = sorted(x for x in conds if x)
    for k in ("molduras", "DIMPLAN", "DIMELEV", "DIMSECTSIDE", "LABELLING", "condicoes"):
        _so_dv(c[k])
    return c


def colunas(cfg_t: dict, cfg_o: dict, tabelas: list[str]) -> dict[str, list[str]]:
    """Colunas copiáveis (sem identidades nem calculadas), iguais nas duas bases."""
    q = ("SELECT t.name tab, c.name col FROM sys.columns c JOIN sys.tables t ON t.object_id = c.object_id "
         f"WHERE t.name IN ({lista(tabelas)}) AND c.is_identity = 0 AND c.is_computed = 0 "
         "AND TYPE_NAME(c.system_type_id) <> 'timestamp' ORDER BY t.name, c.column_id")
    out: dict[str, list[str]] = {}
    for nome, cfg in (("t", cfg_t), ("o", cfg_o)):
        m: dict[str, list[str]] = {}
        for r in _select(cfg, q):
            m.setdefault(r["tab"], []).append(r["col"])
        out[nome] = m
    for t in tabelas:
        if out["t"].get(t) != out["o"].get(t):
            raise SystemExit(f"A tabela {t} tem colunas diferentes nas duas bases: não copio.")
    return out["t"]


def _pasta(tabela: str) -> list[str]:
    return [
        f"SELECT @raiz = MIN(DIR_ID) FROM dbo.{tabela} WHERE PARENT_ID = 0;",
        f"IF NOT EXISTS (SELECT 1 FROM dbo.{tabela} WHERE NAME = {lit(PASTA)} AND TYPE = 1000001 AND PARENT_ID = @raiz)",
        f"    INSERT INTO dbo.{tabela} (NAME, TYPE, PARENT_ID) VALUES ({lit(PASTA)}, 1000001, @raiz);",
        f"SELECT @pasta = MIN(DIR_ID) FROM dbo.{tabela} WHERE NAME = {lit(PASTA)} AND TYPE = 1000001 AND PARENT_ID = @raiz;",
    ]


def _copia(cols: dict, tabela: str, chave: str, nomes: list[str], extra: str = "") -> list[str]:
    cs = ", ".join(f"[{c}]" for c in cols[tabela])
    onde = f"[{chave}] IN ({lista(nomes)}){extra}"
    return [f"DELETE FROM dbo.{tabela} WHERE {onde};",
            f"INSERT INTO dbo.{tabela} ({cs}) SELECT {cs} FROM {T}.{tabela} WHERE {onde};"]


def _pastas(tabela: str, tipo: int, nomes: list[str]) -> list[str]:
    s = [f"DELETE FROM dbo.{tabela} WHERE NAME IN ({lista(nomes)}) AND TYPE = {tipo};", *_pasta(tabela)]
    s += [f"INSERT INTO dbo.{tabela} (NAME, TYPE, PARENT_ID) VALUES ({lit(n)}, {tipo}, @pasta);" for n in nomes]
    return s


def gerar_sql(c: dict, cols: dict) -> str:
    s: list[str] = []
    # condições: CONDITIONID novo (identidade) e os termos copiados com ele
    s.append("-- condições")
    nomes = c["condicoes"]
    s += [
        f"INSERT INTO @ids SELECT CONDITIONID FROM dbo.CONDITIONSPRINCIPLE WHERE NAME IN ({lista(nomes)});",
        "DELETE FROM dbo.CONDITIONSCOMPARISONS WHERE CONDITIONID IN (SELECT id FROM @ids);",
        "DELETE FROM dbo.CONDITIONSOPERATIONS WHERE CONDITIONID IN (SELECT id FROM @ids);",
        "DELETE FROM dbo.CONDITIONS WHERE CONDITIONID IN (SELECT id FROM @ids);",
        f"DELETE FROM dbo.CONDITIONSPRINCIPLEDECLARATIONS WHERE NAME IN ({lista(nomes)});",
        f"DELETE FROM dbo.CONDITIONSPRINCIPLE WHERE NAME IN ({lista(nomes)});",
    ]
    sem_id = lambda t: [x for x in cols[t] if x != "CONDITIONID"]  # noqa: E731
    for n in nomes:
        cc = ", ".join(f"[{x}]" for x in cols["CONDITIONS"])
        s += [
            "SET @velho = NULL;",
            f"SELECT @velho = CONDITIONID FROM {T}.CONDITIONSPRINCIPLE WHERE NAME = {lit(n)};",
            f"IF @velho IS NULL THROW 50002, N'Falta a condicao {n} na {BASE_TESTES}.', 1;",
            f"INSERT INTO dbo.CONDITIONS ({cc}) SELECT {cc} FROM {T}.CONDITIONS WHERE CONDITIONID = @velho;",
            "SET @cid = CAST(SCOPE_IDENTITY() AS int);",
        ]
        for t in ("CONDITIONSOPERATIONS", "CONDITIONSCOMPARISONS", "CONDITIONSPRINCIPLE"):
            resto = sem_id(t)
            cs = ", ".join(f"[{x}]" for x in resto)
            s.append(f"INSERT INTO dbo.{t} ([CONDITIONID], {cs}) SELECT @cid, {cs} FROM {T}.{t} "
                     + (f"WHERE NAME = {lit(n)};" if t == "CONDITIONSPRINCIPLE" else "WHERE CONDITIONID = @velho;"))
        dc = ", ".join(f"[{x}]" for x in cols["CONDITIONSPRINCIPLEDECLARATIONS"])
        s.append(f"INSERT INTO dbo.CONDITIONSPRINCIPLEDECLARATIONS ({dc}) SELECT {dc} "
                 f"FROM {T}.CONDITIONSPRINCIPLEDECLARATIONS WHERE NAME = {lit(n)};")
    s += _pastas("CONDITIONSPRINCIPLEFOLDER", 309, nomes)
    # cotagem: principal, linhas e atributos
    for pref, tipo in COTAGEM.items():
        s.append(f"-- cotagem {pref}")
        for t in (f"{pref}ATT", f"{pref}LINES", pref):
            s.append(f"DELETE FROM dbo.{t} WHERE NAME IN ({lista(c[pref])});")
        for t in (pref, f"{pref}LINES", f"{pref}ATT"):
            s.append(_copia(cols, t, "NAME", c[pref])[1])
        s += _pastas(f"{pref}FOLDER", tipo, c[pref])
    # etiquetas
    s.append("-- etiquetas")
    s.append(f"DELETE FROM dbo.LABELLING WHERE NAME IN ({lista(c['LABELLING'])});")
    s += _copia(cols, "LABELLINGPRIM", "NAME", c["LABELLING"])
    s.append(_copia(cols, "LABELLING", "NAME", c["LABELLING"])[1])
    s += _pastas("LABELLINGFOLDER", 469, c["LABELLING"])
    # moldura (o DWT vai no BINDATA)
    s.append("-- moldura")
    s += _copia(cols, "BINDATA", "NAME", c["molduras"], " AND [INTERNTYPE] = N'LAYDWT'")
    s += _copia(cols, "DOCMANBORDERPRINCIPLE", "NAME", c["molduras"])
    s += _pastas("DOCMANBORDERPRINCIPLEFOLDER", 480, c["molduras"])
    # batch
    s.append("-- output batch")
    s.append(f"DELETE FROM dbo.CMSOUTPUTITEM WHERE BATCHNAME = {lit(BATCH)};")
    s += _copia(cols, "CMSOUTPUTBATCH", "NAME", [BATCH])
    s.append(_copia(cols, "CMSOUTPUTITEM", "BATCHNAME", [BATCH])[1])
    s += _pastas("CMSOUTPUTBATCHFOLDER", 472, [BATCH])
    return "\n".join([
        "SET XACT_ABORT ON;",
        f"IF DB_NAME() <> {lit(BASE_OFICIAL)} THROW 50001, N'Recusado: este SQL so corre na {BASE_OFICIAL}.', 1;",
        "DECLARE @ids TABLE (id int);",
        "DECLARE @cid int, @velho int, @raiz int, @pasta int;",
        "BEGIN TRANSACTION;",
        *s,
        "COMMIT TRANSACTION;",
    ]) + "\n"


TABELAS = (["CONDITIONS", "CONDITIONSOPERATIONS", "CONDITIONSCOMPARISONS", "CONDITIONSPRINCIPLE",
            "CONDITIONSPRINCIPLEDECLARATIONS", "LABELLINGPRIM", "LABELLING", "BINDATA",
            "DOCMANBORDERPRINCIPLE", "CMSOUTPUTBATCH", "CMSOUTPUTITEM"]
           + [f"{p}{s}" for p in COTAGEM for s in ("", "LINES", "ATT")])


def aplicar(sql: str) -> None:
    from app.services import imos_escrita

    conn = imos_escrita.build_connection_string(_cfg(BASE_OFICIAL))
    with tempfile.TemporaryDirectory() as tmp:
        sqlfile = Path(tmp) / "dv_oficial.sql"
        sqlfile.write_text(sql, encoding="utf-8")
        ps1 = Path(tmp) / "dv.ps1"
        ps1.write_text(_PS, encoding="utf-8")
        payload = base64.b64encode(json.dumps({"conn": conn, "sqlfile": str(sqlfile)}).encode()).decode()
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(ps1), payload],
            capture_output=True, text=True, timeout=240,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
    if r.returncode != 0 or "OK" not in r.stdout:
        raise SystemExit("Falhou (nada foi gravado; a transação é desfeita):\n" + (r.stderr or r.stdout).strip())
    print(f"DV_Roupeiros copiado para a {BASE_OFICIAL}.")


def conferir(c: dict) -> None:
    """Conta as linhas de cada elemento nas duas bases."""
    cfg_t, cfg_o = _cfg(BASE_TESTES), _cfg(BASE_OFICIAL)
    pares = [("CMSOUTPUTBATCH", "NAME", [BATCH]), ("CMSOUTPUTITEM", "BATCHNAME", [BATCH]),
             ("BINDATA", "NAME", c["molduras"]), ("DOCMANBORDERPRINCIPLE", "NAME", c["molduras"]),
             ("LABELLINGPRIM", "NAME", c["LABELLING"]), ("LABELLING", "NAME", c["LABELLING"]),
             ("CONDITIONSPRINCIPLE", "NAME", c["condicoes"])]
    for pref in COTAGEM:
        pares += [(f"{pref}{s}", "NAME", c[pref]) for s in ("", "LINES", "ATT")]
    tudo_igual = True
    for t, k, nomes in pares:
        q = f"SELECT COUNT(*) n FROM dbo.{t} WHERE [{k}] IN ({lista(nomes)})"
        a, b = _select(cfg_t, q)[0]["n"], _select(cfg_o, q)[0]["n"]
        tudo_igual &= a == b
        print(f"  {t:<32} testes {a:>3}   oficial {b:>3}" + ("" if a == b else "   <-- DIFERENTE"))
    print("Tudo igual." if tudo_igual else "HÁ DIFERENÇAS.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--aplicar", action="store_true", help=f"escreve o DV_Roupeiros na {BASE_OFICIAL}")
    ap.add_argument("--conferir", action="store_true", help="compara as contagens nas duas bases")
    a = ap.parse_args()
    cfg_t = _cfg(BASE_TESTES)
    c = conjunto(cfg_t)
    print(json.dumps(c, indent=1, ensure_ascii=False))
    if a.conferir:
        conferir(c)
        return
    cols = colunas(cfg_t, _cfg(BASE_OFICIAL), TABELAS)
    sql = gerar_sql(c, cols)
    if not a.aplicar:
        print(sql)
        return
    aplicar(sql)
    conferir(c)


if __name__ == "__main__":
    main()
