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

Outros usos:
    ... --obra <txt>      comandos para colar numa obra que já tem os DV_* (cotas centradas, R5/R6)
    ... --manual <txt>    o mesmo + IMOS_Text35 à escala dos DV_*, camadas e Model a 1:20 (os
                          estilos de texto não: o iX CAD não tem -STYLE)
    ... --dwt <scr> <dwt> script da consola que faz o IMOS.dwt novo a partir de uma CÓPIA do
                          original (R7 + R8; só acrescenta/ajusta, layouts iguais)
    ... --dwt-r8 <scr> <dwt>  o mesmo, a partir de uma cópia do IMOS.dwt da R7
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


# R7 (06-10): estilos para o Paulo escrever e cotar À MÃO no Model, a 1:1.
# Porquê: o IMOS.dwt abre as obras com o texto IMOS_Text35 e a cota IMOS_VIEW_RED, que são
# anotativos com 35 mm de PAPEL (o iMos pensou-os para ver no Model a 1:1). Quando a escala de
# anotação muda (o batch põe 1:16, 1:25...), o ANNOAUTOSCALE 4 acrescenta-lhes essa escala e
# saem com 35-135 mm na folha. Os DV_* são anotativos em mm de papel a sério: saem sempre com a
# mesma altura na folha, em qualquer janela. A letra é a do IMOS_Text35 (simplex, largura 0,8).
TEXTOS = {  # nome -> altura no papel (mm); o último fica o estilo atual
    "DV_Titulo": 5.0,
    "DV_Texto": 2.5,
}
CAMADAS = {"DV_Texto": 7, "DV_Titulo": 5}  # a cor vem da camada: 7 = preto na folha, 5 = azul
ESCALA_MODELO = "1:20"   # escala de anotação do Model: o texto de 2,5 mm vê-se com 50 mm
# R8: o Paulo cota à mão com o IMOS_Text35 (vermelho, setas, 1 casa decimal) e quer continuar.
# Fica com isso, mas com as medidas e o texto dos DV_* (35 -> 2,5 mm de papel; o estilo de
# texto IMOS_Text35 tem altura fixa 35 e mandava sobre o DIMTXT, por isso o texto passa a ISO).
COTA_MANUAL = "IMOS_Text35"
MEDIDAS_IMOS = [("DIMTXSTY", ESTILO_TEXTO), ("DIMTXT", "2.5"), ("DIMASZ", "1.5"), ("DIMEXO", "1"),
                ("DIMEXE", "1"), ("DIMGAP", "0.6"), ("DIMDLI", "7")]


def linhas_cota_imos() -> list[str]:
    """Redefine o IMOS_Text35 (cota) com as medidas e o comportamento dos DV_* (anotativo)."""
    out = ["-DIMSTYLE", "_R", COTA_MANUAL]
    for var, val in MEDIDAS_IMOS + CENTRADO:
        out += [var, val]
    return out + ["-DIMSTYLE", "_AN", "_Y", COTA_MANUAL, "_Y", "", COTA_MANUAL]


# R8: os 2 MTEXT que o Paulo pôs no Model do IMOS.dwt (título azul e lista de materiais) estão
# no estilo de texto IMOS_Text35 com 135 e 50 mm de PAPEL. A consola não muda o estilo de um
# MTEXT (o CHANGE não os aceita), mas o SCALE muda a altura no papel e todas as escalas do texto
# acompanham: o título fica com 5 mm, a lista com 2,5 mm, no mesmo sítio. A letra é a mesma
# do DV_Texto (simplex 0,8). (janela de seleção a 1:1, ponto de inserção, fator)
TEXTOS_DWT = [
    (("-200,-1740", "4500,-2200"), "28.06911352074531,-1744.13859053227", 5 / 135),
    (("-200,-1100", "4500,-1738"), "620.2358320677331,-1219.592357625775", 2.5 / 50),
]


