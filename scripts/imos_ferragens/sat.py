"""Medir uma peça a partir do SAT (ACIS em texto) que o ``ACISOUT`` grava.

O SAT é a forma de saber as medidas exatas sem abrir o CAD: eixos e raios das
cavilhas e furos (cilindros), posição das faces planas, peso de cada corpo. Foi
assim que se alinhou o nivelador Emuca com o desenho antigo da união.

Uso::

    python -m scripts.imos_ferragens.sat corpos peca.sat
    python -m scripts.imos_ferragens.sat faces peca.sat --corpo 3 --tipo cone --eixo y
    python -m scripts.imos_ferragens.sat faces peca.sat --tipo spline

``corpos`` — por corpo: nº de faces, caixa (pelos vértices) e tipos de superfície.
As faces ``spline`` são as que pesam no DWG (5 a 15 kB cada); planos e cilindros
custam ~0,5 kB.

``faces`` — uma linha por face: tipo, normal (planos) ou centro/eixo/raio
(cilindros e cones, ``cone-surface`` com ``sin=0``) e a caixa dos vértices.

Coordenadas no mundo (já com a transformação de cada corpo). Só lê, não escreve.
"""

from __future__ import annotations

import argparse
import collections
from collections.abc import Iterator
from pathlib import Path

import numpy as np


def tokens(texto: str) -> list[tuple[str, str]]:
    """Separa o corpo do SAT em fichas; ``@N texto`` é uma cadeia de N caracteres."""
    fora: list[tuple[str, str]] = []
    i, n = 0, len(texto)
    while i < n:
        c = texto[i]
        if c.isspace():
            i += 1
            continue
        if c == "@":
            j = i + 1
            while texto[j].isdigit():
                j += 1
            comp = int(texto[i + 1 : j])
            fora.append(("S", texto[j + 1 : j + 1 + comp]))
            i = j + 1 + comp
            continue
        j = i
        while j < n and not texto[j].isspace():
            j += 1
        fora.append(("T", texto[i:j]))
        i = j
    return fora


def registos(caminho: str | Path) -> list[list[str]]:
    """Registos do SAT (cada um termina em ``#``). Índice = número de ``$N``."""
    texto = Path(caminho).read_text(encoding="latin-1")
    corpo = texto.split("\n", 3)[3]  # 3 linhas de cabeçalho
    fora, atual = [], []
    for tipo, valor in tokens(corpo):
        if tipo == "T" and valor == "#":
            fora.append(atual)
            atual = []
        else:
            atual.append(valor)
    return fora


def ref(valor: str) -> int | None:
    return int(valor[1:]) if valor.startswith("$") else None


class Sat:
    """Navegação mínima na topologia: corpo -> lump -> shell -> face -> loop -> coedge."""

    def __init__(self, caminho: str | Path):
        self.r = registos(caminho)
        self.tipo = [x[0] if x else "" for x in self.r]

    def corpos(self) -> list[int]:
        return [i for i, t in enumerate(self.tipo) if t == "body"]

    def transformacao(self, corpo: int) -> tuple[np.ndarray, np.ndarray]:
        t = ref(self.r[corpo][6])
        if t is None or t < 0:
            return np.eye(3), np.zeros(3)
        v = [float(x) for x in self.r[t][3:15]]  # 9 da matriz + 3 da translação
        return np.array(v[:9]).reshape(3, 3), np.array(v[9:12])

    def faces(self, corpo: int) -> Iterator[int]:
        lump = ref(self.r[corpo][4])
        while lump is not None and lump >= 0:
            shell = ref(self.r[lump][5])
            while shell is not None and shell >= 0:
                face = ref(self.r[shell][6])
                while face is not None and face >= 0:
                    yield face
                    face = ref(self.r[face][4])
                shell = ref(self.r[shell][4])
            lump = ref(self.r[lump][4])

    def vertices(self, face: int) -> np.ndarray:
        pts = []
        loop = ref(self.r[face][5])
        while loop is not None and loop >= 0:
            inicio = ref(self.r[loop][5])
            coedge = inicio
            while True:
                aresta = ref(self.r[coedge][7])
                for k in (4, 6):
                    vertice = ref(self.r[aresta][k])
                    ponto = ref(self.r[vertice][5])
                    pts.append([float(x) for x in self.r[ponto][4:7]])
                coedge = ref(self.r[coedge][4])
                if coedge == inicio or coedge is None or coedge < 0:
                    break
            loop = ref(self.r[loop][4])
        return np.array(pts) if pts else np.zeros((0, 3))

    def superficie(self, face: int) -> tuple[str, list[str]]:
        s = ref(self.r[face][8])
        return self.tipo[s], self.r[s]


