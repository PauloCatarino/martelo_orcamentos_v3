"""Lista de corte das peças lida diretamente da base do iMos (ENSAIO, 30-10-2026).

Hoje as peças chegam à Lista Material por um CSV que o próprio iMos escreve com o
princípio «Processar transferência de dados» (``EXPORT_CSV_CUT_RITE_LE.cfg``), na pasta
``I:\\Cutrite\\Work\\Cutrite_Import_CSV``. Este módulo faz a mesma lista dentro do
Martelo: lê a obra na base do iMos (só SELECT) e escreve um CSV com as MESMAS 22 colunas,
pela mesma ordem — a macro do Excel copia-as por posição para a LISTA_ORDENADA — e mais
quatro no fim, que o ``.cfg`` não consegue dar:

- ``Artigo/SubArtigo``: o artigo mais próximo da peça (num gaveteiro, o sub-artigo);
- ``Piso``: o campo «Name» do artigo PRINCIPAL (ex.: R/C), vazio quando não é um piso;
- ``ArtigoNome``: o nome do artigo principal;
- ``ISPEC``: a forma da peça (0 = retangular de 4 lados).

É um caminho EM PARALELO, pedido pelo Paulo a 29-10-2026 para ensaio: o CSV do ``.cfg``
e a macro ``Import_CSV_Imos_1`` continuam a ser o caminho normal.

Regras do motor do iMos que a lista reproduz (confirmadas a 29-10-2026 contra os CSV do
``.cfg`` de 8 obras, ~2100 linhas, todas as colunas iguais):

- entram as peças da ``IDBGPL`` com o mesmo filtro do ``.cfg`` (``CUT_FLAG`` e ``TYP``) e
  com material; as que não têm material o ``.cfg`` também deixa de fora;
- a quantidade é ``CNT`` × as quantidades (``IDBINFO.BOMFACTOR``) de todos os artigos
  acima da peça: um artigo com quantidade 0 dá linhas com Qt. 0 (a macro pergunta se as
  importa), um com 2 dobra as peças;
- um artigo ou grupo liga ao de cima pelo ``ARTID`` quando o tem, senão pelo ``ASSID``;
- Veio = 1 quando o material tem veio (``MATGRID`` diferente de 0);
- orlas = ``IDBPRF`` (sem os perfis interiores ``PTYPE='I'``): 1 ESQ, 3 DIR, 4 CIMA, 2 BAIXO;
- CNC_1 e CNC_2 = o 1.º e o 2.º número de programa (``ncnum``) diferentes, pela ordem da
  sequência, sem as máquinas ``Dummy*`` nem os programas espelhados;
- Enc. = ``PROADMIN.ARTICLENO``, Cliente = ``CLIENT``, Cliente_Final = ``CUSTOMER``;
- Notas = ``INFO1`` e Notas_1 = ``INFO2`` da peça; CNC/ABD/BHT saem sempre vazias (nos 316
  CSV dos últimos 120 dias nunca tiveram nada).

Junta numa linha só as peças com TODAS as colunas iguais. O ``.cfg`` junta por menos
colunas (sem as Notas) e chega a pôr a nota de uma peça noutra (obra 1608_03, RP_APT4_14).
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.services.imos_sql import ImosConfig, nome_imos_valido, run_imos_select

# As 22 colunas do CSV do .cfg por defeito, pela mesma ordem: a macro
# Import_CSV_Imos_1 copia-as POR POSIÇÃO para a LISTA_ORDENADA (B a W).
COLUNAS_IMOS: tuple[str, ...] = (
    "Descricao", "Material", "Comp.", "Larg.", "Esp", "Qt.", "Veio",
    "Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO", "CNC_1", "CNC_2",
    "Enc.", "Cliente", "RP", "Notas", "Notas_1", "Cliente_Final", "CNC", "ABD", "BHT",
)
# Colunas que só a leitura da base consegue dar; ficam depois das 22.
COLUNAS_NOVAS: tuple[str, ...] = ("Artigo/SubArtigo", "Piso", "ArtigoNome", "ISPEC")
COLUNAS_CSV: tuple[str, ...] = COLUNAS_IMOS + COLUNAS_NOVAS

# O mesmo FILTER do .cfg: só peças cortadas, sem ferragens nem uniões.
TIPOS_FORA = (11, 15, 16, 17, 18, 19, 20, 43, 44)
# Orlas: número do perfil na IDBPRF -> coluna do CSV.
ORLAS = {1: "Orla ESQ", 3: "Orla DIR", 4: "Orla CIMA", 2: "Orla BAIXO"}
# O «Name» do artigo vem com "." quando ninguém o preencheu.
PISO_VAZIO = ("", ".")

Executar = Callable[[ImosConfig, str], list[dict]]


@dataclass(frozen=True)
class DadosObraImos:
    """O que a lista precisa da base do iMos para uma obra (linhas tal como vêm do SQL)."""

    nome: str
    cabecalho: dict
    grupos: list[dict]
    artigos: list[dict]
    pecas: list[dict]
    orlas: list[dict]
    programas: list[dict]
    ultima_gravacao: datetime | None = None


@dataclass
class LinhaCorte:
    """Uma linha da lista: as colunas (sem a Qt.) e a quantidade somada."""

    colunas: dict[str, str]
    qt: float = 0.0

    def valor(self, coluna: str) -> str:
        if coluna == "Qt.":
            return f"{self.qt:.0f}"
        return self.colunas.get(coluna, "")


@dataclass
class ComparacaoLista:
    """Resultado de comparar a lista da base com um CSV do .cfg."""

    pecas_base: float
    pecas_csv: float
    linhas_base: int
    linhas_csv: int
    diferencas: list[str] = field(default_factory=list)

    @property
    def iguais(self) -> bool:
        return not self.diferencas


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip()


def _inteiro(valor, defeito: int = 0) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return defeito


def _numero(valor, defeito: float = 0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defeito


# ---------------------------------------------------------------------------
# Leitura da base (só SELECT)
# ---------------------------------------------------------------------------

def ler_obra(
    cfg: ImosConfig, nome_obra: str, *, executar: Executar = run_imos_select
) -> DadosObraImos:
    """Lê da base do iMos tudo o que a lista de corte da obra precisa."""
    nome = _texto(nome_obra)
    if not nome_imos_valido(nome):
        raise ValueError(
            f"Nome Enc IMOS IX inválido: «{nome}». Tem de ser igual ao nome da "
            "encomenda no iMos."
        )
    obra = "N'" + nome.replace("'", "''") + "'"
    cabecalhos = executar(
        cfg,
        "SELECT ID, ARTICLENO, CLIENT, CUSTOMER, CONVERT(varchar(19), LCHANGE, 120) AS GRAVADA "
        f"FROM PROADMIN WHERE NAME = {obra} ORDER BY LCHANGE DESC",
    )
    if not cabecalhos:
        raise ValueError(
            f"Não encontrei no iMos a encomenda «{nome}».\n\n"
            "Confirme o Nome Enc IMOS IX da obra: tem de ser igual ao nome da "
            "encomenda no iMos."
        )
    fora = ", ".join(str(t) for t in TIPOS_FORA)
    pecas = executar(
        cfg,
        "SELECT ID, CNT, NAME1, MATID, MATNAME, MATGRID, CLENG, CWIDTH, CTHK, INFO1, INFO2, "
        f"PARTPOSSTR, ISPEC FROM IDBGPL WHERE ORDERID = {obra} "
        f"AND (CUT_FLAG <> 0 OR CUT_FLAG IS NULL) AND TYP NOT IN ({fora}) ORDER BY ID",
    )
    grupos = executar(
        cfg, f"SELECT ID, TYP, ARTID, ASSID, NAME FROM IDBGRPS WHERE ORDERID = {obra}"
    )
    artigos = executar(
        cfg,
        f"SELECT ID, GROUPNAME, CPID, BOMFACTOR FROM IDBINFO WHERE ORDERID = {obra}",
    )
    orlas = executar(
        cfg, f"SELECT ID, PRFNO, PRFNAME, PTYPE FROM IDBPRF WHERE ORDERID = {obra}"
    )
    programas = executar(
        cfg,
        "SELECT c.PARTID, c.PROGRAMID, c.SEQUENCENUM, a.ATTRIBUTE, a.ATTRVALUE "
        "FROM IDBCAMPROGRAM c JOIN IDBCAMATTRVALUE a ON a.ATTRSETID = c.ATTRSETID "
        f"WHERE c.ORDERID = {obra} AND a.ATTRIBUTE IN ('ncnum', 'machine', 'mirrored')",
    )
    gravada = None
    texto = _texto(cabecalhos[0].get("GRAVADA"))
    if texto:
        try:
            gravada = datetime.strptime(texto[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            gravada = None
    return DadosObraImos(
        nome=nome,
        cabecalho=cabecalhos[0],
        grupos=grupos,
        artigos=artigos,
        pecas=pecas,
        orlas=orlas,
        programas=programas,
        ultima_gravacao=gravada,
    )


# ---------------------------------------------------------------------------
# Montagem da lista (sem base: testável com linhas inventadas)
# ---------------------------------------------------------------------------

def _cadeia_artigos(dados: DadosObraImos) -> Callable[[int], list[dict]]:
    """Devolve f(id da peça) -> artigos acima dela, do mais próximo ao principal.

    Na ``IDBGRPS`` cada linha aponta para a de cima pelo ``ARTID`` (o 1.º grupo de um
    artigo, ou um artigo pendurado diretamente noutro) ou pelo ``ASSID`` (o grupo pai).
    Os artigos são as linhas com ``TYP`` 2; os dados deles estão na ``IDBINFO``.
    """
    grupos = {_inteiro(g.get("ID")): g for g in dados.grupos}
    info = {_inteiro(a.get("ID")): a for a in dados.artigos}

    def acima(id_peca: int) -> list[dict]:
        artigos: list[dict] = []
        atual, vistos = grupos.get(id_peca), set()
        while atual is not None:
            gid = _inteiro(atual.get("ID"))
            if gid in vistos:
                break
            vistos.add(gid)
            if _inteiro(atual.get("TYP")) == 2:
                a = info.get(gid, {})
                bom = a.get("BOMFACTOR")
                artigos.append({
                    "id": gid,
                    "nome": _texto(a.get("GROUPNAME")) or _texto(atual.get("NAME")),
                    "name": _texto(a.get("CPID")),
                    "quantidade": 1.0 if bom is None or _texto(bom) == "" else _numero(bom, 1.0),
                })
            artid, assid = _inteiro(atual.get("ARTID")), _inteiro(atual.get("ASSID"))
            seguinte = artid or assid
            atual = grupos.get(seguinte) if seguinte else None
        return artigos

    return acima


def _piso(artigos: list[dict]) -> str:
    """O piso é o «Name» do artigo principal; se esse não tiver piso, o do mais próximo.

    Não é piso: o "." por defeito, o próprio número do artigo (o iMos preenche o «Name»
    de um artigo novo com o ID dele, ex.: 49187) e o nome do grupo repetido.
    """
    for artigo in reversed(artigos):
        nome = artigo["name"]
        if nome in PISO_VAZIO or nome == str(artigo["id"]) or nome == artigo["nome"]:
            continue
        return nome
    return ""


def _programas_por_peca(dados: DadosObraImos) -> dict[int, list[str]]:
    """Números de programa CNC de cada peça, como o ``PXM_PROGRAM_INFO_VALID`` do .cfg."""
    por_programa: dict[tuple[int, str], dict] = defaultdict(dict)
    for linha in dados.programas:
        chave = (_inteiro(linha.get("PARTID")), _texto(linha.get("PROGRAMID")))
        atributos = por_programa[chave]
        atributos["seq"] = _inteiro(linha.get("SEQUENCENUM"))
        atributos[_texto(linha.get("ATTRIBUTE")).lower()] = _texto(linha.get("ATTRVALUE"))
    por_peca: dict[int, list[dict]] = defaultdict(list)
    for (id_peca, _), atributos in por_programa.items():
        por_peca[id_peca].append(atributos)
    numeros: dict[int, list[str]] = {}
    for id_peca, progs in por_peca.items():
        lista: list[str] = []
        for prog in sorted(progs, key=lambda p: p.get("seq", 0)):
            numero = prog.get("ncnum", "")
            if not numero or prog.get("machine", "").startswith("Dummy"):
                continue
            if prog.get("mirrored", "").lower() == "yes" or numero in lista:
                continue
            lista.append(numero)
        numeros[id_peca] = lista
    return numeros


def montar_lista(dados: DadosObraImos) -> list[LinhaCorte]:
    """Monta as linhas da lista de corte, juntando as peças com as colunas todas iguais."""
    acima = _cadeia_artigos(dados)
    programas = _programas_por_peca(dados)
    orlas: dict[int, dict[str, str]] = defaultdict(dict)
    for linha in dados.orlas:
        coluna = ORLAS.get(_inteiro(linha.get("PRFNO")))
        if coluna and _texto(linha.get("PTYPE")).upper() != "I":
            orlas[_inteiro(linha.get("ID"))][coluna] = _texto(linha.get("PRFNAME"))
    cab = dados.cabecalho

    linhas: dict[tuple, LinhaCorte] = {}
    for peca in dados.pecas:
        material = _texto(peca.get("MATNAME")) or _texto(peca.get("MATID"))
        if not material:
            continue  # sem material: o .cfg também não a exporta
        id_peca = _inteiro(peca.get("ID"))
        artigos = acima(id_peca)
        quantidade = _numero(peca.get("CNT"))
        for artigo in artigos:
            quantidade *= artigo["quantidade"]
        ncs = programas.get(id_peca, [])
        colunas = {
            "Descricao": _texto(peca.get("NAME1")),
            "Material": material,
            "Comp.": f"{_numero(peca.get('CLENG')):.1f}",
            "Larg.": f"{_numero(peca.get('CWIDTH')):.1f}",
            "Esp": f"{_numero(peca.get('CTHK')):.1f}",
            "Veio": "0" if _inteiro(peca.get("MATGRID")) == 0 else "1",
            "CNC_1": ncs[0] if ncs else "",
            "CNC_2": ncs[1] if len(ncs) > 1 else "",
            "Enc.": _texto(cab.get("ARTICLENO")),
            "Cliente": _texto(cab.get("CLIENT")),
            "RP": _texto(peca.get("PARTPOSSTR")).split(".")[0],
            "Notas": _texto(peca.get("INFO1")),
            "Notas_1": _texto(peca.get("INFO2")),
            "Cliente_Final": _texto(cab.get("CUSTOMER")),
            "CNC": "",
            "ABD": "",
            "BHT": "",
            "Artigo/SubArtigo": artigos[0]["nome"] if artigos else "",
            "Piso": _piso(artigos),
            "ArtigoNome": artigos[-1]["nome"] if artigos else "",
            "ISPEC": str(_inteiro(peca.get("ISPEC"))),
        }
        for coluna in ORLAS.values():
            colunas[coluna] = orlas.get(id_peca, {}).get(coluna, "")
        chave = tuple(colunas[c] for c in COLUNAS_CSV if c != "Qt.")
        if chave not in linhas:
            linhas[chave] = LinhaCorte(colunas=colunas)
        linhas[chave].qt += quantidade
    # Como o .cfg (POSITION_SORT): por posição; dentro dela, pela ordem das peças.
    return sorted(linhas.values(), key=lambda l: l.colunas["RP"])


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def escrever_csv(linhas: list[LinhaCorte], destino: Path) -> Path:
    """Escreve o CSV como o do iMos: «;», CRLF, ANSI e uma «;» no fim de cada linha."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = ["".join(f"{c};" for c in COLUNAS_CSV)]
    for linha in linhas:
        texto.append("".join(f"{linha.valor(c).replace(';', ',')};" for c in COLUNAS_CSV))
    destino.write_bytes(("\r\n".join(texto) + "\r\n").encode("cp1252", errors="replace"))
    return destino


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    """Lê um CSV da lista de corte (do .cfg ou deste módulo)."""
    with Path(caminho).open(encoding="cp1252", errors="replace", newline="") as f:
        return [
            {(k or "").strip(): (v or "").strip() for k, v in linha.items() if k}
            for linha in csv.DictReader(f, delimiter=";")
        ]


