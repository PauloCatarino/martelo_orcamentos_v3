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
from dataclasses import dataclass, field, replace
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

BASE_TESTES = "imos_LE_TESTES"
PASTA = "DV_Desenhos"
SOURCE = "IMOSADMIN"

E, OU = 0, 2
ARTIGO, PECA = 10250, 10300

# Estilos de cota DV_* (estilos_cota_dv.py, gravados no config\imosBlocks.dwg, onde o iMos os
# vai buscar quando o desenho não os tem): mm de PAPEL e anotativos, por isso seguem a escala
# da folha que o Output batch escolhe. Os IMOS_VIEW_* da LE (texto de 35 mm) só funcionam com
# a escala de anotação a 1:1: no batch as cotas saíam 20-100 vezes maiores (teste de 05-10).
# (Os DV_COTA_* da 1.ª tentativa tinham texto de altura fixa e ficaram na ORC_260881_2604023.)
AZUL, VERM, PRETO, VERDE = "DV_AZUL", "DV_VERMELHO", "DV_PRETO", "DV_VERDE"

# Altura que separa os módulos de baixo dos de cima (pedido do Paulo, 05-10): acima de
# 1490 mm a vermelho (etiqueta e cotas); do chão até 1490, e as colunas, a azul.
Z_CIMA = "1490"

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
    Cond("DV_Art_Chao", ARTIGO, "Modulos do chao: inferiores e colunas (Z<=250)", E,
         MODULO + [("group insertionZ", "<=", "250", "FL")]),
    Cond("DV_Art_Nichos", ARTIGO, f"Modulos intermedios (250<Z<={Z_CIMA})", E,
         MODULO + [("group insertionZ", ">", "250", "FL"), ("group insertionZ", "<=", Z_CIMA, "FL")]),
    Cond("DV_Art_Superiores", ARTIGO, f"Modulos de cima (Z>{Z_CIMA})", E,
         MODULO + [("group insertionZ", ">", Z_CIMA, "FL")]),
    Cond("DV_Art_Azul", ARTIGO, f"Etiqueta azul: do chao ate {Z_CIMA} (inclui colunas)", E,
         MODULO + [("group insertionZ", "<=", Z_CIMA, "FL")]),
    Cond("DV_Art_Verm", ARTIGO, f"Etiqueta vermelha: acima de {Z_CIMA}", E,
         MODULO + [("group insertionZ", ">", Z_CIMA, "FL")]),
    # Volta 3 juntou aqui os rodapés e a cadeia de alturas triplicou (810/620/880,
    # 810/1380/120, 2190/120): o rodapé passa a ter uma linha própria (DV_Rodapes)
    Cond("DV_Art_Alturas", ARTIGO, "Modulos para a cadeia de alturas (sem rodapes)", E,
         MODULO + [("group depth", ">", "1", "FL")]),
    Cond("DV_Rodapes", ARTIGO, "Rodapes (nome comeca por RDP): so a altura", E,
         [t for t in MODULO if t[0] != "group name"] + [("group name", "B", "RDP", "CI")]),
    Cond("DV_Art_Todos", ARTIGO, "Todos os modulos (sem rodapes, deco, comprados)", E, MODULO),
    Cond("DV_Frentes", PECA, "Portas e frentes de gaveta", OU, FRENTES),
    Cond("DV_Frentes_Baixo", PECA, "Portas e frentes de gaveta abaixo de 1280", E,
         [("part insertionZ", "<", "1280", "FL"), ("OU", FRENTES)]),
    Cond("DV_Frentes_Cima", PECA, "Portas e frentes de gaveta a partir de 1280", E,
         [("part insertionZ", ">=", "1280", "FL"), ("OU", FRENTES)]),
    Cond("DV_Tampos", PECA, "Tampos", E, [("part type", "=", "work surface", "CI")]),
    # roupeiros, planta: só as portas (as frentes de gaveta ficam por trás e repetiam medidas)
    Cond("DV_Portas", PECA, "Portas (sem frentes de gaveta)", OU, FRENTES[:4]),
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


