"""Sobrepõe as silhuetas de duas peças no mesmo referencial (prova de alinhamento).

Quando uma ferragem nova substitui o desenho de uma união que já existe, o DWG
novo deve ter a mesma origem e orientação do antigo — assim basta trocar o
"Nome do desenho" na união. Esta folha mostra as duas peças por cima uma da
outra em três vistas: vermelho = A, azul = B, roxo = ambas. Grelha de 10 mm,
eixos a preto.

Uso::

    python -m scripts.imos_ferragens.sobrepor antigo_cortes.dxf novo_cortes.dxf \\
        --saida sobreposicao.png --nome-a "GS_SH_6301 (antigo)" --nome-b "EMUCA (novo)"
"""

from __future__ import annotations

import argparse

import numpy as np
from PIL import Image, ImageDraw

from scripts.imos_ferragens.volume import Cortes, carregar_cortes

PX_POR_MM = 4.0
VERMELHO, AZUL, ROXO = (230, 80, 70), (60, 110, 230), (140, 70, 160)


def _limites(*cortes: Cortes) -> tuple[np.ndarray, np.ndarray]:
    lo = np.min([c.origem for c in cortes], axis=0) - 5
    hi = np.max([c.origem + np.array(c.V.shape[::-1]) * c.passo for c in cortes], axis=0) + 5
    return lo, hi


def projetar(c: Cortes, horizontal: int, vertical: int, lo, hi) -> np.ndarray:
    """Silhueta da peça vista ao longo do eixo que sobra (0=x, 1=y, 2=z)."""
    largado = 3 - horizontal - vertical
    m = c.V.any(axis=2 - largado).T  # eixos que ficam, por ordem crescente
    ficam = [a for a in (0, 1, 2) if a != largado]
    W = int((hi[horizontal] - lo[horizontal]) * PX_POR_MM)
    H = int((hi[vertical] - lo[vertical]) * PX_POR_MM)
    img = np.zeros((H, W), bool)
    i0, i1 = np.nonzero(m)
    coord = {ficam[0]: c.origem[ficam[0]] + i0 * c.passo, ficam[1]: c.origem[ficam[1]] + i1 * c.passo}
    X = ((coord[horizontal] - lo[horizontal]) * PX_POR_MM).astype(int)
    Y = ((hi[vertical] - coord[vertical]) * PX_POR_MM).astype(int)
    pegada = int(np.ceil(c.passo * PX_POR_MM)) + 1
    for dx in range(pegada):
        for dy in range(pegada):
            img[np.clip(Y - dy, 0, H - 1), np.clip(X + dx, 0, W - 1)] = True
    return img


def painel(a: Cortes, b: Cortes, horizontal: int, vertical: int, lo, hi, titulo: str) -> Image.Image:
    ma = projetar(a, horizontal, vertical, lo, hi)
    mb = projetar(b, horizontal, vertical, lo, hi)
    H, W = ma.shape
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    for g in range(int(np.floor(lo[horizontal] / 10)) * 10, int(hi[horizontal]) + 1, 10):
        x = int((g - lo[horizontal]) * PX_POR_MM)
        d.line([(x, 0), (x, H)], fill=(0, 0, 0) if g == 0 else (215, 215, 215))
    for g in range(int(np.floor(lo[vertical] / 10)) * 10, int(hi[vertical]) + 1, 10):
        y = int((hi[vertical] - g) * PX_POR_MM)
        d.line([(0, y), (W, y)], fill=(0, 0, 0) if g == 0 else (215, 215, 215))
    arr = np.asarray(im).copy()
    arr[ma & ~mb] = VERMELHO
    arr[mb & ~ma] = AZUL
    arr[ma & mb] = ROXO
    im = Image.fromarray(arr)
    ImageDraw.Draw(im).text((6, 4), titulo, fill=(0, 0, 0))
    return im


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cortes_a")
    ap.add_argument("cortes_b")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--nome-a", default="A")
    ap.add_argument("--nome-b", default="B")
    args = ap.parse_args(argv)
    a, b = carregar_cortes(args.cortes_a), carregar_cortes(args.cortes_b)
    lo, hi = _limites(a, b)
    paineis = [painel(a, b, 0, 2, lo, hi, "frente: X (horiz.) / Z"),
               painel(a, b, 1, 2, lo, hi, "lado: Y (horiz.) / Z"),
               painel(a, b, 0, 1, lo, hi, "cima: X / Y")]
    W = sum(p.width for p in paineis) + 20 * (len(paineis) - 1)
    folha = Image.new("RGB", (max(W, 720), max(p.height for p in paineis) + 30), "white")
    x = 0
    for p in paineis:
        folha.paste(p, (x, 30))
        x += p.width + 20
    d = ImageDraw.Draw(folha)
    for n, (cor, texto) in enumerate([(VERMELHO, args.nome_a), (AZUL, args.nome_b), (ROXO, "ambas")]):
        d.rectangle([6 + 240 * n, 8, 20 + 240 * n, 22], fill=cor)
        d.text((26 + 240 * n, 10), texto, fill=(0, 0, 0))
    folha.save(args.saida)
    print("gravado", args.saida, folha.size)


if __name__ == "__main__":
    main()