def _num(r, a, b) -> np.ndarray:
    return np.array([float(x) for x in r[a:b]])


def descrever_face(sat: Sat, corpo: int, face: int) -> dict:
    T, off = sat.transformacao(corpo)
    tipo, s = sat.superficie(face)
    V = sat.vertices(face)
    P = V @ T + off if len(V) else V
    info: dict = {"face": face, "tipo": tipo.replace("-surface", ""),
                  "min": P.min(0) if len(P) else None, "max": P.max(0) if len(P) else None}
    if tipo == "plane-surface":
        info["normal"] = _num(s, 7, 10) @ T
    elif tipo == "cone-surface":
        info["centro"] = _num(s, 4, 7) @ T + off
        info["eixo"] = _num(s, 7, 10) @ T
        info["raio"] = float(np.linalg.norm(_num(s, 10, 13)))
        resto = s[14:]
        if resto and resto[0] == "I":  # "I I sin cos" ou "F a F b sin cos"
            info["sin"] = float(resto[2])
        elif len(resto) > 4:
            info["sin"] = float(resto[4])
    return info


def _eixo_ou_normal(info: dict) -> np.ndarray | None:
    return info.get("normal", info.get("eixo"))


def _fmt(v) -> str:
    return "[" + " ".join(f"{x:8.3f}" for x in v) + "]"


def cmd_corpos(caminho: str) -> None:
    sat = Sat(caminho)
    for n, corpo in enumerate(sat.corpos()):
        T, off = sat.transformacao(corpo)
        tipos: collections.Counter = collections.Counter()
        pts = []
        faces = list(sat.faces(corpo))
        for face in faces:
            tipos[sat.superficie(face)[0].replace("-surface", "")] += 1
            V = sat.vertices(face)
            if len(V):
                pts.append(V @ T + off)
        P = np.vstack(pts) if pts else np.zeros((1, 3))
        print(f"corpo {n}: {len(faces):4d} faces  min={_fmt(P.min(0))} max={_fmt(P.max(0))}  "
              f"{dict(tipos)}")


def cmd_faces(caminho: str, corpo: int | None, tipo: str | None, eixo: str | None) -> None:
    sat = Sat(caminho)
    for n, c in enumerate(sat.corpos()):
        if corpo is not None and n != corpo:
            continue
        for face in sat.faces(c):
            info = descrever_face(sat, c, face)
            if tipo and not info["tipo"].startswith(tipo):
                continue
            direcao = _eixo_ou_normal(info)
            if eixo:
                if direcao is None or abs(abs(direcao["xyz".index(eixo)]) - 1) > 1e-3:
                    continue
            extra = ""
            if "normal" in info:
                extra = f"normal={_fmt(info['normal'])}"
            elif "eixo" in info:
                extra = (f"centro={_fmt(info['centro'])} eixo={_fmt(info['eixo'])} "
                         f"r={info['raio']:.3f} sin={info.get('sin', 0):.3f}")
            caixa = (f"min={_fmt(info['min'])} max={_fmt(info['max'])}"
                     if info["min"] is not None else "")
            print(f"corpo {n} face {face:6d} {info['tipo']:7s} {extra} {caixa}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("corpos", help="resumo por corpo")
    a.add_argument("sat")
    b = sub.add_parser("faces", help="lista de faces")
    b.add_argument("sat")
    b.add_argument("--corpo", type=int, help="índice do corpo (o do comando corpos)")
    b.add_argument("--tipo", help="plane, cone, spline, torus, sphere")
    b.add_argument("--eixo", choices=["x", "y", "z"],
                   help="só planos com essa normal / cilindros com esse eixo")
    args = ap.parse_args(argv)
    if args.cmd == "corpos":
        cmd_corpos(args.sat)
    else:
        cmd_faces(args.sat, args.corpo, args.tipo, args.eixo)


if __name__ == "__main__":
    main()
