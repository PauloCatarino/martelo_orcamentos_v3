"""Redesenha o símbolo de nome das vistas (imosLabelElevation / imosLabelPlanview) num DXF.

O iMos põe por baixo de cada vista um círculo com o número da vista e, ao lado, o nome
("Vista 1") e a escala. Os blocos vêm de %APPDATA%\\imos AG\\iX CAD 2025\\config\\DrawingFlags.
Pedido do Paulo (05-10-2026): o texto pequeno de dentro do círculo maior, o "Vista 1" mais
pequeno e a linha horizontal mais curta. No original, o "Planta 1" (vista de origem) não
cabia no quarto de círculo e saía para fora.

Mudanças (centro do círculo em -58,-15, como no original; o ponto de inserção não mexe):
- círculo de raio 8 -> 11 (e o anel preenchido, 8,25 -> 11,25);
- número da vista 2,5 -> 3,2; textos pequenos 1,5 -> 1,8;
- nome da vista 5 -> 3,5, encostado ao círculo;
- linha horizontal: do círculo até x = -20 (era até 0).

Uso:
    python etiqueta_vista_dxf.py entrada.dxf saida.dxf
(o DXF vem da consola do iX CAD: SAVEAS DXF do DWG da pasta DrawingFlags; o
criar_etiqueta_vista.ps1 faz o caminho todo).
"""
from __future__ import annotations

import sys

CX, CY = -58.0, -15.0
R, R_ANEL = 11.0, 11.25
FIM_LINHA = -20.0
X_TEXTO = CX + R_ANEL + 2.0          # nome e escala, à direita do círculo
ALTURAS = {"IMOSSECTIONNAME": 3.5, "IMOSSECTIONINDEX": 3.2}
ALTURA_PEQUENA = 1.8


def _pares(linhas: list[str]) -> list[list[str]]:
    return [[linhas[i].strip(), linhas[i + 1].rstrip("\r")] for i in range(0, len(linhas) - 1, 2)]


def _f(v: float) -> str:
    return repr(float(round(v, 6)))


def _editar_entidade(ent: list[list[str]]) -> None:
    tipo = ent[0][1].strip()
    cod = {}
    for i, (c, v) in enumerate(ent):
        cod.setdefault(c, i)

    def pos(c: str) -> float:
        return float(ent[cod[c]][1])

    def poe(c: str, v: float) -> None:
        if c in cod:
            ent[cod[c]][1] = _f(v)

    if tipo == "CIRCLE":
        poe("40", R if pos("40") < 8.1 else R_ANEL)
    elif tipo == "LINE":
        if abs(pos("10") - pos("11")) < 1e-6:          # vertical: divide a metade de baixo
            poe("21", CY - R)
        else:                                          # horizontal: nome e escala por cima/baixo
            poe("10", CX - R_ANEL)
            poe("11", FIM_LINHA)
    elif tipo == "HATCH":
        # anel entre os dois círculos: duas fronteiras de 2 vértices com bulge +-1
        xs = [i for i, (c, _) in enumerate(ent) if c == "10"]
        for n, i in enumerate(xs[:4]):
            x = float(ent[i][1])
            raio = R_ANEL if n < 2 else R
            ent[i][1] = _f(CX - raio if x < CX else CX + raio)
    elif tipo == "ATTDEF":
        tag = ent[cod["2"]][1].strip()
        altura = ALTURAS.get(tag, ALTURA_PEQUENA)
        poe("40", altura)
        if tag == "IMOSSECTIONNAME":                    # meio-esquerda, acima da linha
            for c, v in (("10", X_TEXTO), ("11", X_TEXTO), ("20", CY + 2.5), ("21", CY + 2.5 + altura / 2)):
                poe(c, v)
        elif tag == "IMOSSECTIONSCALE":
            for c, v in (("10", X_TEXTO), ("11", X_TEXTO), ("20", CY - 1.5 - altura), ("21", CY - 1.5)):
                poe(c, v)
        elif tag == "ADDITIONAL_INFO":
            poe("11", FIM_LINHA)
            poe("21", CY - 1.5)
        elif tag == "IMOSSECTIONINDEX":                 # número, metade de cima do círculo
            poe("11", CX)
            poe("21", CY + 4.25)
        elif tag in ("IMOSSECTIONPARENTLAYOUTNAME", "IMOSSECTIONLAYOUTNAME"):
            poe("21", CY - 4.0)                          # quarto de baixo (esq.) / metade de baixo
        elif tag == "IMOSSECTIONPARENTINDEX":
            for c, v in (("10", CX + 1.5), ("11", CX + 1.5), ("21", CY - 4.0)):
                poe(c, v)


def editar(texto: str) -> str:
    linhas = texto.split("\n")
    pares = _pares(linhas)
    out: list[list[str]] = []
    sec = None
    ent: list[list[str]] | None = None
    for c, v in pares:
        if c == "0" and v.strip() == "SECTION":
            sec = "?"
        elif c == "2" and sec == "?":
            sec = v.strip()
        if sec == "ENTITIES" and c == "0":
            if ent:
                _editar_entidade(ent)
                out += ent
            ent = [[c, v]] if v.strip() not in ("ENDSEC",) else None
            if ent is None:
                out.append([c, v])
                sec = None
            continue
        if ent is not None and sec == "ENTITIES":
            ent.append([c, v])
        else:
            out.append([c, v])
    return "\n".join(f"{c}\n{v}" for c, v in out) + "\n"


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ent, sai = sys.argv[1], sys.argv[2]
    texto = open(ent, encoding="cp1252", errors="replace").read()
    open(sai, "w", encoding="cp1252", errors="replace", newline="\r\n").write(editar(texto))
    print(f"Gravado: {sai}")


if __name__ == "__main__":
    main()
