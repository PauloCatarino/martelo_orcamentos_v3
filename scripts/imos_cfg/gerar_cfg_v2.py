"""Gera o EXPORT_CSV_CUT_RITE_LE_V2.cfg a partir do EXPORT_CSV_CUT_RITE_LE.cfg em uso.

Mantém latin1 + CRLF e todo o resto do ficheiro; só troca as linhas ativas que mudam
(as antigas ficam comentadas, como o ficheiro já faz).

Ronda 3 (ensaio): SubArtigo vazio quando o nome é igual ao do artigo principal, com 3
colunas TESTE_* no fim. Para a versão final: TESTES = [].

Uso (grava no repositório; depois copiar para ``I:\\CFG`` e reimportar no princípio):

    python scripts/imos_cfg/gerar_cfg_v2.py scripts/imos_cfg/EXPORT_CSV_CUT_RITE_LE_V2.cfg
"""
import sys
from pathlib import Path

ORIGEM = Path(r"\\SERVER_LE\Homag_iX\CFG\EXPORT_CSV_CUT_RITE_LE.cfg")
destino = Path(sys.argv[1])

# SubArtigo = nome do artigo mais próximo (ARTNR) só se for diferente do nome do artigo
# principal (TOPARTICLE_NAME); senão VENEER_ID, que está sempre vazio (TEXT[] não funciona).
SUB_EXPR = "IFEQUAL[ARTNR;TOPARTICLE_NAME[ARTNR_NR_ID];VENEER_ID;ARTNR]"
TESTES = [  # (cabeçalho, expressão) - só no ensaio
    ("TESTE_IFEQUAL_TXT", "IFEQUAL[ARTNR;TOPARTICLE_NAME[ARTNR_NR_ID];TEXT[IGUAL];TEXT[DIFERENTE]]"),
    ("TESTE_IFEMPTY_CAMPO", "IFEMPTY[POSSTR;ARTNR;VENEER_ID]"),
    ("TESTE_IFEMPTY_TXT", "IFEMPTY[POSSTR;TEXT[VAZIO];TEXT[CHEIO]]"),
]

t = ORIGEM.read_bytes().decode("latin1")
assert "\r\n" in t
NL = "\r\n"

CABECALHO = NL.join([
    ";",
    "; ============================================================================",
    "; EXPORT_CSV_CUT_RITE_LE_V2.cfg - 29-10-2026 - "
    + ("ronda 3 (ENSAIO: colunas TESTE_* no fim)" if TESTES else "versão final"),
    "; Cópia do EXPORT_CSV_CUT_RITE_LE.cfg (o que está em uso) com estas mudanças:",
    ";  1) A coluna \"RP\" passa a chamar-se \"Artigo\" (o conteúdo é o mesmo: o",
    ";     artigo principal, SPLITLEFT[PARTPOSSTR;.]).",
    ";  2) Coluna nova \"SubArtigo\", logo à direita de Artigo: o nome do artigo mais",
    ";     próximo da peça (ARTNR) quando é DIFERENTE do nome do artigo principal",
    ";     (TOPARTICLE_NAME[ARTNR_NR_ID]), ex.: BL_3GVT_RP_01 dentro do RP_A_01_ESQ.",
    ";     Quando o nome é igual fica vazio (escreve VENEER_ID, sempre vazio na LE:",
    ";     o TEXT[] vazio não funciona dentro das funções).",
    ";  3) Saíram as colunas CNC, ABD e BHT (nunca tiveram dados).",
    ";  4) ACCUMULATE com ARTNR_NR_ID (o artigo onde a peça está): sem isto, peças",
    ";     iguais de sub-artigos de RPs diferentes juntavam-se numa só linha com o RP",
    ";     da primeira (ex.: obra CRW_2128_2711_01, 18 laterais de gaveta no RP_01",
    ";     quando são 6 em cada RP_01/02/03).",
    "; Ordem: Descricao..Cliente (1-15, iguais) | Artigo | SubArtigo | Notas | Notas_1",
    ";        | Cliente_Final" + (" | " + " | ".join(h for h, _ in TESTES) + " (só no ensaio)" if TESTES else ""),
    "; ATENÇÃO: as colunas 17 a 20 mudaram de sítio e \"RP\" mudou de nome. O modelo da",
    "; Lista Material (macro Import_CSV_Imos_1) ainda NÃO está adaptado: até lá, usar",
    "; este .cfg só em obras de teste (o ficheiro tem o mesmo nome do CSV normal).",
    "; Fonte com histórico: Martelo_Orcamentos_V3\\scripts\\imos_cfg\\ (README.md).",
    "; ============================================================================",
    "",
])


def trocar(texto: str, antigo: str, novo: str) -> str:
    assert texto.count(antigo) == 1, antigo[:60]
    return texto.replace(antigo, novo)


