"""Converte a ficha técnica (PDF do fabricante) em PNG, para ler as cotas.

As fichas da Emuca e de outros fabricantes trazem as cotas de montagem (diâmetro
e profundidade dos furos, distância entre cavilhas, saliência) que decidem o
referencial do DWG. Usa o QtPdf, que o Martelo já tem.

Uso::

    python -m scripts.imos_ferragens.ficha_pdf ficha.pdf --saida ficha --escala 2.5

Grava ``ficha_1.png``, ``ficha_2.png``, ... (uma por página).
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pdf")
    ap.add_argument("--saida", required=True, help="prefixo dos PNG")
    ap.add_argument("--escala", type=float, default=2.5, help="píxeis por ponto do PDF")
    args = ap.parse_args(argv)

    from PySide6.QtCore import QSize
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtPdf import QPdfDocument

    _app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    doc = QPdfDocument()
    doc.load(args.pdf)
    if doc.pageCount() <= 0:
        raise SystemExit(f"Não consegui abrir {args.pdf}")
    for n in range(doc.pageCount()):
        tamanho = doc.pagePointSize(n)
        img = doc.render(n, QSize(int(tamanho.width() * args.escala),
                                  int(tamanho.height() * args.escala)))
        destino = f"{args.saida}_{n + 1}.png"
        img.save(destino)
        print("gravado", destino, img.width(), "x", img.height())


if __name__ == "__main__":
    main()
