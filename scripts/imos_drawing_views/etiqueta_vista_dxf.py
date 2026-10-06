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


# Versão simples (pedido do Paulo, 06-10, R4 dos roupeiros): só o nome da vista ("Vista 1"),
# sem círculo, linha, número nem escala, encostado ao desenho. O círculo original ficava à
# ESQUERDA do ponto de inserção (centro em -58,-15 mm de papel: ~930 mm do modelo a 1:16), por
# isso a etiqueta ficava longe e alargava a vista. O iMos insere a etiqueta 5 mm à esquerda e
# 6 mm abaixo do canto inferior esquerdo da vista (medido na APAGAR_15: -80,-96 a 1:16).
#   alçado: à esquerda do desenho, na linha do chão (à direita estão as alturas);
#   planta: por baixo do canto (à esquerda está a profundidade).
SIMPLES = {
    # tipo: (x, y, alinhamento horizontal 0 esq. / 2 dir., vertical 1 baixo / 3 cima)
    "alcado": (-1.0, 6.0, 2, 1),
    "planta": (5.0, -1.0, 0, 3),
}
ALTURA_SIMPLES = 3.0


def _simples(ent: list[list[str]], tipo: str) -> list[list[str]] | None:
    """Só fica o atributo do nome, reposicionado; o resto sai."""
    if ent[0][1].strip() != "ATTDEF":
        return None
    tag = next(v for c, v in ent if c == "2").strip()
    if tag != "IMOSSECTIONNAME":
        return None
    x, y, h, v = SIMPLES[tipo]
    novo = []
    for c, val in ent:
        if c == "72":
            continue
        if c == "11":
            novo.append(["72", f"{h:>6}"])
        if c in ("10", "11"):
            val = _f(x)
        elif c in ("20", "21"):
            val = _f(y)
        elif c == "40":
            val = _f(ALTURA_SIMPLES)
        elif c == "74":
            val = f"{v:>6}"
        novo.append([c, val])
    return novo


def editar(texto: str, simples: str | None = None) -> str:
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
            if ent and simples:
                out += _simples(ent, simples) or []
            elif ent:
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
    simples = sys.argv[3] if len(sys.argv) > 3 else None  # "alcado" ou "planta"
    if simples and simples not in SIMPLES:
        sys.exit(f"Tipo simples desconhecido: {simples} ({', '.join(SIMPLES)})")
    texto = open(ent, encoding="cp1252", errors="replace").read()
    open(sai, "w", encoding="cp1252", errors="replace", newline="\r\n").write(editar(texto, simples))
    print(f"Gravado: {sai}")


if __name__ == "__main__":
    main()
