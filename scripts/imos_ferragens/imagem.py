"""Imagem da ferragem para a lista do iMos: JPG 256x256, fundo branco.

Uso::

    python -m scripts.imos_ferragens.imagem peca_cortes.dxf --vista=-0.5,-1,-0.45 \\
        --saida EMUCA_4030705_NIVELADOR_LEVEL_UP_DIR.jpg --grande conferir.png

* ``--vista``: para onde a câmara olha. Escolher o lado que aparece na foto do
  fabricante — é o que ajuda a reconhecer a ferragem na lista.
* ``--cor``: ``zincado`` (omissão), ``aluminio`` ou ``r,g,b`` em 0..1.
* ``--grande``: grava também uma versão grande (768 px) para conferir detalhes.

Os cortes devem ter passo pequeno (0,15 mm) para a imagem sair lisa; com 0,25 mm
já se vê bem a forma, mas aparece algum "granulado" nas faces planas.
"""

from __future__ import annotations

import argparse

from scripts.imos_ferragens.volume import COR_ALUMINIO, COR_ZINCADO, carregar_cortes, render

CORES = {"zincado": COR_ZINCADO, "aluminio": COR_ALUMINIO}


def _cor(texto: str):
    if texto in CORES:
        return CORES[texto]
    return tuple(float(x) for x in texto.split(","))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cortes", help="DXF R12 gerado pelo cortes.ps1")
    ap.add_argument("--vista", required=True, help="direção da câmara x,y,z")
    ap.add_argument("--saida", required=True, help="ficheiro .jpg")
    ap.add_argument("--cor", default="zincado")
    ap.add_argument("--sigma", type=float, default=2.0,
                    help="suavização das normais, em voxels (mais = mais liso)")
    ap.add_argument("--tamanho", type=int, default=256)
    ap.add_argument("--grande", help="grava também uma versão de 768 px (png)")
    args = ap.parse_args(argv)
    cortes = carregar_cortes(args.cortes)
    direcao = [float(x) for x in args.vista.split(",")]
    opcoes = dict(cor=_cor(args.cor), sigma=args.sigma)
    im = render(cortes, direcao, tamanho=args.tamanho, supersample=4, **opcoes)
    im.save(args.saida, quality=95, subsampling=0)
    print("gravado", args.saida, im.size)
    if args.grande:
        render(cortes, direcao, tamanho=768, supersample=2, **opcoes).save(args.grande)
        print("gravado", args.grande)


if __name__ == "__main__":
    main()