def linhas_textos(comando: str = "-STYLE") -> list[str]:
    """Estilos de texto anotativos. No iX CAD é -STYLE; na consola é _.STYLE (não tem -STYLE)."""
    out = []
    for nome, altura in TEXTOS.items():
        # fonte, Annotative, Sim, não acompanha o layout, altura no papel, largura, inclinação,
        # ao contrário, de pernas para o ar, vertical
        out += [comando, nome, "simplex.shx", "_A", "_Y", "_N", str(altura), "0.8", "0",
                "_N", "_N", "_N"]
    return out


def linhas_camadas() -> list[str]:
    out = ["-LAYER"]
    for nome, cor in CAMADAS.items():
        out += ["_N", nome, "_C", str(cor), nome]
    return out + [""]


def linhas_manual() -> list[str]:
    """Para colar no Model de uma obra aberta: cotas DV_* centradas (R6), IMOS_Text35 à escala
    dos DV_* (R8), camadas e escala de anotação. Os estilos de texto DV_Texto/DV_Titulo NÃO
    vão aqui: o iX CAD não tem -STYLE (teste do Paulo, 06-10), só vêm pelo IMOS.dwt."""
    out = linhas_obra()
    out += linhas_cota_imos()
    out += linhas_camadas()
    out += ["ANNOALLVISIBLE", "1", "CANNOSCALE", ESCALA_MODELO]
    return out


def _fim_dwt(destino: str) -> list[str]:
    """R8: IMOS_Text35 à escala dos DV_* e atual, os 2 MTEXT do Model a 5 e 2,5 mm de papel,
    Model a 1:20 e gravar como template."""
    out = linhas_cota_imos()
    # a 1:1 para a janela apanhar o texto pelo tamanho de 1:1; o ZOOM E põe-no no ecrã (sem
    # isso a seleção por janela da consola não encontra nada)
    out += ["CANNOSCALE", "1:1", "_.ZOOM", "_E"]
    for (c1, c2), base, fator in TEXTOS_DWT:
        out += ["_.SCALE", "_W", "_NON", c1, "_NON", c2, "", "_NON", base, f"{fator:.10f}"]
    out += ["CANNOSCALE", ESCALA_MODELO, "-DIMSTYLE", "_R", COTA_MANUAL]
    # Template: medidas (Enter = Metric) e descrição (Enter = vazia)
    return out + ["_.SAVEAS", "_T", destino, "", ""]


def linhas_dwt_r8(destino: str) -> list[str]:
    """Script da consola sobre uma CÓPIA do IMOS.dwt da R7 (o que já tem os DV_*)."""
    return ["FILEDIA", "0", "CMDDIA", "0", "OSMODE", "0", "OSNAPCOORD", "1"] + _fim_dwt(destino)


def linhas_dwt(destino: str) -> list[str]:
    """Script da consola sobre uma CÓPIA do IMOS.dwt de antes da R7: junta as cotas DV_*, as
    camadas e os estilos de texto (R7) e depois o _fim_dwt (R8). Os layouts (o "1") não são
    tocados."""
    out = ["FILEDIA", "0", "CMDDIA", "0", "OSMODE", "0", "OSNAPCOORD", "1"]
    out += linhas_estilos()
    out += linhas_camadas()
    out += linhas_textos("_.STYLE")
    return out + _fim_dwt(destino)


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
    if len(sys.argv) == 3 and sys.argv[1] == "--manual":
        Path(sys.argv[2]).write_bytes(("\r\n".join(linhas_manual()) + "\r\n").encode("ascii"))
        print(f"Comandos: {sys.argv[2]}")
        return
    if len(sys.argv) == 4 and sys.argv[1] in ("--dwt", "--dwt-r8"):
        scr = Path(sys.argv[2])
        f = linhas_dwt if sys.argv[1] == "--dwt" else linhas_dwt_r8
        scr.write_bytes(("\r\n".join(f(sys.argv[3])) + "\r\n").encode("ascii"))
        print(f"Script: {scr}")
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
