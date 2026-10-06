"""Gera o script (.scr) da consola do iX CAD que cria os estilos de cota DV_* das Drawing Views.

Porquê (testes de 05-10-2026):
- Os IMOS_VIEW_* da LE têm texto de 35 mm e são anotativos. O Output batch põe a escala de
  anotação igual à da folha (1:20, 1:25...) e as cotas saíam 20-25 vezes maiores.
- Os estilos DV_* estão em mm de PAPEL (texto de 2,5 mm) e são anotativos, como manda a ajuda
  do iMos, e saem sempre do mesmo tamanho na folha.
- O texto usa o estilo "ISO" (isocp.shx, altura 0). O estilo "IMOS" que o IMOS_VIEW traz tem
  altura FIXA de 25: o DIMTXT era ignorado e o texto saía com 25 mm de papel (2.º batch).
- O iMos procura o estilo de cada linha da cotagem no desenho, e se não o encontrar, no
  config\\imos.dwt e no config\\imosBlocks.dwg (mensagem "Dimstyle ... not found"). O
  imosBlocks.dwg não existia: este script cria-o, só com estes estilos, e assim o imos.dwt
  partilhado fica como está.
- O 1.º nome (DV_COTA_*) ficou na ORC_260881_2604023 com o texto de 25 mm. Como o desenho
  manda sobre o imosBlocks.dwg, os estilos passaram a chamar-se DV_AZUL, DV_VERMELHO...

Partem do IMOS_VIEW (estilo do iMos em mm de papel, anotativo) e mudam:
- cor da linha, das chamadas e do texto;
- sem casas decimais;
- traço oblíquo nas pontas;
- texto por cima da linha, com fundo branco (DIMTFILL);
- texto que não cabe sai para fora sem linha de chamada (DIMTMOVE 2).

Uso (o .scr corre na consola sobre uma CÓPIA do config\\IMOS.dwt):
    python scripts/imos_drawing_views/estilos_cota_dv.py <script.scr> <imosBlocks.dwg>
O script apaga o desenho da cópia, cria os estilos, desenha uma cota com cada um e grava só
essas cotas (-WBLOCK) no imosBlocks.dwg: o ficheiro leva os estilos e o estilo de texto ISO,
e nada mais do IMOS.dwt.
"""
from __future__ import annotations

import sys
from pathlib import Path

ESTILOS = {  # nome -> cor ACI
    "DV_AZUL": 5,
    "DV_MAGENTA": 6,
    "DV_VERMELHO": 1,
    "DV_PRETO": 7,
    "DV_VERDE": 3,
}

ESTILO_TEXTO = "ISO"  # isocp.shx, altura 0 (o "IMOS" tem altura fixa 25)

COMUNS = [  # (variável, valor) em mm de papel
    ("DIMTXSTY", ESTILO_TEXTO),
    ("DIMTXT", "2.5"), ("DIMASZ", "1.5"), ("DIMBLK", "_ArchTick"), ("DIMEXO", "1"),
    ("DIMEXE", "1"), ("DIMGAP", "0.6"), ("DIMTAD", "1"), ("DIMJUST", "0"), ("DIMTIH", "0"),
    ("DIMTOH", "0"), ("DIMTMOVE", "2"), ("DIMATFIT", "3"), ("DIMTIX", "0"), ("DIMDEC", "0"),
    ("DIMZIN", "8"), ("DIMTFILL", "1"),
]


# R5 (06-10, pedido do Paulo para estes 4 estilos): texto centrado na linha (DIMTAD 0) e ao
# meio (DIMJUST 0), sem fundo (DIMTFILL 0); quando não cabe entre as chamadas, o texto sai
# para o lado e a linha de cota prolonga-se até ele (DIMTMOVE 0 "Beside the dimension line",
# DIMATFIT 2 "Text" primeiro, DIMSOXD 0), como o "50" azul, em vez de ir por cima com linha de
# chamada. R6: o DV_VERMELHO também (o Paulo tinha-se esquecido dele).
CENTRADOS = {"DV_AZUL", "DV_MAGENTA", "DV_PRETO", "DV_VERDE", "DV_VERMELHO"}
CENTRADO = [("DIMTAD", "0"), ("DIMJUST", "0"), ("DIMTFILL", "0"), ("DIMTMOVE", "0"),
            ("DIMATFIT", "2"), ("DIMSOXD", "0")]


def variaveis(nome: str) -> list[tuple[str, str]]:
    base = dict(COMUNS)
    if nome in CENTRADOS:
        base.update(CENTRADO)
    return list(base.items())


def linhas_obra(nomes=sorted(CENTRADOS)) -> list[str]:
    """Para colar na linha de comandos de uma obra que já tem os estilos DV_* (o desenho manda
    sobre o imosBlocks.dwg): muda só o que o R5 mudou e regrava cada estilo, anotativo."""
    out = []
    for nome in nomes:
        out += ["-DIMSTYLE", "_R", nome]
        for var, val in CENTRADO:
            out += [var, val]
        # _AN _Y <nome> _Y = regravar anotativo por cima; "" + nome = sair com Restore
        out += ["-DIMSTYLE", "_AN", "_Y", nome, "_Y", "", nome]
    return out


def linhas_estilos() -> list[str]:
    out = []
    for nome, cor in ESTILOS.items():
        out += ["-DIMSTYLE", "R", "IMOS_VIEW"]
        for var, val in variaveis(nome):
            out += [var, val]
        for var in ("DIMCLRD", "DIMCLRE", "DIMCLRT"):
            out += [var, str(cor)]
        # o AN volta a perguntar a opção: Enter = Restore, e repõe-se o IMOS_VIEW
        out += ["-DIMSTYLE", "AN", "Y", nome, "", "IMOS_VIEW"]
    out += ["-DIMSTYLE", "R", "IMOS_VIEW"]
    return out


def linhas_imosblocks(destino: str) -> list[str]:
    """Script completo: limpa a cópia, cria os estilos, uma cota por estilo e -WBLOCK."""
    out = ["FILEDIA", "0", "CMDDIA", "0", "OSMODE", "0", "OSNAPCOORD", "1",
           "TILEMODE", "1", "_.ERASE", "_ALL", ""]
    out += linhas_estilos()
    for i, nome in enumerate(ESTILOS):
        y = i * 100
        out += ["-DIMSTYLE", "R", nome,
                "_.DIMLINEAR", "_NON", f"0,{y}", "_NON", f"500,{y}", "_NON", f"250,{y + 40}"]
    out += ["-DIMSTYLE", "R", "IMOS_VIEW"]
    # -WBLOCK: ficheiro, Enter = desenho novo com objetos, ponto base, objetos
    out += ["-WBLOCK", destino, "", "_NON", "0,0", "_ALL", ""]
    return out


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--obra":
        # texto para colar na linha de comandos da obra aberta (uma resposta por linha)
        Path(sys.argv[2]).write_bytes(("\r\n".join(linhas_obra()) + "\r\n").encode("ascii"))
        print(f"Comandos: {sys.argv[2]}")
        return
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    scr, dwg = Path(sys.argv[1]), sys.argv[2]
    # write_bytes: o write_text em Windows voltava a converter os \n e cada linha levava um
    # Enter a mais (\r\r\n), o que desalinha as perguntas do -DIMSTYLE
    scr.write_bytes(("\r\n".join(linhas_imosblocks(dwg)) + "\r\n").encode("ascii"))
    print(f"Script: {scr}")


if __name__ == "__main__":
    main()
