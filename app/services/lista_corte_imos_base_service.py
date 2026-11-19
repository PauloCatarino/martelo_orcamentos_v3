"""Lista de corte das peças lida diretamente da base do iMos (ENSAIO, 29-10-2026).

Hoje as peças chegam à Lista Material por um CSV que o próprio iMos escreve com o
princípio «Processar transferência de dados» (``EXPORT_CSV_CUT_RITE_LE.cfg``), na pasta
``I:\\Cutrite\\Work\\Cutrite_Import_CSV``. Este módulo faz a mesma lista dentro do
Martelo: lê a obra na base do iMos (só SELECT) e escreve um CSV com as 17 primeiras colunas
do CSV do ``.cfg`` (Descricao a Notas), pela mesma ordem, e mais cinco que o ``.cfg`` não
consegue dar:

- ``Artigo``: o que vai para a coluna Artigo da LISTAGEM_CUT_RITE (19-11-2026):
  ``ArtigoNome[_Artigo/SubArtigo]_Descricao``, com o sub-artigo só quando é diferente
  do ArtigoNome (ver :func:`artigo_composto`);
- ``Artigo/SubArtigo``: o artigo mais próximo da peça (num gaveteiro, o sub-artigo);
- ``Descricao`` (2.ª coluna com este nome; até 19-11-2026 chamava-se ``Piso``): o campo
  «Descricao» do artigo PRINCIPAL no iMos (``IDBINFO.CPID``; ex.: MENINA), vazio quando
  não foi preenchido;
- ``ArtigoNome``: o nome do artigo principal;
- ``ISPEC``: a forma da peça (0 = retangular de 4 lados);
- ``Posicao``: a posição do artigo no iMos (por agora igual ao RP; ainda não se usa).

Desde 19-11-2026 (pedido do Paulo) saem as colunas Notas_1, Cliente_Final, CNC, ABD e
BHT: nenhuma fórmula, macro ou função do Martelo as usava. A macro do ensaio
(``Import_Base_Imos_1``) passou a copiar para a LISTA_ORDENADA pelo NOME da coluna.

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
- Enc. = ``PROADMIN.ARTICLENO``, Cliente = ``CLIENT``;
- Notas = ``INFO1`` da peça.

Multipeça (19-11-2026, regra R102 do iMos): a peça-mãe (``MPE_TYPE = 1``) não tem material
e o ``.cfg`` nunca a exporta. A da frente de gaveta em U (com vidro) tem de ir à lista, com
as medidas, a nota e o CNC, mas SEM material, para o Cut-Rite não a cortar (cortam-se as
filhas). Sai só a mãe com «Peça na lista de corte» (``CUT_FLAG <> 0``), com filhas e com
«frente» no nome: na base há milhares de outras mães com ``CUT_FLAG`` ligado (prateleiras
amovíveis, fundos em L, maleiros...), que continuam de fora (saem só as filhas).

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

# As colunas do CSV do .cfg que a lista da base continua a dar, pela mesma ordem
# (a Import_CSV_Imos_1 copia o CSV do .cfg POR POSIÇÃO para a LISTA_ORDENADA, B a W;
# desde 19-11-2026 a Import_Base_Imos_1 copia pelo nome).
COLUNAS_IMOS: tuple[str, ...] = (
    "Descricao", "Material", "Comp.", "Larg.", "Esp", "Qt.", "Veio",
    "Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO", "CNC_1", "CNC_2",
    "Enc.", "Cliente", "RP", "Notas",
)
# Colunas do CSV do .cfg que a lista da base deixou de escrever (19-11-2026).
COLUNAS_TIRADAS: tuple[str, ...] = ("Notas_1", "Cliente_Final", "CNC", "ABD", "BHT")
# Colunas que só a leitura da base consegue dar; ficam depois das do .cfg.
# A 2.ª «Descricao» (a do artigo) chamava-se «Piso» até 19-11-2026; dentro do Martelo
# é a chave DESCRICAO_ARTIGO, no CSV e no Excel sai com o nome «Descricao».
DESCRICAO_ARTIGO = "Descricao do artigo"
COLUNAS_NOVAS: tuple[str, ...] = (
    "Artigo", "Artigo/SubArtigo", DESCRICAO_ARTIGO, "ArtigoNome", "ISPEC", "Posicao",
)
COLUNAS_CSV: tuple[str, ...] = COLUNAS_IMOS + COLUNAS_NOVAS
# Nome de cada coluna no cabeçalho do CSV (a macro procura pelo nome; a 1.ª
# «Descricao», a da peça, é a que ela encontra primeiro).
CABECALHO_CSV: dict[str, str] = {DESCRICAO_ARTIGO: "Descricao"}

# Peças não retangulares (ISPEC <> 0): a forma faz-se na CNC. Cada aresta do contorno
# tem de levar o perfil de recorte (o perfil tem o CAM da fresa) e a orla vem depois
# da CNC. Na IDBPRF: PRFID = «Nome de perfil»; o 1.º algarismo do PRFB = «Sequência
# de processamento» (3 = «Orla depois de CNC»; 1 = o normal, orla antes).
PERFIS_RECORTE: tuple[str, ...] = ("FRESAR_RECORTES_VARADO",)
SEQUENCIA_ORLA_DEPOIS_CNC = "3"

# A frente de gaveta em U (multipeça): descrição da linha da mãe na lista.
DESCRICAO_FRENTE_U = "Frente Gaveta |U|"
# O que significa o ISPEC (forma da peça na IDBGPL).
FORMAS_ISPEC = {
    1: "4 lados, não retangular",
    2: "mais de 4 lados",
}

# Onde ficam os ficheiros do ensaio: numa subpasta da obra, para nenhuma função
# do Martelo (Enviar CUT-RITE, Analisar, PDFs) os confundir com a Lista Material.
PASTA_ENSAIO = "Ensaio_Lista_Base_iMos"
# Onde o .cfg escreve o CSV (a mesma pasta da macro Import_CSV_Imos_1).
PASTAS_CSV_IMOS: tuple[Path, ...] = (
    Path(r"I:\Cutrite\Work\Cutrite_Import_CSV"),
    Path(r"\\SERVER_LE\Homag_iX\Cutrite\Work\Cutrite_Import_CSV"),
)

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
    # Linha da peça-mãe de uma multipeça (a frente em U): não se compara com o .cfg.
    mae: bool = False
    # Peça não retangular: o que falta para a CNC lhe dar a forma (ver pecas_forma_sem_cam).
    falhas_forma: list[str] = field(default_factory=list)

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
        "SELECT ID, CNT, NAME1, MATID, MATNAME, MATGRID, CLENG, CWIDTH, CTHK, INFO1, "
        f"PARTPOSSTR, ISPEC, MPE_TYPE, PARENT_ID FROM IDBGPL WHERE ORDERID = {obra} "
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
        cfg,
        f"SELECT ID, PRFNO, PRFNAME, PRFID, PRFB, PTYPE FROM IDBPRF WHERE ORDERID = {obra}",
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


def artigo_composto(artigo_nome: str, sub_artigo: str, descricao: str) -> str:
    """A coluna Artigo da lista: ``ArtigoNome[_Artigo/SubArtigo]_Descricao``.

    Regra do Paulo (19-11-2026, Excel da obra 1957_01_26): a ``Descricao`` é a do artigo
    (ex.: RP_A_01_MENINA); o Artigo/SubArtigo só entra quando é diferente do ArtigoNome
    (ex.: RP_A_01_GV1_MENINA). As partes vazias não entram. A Posicao não entra.
    """
    partes = [artigo_nome]
    if sub_artigo and sub_artigo != artigo_nome:
        partes.append(sub_artigo)
    partes.append(descricao)
    return "_".join(p for p in partes if p)


def _falhas_forma(arestas: list[dict]) -> list[str]:
    """O que falta às arestas de uma peça não retangular para a CNC lhe dar a forma.

    Todas as arestas do contorno (``PTYPE`` diferente de «I») têm de ter o perfil de
    recorte (``PERFIS_RECORTE``) com a «Sequência de processamento» «Orla depois de CNC».
    """
    if not arestas:
        return ["sem arestas na base"]
    sem_perfil = [a for a in arestas if _texto(a.get("PRFID")) not in PERFIS_RECORTE]
    com_perfil = [a for a in arestas if a not in sem_perfil]
    sequencia_errada = [
        a for a in com_perfil
        if not _texto(a.get("PRFB")).startswith(SEQUENCIA_ORLA_DEPOIS_CNC)
    ]
    falhas = []

    def lados(lista: list[dict]) -> str:
        numeros = sorted(_inteiro(a.get("PRFNO")) for a in lista)
        return ", ".join(str(n) for n in numeros)

    if sem_perfil:
        falhas.append(
            f"aresta(s) {lados(sem_perfil)} de {len(arestas)} sem o perfil "
            f"{' / '.join(PERFIS_RECORTE)}"
        )
    if sequencia_errada:
        falhas.append(
            f"aresta(s) {lados(sequencia_errada)} sem «Orla depois de CNC»"
        )
    return falhas


def _e_frente_u(peca: dict, maes_com_filhas: set[int]) -> bool:
    """A peça-mãe da frente de gaveta em U, que vai à lista sem material."""
    return (
        _inteiro(peca.get("MPE_TYPE")) == 1
        and _inteiro(peca.get("ID")) in maes_com_filhas
        and "frente" in _texto(peca.get("NAME1")).casefold()
    )


def montar_lista(dados: DadosObraImos) -> list[LinhaCorte]:
    """Monta as linhas da lista de corte, juntando as peças com as colunas todas iguais."""
    acima = _cadeia_artigos(dados)
    # Os IDs mudam sempre que a obra é gravada: liga-se pelo PARENT_ID desta leitura.
    maes_com_filhas = {
        _inteiro(p.get("PARENT_ID")) for p in dados.pecas if _inteiro(p.get("PARENT_ID"))
    }
    programas = _programas_por_peca(dados)
    orlas: dict[int, dict[str, str]] = defaultdict(dict)
    arestas: dict[int, list[dict]] = defaultdict(list)
    for linha in dados.orlas:
        if _texto(linha.get("PTYPE")).upper() == "I":
            continue  # perfis interiores (rasgos, cavidades)
        arestas[_inteiro(linha.get("ID"))].append(linha)
        coluna = ORLAS.get(_inteiro(linha.get("PRFNO")))
        if coluna:
            orlas[_inteiro(linha.get("ID"))][coluna] = _texto(linha.get("PRFNAME"))
    cab = dados.cabecalho

    linhas: dict[tuple, LinhaCorte] = {}
    for peca in dados.pecas:
        material = _texto(peca.get("MATNAME")) or _texto(peca.get("MATID"))
        mae = not material and _e_frente_u(peca, maes_com_filhas)
        if not material and not mae:
            continue  # sem material: o .cfg também não a exporta
        id_peca = _inteiro(peca.get("ID"))
        artigos = acima(id_peca)
        quantidade = _numero(peca.get("CNT"))
        for artigo in artigos:
            quantidade *= artigo["quantidade"]
        ncs = programas.get(id_peca, [])
        descricao = DESCRICAO_FRENTE_U if mae else _texto(peca.get("NAME1"))
        sub_artigo = artigos[0]["nome"] if artigos else ""
        artigo_nome = artigos[-1]["nome"] if artigos else ""
        rp = _texto(peca.get("PARTPOSSTR")).split(".")[0]
        descricao_artigo = _piso(artigos)
        colunas = {
            "Descricao": descricao,
            "Material": material,
            "Comp.": f"{_numero(peca.get('CLENG')):.1f}",
            "Larg.": f"{_numero(peca.get('CWIDTH')):.1f}",
            "Esp": f"{_numero(peca.get('CTHK')):.1f}",
            "Veio": "0" if _inteiro(peca.get("MATGRID")) == 0 else "1",
            "CNC_1": ncs[0] if ncs else "",
            "CNC_2": ncs[1] if len(ncs) > 1 else "",
            "Enc.": _texto(cab.get("ARTICLENO")),
            "Cliente": _texto(cab.get("CLIENT")),
            "RP": rp,
            "Notas": _texto(peca.get("INFO1")),
            "Artigo": artigo_composto(artigo_nome, sub_artigo, descricao_artigo) or rp,
            "Artigo/SubArtigo": sub_artigo,
            DESCRICAO_ARTIGO: descricao_artigo,
            "ArtigoNome": artigo_nome,
            "ISPEC": str(_inteiro(peca.get("ISPEC"))),
            "Posicao": rp,
        }
        for coluna in ORLAS.values():
            # A mãe da frente em U não leva orlas: as filhas já as têm (senão o
            # ResumoOrlas contava-as duas vezes).
            colunas[coluna] = "" if mae else orlas.get(id_peca, {}).get(coluna, "")
        chave = tuple(colunas[c] for c in COLUNAS_CSV if c != "Qt.")
        if chave not in linhas:
            linhas[chave] = LinhaCorte(colunas=colunas, mae=mae)
        linhas[chave].qt += quantidade
        if not mae and _inteiro(peca.get("ISPEC")) != 0:
            for falha in _falhas_forma(arestas.get(id_peca, [])):
                if falha not in linhas[chave].falhas_forma:
                    linhas[chave].falhas_forma.append(falha)
    # Como o .cfg (POSITION_SORT): por posição; dentro dela, pela ordem das peças.
    return sorted(linhas.values(), key=lambda l: l.colunas["RP"])


def pecas_forma_sem_cam(linhas: list[LinhaCorte]) -> list[str]:
    """As peças não retangulares (ISPEC <> 0) que a CNC não vai recortar, para avisar.

    Uma peça com contorno especial tem de ser feita na CNC. Avisa quando:

    - não tem programa CAM (CNC_1 vazio). O ``NCNO`` não serve: o iMos preenche-o
      sempre (é o número reservado); vale o programa na base (``IDBCAMPROGRAM``);
    - tem programa (ex.: só furos), mas alguma aresta do contorno não tem o perfil de
      recorte ou não está com «Orla depois de CNC» (ideia do Paulo, 19-11-2026): sem
      isso a fresa não dá a forma à peça.
    """
    avisos = []
    for linha in linhas:
        ispec = _inteiro(linha.valor("ISPEC"))
        if linha.mae or ispec == 0:
            continue
        falhas = ([] if linha.valor("CNC_1") else ["sem programa CAM"]) + linha.falhas_forma
        if not falhas:
            continue
        forma = FORMAS_ISPEC.get(ispec, f"forma especial, ISPEC {ispec}")
        avisos.append(
            f"{linha.valor('Descricao')} ({linha.valor('Comp.')} x {linha.valor('Larg.')}, "
            f"{linha.valor('Artigo')}; {forma}): " + "; ".join(falhas)
        )
    return avisos


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def escrever_csv(linhas: list[LinhaCorte], destino: Path) -> Path:
    """Escreve o CSV como o do iMos: «;», CRLF, ANSI e uma «;» no fim de cada linha."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = ["".join(f"{CABECALHO_CSV.get(c, c)};" for c in COLUNAS_CSV)]
    for linha in linhas:
        texto.append("".join(f"{linha.valor(c).replace(';', ',')};" for c in COLUNAS_CSV))
    destino.write_bytes(("\r\n".join(texto) + "\r\n").encode("cp1252", errors="replace"))
    return destino


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    """Lê um CSV da lista de corte (do .cfg ou deste módulo).

    A 2.ª coluna «Descricao» (a do artigo, neste módulo) fica com a chave
    ``DESCRICAO_ARTIGO``, para não tapar a da peça.
    """
    with Path(caminho).open(encoding="cp1252", errors="replace", newline="") as f:
        leitor = csv.reader(f, delimiter=";")
        cabecalho = next(leitor, [])
        nomes: list[str] = []
        for nome in (c.strip() for c in cabecalho):
            if nome == "Descricao" and nome in nomes:
                nome = DESCRICAO_ARTIGO
            nomes.append(nome)
        return [
            {k: (v or "").strip() for k, v in zip(nomes, valores) if k}
            for valores in leitor
            if any(v.strip() for v in valores)
        ]


