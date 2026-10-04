"""Folha com várias vistas de uma peça, a partir dos cortes (para conferir a forma).

Uso::

    python -m scripts.imos_ferragens.vistas peca_cortes.dxf --saida peca_vistas.png
    python -m scripts.imos_ferragens.vistas peca_cortes.dxf --saida v.png --vista=0,1,0 --vista=-1,0,0

Cada ``--vista`` é a direção para onde a câmara olha (x,y,z). Sem ``--vista`` faz
seis: quatro de 3/4 vindas de cima e duas de frente/lado. Confirmar sempre que o
"para cima" e o lado das cavilhas/furos ficaram como se quer.
"""

from __future__ import annotations

import argparse

from PIL import Image

from scripts.imos_ferragens.volume import carregar_cortes, render

VISTAS_PADRAO = ["-0.55,1,-0.45", "0.55,1,-0.45", "-0.5,-1,-0.45", "0.5,-1,-0.45", "0,1,0", "-1,0,0"]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cortes", help="DXF R12 gerado pelo cortes.ps1")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--vista", action="append", help="direção da câmara x,y,z (repetível)")
    ap.add_argument("--tamanho", type=int, default=380, help="lado de cada vista em píxeis")
    args = ap.parse_args(argv)
    cortes = carregar_cortes(args.cortes)
    vistas = args.vista or VISTAS_PADRAO
    ims = [render(cortes, [float(x) for x in v.split(",")], tamanho=args.tamanho, supersample=2)
           for v in vistas]
    colunas = min(3, len(ims))
    linhas = (len(ims) + colunas - 1) // colunas
    folha = Image.new("RGB", (colunas * args.tamanho, linhas * args.tamanho), "white")
    for n, im in enumerate(ims):
        folha.paste(im, ((n % colunas) * args.tamanho, (n // colunas) * args.tamanho))
    folha.save(args.saida)
    print("gravado", args.saida, "vistas:", ", ".join(vistas))


if __name__ == "__main__":
    main()
