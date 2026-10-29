"""Gera o EXPORT_CSV_CUT_RITE_LE_V1.cfg (Posicao, Artigo/SubArtigo e Piso) a partir da V2.

A V2 (``EXPORT_CSV_CUT_RITE_LE_V2.cfg``, testada na APAGAR_14 a 29-10-2026) fica como está,
como cópia de referência. Este .cfg muda só as colunas 16-18, que passam a ter os nomes que
o Paulo deu aos campos do artigo no ``imos.msg`` (29-10-2026):

- 10410 «Pos. Number» → «Posicao»: a posição do artigo principal (``SPLITLEFT[PARTPOSSTR;.]``);
- 41 «Name of Element Group» → «Artigo/SubArtigo»: o nome do grupo do artigo mais próximo
  da peça (``ARTNR``);
- 1219 «Name» → «Piso»: o campo «Name» do artigo, que na base é ``IDBINFO.CPID``. No .cfg
  é o ``CP90NAME``, que a imos usa nos .cfg dela (o ``IDBCCLG25.dll`` lê-o na coluna CPID da
  ``IDBINFO`` do artigo da peça, ``ARTNR_NR_ID``). O ``ART_CPID`` do 1.º ensaio saiu vazio:
  o ``ART_<campo>`` vai ao artigo do CATÁLOGO com o nome que está no «Name».

Mantém latin1 + CRLF. Uso (grava no repositório; depois copiar para ``I:\\CFG`` e
reimportar no princípio ``EXPORT_CSV_CUT_RITE_LE_V1``):

    python scripts/imos_cfg/gerar_cfg_v1_piso.py scripts/imos_cfg/EXPORT_CSV_CUT_RITE_LE_V1.cfg
"""
import sys
from pathlib import Path

ORIGEM = Path(__file__).with_name("EXPORT_CSV_CUT_RITE_LE_V2.cfg")
destino = Path(sys.argv[1])

PISO_EXPR = "CP90NAME"

t = ORIGEM.read_bytes().decode("latin1")
NL = "\r\n"
assert NL in t


def trocar(texto: str, antigo: str, novo: str) -> str:
    assert texto.count(antigo) == 1, antigo[:60]
    return texto.replace(antigo, novo)


# 1) cabeçalho: o bloco da V1 vem antes da descrição da V2, que fica como estava
titulo_v2 = "; EXPORT_CSV_CUT_RITE_LE_V2.cfg - 29-10-2026 - versão final da exportação" + NL
t = trocar(t, titulo_v2, NL.join([
    "; EXPORT_CSV_CUT_RITE_LE_V1.cfg - 29-10-2026 - ENSAIO: Posicao, Artigo/SubArtigo e Piso",
    "; Feito a partir do EXPORT_CSV_CUT_RITE_LE_V2.cfg (testado na APAGAR_14), que fica",
    "; como cópia de referência. Mudam só as colunas 16 a 18, com os nomes que o Paulo",
    "; deu aos campos do artigo no imos.msg:",
    ";  a) \"Artigo\" passa a \"Posicao\" (o mesmo: SPLITLEFT[PARTPOSSTR;.], a posição",
    ";     do artigo principal, ex.: Fração_A).",
    ";  b) \"SubArtigo\" passa a \"Artigo/SubArtigo\" (o mesmo: ARTNR, o nome do grupo do",
    ";     artigo mais próximo da peça, ex.: RP_04_DIR, ou BL_3GVT_RP_01 num sub-artigo).",
    ";  c) Coluna nova \"Piso\" à direita: " + PISO_EXPR + ", o campo «Name» do artigo onde",
    ";     a peça está (IDBINFO.CPID; ex.: Piso 1º). Num sub-artigo vem o «Name» do",
    ";     sub-artigo, não o do principal (o Excel corrige pelo ArtigoNome); artigos",
    ";     sem piso têm \".\", o valor por defeito.",
    ";  O 1.º ensaio usou ART_CPID e saiu vazio: o prefixo ART_ vai ao artigo do",
    ";  catálogo com o nome que está no «Name». O CP90NAME é o campo que a imos usa",
    ";  nos .cfg dela para o «Name» do artigo (visto no motor, IDBCCLG25.dll).",
    "; Descrição da V2, de onde este vem:",
    "",
]))
t = trocar(
    t,
    "; Ordem: Descricao..Cliente (1-15, iguais) | Artigo | SubArtigo | Notas | Notas_1" + NL
    + ";        | Cliente_Final | ArtigoNome | ISPEC" + NL,
    "; Ordem (V1): Descricao..Cliente (1-15, iguais) | Posicao | Artigo/SubArtigo | Piso" + NL
    + ";        | Notas | Notas_1 | Cliente_Final | ArtigoNome | ISPEC" + NL,
)

# 2) cabeçalho das colunas
hdr_v2 = ('STRING_MAT_HEADER=("Descricao;Material;Comp.;Larg.;Esp;Qt.;Veio;Orla ESQ;Orla DIR;Orla CIMA;Orla BAIXO;'
          'CNC_1;CNC_2;Enc.;Cliente;Artigo;SubArtigo;Notas;Notas_1;Cliente_Final;ArtigoNome;ISPEC;\\r\\n")')
hdr_v1 = hdr_v2.replace(";Artigo;SubArtigo;", ";Posicao;Artigo/SubArtigo;Piso;")
t = trocar(
    t,
    hdr_v2 + NL,
    ";V2: " + hdr_v2 + NL
    + "; V1: Artigo passa a Posicao; SubArtigo passa a Artigo/SubArtigo; + Piso à direita" + NL
    + hdr_v1 + NL,
)

# 3) linha das peças
inicio = 'STRING_MAT=("'
linhas = t.split(NL)
idx = [i for i, ln in enumerate(linhas) if ln.startswith(inicio)]
assert len(idx) == 1, idx
mat_v2 = linhas[idx[0]]
fmt, args = mat_v2[len(inicio):].split('\\r\\n",')
assert fmt.count("%") == 22, fmt.count("%")
assert args.count(",SPLITLEFT[PARTPOSSTR;.],ARTNR,") == 1
mat_v1 = (inicio + fmt + "%s;" + '\\r\\n",'
          + args.replace(",SPLITLEFT[PARTPOSSTR;.],ARTNR,", ",SPLITLEFT[PARTPOSSTR;.],ARTNR," + PISO_EXPR + ","))
n_fmt = mat_v1.split('\\r\\n",')[0].count("%")
n_args = len(mat_v1.split('\\r\\n",')[1].rstrip(")").split(","))
assert n_fmt == n_args == 23 == hdr_v1.count(";"), (n_fmt, n_args, hdr_v1.count(";"))
linhas[idx[0]] = NL.join([
    ";V2: " + mat_v2,
    "; V1: 16 Posicao (era Artigo); 17 Artigo/SubArtigo (era SubArtigo); 18 Piso (" + PISO_EXPR
    + "); 19 Notas; 20 Notas_1; 21 Cliente_Final; 22 ArtigoNome; 23 ISPEC",
    mat_v1,
])
t = NL.join(linhas)

assert "\n" not in t.replace(NL, "")
destino.write_bytes(t.encode("latin1"))
print("Gravado", destino, len(t.encode("latin1")), "bytes")
