"""Confere o CSV da transferência de dados do iMos (lista de corte) contra a base do iMos.

Para cada peça cortada da obra, sobe a árvore ``IDBGRPS`` e sabe em que artigo principal
(coluna Artigo, antes RP) e em que artigo mais próximo (coluna SubArtigo = ``ARTNR``: o
sub-artigo, ou o próprio artigo quando a peça está diretamente nele) ela está. Depois soma
as quantidades por (Artigo, SubArtigo, descrição, material, comprimento, largura) e compara
com o CSV. Serve para:

- validar as colunas Artigo/SubArtigo do ``EXPORT_CSV_CUT_RITE_LE_V2.cfg``;
- apanhar peças de RPs diferentes juntadas numa só linha (o ``ACCUMULATE`` antigo fazia
  isso às peças de sub-artigos, por terem ``POSSTR`` vazio).

Só faz SELECT. Uso (a partir da pasta principal do Martelo, para apanhar o ``.env``):

    python scripts/imos_cfg/verificar_csv_subartigos.py APAGAR_14
    python scripts/imos_cfg/verificar_csv_subartigos.py 1172_01_26_INNERE caminho\\do.csv

Sem caminho, lê ``...\\Cutrite_Import_CSV\\<obra>_Lista_Corte.csv``. Aceita os cabeçalhos
antigos (``RP``; ``DIAG_ARTNR`` do ensaio de 29-10); um CSV sem SubArtigo (o do ``.cfg``
antigo) é conferido só pelo artigo.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

PASTA_CSV = Path(r"\\SERVER_LE\Homag_iX\Cutrite\Work\Cutrite_Import_CSV")
# O mesmo FILTER do .cfg: só peças cortadas, sem ferragens/uniões.
TIPOS_FORA = (11, 15, 16, 17, 18, 19, 20, 43, 44)


def _sql_texto(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def ler_base(orderid: str) -> tuple[list[dict], list[dict], list[dict]]:
    from app.db.session import SessionLocal
    from app.services import imos_sql

    with SessionLocal() as s:
        cfg = dict(imos_sql.load_imos_config(s))
    oid = _sql_texto(orderid)
    grps = imos_sql.run_imos_select(
        cfg, f"SELECT ID, TYP, ARTID, ASSID, NAME FROM IDBGRPS WHERE ORDERID={oid}")
    info = imos_sql.run_imos_select(
        cfg, f"SELECT ID, GROUPNAME FROM IDBINFO WHERE ORDERID={oid}")
    fora = ",".join(str(t) for t in TIPOS_FORA)
    pecas = imos_sql.run_imos_select(
        cfg,
        "SELECT ID, NAME1, MATID, MATNAME, CLENG, CWIDTH, CNT, PARTPOSSTR FROM IDBGPL "
        f"WHERE ORDERID={oid} AND (CUT_FLAG <> 0 OR CUT_FLAG IS NULL) AND TYP NOT IN ({fora})",
    )
    return grps, info, pecas


def sub_artigos(grps: list[dict], info: list[dict]):
    """Devolve f(id_peca) -> lista dos artigos acima da peça, do mais próximo ao de topo.

    Na ``IDBGRPS`` uma peça aponta para o grupo pai (``ASSID``); o primeiro grupo de um
    artigo aponta para o artigo (``ARTID``); um artigo (``TYP`` 2) dentro de outro aponta
    para o grupo onde está (``ASSID``).
    """
    g = {int(r["ID"]): r for r in grps}
    nome = {int(r["ID"]): (r["GROUPNAME"] or "").strip() for r in info}

    def acima(pid: int) -> list[str]:
        out, atual, vistos = [], g.get(pid), set()
        while atual is not None and int(atual["ID"]) not in vistos:
            vistos.add(int(atual["ID"]))
            typ, artid, assid = int(atual["TYP"]), int(atual["ARTID"] or 0), int(atual["ASSID"] or 0)
            if typ == 2:
                out.append(nome.get(int(atual["ID"])) or (atual["NAME"] or "").strip())
            atual = g.get(artid) if (typ == 3 and artid) else (g.get(assid) if assid else None)
        return out

    return acima


def _chave(rp, sub, desc, mat, comp, larg):
    return (rp.strip(), sub.strip(), desc.strip().lower(), mat.strip(),
            round(float(comp), 1), round(float(larg), 1))


def esperado(orderid: str) -> dict:
    grps, info, pecas = ler_base(orderid)
    acima = sub_artigos(grps, info)
    soma: dict = defaultdict(float)
    for p in pecas:
        arts = acima(int(p["ID"]))
        sub = arts[0] if arts else ""  # = ARTNR do .cfg: o artigo mais próximo da peça
        rp = (p["PARTPOSSTR"] or "").split(".")[0]  # = SPLITLEFT[PARTPOSSTR;.] do .cfg
        mat = (p["MATNAME"] or "").strip() or (p["MATID"] or "").strip()  # = REPLACE_EMPTY[MATNAME;MATID]
        soma[_chave(rp, sub, p["NAME1"] or "", mat, p["CLENG"] or 0, p["CWIDTH"] or 0)] += float(p["CNT"] or 0)
    return soma


def ler_csv(caminho: Path) -> tuple[dict, bool, list[dict]]:
    with caminho.open(encoding="latin1", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    col_art = next((c for c in ("Artigo", "RP") if linhas and c in linhas[0]), "Artigo")
    col_sub = next((c for c in ("SubArtigo", "DIAG_ARTNR") if linhas and c in linhas[0]), None)
    soma: dict = defaultdict(float)
    for r in linhas:
        r["Artigo"], r["SubArtigo"] = r.get(col_art) or "", (r.get(col_sub) or "") if col_sub else ""
        soma[_chave(r["Artigo"], r["SubArtigo"], r["Descricao"], r["Material"],
                    r["Comp."], r["Larg."])] += float(r["Qt."] or 0)
    return soma, col_sub is not None, linhas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("obra", help="nome da obra no iMos (PROADMIN.NAME), ex. APAGAR_14")
    ap.add_argument("csv", nargs="?", help="CSV a conferir (por defeito, o da pasta Cutrite_Import_CSV)")
    a = ap.parse_args()
    caminho = Path(a.csv) if a.csv else PASTA_CSV / f"{a.obra}_Lista_Corte.csv"
    if not caminho.is_file():
        print(f"CSV não encontrado: {caminho}")
        return 2

    base = esperado(a.obra)
    lido, tem_sub, linhas = ler_csv(caminho)

    print(f"CSV: {caminho}  ({len(linhas)} linhas)")
    subs = Counter((k[0], k[1]) for k, q in base.items() if k[1] and k[1] != k[0])
    print(f"Na base: {sum(q for k, q in base.items() if k[1] and k[1] != k[0]):.0f} peças em "
          f"sub-artigos ({len(subs)} pares Artigo/SubArtigo)")
    for (rp, sub), n in sorted(subs.items()):
        print(f"   {rp:<24} {sub}")

    if not tem_sub:  # .cfg antigo: compara só pelo artigo
        print("O CSV não tem a coluna SubArtigo: a conferir só pelo Artigo.")
        sem_sub: dict = defaultdict(float)
        for k, q in base.items():
            sem_sub[(k[0], "") + k[2:]] += q
        base = sem_sub

    difs = []
    for k in sorted(set(base) | set(lido)):
        qb, qc = base.get(k, 0.0), lido.get(k, 0.0)
        if abs(qb - qc) > 1e-6:
            difs.append((k, qb, qc))
    if not difs:
        print("\nOK: Artigo, SubArtigo e quantidades do CSV batem certo com a base.")
    else:
        print(f"\n{len(difs)} diferença(s)  [Artigo | SubArtigo | descrição | material | comp x larg]  base -> CSV")
        for (rp, sub, desc, mat, c, l), qb, qc in difs[:60]:
            print(f"   {rp} | {sub or '-'} | {desc} | {mat} | {c}x{l}   {qb:g} -> {qc:g}")
    return 0 if not difs else 1


if __name__ == "__main__":
    raise SystemExit(main())
