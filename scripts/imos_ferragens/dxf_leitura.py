"""Leitura mínima de DXF em texto, para as ferramentas das ferragens do iMos.

Dois usos, ambos com ficheiros gerados pela consola do iX CAD:

* :func:`ler_arestas` — arestas soltas (LINE, ARC, CIRCLE, ELLIPSE, SPLINE) de um
  DXF moderno, como as que o ``XEDGES`` cria. Serve para desenhar a peça em
  arame e perceber a geometria antes de decidir o que simplificar.
* :func:`ler_regioes` — os cortes de um sólido gravados em DXF **R12**. Nesse
  formato cada REGION do ``SECTION`` passa a um bloco anónimo (``*Unn``) com
  linhas, arcos e polilinhas; cada bloco é devolvido como uma região.

Tudo em coordenadas do mundo (os ARC/CIRCLE/POLYLINE 2D vêm no sistema do objeto
e são convertidos aqui). Sem dependências além do numpy.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from pathlib import Path

import numpy as np

#: Comprimento máximo de cada segmento quando se aproxima um arco (mm).
PASSO_ARCO = 0.08


# --------------------------------------------------------------------- comuns
def _ler_pares(caminho: str | Path) -> tuple[list[str], list[str]]:
    with open(caminho, encoding="latin-1") as f:
        dados = f.read().split("\n")
    n = len(dados) // 2
    codigos = [c.strip() for c in dados[0 : 2 * n : 2]]
    valores = [v.rstrip("\r") for v in dados[1 : 2 * n : 2]]
    return codigos, valores


def eixos_ocs(normal) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Eixos X, Y, Z do sistema do objeto (algoritmo do eixo arbitrário do DXF)."""
    n = np.asarray(normal, float)
    n = n / np.linalg.norm(n)
    if abs(n[0]) < 1 / 64 and abs(n[1]) < 1 / 64:
        ax = np.cross([0.0, 1.0, 0.0], n)
    else:
        ax = np.cross([0.0, 0.0, 1.0], n)
    ax /= np.linalg.norm(ax)
    ay = np.cross(n, ax)
    return ax, ay, n


def _g(grupo, codigo: str, omissao=None):
    for c, v in grupo:
        if c == codigo:
            return v
    return omissao


def _todos(grupo, codigo: str) -> list[str]:
    return [v for c, v in grupo if c == codigo]


def _normal(grupo) -> list[float]:
    n = [float(_g(grupo, k, "0")) for k in ("210", "220", "230")]
    return n if any(n) else [0.0, 0.0, 1.0]


def _entidades(codigos, valores, i0: int, i1: int) -> list[tuple[str, list]]:
    """Divide ``[i0, i1)`` em entidades ``(tipo, [(código, valor), ...])``."""
    fora: list[tuple[str, list]] = []
    atual = None
    for i in range(i0, i1):
        if codigos[i] == "0":
            if atual is not None:
                fora.append(atual)
            atual = (valores[i].strip(), [])
        elif atual is not None:
            atual[1].append((codigos[i], valores[i]))
    if atual is not None:
        fora.append(atual)
    return fora


def _seccoes(codigos, valores) -> dict[str, tuple[int, int]]:
    inicio = {}
    for i in range(len(codigos) - 1):
        if codigos[i] == "0" and valores[i].strip() == "SECTION" and codigos[i + 1] == "2":
            inicio[valores[i + 1].strip()] = i + 2
    fora = {}
    for nome, i in inicio.items():
        j = i
        while not (codigos[j] == "0" and valores[j].strip() == "ENDSEC"):
            j += 1
        fora[nome] = (i, j)
    return fora


def pontos_arco(cx, cy, r, a0, a1, passo=PASSO_ARCO) -> np.ndarray:
    """Pontos 2D de um arco de ``a0`` a ``a1`` (radianos, sentido direto)."""
    if a1 <= a0:
        a1 += 2 * math.pi
    n = min(720, max(6, int(math.ceil(r * (a1 - a0) / passo))))
    aa = np.linspace(a0, a1, n + 1)
    return np.stack([cx + r * np.cos(aa), cy + r * np.sin(aa)], 1)