# ---------------------------------------------------------------------------
# Comparação com o CSV do .cfg
# ---------------------------------------------------------------------------

_COLUNAS_COMPARADAS = (
    "Veio", "Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO", "CNC_1", "CNC_2",
    "Enc.", "Cliente",
)


def comparar_com_csv_imos(
    linhas: list[LinhaCorte], linhas_csv: list[dict[str, str]], *, maximo: int = 40
) -> ComparacaoLista:
    """Compara a lista da base com o CSV do .cfg, peça a peça e coluna a coluna.

    Agrupa pelas colunas que identificam a peça (descrição, material, medidas, posição,
    notas) e compara as quantidades e o resto das colunas do CSV antigo. As colunas
    novas não entram: o .cfg não as tem; nem a linha da frente em U, que o .cfg
    nunca exporta.
    """
    col_pos = next(
        (c for c in ("RP", "Posicao", "Artigo") if linhas_csv and c in linhas_csv[0]), "RP"
    )

    def chave(get, pos) -> tuple:
        return (get("Descricao"), get("Material"), get("Comp."), get("Larg."), get("Esp"),
                pos, get("Notas"))

    qt_base: dict[tuple, float] = defaultdict(float)
    qt_csv: dict[tuple, float] = defaultdict(float)
    val_base: dict[tuple, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    val_csv: dict[tuple, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for linha in linhas:
        if linha.mae:
            continue
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
            desc, mat, comp, larg, _, pos, notas = k
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
        linhas_base=sum(1 for l in linhas if not l.mae),
        linhas_csv=len(linhas_csv),
        diferencas=diferencas,
    )


# ---------------------------------------------------------------------------
# Ensaio: ficheiros na subpasta da obra
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EnsaioListaBase:
    """Os ficheiros do ensaio de uma obra e o resultado da comparação."""

    pasta: Path
    csv: Path
    relatorio: Path
    excel: Path
    csv_imos: Path | None
    comparacao: ComparacaoLista | None
    resumo: str


def procurar_csv_imos(
    nome_enc: str, pastas: tuple[Path, ...] = PASTAS_CSV_IMOS
) -> Path | None:
    """O CSV do .cfg que a ``Import_CSV_Imos_1`` importaria para esta obra.

    A macro aceita o 1.º ``*.csv`` com o nome da obra; aqui vale primeiro o nome
    exato que o .cfg escreve (``<obra>_Lista_Corte.csv``).
    """
    nome = _texto(nome_enc)
    if not nome:
        return None
    for pasta in pastas:
        try:
            exato = pasta / f"{nome}_Lista_Corte.csv"
            if exato.is_file():
                return exato
            if not pasta.is_dir():
                continue
            for ficheiro in sorted(pasta.glob("*.csv")):
                if nome.casefold() in ficheiro.name.casefold():
                    return ficheiro
        except OSError:
            continue
    return None


def _hora(valor: datetime | None) -> str:
    return valor.strftime("%d-%m-%Y %H:%M") if valor else "(sem data)"


def gravar_ensaio(
    pasta_obra: Path,
    dados: DadosObraImos,
    linhas: list[LinhaCorte],
    *,
    csv_imos: Path | None = None,
    agora: datetime | None = None,
) -> EnsaioListaBase:
    """Escreve o CSV e o relatório da comparação na subpasta de ensaio da obra."""
    pasta = Path(pasta_obra) / PASTA_ENSAIO
    nome = dados.nome
    csv_base = escrever_csv(linhas, pasta / f"{nome}_Lista_Corte_Base.csv")
    pecas = sum(l.qt for l in linhas)

    texto = [
        "Lista de corte lida pelo Martelo da base do iMos — ENSAIO",
        f"Obra: {nome}",
        f"Lida em: {_hora(agora or datetime.now())}",
        f"Desenho gravado no iMos: {_hora(dados.ultima_gravacao)}",
        f"Lista da base: {len(linhas)} linhas, {pecas:g} peças",
    ]
    comparacao = None
    if csv_imos is None:
        texto.append("CSV do iMos: não encontrado — não houve comparação.")
    else:
        try:
            exportado = datetime.fromtimestamp(csv_imos.stat().st_mtime)
            comparacao = comparar_com_csv_imos(linhas, ler_csv(csv_imos))
        except OSError as erro:
            texto.append(f"CSV do iMos: não foi possível ler {csv_imos} ({erro}).")
        else:
            texto.append(
                f"CSV do iMos: {csv_imos} (exportado {_hora(exportado)}): "
                f"{comparacao.linhas_csv} linhas, {comparacao.pecas_csv:g} peças"
            )
            if dados.ultima_gravacao and dados.ultima_gravacao > exportado:
                texto.append(
                    "ATENÇÃO: o desenho foi gravado DEPOIS de o CSV ser exportado; as "
                    "diferenças podem ser só isso. Exporte o CSV outra vez para comparar."
                )
            if comparacao.iguais:
                texto.append("Resultado: as peças, quantidades e colunas do CSV são IGUAIS.")
            else:
                texto.append(f"Resultado: {len(comparacao.diferencas)} diferença(s):")
                texto.extend(f"  - {d}" for d in comparacao.diferencas)
    texto.append(
        "As linhas iguais em todas as colunas ficam numa só (o .cfg às vezes parte-as); "
        "por isso o número de linhas pode ser menor com as mesmas peças."
    )
    maes = [l for l in linhas if l.mae]
    if maes:
        texto.append(
            f"Frente em U: {len(maes)} linha(s) «{DESCRICAO_FRENTE_U}» sem material "
            "(o Cut-Rite não as corta; cortam-se as peças que as compõem). O CSV do "
            "iMos não as tem: ficam fora da comparação."
        )
    sem_cam = pecas_forma_sem_cam(linhas)
    if sem_cam:
        texto.append(
            f"ATENÇÃO: {len(sem_cam)} peça(s) não retangular(es) que a CNC não vai "
            "recortar (falta o CAM, ou o perfil de recorte / «Orla depois de CNC» "
            "nas arestas):"
        )
        texto.extend(f"  - {p}" for p in sem_cam)
    texto.append(
        "Coluna Artigo = ArtigoNome_Descricao do artigo, com o Artigo/SubArtigo no meio "
        "quando é diferente do ArtigoNome. Colunas só no separador da importação: "
        "Artigo/SubArtigo, Descricao (do artigo), ArtigoNome, ISPEC, Posicao. Saíram: "
        + ", ".join(COLUNAS_TIRADAS) + "."
    )
    resumo = "\r\n".join(texto)
    relatorio = pasta / f"{nome}_Comparacao_com_CSV_iMos.txt"
    relatorio.write_text(resumo + "\r\n", encoding="utf-8-sig", newline="")
    return EnsaioListaBase(
        pasta=pasta,
        csv=csv_base,
        relatorio=relatorio,
        excel=pasta / f"Lista_Material_{nome}_BASE.xlsm",
        csv_imos=csv_imos,
        comparacao=comparacao,
        resumo=resumo.replace("\r\n", "\n"),
    )
