"""Volume (voxels) a partir dos cortes de um sólido, e render ortográfico sombreado.

A consola do iX CAD não exporta malhas nem imagens (não há MESHSMOOTH, STLOUT,
PNGOUT). O que ela faz bem é cortar: o ``cortes.ps1`` corta o sólido com planos
horizontais (Z constante) e grava as regiões num DXF R12. Aqui cada região é
preenchida na grelha pela regra par/ímpar, as regiões do mesmo corte juntam-se,
e os cortes empilhados dão o volume. O render pinta os voxels da superfície com
normais tiradas do volume suavizado (dá um aspeto liso), oclusão ambiente,
sombra da luz principal e brilho metálico.

Uso típico (pelos comandos ``vistas`` e ``imagem``)::

    cortes = carregar_cortes("peca_cortes.dxf")   # lê o .json do cortes.ps1
    im = render(cortes, (-0.5, -1, -0.45), tamanho=256)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage

from scripts.imos_ferragens.dxf_leitura import ler_regioes

#: Cor base do aço zincado (0..1) — a mesma dos sólidos (RGB 186,192,200) mais clara
#: para compensar a luz.
COR_ZINCADO = (0.84, 0.86, 0.90)
#: Alumínio (RGB 161,161,160 nos sólidos; mais claro na imagem).
COR_ALUMINIO = (0.80, 0.80, 0.80)


@dataclass
class Cortes:
    """Volume pronto a desenhar. ``V[k, j, i]``: k = Z, j = Y, i = X."""

    V: np.ndarray
    origem: np.ndarray  # centro do voxel (0,0,0) em mm (x, y, z)
    passo: float

    def pontos(self, mascara: np.ndarray) -> np.ndarray:
        k, j, i = np.nonzero(mascara)
        return self.origem + np.stack([i, j, k], 1) * self.passo


def voxelizar(regioes, passo: float, z0: float, dz: float) -> Cortes:
    """Regiões (listas de polilinhas 3D em planos Z constante) -> volume.

    ``passo`` é o lado do voxel em X/Y; ``z0``/``dz`` são o primeiro corte e o
    intervalo entre cortes (o render assume ``passo == dz``).

    Um corte sem região no meio da peça (o kernel às vezes falha o SECTION num
    sólido com defeitos: "Modeling Operation Error") fica igual ao de baixo, para
    não aparecer uma risca vazia.
    """
    pontos = np.vstack([np.vstack(r) for r in regioes if r])
    lo = pontos.min(0) - 2 * passo
    hi = pontos.max(0) + 2 * passo
    na = int(math.ceil((hi[0] - lo[0]) / passo)) + 1
    nb = int(math.ceil((hi[1] - lo[1]) / passo)) + 1
    nk = int(round((hi[2] - z0) / dz)) + 1
    V = np.zeros((nk, nb, na), bool)
    tem = np.zeros(nk, bool)
    for reg in regioes:
        if not reg:
            continue
        P = np.vstack(reg)
        k = int(round((float(np.median(P[:, 2])) - z0) / dz))
        if 0 <= k < nk:
            V[k] |= _preencher(reg, lo, passo, na, nb)
            tem[k] = True
    com = np.nonzero(tem)[0]
    if len(com):
        for k in range(com[0], com[-1] + 1):
            if not tem[k]:
                V[k] = V[k - 1]
    origem = np.array([lo[0] + 0.5 * passo, lo[1] + 0.5 * passo, z0])
    return Cortes(V=V, origem=origem, passo=passo)


def _preencher(reg, lo, h, na, nb) -> np.ndarray:
    """Preenchimento par/ímpar de uma região na grelha (centros dos voxels)."""
    segs = np.concatenate([np.stack([p[:-1], p[1:]], 1) for p in reg if len(p) > 1])
    a0, b0 = segs[:, 0, 0], segs[:, 0, 1]
    a1, b1 = segs[:, 1, 0], segs[:, 1, 1]
    js = np.ceil((np.minimum(b0, b1) - lo[1]) / h - 0.5).astype(int)
    je = np.ceil((np.maximum(b0, b1) - lo[1]) / h - 0.5).astype(int) - 1
    cnt = np.maximum(je - js + 1, 0)
    dentro = np.zeros((nb, na), bool)
    ok = cnt > 0
    if not ok.any():
        return dentro
    idx = np.repeat(np.nonzero(ok)[0], cnt[ok])
    desloc = np.arange(len(idx)) - np.repeat(np.cumsum(cnt[ok]) - cnt[ok], cnt[ok])
    linhas = js[idx] + desloc
    t = (lo[1] + (linhas + 0.5) * h - b0[idx]) / (b1[idx] - b0[idx])
    colunas = np.ceil((a0[idx] + t * (a1[idx] - a0[idx]) - lo[0]) / h - 0.5).astype(int)
    bons = (linhas >= 0) & (linhas < nb)
    T = np.zeros((nb, na + 1), np.int32)
    np.add.at(T, (linhas[bons], np.clip(colunas[bons], 0, na)), 1)
    dentro = (np.cumsum(T, axis=1)[:, :na] % 2) == 1
    # linha com nº ímpar de cruzamentos = contorno mal fechado: ignora-se (senão
    # aparece um risco até à borda)
    dentro[(T.sum(axis=1) % 2) == 1] = False
    return dentro


def carregar_cortes(caminho_dxf: str | Path, z0: float | None = None,
                    dz: float | None = None) -> Cortes:
    """Lê os cortes de um DXF R12. ``z0``/``dz`` vêm do ``.json`` do ``cortes.ps1``."""
    caminho_dxf = Path(caminho_dxf)
    meta = Path(str(caminho_dxf) + ".json")
    if (z0 is None or dz is None) and meta.exists():
        dados = json.loads(meta.read_text(encoding="utf-8-sig"))
        z0 = dados["de"] if z0 is None else z0
        dz = dados["passo"] if dz is None else dz
    if z0 is None or dz is None:
        raise ValueError(f"Falta o primeiro corte e o passo (não há {meta.name})")
    return voxelizar(ler_regioes(caminho_dxf), dz, z0, dz)


# ---------------------------------------------------------------------- render
def _unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _camara(direcao, cima=(0.0, 0.0, 1.0)):
    d = _unit(direcao)
    r = np.cross(d, cima)
    if np.linalg.norm(r) < 1e-6:
        r = np.cross(d, (0.0, 1.0, 0.0))
    r = _unit(r)
    return r, np.cross(r, d), d


def _zbuffer(P, r, u, d, escala, u0, v0, W, H, pegada):
    """Índice do ponto mais próximo por píxel (-1 = fundo) e profundidade."""
    px = (P @ r - u0) * escala
    py = (v0 - P @ u) * escala
    prof = P @ d
    melhor = np.full(W * H, np.inf)
    quem = np.full(W * H, -1, np.int64)
    for oy in range(-pegada, pegada + 1):
        for ox in range(-pegada, pegada + 1):
            ix = np.floor(px).astype(np.int64) + ox
            iy = np.floor(py).astype(np.int64) + oy
            ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
            pid = iy[ok] * W + ix[ok]
            dd = prof[ok]
            ids = np.nonzero(ok)[0]
            ordem = np.lexsort((dd, pid))
            ps = pid[ordem]
            primeiro = np.ones(len(ps), bool)
            primeiro[1:] = ps[1:] != ps[:-1]
            sel = ordem[primeiro]
            melhora = dd[sel] < melhor[pid[sel]]
            melhor[pid[sel][melhora]] = dd[sel][melhora]
            quem[pid[sel][melhora]] = ids[sel][melhora]
    return quem.reshape(H, W), melhor.reshape(H, W)


def render(cortes: Cortes, direcao, tamanho: int = 256, supersample: int = 4,
           margem: float = 0.05, cor=COR_ZINCADO, sigma: float = 2.0,
           luz=(-0.55, 0.75, 0.55), sombra: bool = True, cima=(0.0, 0.0, 1.0)):
    """Imagem PIL ``tamanho x tamanho`` (fundo branco, peça centrada).

    ``direcao`` = para onde a câmara olha (da câmara para a peça); ``luz`` é dada
    em coordenadas da câmara (direita, cima, para o observador) para a peça ficar
    sempre iluminada de cima à esquerda, seja qual for o ângulo.
    """
    from PIL import Image

    V, h = cortes.V, cortes.passo
    Vf = V.astype(np.float32)
    F = ndimage.gaussian_filter(Vf, sigma)
    F_largo = ndimage.gaussian_filter(Vf, 4.0)
    gz, gy, gx = np.gradient(F)
    sup = V & ~ndimage.binary_erosion(V)
    k, j, i = np.nonzero(sup)
    P = cortes.pontos(sup)
    N = -np.stack([gx[k, j, i], gy[k, j, i], gz[k, j, i]], 1)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    ocl = F_largo[k, j, i]

    r, u, d = _camara(direcao, cima)
    W = H = tamanho * supersample
    pu, pv = P @ r, P @ u
    vao = max(pu.max() - pu.min(), pv.max() - pv.min())
    escala = W * (1 - 2 * margem) / vao
    u0 = (pu.max() + pu.min()) / 2 - (W / 2) / escala
    v0 = (pv.max() + pv.min()) / 2 + (H / 2) / escala
    quem, _ = _zbuffer(P, r, u, d, escala, u0, v0, W, H, max(1, int(math.ceil(h * escala * 0.55))))
    mask = quem >= 0
    n = N[quem[mask]]
    ver = -d
    n[(n @ ver) < 0] *= -1
    lc = np.asarray(luz, float)
    L = _unit(lc[0] * r + lc[1] * u + lc[2] * ver)

    iluminado = np.ones(int(mask.sum()))
    if sombra:
        cima_luz = cima if abs(float(np.dot(L, cima))) < 0.95 else (0.0, 1.0, 0.0)
        rl, ul, dl = _camara(-L, cima_luz)
        lu, lv = P @ rl, P @ ul
        vao_l = max(lu.max() - lu.min(), lv.max() - lv.min())
        esc_l = W * 0.96 / vao_l
        lu0 = (lu.max() + lu.min()) / 2 - (W / 2) / esc_l
        lv0 = (lv.max() + lv.min()) / 2 + (W / 2) / esc_l
        _, prof_l = _zbuffer(P, rl, ul, dl, esc_l, lu0, lv0, W, W,
                             max(1, int(math.ceil(h * esc_l * 0.55))))
        Pv = P[quem[mask]]
        sx = np.clip(np.floor((Pv @ rl - lu0) * esc_l).astype(int), 0, W - 1)
        sy = np.clip(np.floor((lv0 - Pv @ ul) * esc_l).astype(int), 0, W - 1)
        visto = (Pv @ dl) <= ndimage.minimum_filter(prof_l, size=3)[sy, sx] + 2.5 * h
        iluminado = 0.35 + 0.65 * visto.astype(float)

    ao = np.clip(1.0 - 1.6 * (ocl[quem[mask]] - 0.35), 0.45, 1.0)
    ndl = np.clip(n @ L, 0, 1)
    ndf = np.clip(n @ _unit(0.7 * r + 0.15 * u + 0.5 * ver), 0, 1)
    ceu = 0.5 + 0.5 * (n @ np.asarray(cima, float))
    brilho = np.clip(n @ _unit(L + ver), 0, 1) ** 28
    rebordo = (1 - np.clip(n @ ver, 0, 1)) ** 3
    base = np.asarray(cor, float)
    rgb = (base[None, :] * (0.40 * ceu + 0.20 + 0.55 * ndl * iluminado + 0.22 * ndf)[:, None]
           * ao[:, None]
           + (0.45 * brilho * iluminado)[:, None] + (0.10 * rebordo)[:, None])
    img = np.ones((H, W, 3))
    img[mask] = np.clip(rgb, 0, 1)
    grande = Image.fromarray((img * 255).astype(np.uint8))
    return grande.resize((tamanho, tamanho), Image.LANCZOS)
