"""Desenho em arame (seis vistas) a partir das arestas que o ``arestas.ps1`` extrai.

Serve para perceber a peça logo a seguir à conversão do STEP — antes de haver um
sólido limpo para cortar — e para ver uma peça de cada vez (cada camada tem a sua
cor; o ``arestas.ps1 -Camadas`` põe as arestas de cada peça na camada dela).

Uso::

    python -m scripts.imos_ferragens.arame peca_arestas.dxf --saida peca_arame.png
    python -m scripts.imos_ferragens.arame peca_arestas.dxf --saida p.png --camadas 3,10,16

Imprime também a caixa de cada camada (mm).
"""

from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

from scripts.imos_ferragens.dxf_leitura import ler_arestas  # noqa: E402


def _iso(p: np.ndarray, d) -> np.ndarray:
    d = np.asarray(d, float)
    d /= np.linalg.norm(d)
    r = np.cross(d, [0, 0, 1.0])
    r /= np.linalg.norm(r)
    return np.stack([p @ r, p @ np.cross(r, d)], 1)


VISTAS = [
    ("frente X-Z (a olhar para +Y)", lambda p: p[:, [0, 2]]),
    ("lado Y-Z (a olhar para -X)", lambda p: p[:, [1, 2]]),
    ("cima X-Y", lambda p: p[:, [0, 1]]),
    ("3/4 (1,-1,0.7)", lambda p: _iso(p, [-1, 1, -0.7])),
    ("3/4 (-1,-1,0.7)", lambda p: _iso(p, [1, 1, -0.7])),
    ("3/4 (1,1,0.7)", lambda p: _iso(p, [-1, -1, -0.7])),
]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("arestas", help="DXF gravado pelo arestas.ps1")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--camadas", help="só estas camadas, separadas por vírgulas")
    args = ap.parse_args(argv)
    polis = ler_arestas(args.arestas)
    if args.camadas:
        queridas = set(args.camadas.split(","))
        polis = [(c, p) for c, p in polis if c in queridas]
    if not polis:
        raise SystemExit("Nenhuma aresta (camadas certas?)")
    camadas = sorted({c for c, _ in polis}, key=lambda s: (len(s), s))
    paleta = plt.get_cmap("tab20")
    cor = {c: paleta(n % 20) for n, c in enumerate(camadas)}
    for c in camadas:
        P = np.vstack([p for cc, p in polis if cc == c])
        print(f"camada {c:>4}: min={P.min(0).round(2)} max={P.max(0).round(2)}")
    fig, eixos = plt.subplots(2, 3, figsize=(18, 13))
    for ax, (titulo, f) in zip(eixos.flat, VISTAS):
        for c in camadas:
            segs = []
            for cc, p in polis:
                if cc == c:
                    q = f(p)
                    segs.extend(np.stack([q[:-1], q[1:]], 1))
            ax.add_collection(LineCollection(segs, colors=[cor[c]], linewidths=0.5, label=c))
        ax.autoscale()
        ax.set_aspect("equal")
        ax.set_title(titulo)
        ax.grid(alpha=0.3)
    eixos.flat[0].legend(fontsize=7, loc="upper left")
    plt.tight_layout()
    plt.savefig(args.saida, dpi=80)
    print("gravado", args.saida)


if __name__ == "__main__":
    main()