def pontos_bulge(p0, p1, bulge, passo=PASSO_ARCO) -> np.ndarray:
    """Troço de polilinha 2D com ``bulge`` (tan de 1/4 do ângulo) -> pontos."""
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    if abs(bulge) < 1e-12:
        return np.array([p0, p1])
    teta = 4 * math.atan(bulge)
    d = p1 - p0
    corda = float(np.linalg.norm(d))
    r = corda / (2 * math.sin(abs(teta) / 2))
    perp = np.array([-d[1], d[0]]) / corda
    centro = (p0 + p1) / 2 + perp * r * math.cos(abs(teta) / 2) * (1 if bulge > 0 else -1)
    a0 = math.atan2(p0[1] - centro[1], p0[0] - centro[0])
    n = min(720, max(4, int(abs(teta) * r / passo) + 1))
    aa = a0 + np.linspace(0, teta, n + 1)
    return np.stack([centro[0] + r * np.cos(aa), centro[1] + r * np.sin(aa)], 1)


def _bspline(ctrl, nos, grau, pesos, n=60) -> np.ndarray:
    ctrl = np.asarray(ctrl, float)
    k = np.asarray(nos, float)
    w = np.asarray(pesos if pesos else [1.0] * len(ctrl), float)
    fora = []
    for t in np.linspace(k[grau], k[len(k) - grau - 1], n):
        s = int(np.searchsorted(k, t, side="right") - 1)
        s = min(max(s, grau), len(k) - grau - 2)
        d = [np.append(ctrl[j] * w[j], w[j]) for j in range(s - grau, s + 1)]
        for r in range(1, grau + 1):
            for j in range(grau, r - 1, -1):
                i = j + s - grau
                den = k[i + grau + 1 - r] - k[i]
                a = 0.0 if den == 0 else (t - k[i]) / den
                d[j] = (1 - a) * d[j - 1] + a * d[j]
        fora.append(d[grau][:3] / d[grau][3])
    return np.array(fora)


def _polilinhas(entidades) -> Iterator[tuple[str, np.ndarray]]:
    """Entidades -> ``(camada, pontos Nx3 no mundo)``."""
    i = 0
    while i < len(entidades):
        tipo, g = entidades[i]
        camada = (_g(g, "8", "0") or "0").strip()
        if tipo == "LINE":
            p = [float(_g(g, k)) for k in ("10", "20", "30")]
            q = [float(_g(g, k)) for k in ("11", "21", "31")]
            yield camada, np.array([p, q])
        elif tipo in ("ARC", "CIRCLE"):
            cx, cy, cz = (float(_g(g, k)) for k in ("10", "20", "30"))
            r = float(_g(g, "40"))
            ax, ay, az = eixos_ocs(_normal(g))
            if tipo == "ARC":
                a0 = math.radians(float(_g(g, "50")))
                a1 = math.radians(float(_g(g, "51")))
            else:
                a0, a1 = 0.0, 2 * math.pi
            p2 = pontos_arco(cx, cy, r, a0, a1)
            yield camada, p2[:, :1] * ax + p2[:, 1:2] * ay + cz * az
        elif tipo == "ELLIPSE":
            c = np.array([float(_g(g, k)) for k in ("10", "20", "30")])
            maior = np.array([float(_g(g, k)) for k in ("11", "21", "31")])
            n = np.asarray(_normal(g), float)
            a0 = float(_g(g, "41", "0"))
            a1 = float(_g(g, "42", str(2 * math.pi)))
            if a1 <= a0:
                a1 += 2 * math.pi
            menor = np.cross(n / np.linalg.norm(n), maior) * float(_g(g, "40"))
            aa = np.linspace(a0, a1, max(8, int(48 * (a1 - a0) / (2 * math.pi)) + 1))
            yield camada, c + np.outer(np.cos(aa), maior) + np.outer(np.sin(aa), menor)
        elif tipo == "SPLINE":
            nos = [float(v) for v in _todos(g, "40")]
            pesos = [float(v) for v in _todos(g, "41")]
            ctrl = [[float(a), float(b), float(c)]
                    for a, b, c in zip(_todos(g, "10"), _todos(g, "20"), _todos(g, "30"))]
            if ctrl and nos:
                yield camada, _bspline(ctrl, nos, int(_g(g, "71")),
                                       pesos if len(pesos) == len(ctrl) else None)
            else:
                ajuste = [[float(a), float(b), float(c)]
                          for a, b, c in zip(_todos(g, "11"), _todos(g, "21"), _todos(g, "31"))]
                if ajuste:
                    yield camada, np.array(ajuste)
        elif tipo == "POLYLINE":
            flags = int(_g(g, "70", "0"))
            elevacao = float(_g(g, "30", "0"))
            vertices = []
            j = i + 1
            while j < len(entidades) and entidades[j][0] == "VERTEX":
                vg = entidades[j][1]
                vertices.append((float(_g(vg, "10")), float(_g(vg, "20")),
                                 float(_g(vg, "30", "0")), float(_g(vg, "42", "0"))))
                j += 1
            fechada = bool(flags & 1)
            if vertices and flags & 8:  # polilinha 3D: já está no mundo
                P = np.array([v[:3] for v in vertices])
                yield camada, (np.vstack([P, P[:1]]) if fechada else P)
            elif vertices:
                ax, ay, az = eixos_ocs(_normal(g))
                m = len(vertices)
                trocos = []
                for k in range(m if fechada else m - 1):
                    a, b = vertices[k], vertices[(k + 1) % m]
                    seg = pontos_bulge(a[:2], b[:2], a[3])
                    trocos.append(seg if not trocos else seg[1:])
                if trocos:
                    p2 = np.vstack(trocos)
                    yield camada, p2[:, :1] * ax + p2[:, 1:2] * ay + elevacao * az
            i = j
            continue
        i += 1


