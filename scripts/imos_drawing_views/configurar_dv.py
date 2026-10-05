"""Configuração DV_* das Drawing Views do iMos: condições, cotas de planta e alçado, etiquetas.

Escreve SÓ na base de testes ``imos_LE_TESTES`` e SÓ linhas cujo nome começa por ``DV_``
(autorização do Paulo, 05-10-2026). Os princípios que já existiam nunca são tocados. Cada
corrida apaga as ``DV_*`` desta lista e volta a escrevê-las, tudo numa só transação.

Uso (a partir da pasta principal do Martelo, para apanhar o ``.env``):

    python scripts/imos_drawing_views/configurar_dv.py            # mostra o SQL, não escreve
    python scripts/imos_drawing_views/configurar_dv.py --aplicar  # escreve na imos_LE_TESTES
    python scripts/imos_drawing_views/configurar_dv.py --ver      # lê o que lá está (SELECT)

Depois de aplicar: no Element Manager, carregar em "Atualizar" (⟳) para ver a pasta
``DV_Desenhos`` nas Condições, Cotagem de planta/alçado e Anotação.

Códigos (confirmados na base e em ``iX CAD 2025\\BIN\\MSG\\imos.msg``):
- tipos de cota: 1950 Furniture, 1951 Work surfaces, 1952 Wall, 1954 Height,
  1955 Front heights, 1960 Front widths;
- atributos: 1956 Depth dim (1=sim), 1957 Dimension cutout, 1958 Position of width
  dimensions (1=em baixo, 0=em cima), 1959 Separate worktop height, 2057 Dimension height;
- condições: CONDTYPE 10250 = artigo (group), 10300 = peça (part); operação 0=E, 2=OU;
- anotação: OBJECTTYPE 3 = artigo, 1 = peça; posição -1/0/1; FUNCT 0 = Standard.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

BASE_TESTES = "imos_LE_TESTES"
PASTA = "DV_Desenhos"
SOURCE = "IMOSADMIN"

E, OU = 0, 2
ARTIGO, PECA = 10250, 10300

BLUE, MAG, RED, BLACK, GREEN = (
    "IMOS_VIEW_BLUE", "IMOS_VIEW_MAG", "IMOS_VIEW_RED", "IMOS_VIEW_BLACK", "IMOS_VIEW_GREEN")

# ----------------------------------------------------------------------------- condições

@dataclass
class Cond:
    nome: str
    tipo: int
    comentario: str
    op: int
    termos: list  # (campo, comparação, valor, tipo_dado) ou ("E"/"OU", [termos])


MODULO = [
    ("group type", "=", "article", "CI"),
    ("group superior article", "=", "0", "ID"),
    ("group width", ">", "15", "FL"),
    ("group is deco article", "=", "no", "BO"),
    ("group is purchased", "=", "no", "BO"),
    ("group is installation object", "=", "no", "BO"),
    ("group name", "!B", "RDP", "CI"),  # rodapés: sem cotas nem etiqueta própria
]
FRENTES = [("part type", "=", v, "CI")
           for v in ("door", "door left", "door right", "door sliding folding", "drawer front")]

CONDICOES = [
    Cond("DV_Art_Inferiores", ARTIGO, "Modulos do chao (Z<=250, altura<=1250), sem rodapes", E,
         MODULO + [("group insertionZ", "<=", "250", "FL"), ("group height", "<=", "1250", "FL")]),
    Cond("DV_Art_Colunas", ARTIGO, "Colunas (Z<250, altura>1250)", E,
         MODULO + [("group insertionZ", "<", "250", "FL"), ("group height", ">", "1250", "FL")]),
    Cond("DV_Art_Nichos", ARTIGO, "Modulos intermedios (250<Z<=1280)", E,
         MODULO + [("group insertionZ", ">", "250", "FL"), ("group insertionZ", "<=", "1280", "FL")]),
    Cond("DV_Art_Superiores", ARTIGO, "Modulos suspensos (Z>1280)", E,
         MODULO + [("group insertionZ", ">", "1280", "FL")]),
    Cond("DV_Art_Alturas", ARTIGO, "Modulos para a cadeia de alturas (sem rodapes)", E,
         MODULO + [("group depth", ">", "1", "FL")]),
    Cond("DV_Art_Todos", ARTIGO, "Todos os modulos (sem rodapes, deco, comprados)", E, MODULO),
    Cond("DV_Frentes", PECA, "Portas e frentes de gaveta", OU, FRENTES),
    Cond("DV_Frentes_Baixo", PECA, "Portas e frentes de gaveta abaixo de 1280", E,
         [("part insertionZ", "<", "1280", "FL"), ("OU", FRENTES)]),
    Cond("DV_Frentes_Cima", PECA, "Portas e frentes de gaveta a partir de 1280", E,
         [("part insertionZ", ">=", "1280", "FL"), ("OU", FRENTES)]),
    Cond("DV_Tampos", PECA, "Tampos", E, [("part type", "=", "work surface", "CI")]),
]

# ----------------------------------------------------------------------------- cotagem

@dataclass
class Linha:
    tipo: int
    condicao: str
    estilo: str
    descricao: str
    atributos: dict = field(default_factory=dict)


@dataclass
class Cotagem:
    nome: str
    descricao: str
    dist_primeira: float
    dist_outras: float
    altura_papel: bool
    linhas: list


ALCADO_BASE = [
    Linha(1950, "DV_Art_Inferiores", BLUE, "Inferiores (larguras em baixo)", {1958: "1"}),
    Linha(1950, "DV_Art_Colunas", RED, "Colunas (larguras em baixo)", {1958: "1"}),
    Linha(1950, "DV_Art_Nichos", BLACK, "Intermedios (larguras em cima)", {1958: "0"}),
    Linha(1950, "DV_Art_Superiores", MAG, "Superiores (larguras em cima)", {1958: "0"}),
    Linha(1954, "DV_Art_Alturas", BLACK, "Alturas (uma so cadeia)", {1959: "1"}),
    Linha(1952, "", GREEN, "Paredes (largura e altura)", {1958: "1", 2057: "1"}),
]
# Testado a 05-10: o DV_Alcado sai limpo (uma cadeia de alturas 880/620/810 + 2310). O
# DV_Alcado_Frentes acrescenta cadeias com as folgas das frentes (1,8 / 3,5 mm) e linhas de
# chamada a atravessar o alçado: fica como opção; as medidas das portas vão nas etiquetas.
ALCADO = [
    Cotagem("DV_Alcado", "Alcado A3: larguras por fiada, uma cadeia de alturas, paredes",
            150, 150, False, ALCADO_BASE),
    Cotagem("DV_Alcado_Frentes", "Alcado A3 + cadeias das frentes (carregado: folgas incluidas)",
            150, 150, False, ALCADO_BASE + [
                Linha(1960, "DV_Frentes_Baixo", BLACK, "Frentes de baixo (larguras)", {1958: "1"}),
                Linha(1960, "DV_Frentes_Cima", BLACK, "Frentes de cima (larguras)", {1958: "0"}),
                Linha(1955, "DV_Frentes", BLACK, "Frentes (alturas)"),
            ]),
]
# Planta, testado a 05-10 na ORC_260881_2604023: com a "Depth dim" (1956) das linhas Furniture
# a profundidade cai por cima do desenho; com linhas "Furniture depth" (1962, 1963=1) vai para
# longe, com linhas de chamada a atravessar a planta. Fica sem profundidades: vão na tabela.
PLANTA = [
    Cotagem("DV_Planta", "Planta A3: inferiores, colunas, tampos, superiores, paredes",
            250, 200, False, [
                Linha(1950, "DV_Art_Inferiores", BLUE, "Inferiores", {1956: "0"}),
                Linha(1950, "DV_Art_Colunas", RED, "Colunas", {1956: "0"}),
                Linha(1951, "DV_Tampos", BLACK, "Tampos", {1956: "0", 1957: "0"}),
                Linha(1950, "DV_Art_Nichos", BLACK, "Intermedios", {1956: "0"}),
                Linha(1950, "DV_Art_Superiores", MAG, "Superiores", {1956: "0"}),
                Linha(1952, "", GREEN, "Paredes"),
            ]),
]

# ----------------------------------------------------------------------------- etiquetas

@dataclass
class Etiqueta:
    objeto: int          # 3 artigo, 1 peça
    condicao: str
    posicao: tuple       # ponto do objeto (-1/0/1, -1/0/1)
    referencia: tuple    # ponto do bloco
    desvio: tuple        # mm do modelo
    bloco: str
    descricao: str


@dataclass
class Anotacao:
    nome: str
    descricao: str
    linhas: list


# Blocos em I:\Library\AttDWG, feitos pelo criar_blocos_etiqueta.ps1. O iMos insere-os a escala
# 1 no modelo, por isso vão desenhados em mm do modelo para 1:20 e NÃO são anotativos (os
# DV_Artigo_Medidas / DV_Frente_Medidas da 1.ª volta eram anotativos e saíam minúsculos).
BLOCO_MODULO = "DV_Etq_Modulo"   # nome + L x A x P, enquadrado
BLOCO_NOME = "DV_Etq_Nome"       # só o nome, enquadrado (planta: as medidas vão na tabela)
BLOCO_FRENTE = "DV_Etq_Frente"   # L x A da porta / frente de gaveta

ETQ_MODULO_ALCADO = Etiqueta(3, "DV_Art_Todos", (0, 1), (0, 1), (0, -40), BLOCO_MODULO,
                             "Modulos: nome + L x A x P (no topo do modulo)")
ANOTACAO = [
    Anotacao("DV_Alcado_Etiquetas", "Alcado: nome e medidas do modulo + medidas das frentes", [
        ETQ_MODULO_ALCADO,
        Etiqueta(1, "DV_Frentes", (0, 0), (0, 0), (0, 0), BLOCO_FRENTE,
                 "Portas e gavetas: L x A (ao centro)"),
    ]),
    Anotacao("DV_Alcado_Etiquetas_Modulos", "Alcado: so nome e medidas do modulo",
             [ETQ_MODULO_ALCADO]),
    Anotacao("DV_Planta_Etiquetas", "Planta: nome do modulo (as medidas vao na tabela)", [
        Etiqueta(3, "DV_Art_Inferiores", (0, 0), (0, 0), (0, 0), BLOCO_NOME, "Inferiores (ao centro)"),
        Etiqueta(3, "DV_Art_Colunas", (0, 0), (0, 0), (0, 0), BLOCO_NOME, "Colunas (ao centro)"),
        Etiqueta(3, "DV_Art_Nichos", (0, 0), (0, 0), (0, 0), BLOCO_NOME, "Intermedios (ao centro)"),
        Etiqueta(3, "DV_Art_Superiores", (0, 1), (0, 1), (0, -30), BLOCO_NOME,
                 "Superiores (junto a parede)"),
    ]),
]

# ----------------------------------------------------------------------------- SQL


def lit(valor) -> str:
    """Literal T-SQL. Os valores são todos constantes deste ficheiro (nada vem de fora)."""
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, (int, float)):
        return repr(valor)
    return "N'" + str(valor).replace("'", "''") + "'"


def lista(nomes) -> str:
    return ", ".join(lit(n) for n in nomes)


def _so_dv(nomes):
    for n in nomes:
        if not n.startswith("DV_"):
            raise ValueError(f"Nome fora do prefixo DV_: {n}")
    return nomes


def _pasta(tabela: str) -> list[str]:
    """Garante a pasta DV_Desenhos debaixo da raiz da árvore e deixa o DIR_ID em @pasta."""
    return [
        f"SELECT @raiz = MIN(DIR_ID) FROM dbo.{tabela} WHERE PARENT_ID = 0;",
        f"IF NOT EXISTS (SELECT 1 FROM dbo.{tabela} WHERE NAME = {lit(PASTA)} AND TYPE = 1000001 AND PARENT_ID = @raiz)",
        f"    INSERT INTO dbo.{tabela} (NAME, TYPE, PARENT_ID) VALUES ({lit(PASTA)}, 1000001, @raiz);",
        f"SELECT @pasta = MIN(DIR_ID) FROM dbo.{tabela} WHERE NAME = {lit(PASTA)} AND TYPE = 1000001 AND PARENT_ID = @raiz;",
    ]


def _termos(termos, pai: int, proximo: list[int], out: list[str]) -> None:
    for t in termos:
        num = proximo[0]
        proximo[0] += 1
        if t[0] in ("E", "OU"):
            out.append("INSERT INTO dbo.CONDITIONSOPERATIONS (CONDITIONID, TERMNUM, PARENTTERMNUM, OPERATIONTYPE) "
                       f"VALUES (@cid, {num}, {pai}, {E if t[0] == 'E' else OU});")
            _termos(t[1], num, proximo, out)
        else:
            campo, comp, valor, dado = t
            out.append("INSERT INTO dbo.CONDITIONSCOMPARISONS (CONDITIONID, TERMNUM, PARENTTERMNUM, LEFTVALUE, "
                       f"COMPARISONTYPE, RIGHTVALUE, DATATYPE) VALUES (@cid, {num}, {pai}, {lit(campo)}, "
                       f"{lit(comp)}, {lit(valor)}, {lit(dado)});")


def sql_condicoes() -> list[str]:
    nomes = _so_dv([c.nome for c in CONDICOES])
    s = ["-- condições"]
    s += [
        "DELETE FROM @ids;",
        f"INSERT INTO @ids SELECT CONDITIONID FROM dbo.CONDITIONSPRINCIPLE WHERE NAME IN ({lista(nomes)});",
        "DELETE FROM dbo.CONDITIONSCOMPARISONS WHERE CONDITIONID IN (SELECT id FROM @ids);",
        "DELETE FROM dbo.CONDITIONSOPERATIONS WHERE CONDITIONID IN (SELECT id FROM @ids);",
        "DELETE FROM dbo.CONDITIONS WHERE CONDITIONID IN (SELECT id FROM @ids);",
        f"DELETE FROM dbo.CONDITIONSPRINCIPLEDECLARATIONS WHERE NAME IN ({lista(nomes)});",
        f"DELETE FROM dbo.CONDITIONSPRINCIPLE WHERE NAME IN ({lista(nomes)});",
        f"DELETE FROM dbo.CONDITIONSPRINCIPLEFOLDER WHERE NAME IN ({lista(nomes)}) AND TYPE = 309;",
    ]
    s += _pasta("CONDITIONSPRINCIPLEFOLDER")
    for c in CONDICOES:
        s.append(f"-- {c.nome}")
        s.append("INSERT INTO dbo.CONDITIONS (COMMENT, ROOTTERMNUM) VALUES (N'', 1);")
        s.append("SET @cid = CAST(SCOPE_IDENTITY() AS int);")
        s.append("INSERT INTO dbo.CONDITIONSOPERATIONS (CONDITIONID, TERMNUM, PARENTTERMNUM, OPERATIONTYPE) "
                 f"VALUES (@cid, 1, 0, {c.op});")
        _termos(c.termos, 1, [2], s)
        s.append("INSERT INTO dbo.CONDITIONSPRINCIPLE (NAME, CONDTYPE, CONDITIONID, COMMENT, INORDER, SOURCE, PRODUCER, SYS) "
                 f"VALUES ({lit(c.nome)}, {c.tipo}, @cid, {lit(c.comentario)}, N'', {lit(SOURCE)}, N'', 0);")
        s.append(f"INSERT INTO dbo.CONDITIONSPRINCIPLEFOLDER (NAME, TYPE, PARENT_ID) VALUES ({lit(c.nome)}, 309, @pasta);")
    return s


def sql_cotagem(prefixo: str, tipo_no: int, principios: list[Cotagem]) -> list[str]:
    nomes = _so_dv([p.nome for p in principios])
    s = [f"-- cotagem {prefixo}"]
    s += [
        f"DELETE FROM dbo.{prefixo}ATT WHERE NAME IN ({lista(nomes)});",
        f"DELETE FROM dbo.{prefixo}LINES WHERE NAME IN ({lista(nomes)});",
        f"DELETE FROM dbo.{prefixo} WHERE NAME IN ({lista(nomes)});",
        f"DELETE FROM dbo.{prefixo}FOLDER WHERE NAME IN ({lista(nomes)}) AND TYPE = {tipo_no};",
    ]
    s += _pasta(f"{prefixo}FOLDER")
    for p in principios:
        s.append(f"INSERT INTO dbo.{prefixo} (NAME, DESCRIPTION, DIST_FIRST, DIST_OTHER, USEPAPERHEIGHT, SOURCE, PRODUCER, SYS) "
                 f"VALUES ({lit(p.nome)}, {lit(p.descricao)}, {lit(p.dist_primeira)}, {lit(p.dist_outras)}, "
                 f"{lit(p.altura_papel)}, {lit(SOURCE)}, N'', 0);")
        for i, ln in enumerate(p.linhas, start=1):
            s.append(f"INSERT INTO dbo.{prefixo}LINES (NAME, LINENUMBER, DIMTYPE, CONDITION, CAD_DIMSTYLE, DESCRIPTION) "
                     f"VALUES ({lit(p.nome)}, {i}, {ln.tipo}, {lit(ln.condicao)}, {lit(ln.estilo)}, {lit(ln.descricao)});")
            for num, valor in ln.atributos.items():
                s.append(f"INSERT INTO dbo.{prefixo}ATT (NAME, LINENUMBER, ATTRIBUTE_NUM, VALUE) "
                         f"VALUES ({lit(p.nome)}, {i}, {num}, {lit(valor)});")
        s.append(f"INSERT INTO dbo.{prefixo}FOLDER (NAME, TYPE, PARENT_ID) VALUES ({lit(p.nome)}, {tipo_no}, @pasta);")
    return s


def sql_anotacao() -> list[str]:
    nomes = _so_dv([a.nome for a in ANOTACAO])
    s = ["-- anotação"]
    s += [
        f"DELETE FROM dbo.LABELLING WHERE NAME IN ({lista(nomes)});",
        f"DELETE FROM dbo.LABELLINGPRIM WHERE NAME IN ({lista(nomes)});",
        f"DELETE FROM dbo.LABELLINGFOLDER WHERE NAME IN ({lista(nomes)}) AND TYPE = 469;",
    ]
    s += _pasta("LABELLINGFOLDER")
    for a in ANOTACAO:
        s.append("INSERT INTO dbo.LABELLINGPRIM (NAME, DESCRIPTION, SOURCE, PRODUCER, SYS, PICTURE) "
                 f"VALUES ({lit(a.nome)}, {lit(a.descricao)}, {lit(SOURCE)}, N'', 0, N'');")
        for i, e in enumerate(a.linhas, start=1):
            s.append("INSERT INTO dbo.LABELLING (NAME, OBJECTTYPE, CONDITION, POS_X, POS_Y, REF_X, REF_Y, OFF_X, SOFF_X, "
                     "OFF_Y, SOFF_Y, BLOCKNAME, DESCRIPTION, SOURCE, PRODUCER, SYS, NR, FUNCT) VALUES ("
                     f"{lit(a.nome)}, {e.objeto}, {lit(e.condicao)}, {e.posicao[0]}, {e.posicao[1]}, "
                     f"{e.referencia[0]}, {e.referencia[1]}, {lit(float(e.desvio[0]))}, N'', {lit(float(e.desvio[1]))}, N'', "
                     f"{lit(e.bloco)}, {lit(e.descricao)}, {lit(SOURCE)}, N'', 0, {i}, 0);")
        s.append(f"INSERT INTO dbo.LABELLINGFOLDER (NAME, TYPE, PARENT_ID) VALUES ({lit(a.nome)}, 469, @pasta);")
    return s


MOLDURA = "DV_A3_Obra"
MOLDURA_NOTA = "A3 horizontal de obra (Drawing Views): legenda neutra, sem nome da empresa"


def sql_moldura(dwt: Path) -> list[str]:
    """Moldura: o DWT vai para a BINDATA (é de lá que o iMos o lê) + princípio + nó da árvore.

    O ficheiro é feito pelo criar_moldura_a3.ps1. Os .dwt de I:\\Library\\Bord são cópias
    antigas: a base é que manda (confirmado com o STANDARD, diferente nos dois sítios).
    """
    dados = dwt.read_bytes()
    if not dados.startswith(b"AC10"):
        raise SystemExit(f"Não parece um DWG/DWT: {dwt}")
    nome = _so_dv([MOLDURA])[0]
    return [
        "-- moldura",
        f"DELETE FROM dbo.BINDATA WHERE NAME = {lit(nome)} AND INTERNTYPE = N'LAYDWT';",
        f"DELETE FROM dbo.DOCMANBORDERPRINCIPLE WHERE NAME = {lit(nome)};",
        f"DELETE FROM dbo.DOCMANBORDERPRINCIPLEFOLDER WHERE NAME = {lit(nome)} AND TYPE = 480;",
        *_pasta("DOCMANBORDERPRINCIPLEFOLDER"),
        "INSERT INTO dbo.BINDATA (NAME, INTERNTYPE, BINCONTENT, SOURCE, PRODUCER, SYS) "
        f"VALUES ({lit(nome)}, N'LAYDWT', 0x{dados.hex().upper()}, {lit(SOURCE)}, N'', 0);",
        "INSERT INTO dbo.DOCMANBORDERPRINCIPLE (NAME, COMMENT, DATAFILE, SOURCE, PRODUCER, SYS, PICTURE) "
        f"VALUES ({lit(nome)}, {lit(MOLDURA_NOTA)}, {lit('DmLayout_' + nome + '.dwt')}, {lit(SOURCE)}, N'', 0, N'');",
        f"INSERT INTO dbo.DOCMANBORDERPRINCIPLEFOLDER (NAME, TYPE, PARENT_ID) VALUES ({lit(nome)}, 480, @pasta);",
    ]


BATCH = "DV_Desenhos_Obra"
BATCH_NOTA = "Drawing Views por obra: planta + alcados em A3 (moldura DV_A3_Obra), layouts e PDF"
BATCH_SAIDA = r"C:\IMOS_Output_Batches\DV_Desenhos"

# Saída "Drawing views" de um Output batch: CMSOUTPUTITEM.TYPE = 44 e PARAM_3 = JSON.
# Formato lido da base depois de a configurar no Element Manager (05-10-2026):
#   generate 1 Layouts / 2 Multi-Sheet-PDF / 3 Layouts & PDF;
#   scaling  0 Zoom extents / 1 Fix scale / 2 Best scale;
#   visugrad = "Modus" 1..6; hiddenlines 0 All / 1 interior detalhado / 2 interior draft / 3 None;
#   drawingsymbol = "Criar: 2D Symbols".
SAIDA_DESENHOS = {
    "submittaldrawingdefinition": {
        "general": {"generate": 3, "outputpath": BATCH_SAIDA},
        "planview": {"layout": "DV_A3_Obra", "scaling": 2, "visugrad": 4,
                     "dimensioning": "DV_Planta", "annotation": "DV_Planta_Etiquetas",
                     "hiddenlines": 0, "contour": 0, "coloration": 0, "connector": 0},
        "elevation": {"layout": "DV_A3_Obra", "scaling": 2, "visugrad": 4,
                      "dimensioning": "DV_Alcado", "annotation": "DV_Alcado_Etiquetas",
                      "hiddenlines": 2, "surfacesymbol": 0, "surfacename": 0, "materialsymbol": 0,
                      "materialname": 0, "hatch": 0, "coloration": 0, "drawingsymbol": 1,
                      "connector": 0},
    }
}


def sql_batch() -> list[str]:
    """Output batch DV_Desenhos_Obra (modo Encomenda = OUTPUTMODE 0) com a saída Drawing views."""
    nome = _so_dv([BATCH])[0]
    return [
        "-- output batch",
        *_pasta("CMSOUTPUTBATCHFOLDER"),
        f"DELETE FROM dbo.CMSOUTPUTITEM WHERE BATCHNAME = {lit(nome)};",
        f"DELETE FROM dbo.CMSOUTPUTBATCH WHERE NAME = {lit(nome)};",
        f"DELETE FROM dbo.CMSOUTPUTBATCHFOLDER WHERE NAME = {lit(nome)} AND TYPE = 472;",
        "INSERT INTO dbo.CMSOUTPUTBATCH (NAME, SEQUENCE, TEXTLONG, STARTMODE, SAVEMODE, SOURCE, PRODUCER, SYS, "
        "FXMMODE, OUTPUTMODE, PARAM_1, PARAM_2, SHOWOUTPUT, TYPE) "
        f"VALUES ({lit(nome)}, 1, {lit(BATCH_NOTA)}, 1, 1, {lit(SOURCE)}, N'', 0, 0, 0, N'', N'', 1, 0);",
        "INSERT INTO dbo.CMSOUTPUTITEM (BATCHNAME, ITEMNAME, SEQUENCE, TYPE, PARAM_1, PARAM_2, PARAM_3) "
        f"VALUES ({lit(nome)}, N'Desenhos A3 (planta + alcados)', 1, 44, N'', N'', "
        f"{lit(json.dumps(SAIDA_DESENHOS, separators=(',', ':')))});",
        f"INSERT INTO dbo.CMSOUTPUTBATCHFOLDER (NAME, TYPE, PARENT_ID) VALUES ({lit(nome)}, 472, @pasta);",
    ]


def gerar_sql(dwt: Path | None = None) -> str:
    corpo = (sql_condicoes() + sql_cotagem("DIMELEV", 487, ALCADO)
             + sql_cotagem("DIMPLAN", 486, PLANTA) + sql_anotacao() + sql_batch())
    if dwt is not None:
        corpo += sql_moldura(dwt)
    return "\n".join([
        "SET XACT_ABORT ON;",
        f"IF DB_NAME() <> {lit(BASE_TESTES)} THROW 50001, N'Recusado: esta configuracao so se escreve na {BASE_TESTES}.', 1;",
        "DECLARE @ids TABLE (id int);",
        "DECLARE @cid int, @raiz int, @pasta int;",
        "BEGIN TRANSACTION;",
        *corpo,
        "COMMIT TRANSACTION;",
    ]) + "\n"

# ----------------------------------------------------------------------------- execução

_PS = r"""
param([Parameter(Mandatory=$true)][string]$PayloadB64)
$ErrorActionPreference = 'Stop'
$p = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PayloadB64)) | ConvertFrom-Json
$sql = [IO.File]::ReadAllText([string]$p.sqlfile, [Text.Encoding]::UTF8)
Add-Type -AssemblyName System.Data
$conn = New-Object System.Data.SqlClient.SqlConnection ([string]$p.conn)
$conn.Open()
try {
  $cmd = $conn.CreateCommand()
  $cmd.CommandTimeout = 180
  $cmd.CommandText = $sql
  [void]$cmd.ExecuteNonQuery()
  Write-Output 'OK'
} finally { $conn.Close() }
"""


def _ligacao_testes() -> str:
    from app.db.session import SessionLocal
    from app.services import imos_escrita, imos_sql

    with SessionLocal() as s:
        cfg = dict(imos_sql.load_imos_config(s))
    cfg["database"] = BASE_TESTES
    return imos_escrita.build_connection_string(cfg)


def aplicar(sql: str) -> None:
    conn = _ligacao_testes()
    with tempfile.TemporaryDirectory() as tmp:
        sqlfile = Path(tmp) / "dv.sql"
        sqlfile.write_text(sql, encoding="utf-8")
        ps1 = Path(tmp) / "dv.ps1"
        ps1.write_text(_PS, encoding="utf-8")
        payload = base64.b64encode(json.dumps({"conn": conn, "sqlfile": str(sqlfile)}).encode()).decode()
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(ps1), payload],
            capture_output=True, text=True, timeout=240,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
    if r.returncode != 0 or "OK" not in r.stdout:
        raise SystemExit("Falhou (nada foi gravado; a transação é desfeita):\n"
                         + (r.stderr or r.stdout).strip())
    print(f"Configuração DV_* escrita na {BASE_TESTES}.")


def ver() -> None:
    from app.db.session import SessionLocal
    from app.services import imos_sql

    with SessionLocal() as s:
        cfg = dict(imos_sql.load_imos_config(s))
    cfg["database"] = BASE_TESTES
    consultas = {
        "Condições": "SELECT NAME, CONDTYPE, CONDITIONID FROM dbo.CONDITIONSPRINCIPLE WHERE NAME LIKE 'DV[_]%' ORDER BY NAME",
        "Alçado": "SELECT NAME, LINENUMBER, DIMTYPE, CONDITION, CAD_DIMSTYLE FROM dbo.DIMELEVLINES WHERE NAME LIKE 'DV[_]%' ORDER BY NAME, LINENUMBER",
        "Planta": "SELECT NAME, LINENUMBER, DIMTYPE, CONDITION, CAD_DIMSTYLE FROM dbo.DIMPLANLINES WHERE NAME LIKE 'DV[_]%' ORDER BY NAME, LINENUMBER",
        "Anotação": "SELECT NAME, NR, OBJECTTYPE, CONDITION, BLOCKNAME FROM dbo.LABELLING WHERE NAME LIKE 'DV[_]%' ORDER BY NAME, NR",
        "Moldura": "SELECT b.NAME, b.INTERNTYPE, DATALENGTH(b.BINCONTENT) AS bytes, p.DATAFILE FROM dbo.BINDATA b "
                   "LEFT JOIN dbo.DOCMANBORDERPRINCIPLE p ON p.NAME = b.NAME WHERE b.NAME LIKE 'DV[_]%'",
    }
    for titulo, q in consultas.items():
        linhas = imos_sql.run_imos_select(cfg, q)
        print(f"== {titulo} ({len(linhas)})")
        for ln in linhas:
            print("  ", " | ".join(str(v) for v in ln.values()))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--aplicar", action="store_true", help=f"escreve as DV_* na {BASE_TESTES}")
    ap.add_argument("--ver", action="store_true", help="lê as DV_* que lá estão")
    ap.add_argument("--moldura", type=Path, help="DWG/DWT feito pelo criar_moldura_a3.ps1")
    a = ap.parse_args()
    if a.ver:
        ver()
        return
    sql = gerar_sql(a.moldura)
    if a.aplicar:
        aplicar(sql)
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        for ln in sql.splitlines():
            print(ln if len(ln) < 400 else ln[:300] + f"... ({len(ln)} caracteres)")


if __name__ == "__main__":
    main()
