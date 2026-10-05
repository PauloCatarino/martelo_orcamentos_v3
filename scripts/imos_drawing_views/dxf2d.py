"""Desenho 2D de um DXF (modelo ou papel) em matplotlib, expandindo blocos.

Suporta LINE, ARC, CIRCLE, ELLIPSE, SPLINE, LWPOLYLINE, POLYLINE, SOLID, HATCH
(contornos de polilinha/arestas), TEXT, MTEXT, ATTRIB, ATTDEF constante (texto fixo dos
blocos de etiqueta), INSERT (recursivo, com escala/rotação; os DIMENSION desenham-se pelo
bloco *D que trazem).
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
from scripts.imos_ferragens import dxf_leitura as d  # noqa: E402

# para desenhos à escala 1:10–1:25 chega um troço a cada ~1,5 mm (o leitor usa 0,08)
_arco, _bulge = d.pontos_arco, d.pontos_bulge
d.pontos_arco = lambda cx, cy, r, a0, a1, passo=1.5: _arco(cx, cy, r, a0, a1, passo)
d.pontos_bulge = lambda p0, p1, b, passo=1.5: _bulge(p0, p1, b, passo)


class Desenho:
    def __init__(self, caminho):
        self.cod, self.val = d._ler_pares(caminho)
        self.sec = d._seccoes(self.cod, self.val)
        self.blocos = {}
        if "BLOCKS" in self.sec:
            b0, b1 = self.sec["BLOCKS"]
            ents = d._entidades(self.cod, self.val, b0, b1)
            nome = None
            atual = []
            base = (0.0, 0.0)
            for t, g in ents:
                if t == "BLOCK":
                    nome = (d._g(g, "2", "") or "").strip()
                    base = (float(d._g(g, "10", "0")), float(d._g(g, "20", "0")))
                    atual = []
                elif t == "ENDBLK":
                    if nome is not None:
                        self.blocos[nome] = (base, atual)
                    nome = None
                elif nome is not None:
                    atual.append((t, g))
        e0, e1 = self.sec["ENTITIES"]
        self.entidades = d._entidades(self.cod, self.val, e0, e1)

    # ------------------------------------------------------------------ primitivas
    def primitivas(self, ents=None, M=None, camada_pai=None, prof=0, espaco=None):
        """Gera (tipo, camada, dados) já transformados para o mundo (2D)."""
        if ents is None:
            ents = self.entidades
        if M is None:
            M = np.eye(3)
        i = 0
        while i < len(ents):
            t, g = ents[i]
            camada = (d._g(g, "8", "0") or "0").strip()
            if camada == "0" and camada_pai:
                camada = camada_pai
            if espaco is not None and prof == 0:
                e = int(d._g(g, "67", "0") or 0)
                if e != espaco:
                    i += 1
                    continue
            if t in ("INSERT", "DIMENSION"):
                nome = (d._g(g, "2", "") or "").strip()
                if nome in self.blocos and prof < 8:
                    (bx, by), sub = self.blocos[nome]
                    if t == "INSERT":
                        x, y = float(d._g(g, "10", "0")), float(d._g(g, "20", "0"))
                        sx, sy = float(d._g(g, "41", "1")), float(d._g(g, "42", "1"))
                        rot = math.radians(float(d._g(g, "50", "0")))
                        nz = float(d._g(g, "230", "1"))
                        if nz < 0:  # extrusão invertida: espelho em X
                            x = -x
                            sx = -sx
                            rot = -rot
                        c, s = math.cos(rot), math.sin(rot)
                        T = np.array([[c * sx, -s * sy, x], [s * sx, c * sy, y], [0, 0, 1]])
                        B = np.array([[1, 0, -bx], [0, 1, -by], [0, 0, 1]])
                        yield from self.primitivas(sub, M @ T @ B, camada, prof + 1)
                    else:
                        yield from self.primitivas(sub, M, camada, prof + 1)
                # atributos que seguem o INSERT
                if t == "INSERT" and (d._g(g, "66", "0") or "0").strip() == "1":
                    j = i + 1
                    while j < len(ents) and ents[j][0] == "ATTRIB":
                        ag = ents[j][1]
                        yield from self._texto("ATTRIB", ag, M, camada)
                        j += 1
                    i = j
                    continue
            elif t in ("TEXT", "MTEXT"):
                yield from self._texto(t, g, M, camada)
            elif t == "ATTDEF" and int(d._g(g, "70", "0") or 0) & 2:
                # atributo constante = texto fixo do bloco (ex.: o "x" das etiquetas DV_Etq_*)
                yield from self._texto("ATTDEF", g, M, camada)
            elif t == "LWPOLYLINE":
                xs = [float(v) for v in d._todos(g, "10")]
                ys = [float(v) for v in d._todos(g, "20")]
                bul = []
                # bulges alinhados com os vértices
                k = -1
                for c, v in g:
                    if c == "10":
                        k += 1
                        bul.append(0.0)
                    elif c == "42" and k >= 0:
                        bul[k] = float(v)
                fechada = bool(int(d._g(g, "70", "0") or 0) & 1)
                pts = []
                n = len(xs)
                for k in range(n if fechada else n - 1):
                    a = (xs[k], ys[k])
                    b = (xs[(k + 1) % n], ys[(k + 1) % n])
                    seg = d.pontos_bulge(a, b, bul[k] if k < len(bul) else 0.0)
                    pts.append(seg if not pts else seg[1:])
                if pts:
                    P = np.vstack(pts)
                    if float(d._g(g, "230", "1")) < 0:
                        P[:, 0] = -P[:, 0]
                    yield ("poly", camada, self._tr(P, M))
            elif t == "SOLID":
                P = np.array([[float(d._g(g, f"1{k}", "0")), float(d._g(g, f"2{k}", "0"))] for k in range(4)])
                P = P[[0, 1, 3, 2]]
                yield ("fill", camada, self._tr(P, M))
            elif t == "HATCH":
                for laco in self._hatch(g):
                    yield ("hatch", camada, self._tr(laco, M))
            elif t in ("LINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE", "POLYLINE"):
                sub = [ents[i]]
                if t == "POLYLINE":
                    j = i + 1
                    while j < len(ents) and ents[j][0] in ("VERTEX", "SEQEND"):
                        sub.append(ents[j])
                        j += 1
                    i = j - 1
                for _, P in d._polilinhas(sub):
                    yield ("poly", camada, self._tr(P[:, :2], M))
            i += 1

    @staticmethod
    def _tr(P, M):
        P = np.asarray(P, float)
        H = np.c_[P[:, :2], np.ones(len(P))]
        return (H @ M.T)[:, :2]

    def _texto(self, t, g, M, camada):
        txt = d._g(g, "1", "") or ""
        if t == "MTEXT":
            extra = "".join(v for c, v in g if c == "3")
            txt = extra + txt
            txt = re.sub(r"\\[A-Za-z][^;\\]*;", "", txt)
            txt = txt.replace("\\P", "\n").replace("{", "").replace("}", "")
        if not txt.strip():
            return
        x, y = float(d._g(g, "10", "0")), float(d._g(g, "20", "0"))
        if t != "MTEXT" and (d._g(g, "72", "0") not in (None, "0") or d._g(g, "73", "0") not in (None, "0")):
            if d._g(g, "11") is not None:
                x, y = float(d._g(g, "11", "0")), float(d._g(g, "21", "0"))
        h = float(d._g(g, "40", "2.5"))
        rot = float(d._g(g, "50", "0"))
        if t == "MTEXT":
            dx, dy = float(d._g(g, "11", "1")), float(d._g(g, "21", "0"))
            rot = math.degrees(math.atan2(dy, dx))
        p = self._tr(np.array([[x, y]]), M)[0]
        esc = math.hypot(M[0, 0], M[1, 0])
        ang = math.degrees(math.atan2(M[1, 0], M[0, 0]))
        alin = "left"
        if t != "MTEXT":
            h72 = int(d._g(g, "72", "0") or 0)
            alin = {1: "center", 2: "right", 4: "center"}.get(h72, "left")
        else:
            a71 = int(d._g(g, "71", "1") or 1)
            alin = {1: "left", 2: "center", 3: "right", 4: "left", 5: "center", 6: "right",
                    7: "left", 8: "center", 9: "right"}.get(a71, "left")
        yield ("text", camada, (p, txt, h * esc, rot + ang, alin))

    @staticmethod
    def _hatch(g):
        """Contornos de um HATCH: polilinhas (com bulge) e arestas linha/arco."""
        lacos = []
        i = 0
        n = len(g)
        while i < n:
            c, v = g[i]
            if c == "92":
                tipo = int(v)
                if tipo & 2:  # polilinha
                    i += 1
                    tem_bulge = fechado = 0
                    while i < n and g[i][0] in ("72", "73"):
                        if g[i][0] == "72":
                            tem_bulge = int(g[i][1])
                        else:
                            fechado = int(g[i][1])
                        i += 1
                    nv = int(g[i][1]) if g[i][0] == "93" else 0
                    i += 1
                    vs = []
                    for _ in range(nv):
                        x = float(g[i][1]); y = float(g[i + 1][1]); i += 2
                        b = 0.0
                        if tem_bulge and i < n and g[i][0] == "42":
                            b = float(g[i][1]); i += 1
                        vs.append((x, y, b))
                    pts = []
                    for k in range(len(vs)):
                        a, bb = vs[k], vs[(k + 1) % len(vs)]
                        seg = d.pontos_bulge(a[:2], bb[:2], a[2])
                        pts.append(seg if not pts else seg[1:])
                    if pts:
                        lacos.append(np.vstack(pts))
                    continue
                else:
                    i += 1
                    ne = int(g[i][1]) if g[i][0] == "93" else 0
                    i += 1
                    pts = []
                    for _ in range(ne):
                        et = int(g[i][1]); i += 1
                        if et == 1:
                            x1, y1, x2, y2 = (float(g[i + k][1]) for k in range(4)); i += 4
                            seg = np.array([[x1, y1], [x2, y2]])
                        elif et == 2:
                            cx, cy, r, a0, a1 = (float(g[i + k][1]) for k in range(5)); i += 5
                            ccw = int(g[i][1]); i += 1
                            if not ccw:
                                a0, a1 = -a1, -a0
                            seg = d.pontos_arco(cx, cy, r, math.radians(a0), math.radians(a1))
                        else:
                            break
                        pts.append(seg)
                    if pts:
                        lacos.append(np.vstack(pts))
                    continue
            i += 1
        return lacos


def desenhar(ax, prims, estilo, transformar=None):
    """Desenha primitivas; estilo(camada, tipo) -> dict ou None (não desenha)."""
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Polygon

    linhas = {}
    for tipo, camada, dados in prims:
        st = estilo(camada, tipo)
        if st is None:
            continue
        if transformar is not None and tipo != "text":
            dados = transformar(dados)
        if tipo == "poly":
            chave = (st.get("cor", "k"), st.get("lw", 0.3), st.get("ls", "-"))
            linhas.setdefault(chave, []).extend(np.stack([dados[:-1], dados[1:]], 1))
        elif tipo in ("fill", "hatch"):
            ax.add_patch(Polygon(dados, closed=True, facecolor=st.get("fill", "0.8"),
                                 edgecolor=st.get("cor", "none"), lw=st.get("lw", 0)))
        elif tipo == "text":
            p, txt, h, rot, alin = dados
            if transformar is not None:
                p, h = transformar(("ponto", p, h))
            ax.text(p[0], p[1], txt, fontsize=st.get("fs", max(2.0, h * st.get("k", 1.0))),
                    rotation=rot, ha=alin, va="baseline", color=st.get("cor", "k"),
                    family="DejaVu Sans")
    for (cor, lw, ls), segs in linhas.items():
        ax.add_collection(LineCollection(segs, colors=cor, linewidths=lw, linestyles=ls))