# ---------------------------------------------------------------- API pública
def ler_arestas(caminho: str | Path) -> list[tuple[str, np.ndarray]]:
    """Arestas da secção ENTITIES: lista de ``(camada, pontos Nx3)``."""
    codigos, valores = _ler_pares(caminho)
    i0, i1 = _seccoes(codigos, valores)["ENTITIES"]
    return list(_polilinhas(_entidades(codigos, valores, i0, i1)))


def ler_regioes(caminho: str | Path) -> list[list[np.ndarray]]:
    """Regiões de um DXF R12 com cortes: cada região é uma lista de polilinhas 3D.

    Só se leem os blocos que as INSERT da secção ENTITIES usam — o R12 escreve
    também as definições de blocos que já não servem e que podem pesar dezenas
    de MB. Entidades soltas (fora de blocos) não são regiões — por exemplo as
    curvas do corte de uma SURFACE — e ficam de fora.
    """
    codigos, valores = _ler_pares(caminho)
    seccoes = _seccoes(codigos, valores)
    i0, i1 = seccoes["ENTITIES"]
    nomes: list[str] = []
    for tipo, g in _entidades(codigos, valores, i0, i1):
        if tipo == "INSERT":
            ponto = [float(_g(g, k, "0")) for k in ("10", "20", "30")]
            if any(abs(x) > 1e-9 for x in ponto):
                raise ValueError(f"INSERT fora da origem {ponto}: os cortes não deviam ter isto")
            nomes.append(_g(g, "2").strip())
    queridos = set(nomes)
    blocos: dict[str, list[np.ndarray]] = {}
    if "BLOCKS" in seccoes:
        b0, b1 = seccoes["BLOCKS"]
        i = b0
        while i < b1:
            if codigos[i] == "0" and valores[i].strip() == "BLOCK":
                j = i + 1
                nome = None
                while codigos[j] != "0":
                    if codigos[j] == "2":
                        nome = valores[j].strip()
                    j += 1
                k = j
                while not (codigos[k] == "0" and valores[k].strip() == "ENDBLK"):
                    k += 1
                if nome in queridos:
                    blocos[nome] = [p for _, p in _polilinhas(_entidades(codigos, valores, j, k))]
                i = k
            i += 1
    return [blocos[n] for n in nomes if n in blocos]
