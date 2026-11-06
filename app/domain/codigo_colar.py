"""Código da coluna «Colar» da Lista Material (PROCESSO_ESPECIAL), em ENSAIO desde 06-11-2026.

Diz à fábrica que peças se colam umas às outras e o que se faz antes e depois da colagem.
Escreve-se na LISTAGEM_CUT_RITE do modelo de ensaio ``Lista_Material_IMOS_MARTELO_COLAR.xltm``
(coluna «Colar», logo a seguir à CNC_2) e segue para o Cut-Rite. As mesmas regras estão no
VBA do modelo (``scripts/vba/colar/modColar.bas``); se mudarem aqui, mudam lá.

Forma: ``[CNC_]conjunto[_orlas][_CNC]``, blocos separados por «_», sem espaços.

- ``CNC`` no início: passa na CNC antes da colagem; ``CNC`` no fim: depois.
- conjunto: os IDs da coluna ID juntos com «+»; ``21x2`` = duas peças do ID 21. Duas
  peças do mesmo ID sozinhas escrevem-se ``14+14`` (como no guia e no hábito antigo).
- orlas depois da colagem: ``O4L`` (4 lados), ``OC2``/``OC1`` (comprimentos),
  ``OL2``/``OL1`` (larguras), ``OR`` (raio / meia-lua), juntas com «+». Com 2
  comprimentos e 2 larguras escreve-se ``O4L`` (decisão do Paulo, 06-11-2026).

Exemplos: ``CNC_20+21x2+22x2_OC2+OL2_CNC``, ``CNC_20+21x2+22x2_O4L``, ``14+14_O4L_CNC``,
``14+16_OC2+OR``. As peças do mesmo conjunto levam todas o mesmo código.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ORLAS = ("O4L", "OC2", "OC1", "OL2", "OL1", "OR")
_PECA = re.compile(r"^(\d+)(?:[xX](\d+))?$")


@dataclass(frozen=True)
class CodigoColar:
    """Um código lido ou por escrever: (ID, quantidade) pela ordem do código."""

    pecas: tuple[tuple[int, int], ...]
    orlas: tuple[str, ...] = ()
    cnc_inicio: bool = False
    cnc_fim: bool = False

    @property
    def ids(self) -> tuple[int, ...]:
        return tuple(i for i, _ in self.pecas)

    @property
    def total_pecas(self) -> int:
        return sum(q for _, q in self.pecas)


def _juntar(pecas) -> tuple[tuple[int, int], ...]:
    """O mesmo ID repetido soma-se, ficando no sítio onde apareceu primeiro."""
    quantidades: dict[int, int] = {}
    for ident, quantidade in pecas:
        quantidades[int(ident)] = quantidades.get(int(ident), 0) + int(quantidade)
    return tuple((i, q) for i, q in quantidades.items() if q > 0)


def orlas_depois(comprimentos: int, larguras: int, raio: bool = False) -> tuple[str, ...]:
    """Os códigos de orla a partir do que se escolhe no menu (0, 1 ou 2 de cada)."""
    if comprimentos == 2 and larguras == 2:
        orlas = ["O4L"]
    else:
        orlas = [f"OC{comprimentos}"] if comprimentos in (1, 2) else []
        if larguras in (1, 2):
            orlas.append(f"OL{larguras}")
    if raio:
        orlas.append("OR")
    return tuple(orlas)


def texto_conjunto(pecas) -> str:
    pecas = _juntar(pecas)
    if len(pecas) == 1 and pecas[0][1] == 2:
        return f"{pecas[0][0]}+{pecas[0][0]}"
    return "+".join(str(i) if q == 1 else f"{i}x{q}" for i, q in pecas)


def montar(codigo: CodigoColar) -> str:
    """O texto do código. Sem peças, devolve vazio."""
    if not codigo.pecas:
        return ""
    blocos = ["CNC"] if codigo.cnc_inicio else []
    blocos.append(texto_conjunto(codigo.pecas))
    if codigo.orlas:
        blocos.append("+".join(codigo.orlas))
    if codigo.cnc_fim:
        blocos.append("CNC")
    return "_".join(blocos)


def ler(texto: str) -> CodigoColar:
    """Lê um código; ``ValueError`` com o motivo em português quando não está certo."""
    original = str(texto or "").strip()
    if not original:
        raise ValueError("está vazio")
    if re.search(r"\s", original):
        raise ValueError("tem espaços (o código escreve-se sem espaços)")
    blocos = original.split("_")
    if any(not b for b in blocos):
        raise ValueError("tem um bloco vazio (dois «_» seguidos ou «_» na ponta)")
    cnc_inicio = blocos[0].upper() == "CNC"
    if cnc_inicio:
        blocos = blocos[1:]
    cnc_fim = bool(blocos) and blocos[-1].upper() == "CNC"
    if cnc_fim:
        blocos = blocos[:-1]
    if not blocos:
        raise ValueError("falta o conjunto de peças (os IDs)")
    if len(blocos) > 2:
        raise ValueError("tem blocos a mais: [CNC_]conjunto[_orlas][_CNC]")

    pecas = []
    for parte in blocos[0].split("+"):
        encontrado = _PECA.match(parte)
        if not encontrado:
            raise ValueError(f"«{parte}» não é um ID (ex.: 14 ou 21x2)")
        quantidade = int(encontrado.group(2) or 1)
        if quantidade < 1:
            raise ValueError(f"«{parte}»: a quantidade tem de ser 1 ou mais")
        pecas.append((int(encontrado.group(1)), quantidade))
    pecas = _juntar(pecas)
    if sum(q for _, q in pecas) < 2:
        raise ValueError("um conjunto para colar tem de ter pelo menos 2 peças")

    orlas: list[str] = []
    if len(blocos) == 2:
        for parte in blocos[1].split("+"):
            orla = parte.upper()
            if orla not in ORLAS:
                raise ValueError(f"«{parte}» não é uma orla ({', '.join(ORLAS)})")
            if orla in orlas:
                raise ValueError(f"a orla {orla} está repetida")
            orlas.append(orla)
        comprimentos = [o for o in orlas if o.startswith("OC")]
        larguras = [o for o in orlas if o.startswith("OL")]
        if "O4L" in orlas and (comprimentos or larguras):
            raise ValueError("O4L já são os 4 lados: não se junta com OC nem OL")
        if len(comprimentos) > 1 or len(larguras) > 1:
            raise ValueError("só um OC (1 ou 2 comprimentos) e um OL (1 ou 2 larguras)")
    return CodigoColar(tuple(pecas), tuple(orlas), cnc_inicio, cnc_fim)


def _id(valor) -> int | None:
    try:
        return int(float(str(valor).strip().replace(",", ".")))
    except (TypeError, ValueError):
        return None


def problemas_na_listagem(linhas) -> list[str]:
    """Confere os códigos de uma listagem: ``linhas`` = pares (ID, Colar) das linhas.

    Apanha códigos mal escritos, IDs que não existem e conjuntos desencontrados: a
    coluna ID renumera-se sozinha quando se insere ou apaga uma linha, e o código, que
    é texto, fica a apontar para os IDs antigos.
    """
    colar_por_id: dict[int, str] = {}
    for ident, colar in linhas:
        numero = _id(ident)
        if numero is not None:
            colar_por_id[numero] = str(colar or "").strip()
    problemas: list[str] = []

    def juntar(texto: str) -> None:
        if texto not in problemas:
            problemas.append(texto)

    for numero, texto in colar_por_id.items():
        if not texto:
            continue
        try:
            codigo = ler(texto)
        except ValueError as erro:
            juntar(f"ID {numero}: o código «{texto}» {erro}.")
            continue
        if numero not in codigo.ids:
            juntar(
                f"ID {numero}: o código «{texto}» não inclui o ID {numero} "
                "(a numeração mudou depois de o código ser escrito?)."
            )
        for outro in codigo.ids:
            if outro not in colar_por_id:
                juntar(f"«{texto}»: o ID {outro} não existe na listagem.")
            elif colar_por_id[outro] != texto:
                juntar(
                    f"«{texto}»: a linha ID {outro} tem outro código "
                    f"({colar_por_id[outro] or 'vazio'}); o conjunto leva o mesmo código "
                    "em todas as peças."
                )
    return problemas
