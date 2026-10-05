"""Desenha as vistas extraídas pelo extrair_vistas.ps1, para conferir sem abrir o iX CAD.

Cada cota sai na cor do seu estilo (IMOS_VIEW_BLUE = azul, ...), as etiquetas (.Label) a
vermelho escuro e o desenho da vista a preto. A imagem fica à escala pedida, como numa folha,
e o terminal lista as cotas por estilo (para conferir as cadeias sem olhar para a imagem).

Uso (a partir da raiz do repositório):
    python scripts/imos_drawing_views/ver_vistas.py C:\\temp\\dv_t1            # todas as vistas
    python scripts/imos_drawing_views/ver_vistas.py C:\\temp\\dv_t1 --escala 25
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
from scripts.imos_drawing_views.dxf2d import Desenho, desenhar  # noqa: E402
from scripts.imos_ferragens import dxf_leitura as d  # noqa: E402

COR_ESTILO = {
    "IMOS_VIEW_BLUE": "#1f4fd8", "IMOS_VIEW_MAG": "#c000c0", "IMOS_VIEW_RED": "#d00000",
    "IMOS_VIEW_BLACK": "#000000", "IMOS_VIEW_GREEN": "#008a00",
}


def _grupos(entidades):
    """Entidades de topo, cada INSERT junto com os ATTRIB/SEQEND que o seguem."""
    i = 0
    while i < len(entidades):
        j = i + 1
        if entidades[i][0] == "INSERT":
            while j < len(entidades) and entidades[j][0] in ("ATTRIB", "SEQEND"):
                j += 1
        yield entidades[i:j]
        i = j


def cotas_por_estilo(D: Desenho) -> dict[str, list]:
    por = defaultdict(list)
    for t, g in D.entidades:
        if t == "DIMENSION":
            valor = d._g(g, "1", "") or round(float(d._g(g, "42", "0") or 0), 1)
            por[(d._g(g, "3", "") or "").strip()].append(valor)
    return por


def desenhar_vista(dxf: Path, png: Path, escala: float) -> None:
    D = Desenho(dxf)
    k = 72 / 25.4 / escala  # mm do modelo -> pontos no papel
    traços = []
    for grupo in _grupos(D.entidades):
        t, g = grupo[0]
        camada = (d._g(g, "8", "") or "").strip()
        if t == "DIMENSION":
            cor = COR_ESTILO.get((d._g(g, "3", "") or "").strip(), "#0050c0")
            estilo = {"cor": cor, "lw": 0.35, "k": k}
        elif camada.endswith(".Label"):
            estilo = {"cor": "#a00000", "lw": 0.5, "k": k}
        else:
            estilo = {"cor": "#000000", "lw": 0.25, "k": k}
        traços.append((list(D.primitivas(grupo)), estilo))

    xs, ys = [], []
    for prims, _ in traços:
        for tipo, _c, dados in prims:
            if tipo == "poly":
                xs += list(dados[:, 0])
                ys += list(dados[:, 1])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    fig, ax = plt.subplots(figsize=((x1 - x0) / escala / 25.4 + 0.4, (y1 - y0) / escala / 25.4 + 0.4))
    for prims, estilo in traços:
        desenhar(ax, prims, lambda c, t, e=estilo: None if t in ("fill", "hatch") else e)
    ax.set_aspect("equal")
    ax.set_xlim(x0 - 50, x1 + 50)
    ax.set_ylim(y0 - 50, y1 + 50)
    ax.axis("off")
    fig.savefig(png, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pasta", type=Path, help="pasta de saída do extrair_vistas.ps1")
    ap.add_argument("--escala", type=float, default=20, help="1:N da imagem (por defeito 20)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    for dxf in sorted(a.pasta.glob("vista_*.dxf")):
        D = Desenho(dxf)
        print(f"== {dxf.stem}")
        for estilo, valores in cotas_por_estilo(D).items():
            print(f"   {estilo}: {valores}")
        png = dxf.with_suffix(".png")
        desenhar_vista(dxf, png, a.escala)
        print(f"   imagem: {png}")


if __name__ == "__main__":
    main()