# ---------------------------------------------------------------------------
# Comparação com o CSV do .cfg
# ---------------------------------------------------------------------------

_COLUNAS_COMPARADAS = (
    "Veio", "Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO", "CNC_1", "CNC_2",
    "Enc.", "Cliente", "Cliente_Final",
)


def comparar_com_csv_imos(
    linhas: list[LinhaCorte], linhas_csv: list[dict[str, str]], *, maximo: int = 40
) -> ComparacaoLista:
    """Compara a lista da base com o CSV do .cfg, peça a peça e coluna a coluna.

    Agrupa pelas colunas que identificam a peça (descrição, material, medidas, posição,
    notas) e compara as quantidades e o resto das colunas do CSV antigo. As colunas
    novas não entram: o .cfg não as tem.
    """
    col_pos = next(
        (c for c in ("RP", "Posicao", "Artigo") if linhas_csv and c in linhas_csv[0]), "RP"
    )

    def chave(get, pos) -> tuple:
        return (get("Descricao"), get("Material"), get("Comp."), get("Larg."), get("Esp"),
                pos, get("Notas"), get("Notas_1"))

    qt_base: dict[tuple, float] = defaultdict(float)
    qt_csv: dict[tuple, float] = defaultdict(float)
    val_base: dict[tuple, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    val_csv: dict[tuple, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for linha in linhas:
        k = chave(linha.valor, linha.valor("RP"))
        qt_base[k] += linha.qt
        for c in _COLUNAS_COMPARADAS:
            val_base[k][c].add(linha.valor(c))
    for r in linhas_csv:
        k = chave(lambda c: r.get(c, ""), r.get(col_pos, ""))
        qt_csv[k] += _numero(r.get("Qt."))
        for c in _COLUNAS_COMPARADAS:
            val_csv[k][c].add(r.get(c, ""))

    diferencas: list[str] = []
    for k in sorted(set(qt_base) | set(qt_csv)):
        b, c = qt_base.get(k, 0.0), qt_csv.get(k, 0.0)
        if abs(b - c) > 1e-6:
            desc, mat, comp, larg, _, pos, notas, _ = k
            diferencas.append(
                f"{pos} | {desc} | {mat} | {comp} x {larg}"
                + (f" | nota «{notas}»" if notas else "")
                + f": base {b:g}, CSV {c:g}"
            )
    for c in _COLUNAS_COMPARADAS:
        erradas = [k for k in qt_base if k in qt_csv and val_base[k][c] != val_csv[k][c]]
        if erradas:
            k = erradas[0]
            diferencas.append(
                f"Coluna {c}: diferente em {len(erradas)} peça(s); ex.: {k[5]} | {k[0]} "
                f"{k[2]} x {k[3]}: base {sorted(val_base[k][c])}, CSV {sorted(val_csv[k][c])}"
            )
    total = len(diferencas)
    if total > maximo:
        diferencas = diferencas[:maximo] + [f"... e mais {total - maximo} diferença(s)."]
    return ComparacaoLista(
        pecas_base=sum(qt_base.values()),
        pecas_csv=sum(qt_csv.values()),
        linhas_base=len(linhas),
        linhas_csv=len(linhas_csv),
        diferencas=diferencas,
    )