# Distâncias em mm de PAPEL ("altura no papel"), iguais em qualquer escala. 3.ª volta (05-10):
# 10 e 7 mm deixavam as cadeias demasiado afastadas; passa a 8 mm até à 1.ª linha e 5 entre linhas.
DIST_1, DIST_N = 8, 5
ALCADO_BASE = [
    Linha(1950, "DV_Art_Chao", AZUL, "Chao: inferiores e colunas (larguras em baixo)", {1958: "1"}),
    Linha(1950, "DV_Art_Nichos", PRETO, "Intermedios (larguras em cima)", {1958: "0"}),
    Linha(1950, "DV_Art_Superiores", VERM, "Superiores (larguras em cima)", {1958: "0"}),
    # 4.ª volta (05-10): com "Separate worktop height" = Sim saíam 3 cadeias pretas repetidas
    # (810/620/880/120, 810/1380/120, 2190/120); testa-se com Não
    Linha(1954, "DV_Art_Alturas", PRETO, "Alturas (uma so cadeia)", {1959: "0"}),
    Linha(1954, "DV_Rodapes", PRETO, "Altura do rodape", {1959: "0"}),
    Linha(1952, "", VERDE, "Paredes (largura e altura)", {1958: "1", 2057: "1"}),
]
# 1.ª volta (05-10): o DV_Alcado_Frentes acrescenta cadeias com as folgas das frentes (1,8 / 3,5
# mm) e linhas de chamada a atravessar o alçado: fica só como opção; as medidas das portas e
# gavetas vão nas etiquetas (pedido do Paulo: sem folgas).
ALCADO = [
    Cotagem("DV_Alcado", "Alcado A3: larguras por fiada, uma cadeia de alturas, paredes",
            DIST_1, DIST_N, True, ALCADO_BASE),
    Cotagem("DV_Alcado_Frentes", "Alcado A3 + cadeias das frentes (carregado: folgas incluidas)",
            DIST_1, DIST_N, True, ALCADO_BASE + [
                Linha(1960, "DV_Frentes_Baixo", PRETO, "Frentes de baixo (larguras)", {1958: "1"}),
                Linha(1960, "DV_Frentes_Cima", PRETO, "Frentes de cima (larguras)", {1958: "0"}),
                Linha(1955, "DV_Frentes", PRETO, "Frentes (alturas)"),
            ]),
]
# Planta: sem profundidades (com a "Depth dim" caíam por cima do desenho; com "Furniture depth"
# iam para longe com linhas a atravessar a planta). Chão numa só cadeia (inferiores + colunas),
# para não repetir a largura das colunas em três linhas.
PLANTA = [
    Cotagem("DV_Planta", "Planta A3: chao, tampos, intermedios, superiores, paredes",
            DIST_1, DIST_N, True, [
                Linha(1950, "DV_Art_Chao", AZUL, "Chao: inferiores e colunas", {1956: "0"}),
                Linha(1951, "DV_Tampos", PRETO, "Tampos", {1956: "0", 1957: "0"}),
                Linha(1950, "DV_Art_Nichos", PRETO, "Intermedios", {1956: "0"}),
                Linha(1950, "DV_Art_Superiores", VERM, "Superiores", {1956: "0"}),
                Linha(1952, "", VERDE, "Paredes"),
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


# Blocos em I:\Library\AttDWG (criar_blocos_etiqueta.ps1, versão "papel"): anotativos, em mm
# de papel, sem moldura, texto azul ou vermelho. Seguem a escala de anotação que o Output
# batch acerta pela escala da folha. (Os DV_Etq_* da volta 1.5 eram em mm do modelo.)
MOD_AZUL, MOD_VERM = "DV_Lbl_Modulo_Azul", "DV_Lbl_Modulo_Verm"
NOME_AZUL, NOME_VERM = "DV_Lbl_Nome_Azul", "DV_Lbl_Nome_Verm"
FRENTE = "DV_Lbl_Frente"

ETQ_MODULOS_ALCADO = [
    Etiqueta(3, "DV_Art_Azul", (0, 1), (0, 1), (0, -40), MOD_AZUL,
             "Modulos ate 1490: nome + L x A x P (azul)"),
    Etiqueta(3, "DV_Art_Verm", (0, 1), (0, 1), (0, -40), MOD_VERM,
             "Modulos acima de 1490 (vermelho)"),
]
ANOTACAO = [
    Anotacao("DV_Alcado_Etiquetas", "Alcado: nome e medidas do modulo + medidas das frentes",
             ETQ_MODULOS_ALCADO + [
                 Etiqueta(1, "DV_Frentes", (0, 0), (0, 0), (0, 0), FRENTE,
                          "Portas e gavetas: L x A (ao centro)"),
             ]),
    Anotacao("DV_Alcado_Etiquetas_Modulos", "Alcado: so nome e medidas do modulo",
             ETQ_MODULOS_ALCADO),
    # 4.ª volta (05-10): sem as medidas das frentes (na planta as portas são vistas de cima e
    # o "2181.4x513.67" caía de lado em cima das linhas); só o nome do módulo
    Anotacao("DV_Planta_Etiquetas", "Planta: so o nome do modulo", [
        Etiqueta(3, "DV_Art_Chao", (0, 0), (0, 0), (0, 0), NOME_AZUL, "Chao (ao centro, azul)"),
        Etiqueta(3, "DV_Art_Nichos", (0, 0), (0, 0), (0, 0), NOME_AZUL,
                 "Intermedios (ao centro, azul)"),
        Etiqueta(3, "DV_Art_Superiores", (0, 1), (0, 1), (0, -30), NOME_VERM,
                 "Superiores (junto a parede, vermelho)"),
    ]),
]

# ----------------------------------------------------------------------------- roupeiros

# Decisão do Paulo (06-10): um Output batch por tipo de obra, cada um com as suas regras, para
# que afinar os roupeiros não mexa nas cozinhas. A ronda 1 copia as regras de obra tal como
# estão; as rondas seguintes (etiqueta do artigo em baixo, portas com 1 casa decimal, cadeia
# vertical com rodapé/rodateto/caixotes/nicho, portas na planta) mudam só as DV_Roup_*.
def _copia(principio, nome: str, descricao: str):
    return replace(principio, nome=nome, descricao=descricao)


def _por_nome(principios, nome: str):
    return next(p for p in principios if p.nome == nome)


# R2 (06-10): a etiqueta do artigo passa para baixo do artigo, por fora; as cotas afastam-se
# 14 mm de papel (eram 8) para lhe dar lugar (etiqueta de ~5,5 mm + desvio de 60 mm do modelo,
# 3 mm a 1:20). Os módulos de cima (acima de 1490) ficam com a etiqueta por cima, por fora.
ROUP_DIST_1 = 14
ALCADO.append(replace(_por_nome(ALCADO, "DV_Alcado"), nome="DV_Roup_Alcado",
                      descricao="Roupeiros: alcado A3 (cotas a 14 mm para a etiqueta do artigo)",
                      dist_primeira=ROUP_DIST_1))
PLANTA.append(_copia(_por_nome(PLANTA, "DV_Planta"), "DV_Roup_Planta",
                     "Roupeiros: planta A3 (copia do DV_Planta)"))
PORTA_LXA, PORTA_L = "DV_Lbl_PortaLxA", "DV_Lbl_PortaL"
ANOTACAO += [
    Anotacao("DV_Roup_Alcado_Etiquetas", "Roupeiros: artigo em baixo por fora + L x A das frentes", [
        Etiqueta(3, "DV_Art_Azul", (0, -1), (0, 1), (0, -60), MOD_AZUL,
                 "Ate 1490: nome + L x A x P, em baixo, por fora"),
        Etiqueta(3, "DV_Art_Verm", (0, 1), (0, -1), (0, 60), MOD_VERM,
                 "Acima de 1490: por cima, por fora"),
        # IMOSPART* (casas da LUPREC da obra) em vez dos COND.PART_SIZE_* em bruto
        Etiqueta(1, "DV_Frentes", (0, 0), (0, 0), (0, 0), PORTA_LXA,
                 "Portas e gavetas: L x A (ao centro)"),
    ]),
    # Na planta, a frente do artigo é o lado y = -1 (o +1 é a parede: ver DV_Planta_Etiquetas)
    Anotacao("DV_Roup_Planta_Etiquetas", "Roupeiros: largura das portas + nome a frente do artigo", [
        Etiqueta(3, "DV_Art_Chao", (0, -1), (0, 1), (0, -150), NOME_AZUL,
                 "Chao: nome ao meio, a frente do artigo"),
        Etiqueta(3, "DV_Art_Nichos", (0, -1), (0, 1), (0, -150), NOME_AZUL,
                 "Intermedios: nome ao meio, a frente do artigo"),
        Etiqueta(3, "DV_Art_Superiores", (0, 1), (0, 1), (0, -30), NOME_VERM,
                 "Superiores (junto a parede, vermelho)"),
        Etiqueta(1, "DV_Portas", (0, 0), (0, 1), (0, -40), PORTA_L,
                 "Portas: largura, a frente da porta"),
    ]),
]

# ----------------------------------------------------------------------------- corte lateral

# Cotagem de corte lateral (tabelas DIMSECTSIDE*, nó 494). Os cortes não saem no Output batch:
# fazem-se à mão com "Create Section" (tipo Side View) e este princípio cota-os.
# Não havia nenhum exemplo nas bases: os códigos seguem a regra das cotas de alçado (o número
# da mensagem do imos.msg): tipos 1966 Article dimension, 1968 Article front, 1969 Niches;
# atributos 1972 Height dim., 1974 Insertion height dim., 1975 Distance between articles,
# 1984 Depth dim. Sim = "1", como nos alçados. A CONFIRMAR no primeiro corte.
CORTE = [
    Cotagem("DV_Corte_Lateral", "Corte lateral: alturas ao chao, vaos, profundidade, frentes",
            DIST_1, DIST_N, True, [
                Linha(1966, "DV_Art_Todos", PRETO, "Artigos: cadeia de alturas do chao + profundidade",
                      {1972: "1", 1974: "0", 1975: "1", 1984: "1"}),
                Linha(1969, "DV_Art_Todos", VERM, "Nichos: vaos entre prateleiras"),
                # 1.º corte (05-10): as frentes saíam com "8" e "0" (recuo e folga das portas):
                # 1981 Vertical front offset dim. e 1986 Vertical front gap dim. = Não
                Linha(1968, "DV_Art_Todos", AZUL, "Frentes: alturas", {1972: "1", 1981: "0", 1986: "0"}),
            ]),
]

# ----------------------------------------------------------------------------- tabela

# Tabela de artigos (tabela ACADTABLE, nó 301): o iMos troca <<IMOSORDERID>> pela obra e põe o
# resultado numa tabela do AutoCAD. Só os artigos de topo (ID = HIGHARTID), sem rodapés; as
# medidas vêm da IDBINFO (as mesmas do Article Center). Artigos iguais juntam-se numa linha.
TABELA = "DV_Tabela_Artigos"
TABELA_ESTILO = "Standard"
TABELA_SQL = """SELECT ROW_NUMBER() OVER (ORDER BY MIN(i.POSSTR)) AS [N],
 i.GROUPNAME AS [Artigo],
 CAST(ROUND(i.WIDTH, 0) AS int) AS [Largura],
 CAST(ROUND(i.HEIGHT, 0) AS int) AS [Altura],
 CAST(ROUND(i.DEPTH, 0) AS int) AS [Prof],
 COUNT(*) AS [Qtd]
FROM IDBGRPS g
JOIN IDBINFO i ON i.ORDERID = g.ORDERID AND i.ID = g.ID
WHERE g.ORDERID = '<<IMOSORDERID>>' AND g.ID = g.HIGHARTID AND g.TYP = 2
 AND i.GROUPNAME NOT LIKE 'RDP%'
GROUP BY i.GROUPNAME, ROUND(i.WIDTH, 0), ROUND(i.HEIGHT, 0), ROUND(i.DEPTH, 0)
ORDER BY [N]"""

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


def sql_tabela() -> list[str]:
    nome = _so_dv([TABELA])[0]
    return [
        "-- tabela",
        f"DELETE FROM dbo.ACADTABLE WHERE NAME = {lit(nome)};",
        f"DELETE FROM dbo.ACADTABLEFOLDER WHERE NAME = {lit(nome)} AND TYPE = 301;",
        *_pasta("ACADTABLEFOLDER"),
        "INSERT INTO dbo.ACADTABLE (NAME, TEXT, SQLQUERY, TABLESTYLE, CATALOG_ID, WORKPLAN_ID, INORDER, SOURCE, PRODUCER, SYS) "
        f"VALUES ({lit(nome)}, N'Artigos', {lit(TABELA_SQL)}, {lit(TABELA_ESTILO)}, 0, 0, N'', {lit(SOURCE)}, N'', 0);",
        f"INSERT INTO dbo.ACADTABLEFOLDER (NAME, TYPE, PARENT_ID) VALUES ({lit(nome)}, 301, @pasta);",
    ]


# O nome da moldura é o nome do ficheiro que o criar_moldura_a3.ps1 grava (<layout>.dwg).
MOLDURAS = {
    "DV_A3_Obra": "A3 horizontal de obra (Drawing Views): legenda neutra, sem nome da empresa",
    "DV_A3_Roupeiro": "A3 horizontal de roupeiros (Drawing Views): legenda de 2 linhas com o artigo",
}


def sql_moldura(dwt: Path) -> list[str]:
    """Moldura: o DWT vai para a BINDATA (é de lá que o iMos o lê) + princípio + nó da árvore.

    O ficheiro é feito pelo criar_moldura_a3.ps1. Os .dwt de I:\\Library\\Bord são cópias
    antigas: a base é que manda (confirmado com o STANDARD, diferente nos dois sítios).
    """
    dados = dwt.read_bytes()
    if not dados.startswith(b"AC10"):
        raise SystemExit(f"Não parece um DWG/DWT: {dwt}")
    nome = _so_dv([dwt.stem])[0]
    if nome not in MOLDURAS:
        raise SystemExit(f"Moldura desconhecida: {nome} (conhecidas: {', '.join(MOLDURAS)})")
    return [
        "-- moldura",
        f"DELETE FROM dbo.BINDATA WHERE NAME = {lit(nome)} AND INTERNTYPE = N'LAYDWT';",
        f"DELETE FROM dbo.DOCMANBORDERPRINCIPLE WHERE NAME = {lit(nome)};",
        f"DELETE FROM dbo.DOCMANBORDERPRINCIPLEFOLDER WHERE NAME = {lit(nome)} AND TYPE = 480;",
        *_pasta("DOCMANBORDERPRINCIPLEFOLDER"),
        "INSERT INTO dbo.BINDATA (NAME, INTERNTYPE, BINCONTENT, SOURCE, PRODUCER, SYS) "
        f"VALUES ({lit(nome)}, N'LAYDWT', 0x{dados.hex().upper()}, {lit(SOURCE)}, N'', 0);",
        "INSERT INTO dbo.DOCMANBORDERPRINCIPLE (NAME, COMMENT, DATAFILE, SOURCE, PRODUCER, SYS, PICTURE) "
        f"VALUES ({lit(nome)}, {lit(MOLDURAS[nome])}, {lit('DmLayout_' + nome + '.dwt')}, {lit(SOURCE)}, N'', 0, N'');",
        f"INSERT INTO dbo.DOCMANBORDERPRINCIPLEFOLDER (NAME, TYPE, PARENT_ID) VALUES ({lit(nome)}, 480, @pasta);",
    ]


# Com "...\DV_Desenhos" o batch gravou o ficheiro C:\IMOS_Output_Batches\DV_Desenhos.pdf (o fim
# do caminho vira o nome); com a barra no fim usa o nome da obra (<obra>_Submittals.pdf).
BATCH_SAIDA = "C:\\IMOS_Output_Batches\\"

# Saída "Drawing views" de um Output batch: CMSOUTPUTITEM.TYPE = 44 e PARAM_3 = JSON.
# Formato lido da base depois de a configurar no Element Manager (05-10-2026):
#   generate 1 Layouts / 2 Multi-Sheet-PDF / 3 Layouts & PDF;
#   scaling  0 Zoom extents / 1 Fix scale / 2 Best scale;
#   visugrad = "Modus" 1..6; hiddenlines 0 All / 1 interior detalhado / 2 interior draft / 3 None;
#   drawingsymbol = "Criar: 2D Symbols".


def saida_desenhos(moldura: str, planta: str, planta_etq: str, alcado: str, alcado_etq: str) -> dict:
    return {
        "submittaldrawingdefinition": {
            "general": {"generate": 3, "outputpath": BATCH_SAIDA},
            # planta como o Paulo a quer: sem linhas escondidas, com conectores e sem cor
            # (a cor foi ele que a desligou no Element Manager, visto na base a 06-10)
            "planview": {"layout": moldura, "scaling": 2, "visugrad": 4,
                         "dimensioning": planta, "annotation": planta_etq,
                         "hiddenlines": 3, "contour": 0, "coloration": 0, "connector": 1},
            # alçado como o Paulo o afinou nas Vistas 3 e 4 (05-10): linhas escondidas "All",
            # Secção (= hatch), 2D Symbols e conectores. As escondidas vão para o layer
            # IMOS_SECTION_BACK_HIDDEN (cor 254): o DV_PlotStyle.ctb da moldura escurece-as.
            "elevation": {"layout": moldura, "scaling": 2, "visugrad": 4,
                          "dimensioning": alcado, "annotation": alcado_etq,
                          "hiddenlines": 0, "surfacesymbol": 0, "surfacename": 0, "materialsymbol": 0,
                          "materialname": 0, "hatch": 1, "coloration": 0, "drawingsymbol": 1,
                          "connector": 1},
        }
    }


@dataclass
class Batch:
    nome: str
    nota: str
    saida: dict


BATCHES = [
    Batch("DV_Desenhos_Obra",
          "Drawing Views por obra: planta + alcados em A3 (moldura DV_A3_Obra), layouts e PDF",
          saida_desenhos("DV_A3_Obra", "DV_Planta", "DV_Planta_Etiquetas",
                         "DV_Alcado", "DV_Alcado_Etiquetas")),
    Batch("DV_Roupeiros",
          "Roupeiros: planta + alcados em A3 (moldura DV_A3_Roupeiro, regras DV_Roup_*), layouts e PDF",
          saida_desenhos("DV_A3_Roupeiro", "DV_Roup_Planta", "DV_Roup_Planta_Etiquetas",
                         "DV_Roup_Alcado", "DV_Roup_Alcado_Etiquetas")),
]


def sql_batch() -> list[str]:
    """Output batches DV_* (modo Encomenda = OUTPUTMODE 0), cada um com a saída Drawing views."""
    s = ["-- output batches", *_pasta("CMSOUTPUTBATCHFOLDER")]
    for b in BATCHES:
        nome = _so_dv([b.nome])[0]
        s += [
            f"DELETE FROM dbo.CMSOUTPUTITEM WHERE BATCHNAME = {lit(nome)};",
            f"DELETE FROM dbo.CMSOUTPUTBATCH WHERE NAME = {lit(nome)};",
            f"DELETE FROM dbo.CMSOUTPUTBATCHFOLDER WHERE NAME = {lit(nome)} AND TYPE = 472;",
            "INSERT INTO dbo.CMSOUTPUTBATCH (NAME, SEQUENCE, TEXTLONG, STARTMODE, SAVEMODE, SOURCE, PRODUCER, SYS, "
            "FXMMODE, OUTPUTMODE, PARAM_1, PARAM_2, SHOWOUTPUT, TYPE) "
            f"VALUES ({lit(nome)}, 1, {lit(b.nota)}, 1, 1, {lit(SOURCE)}, N'', 0, 0, 0, N'', N'', 1, 0);",
            "INSERT INTO dbo.CMSOUTPUTITEM (BATCHNAME, ITEMNAME, SEQUENCE, TYPE, PARAM_1, PARAM_2, PARAM_3) "
            f"VALUES ({lit(nome)}, N'Desenhos A3 (planta + alcados)', 1, 44, N'', N'', "
            f"{lit(json.dumps(b.saida, separators=(',', ':')))});",
            f"INSERT INTO dbo.CMSOUTPUTBATCHFOLDER (NAME, TYPE, PARENT_ID) VALUES ({lit(nome)}, 472, @pasta);",
        ]
    return s


def gerar_sql(molduras: list[Path] | None = None) -> str:
    corpo = (sql_condicoes() + sql_cotagem("DIMELEV", 487, ALCADO)
             + sql_cotagem("DIMPLAN", 486, PLANTA) + sql_cotagem("DIMSECTSIDE", 494, CORTE)
             + sql_anotacao() + sql_tabela() + sql_batch())
    for dwt in molduras or []:
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
        "Corte": "SELECT NAME, LINENUMBER, DIMTYPE, CONDITION, CAD_DIMSTYLE FROM dbo.DIMSECTSIDELINES WHERE NAME LIKE 'DV[_]%' ORDER BY NAME, LINENUMBER",
        "Tabela": "SELECT NAME, TEXT, TABLESTYLE, LEN(SQLQUERY) AS sql_len FROM dbo.ACADTABLE WHERE NAME LIKE 'DV[_]%'",
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
    ap.add_argument("--moldura", type=Path, action="append",
                    help="DWG/DWT feito pelo criar_moldura_a3.ps1 (<moldura>.dwg); pode repetir-se. "
                         "Sem --moldura, as molduras que estão na base ficam como estão")
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