# 1) cabeçalho logo depois das 5 linhas iniciais
fim_intro = "; * Standard Comma Delimmited Table *" + NL + "; ***********************************" + NL
t = trocar(t, fim_intro, fim_intro + CABECALHO)

# 2) ACCUMULATE
acc = "ACCUMULATE=CPID;MATID;FLENG;FWIDTH;INFO5;POSSTR;NAME1;AUFTRAG"
t = trocar(
    t,
    acc + NL,
    ";Original (até à V2): " + acc + NL
    + "; V2: + ARTNR_NR_ID, para não juntar peças de sub-artigos de RPs diferentes" + NL
    + acc + ";ARTNR_NR_ID" + NL,
)

# 3) cabeçalho das colunas
hdr_antigo = 'STRING_MAT_HEADER=("Descricao;Material;Comp.;Larg.;Esp;Qt.;Veio;Orla ESQ;Orla DIR;Orla CIMA;Orla BAIXO;CNC_1;CNC_2;Enc.;Cliente;RP;Notas;Notas_1;Cliente_Final;CNC;ABD;BHT;\\r\\n")'
hdr_novo = ('STRING_MAT_HEADER=("Descricao;Material;Comp.;Larg.;Esp;Qt.;Veio;Orla ESQ;Orla DIR;Orla CIMA;Orla BAIXO;CNC_1;CNC_2;Enc.;Cliente;Artigo;SubArtigo;Notas;Notas_1;Cliente_Final;'
            + "".join(h + ";" for h, _ in TESTES) + '\\r\\n")')
t = trocar(
    t,
    hdr_antigo + NL,
    ";Original (até à V2): " + hdr_antigo + NL
    + "; V2: RP passa a Artigo; + SubArtigo à direita; sem CNC/ABD/BHT" + NL
    + hdr_novo + NL,
)

# 4) linha das peças
mat_antigo = (
    'STRING_MAT=("%s;%s;%-.1f;%-.1f;%-.1f;%-.0f;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;\\r\\n",'
    "NAME1,REPLACE_EMPTY[MATNAME;MATID],CLENG,CWIDTH,CTHK,CNT,ARDISGRAINNEW[MATGROR],1_([PRFNAME1]),PRFNAME3,PRFNAME4,PRFNAME2,"
    "PXM_PROGRAM_INFO_VALID[ID;1;ncnum;fileextension],PXM_PROGRAM_INFO_VALID[ID;2;ncnum;fileextension],IMORDER_NR,IMORDER_CLIENT,"
    "SPLITLEFT[PARTPOSSTR;.],IDENT_INFO1,IDENT_INFO2,IMORDER_CUSTOMER,"
    "CAMINFO[NCNO;MACHNAME;1;1],CAMINFO[NCNO;MACHNAME;2;1],CAMINFO[NCNO;MACHNAME;3;1])"
)
N = 20 + len(TESTES)
mat_novo = (
    'STRING_MAT=("%s;%s;%-.1f;%-.1f;%-.1f;%-.0f;' + "%s;" * (N - 6) + '\\r\\n",'
    "NAME1,REPLACE_EMPTY[MATNAME;MATID],CLENG,CWIDTH,CTHK,CNT,ARDISGRAINNEW[MATGROR],1_([PRFNAME1]),PRFNAME3,PRFNAME4,PRFNAME2,"
    "PXM_PROGRAM_INFO_VALID[ID;1;ncnum;fileextension],PXM_PROGRAM_INFO_VALID[ID;2;ncnum;fileextension],IMORDER_NR,IMORDER_CLIENT,"
    "SPLITLEFT[PARTPOSSTR;.]," + SUB_EXPR + ","
    "IDENT_INFO1,IDENT_INFO2,IMORDER_CUSTOMER" + "".join("," + e for _, e in TESTES) + ")"
)
fmt, args = mat_novo.split('\\r\\n",')
n_fmt, n_args = fmt.count("%"), len(args.rstrip(")").split(","))
assert n_fmt == n_args == N, (n_fmt, n_args)
assert hdr_novo.count(";") == N, hdr_novo.count(";")  # cada coluna acaba em ";"
t = trocar(
    t,
    mat_antigo + NL,
    ";Original (até à V2):" + NL + ";" + mat_antigo + NL
    + "; V2: 1-15 iguais; 16 Artigo (era RP); 17 SubArtigo (vazio se o nome = artigo principal); 18 Notas; 19 Notas_1; 20 Cliente_Final"
    + ("; 21-" + str(N) + " TESTE_* (só no ensaio)" if TESTES else "") + NL
    + mat_novo + NL,
)

destino.write_bytes(t.encode("latin1"))
print("Gravado", destino, len(t.encode("latin1")), "bytes")
