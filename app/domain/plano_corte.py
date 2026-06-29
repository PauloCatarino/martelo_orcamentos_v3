"""Otimizador (puro) do plano de corte: bin-packing de peças numa placa (C3.1).

Sem DB, sem Qt e sem reportlab — só ``dataclasses`` e (opcionalmente)
``rectpack`` — para ser testável e determinístico. Ao contrário do V2 (um só
algoritmo), tenta VÁRIOS algoritmos do ``rectpack`` e escolhe o melhor resultado
(menos placas; desempate por maior aproveitamento). Se o ``rectpack`` não estiver
instalado, recorre a um fallback ingénuo (1 peça por placa) para a app nunca
partir.

VEIO (grão): tratado ao nível do MATERIAL na fase seguinte (C3.2). Se o material
tem veio, o chamador passa ``rotacao=False`` (a placa não roda peças); senão
``rotacao=True``. Aqui não há deteção de veio.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PecaCorte:
    """Uma peça a cortar (dimensões em mm)."""

    id: int
    desc: str
    comp: float
    larg: float


@dataclass
class PecaColocada:
    """Uma peça já posicionada numa placa (dimensões REAIS, sem kerf)."""

    desc: str
    x: float
    y: float
    comp: float
    larg: float


@dataclass
class PlacaColocada:
    """Uma placa com as peças nela colocadas."""

    comp: float
    larg: float
    pecas: list[PecaColocada] = field(default_factory=list)


@dataclass
class ResultadoEmpacotamento:
    """Resultado do empacotamento de um conjunto de peças numa placa."""

    placas: list[PlacaColocada]
    nao_alocadas: list[PecaCorte]
    aproveitamento_pct: float
    area_pecas_m2: float
    area_placas_m2: float


# Algoritmos do rectpack a experimentar (importados tardiamente em
# :func:`_empacotar_rectpack` para o fallback funcionar sem o pacote).
_ALGORITMOS = ("MaxRectsBaf", "MaxRectsBssf", "GuillotineBssfSas", "SkylineBlWm")


def empacotar(
    pecas: list[PecaCorte],
    placa_comp: float,
    placa_larg: float,
    *,
    kerf: float = 3.0,
    rotacao: bool = True,
) -> ResultadoEmpacotamento:
    """Empacota ``pecas`` em placas de ``placa_comp`` x ``placa_larg`` (mm).

    Cada peça ocupa ``(comp+kerf) x (larg+kerf)`` ao empacotar; as
    :class:`PecaColocada` guardam as dimensões REAIS (sem kerf) e a posição
    devolvida. Peças com ``comp<=0``/``larg<=0`` são ignoradas; peças que (com
    kerf) não caibam na placa em nenhuma orientação permitida vão para
    ``nao_alocadas``.
    """
    try:
        return _empacotar_rectpack(
            pecas, placa_comp, placa_larg, kerf=kerf, rotacao=rotacao
        )
    except ImportError:
        return _empacotar_ingenuo(
            pecas, placa_comp, placa_larg, kerf=kerf, rotacao=rotacao
        )


# ----- helpers puros -----


def _validas(pecas: list[PecaCorte]) -> list[PecaCorte]:
    return [p for p in pecas if p.comp > 0 and p.larg > 0]


def _cabe(
    peca: PecaCorte,
    placa_comp: float,
    placa_larg: float,
    kerf: float,
    rotacao: bool,
) -> bool:
    """Diz se a peça (com kerf) cabe na placa numa orientação permitida."""
    comp = peca.comp + kerf
    larg = peca.larg + kerf
    if comp <= placa_comp and larg <= placa_larg:
        return True
    if rotacao and larg <= placa_comp and comp <= placa_larg:
        return True
    return False


def _separar(
    pecas: list[PecaCorte],
    placa_comp: float,
    placa_larg: float,
    kerf: float,
    rotacao: bool,
) -> tuple[list[PecaCorte], list[PecaCorte]]:
    """Separa as peças válidas em (cabem, não cabem)."""
    cabem: list[PecaCorte] = []
    fora: list[PecaCorte] = []
    for peca in _validas(pecas):
        destino = cabem if _cabe(peca, placa_comp, placa_larg, kerf, rotacao) else fora
        destino.append(peca)
    return cabem, fora


def _construir_resultado(
    placas: list[PlacaColocada],
    nao_alocadas: list[PecaCorte],
    placa_comp: float,
    placa_larg: float,
) -> ResultadoEmpacotamento:
    """Calcula áreas (m²) e aproveitamento e monta o resultado."""
    area_pecas_mm2 = sum(
        pc.comp * pc.larg for placa in placas for pc in placa.pecas
    )
    area_placas_mm2 = len(placas) * placa_comp * placa_larg
    aproveitamento = (
        area_pecas_mm2 / area_placas_mm2 * 100 if area_placas_mm2 else 0.0
    )
    return ResultadoEmpacotamento(
        placas=placas,
        nao_alocadas=nao_alocadas,
        aproveitamento_pct=round(aproveitamento, 2),
        area_pecas_m2=round(area_pecas_mm2 / 1_000_000, 3),
        area_placas_m2=round(area_placas_mm2 / 1_000_000, 3),
    )


def _empacotar_rectpack(
    pecas: list[PecaCorte],
    placa_comp: float,
    placa_larg: float,
    *,
    kerf: float,
    rotacao: bool,
) -> ResultadoEmpacotamento:
    """Empacota com o rectpack, escolhendo o melhor de vários algoritmos.

    Levanta ``ImportError`` se o ``rectpack`` não estiver instalado (apanhado
    por :func:`empacotar`, que recorre ao fallback ingénuo).
    """
    import rectpack

    cabem, fora = _separar(pecas, placa_comp, placa_larg, kerf, rotacao)
    por_id = {peca.id: peca for peca in cabem}

    melhor: tuple[tuple[int, float], ResultadoEmpacotamento] | None = None
    for nome in _ALGORITMOS:
        algo = getattr(rectpack, nome)
        placas, nao_colocadas = _correr_algoritmo(
            rectpack, algo, cabem, por_id, placa_comp, placa_larg, kerf, rotacao
        )
        resultado = _construir_resultado(
            placas, fora + nao_colocadas, placa_comp, placa_larg
        )
        # Melhor = menos placas; desempate por maior aproveitamento.
        chave = (len(resultado.placas), -resultado.aproveitamento_pct)
        if melhor is None or chave < melhor[0]:
            melhor = (chave, resultado)

    if melhor is None:
        return _construir_resultado([], fora, placa_comp, placa_larg)
    return melhor[1]


def _correr_algoritmo(
    rectpack,
    algo,
    cabem: list[PecaCorte],
    por_id: dict[int, PecaCorte],
    placa_comp: float,
    placa_larg: float,
    kerf: float,
    rotacao: bool,
) -> tuple[list[PlacaColocada], list[PecaCorte]]:
    """Corre um algoritmo do rectpack e reconstrói as placas (descontando kerf)."""
    packer = rectpack.newPacker(
        mode=rectpack.PackingMode.Offline, pack_algo=algo, rotation=rotacao
    )
    # Tantos bins quantas as peças garante que qualquer peça que caiba é colocada.
    for _ in range(max(len(cabem), 1)):
        packer.add_bin(placa_comp, placa_larg)
    for peca in cabem:
        packer.add_rect(peca.comp + kerf, peca.larg + kerf, peca.id)
    packer.pack()

    pecas_por_bin: dict[int, list[PecaColocada]] = {}
    colocados: set[int] = set()
    for bin_idx, x, y, w, h, rid in packer.rect_list():
        peca = por_id[rid]
        colocados.add(rid)
        pecas_por_bin.setdefault(bin_idx, []).append(
            PecaColocada(
                desc=peca.desc,
                x=float(x),
                y=float(y),
                comp=float(w) - kerf,
                larg=float(h) - kerf,
            )
        )

    placas = [
        PlacaColocada(comp=placa_comp, larg=placa_larg, pecas=pecas_por_bin[bin_idx])
        for bin_idx in sorted(pecas_por_bin)
    ]
    nao_colocadas = [peca for peca in cabem if peca.id not in colocados]
    return placas, nao_colocadas


def _empacotar_ingenuo(
    pecas: list[PecaCorte],
    placa_comp: float,
    placa_larg: float,
    *,
    kerf: float,
    rotacao: bool,
) -> ResultadoEmpacotamento:
    """Fallback (sem rectpack): 1 peça por placa, como o V2 sem rectpack."""
    cabem, fora = _separar(pecas, placa_comp, placa_larg, kerf, rotacao)

    placas: list[PlacaColocada] = []
    for peca in cabem:
        # Orientação normal se couber; senão rodada (já se sabe que cabe numa).
        if peca.comp + kerf <= placa_comp and peca.larg + kerf <= placa_larg:
            comp, larg = peca.comp, peca.larg
        else:
            comp, larg = peca.larg, peca.comp
        placas.append(
            PlacaColocada(
                comp=placa_comp,
                larg=placa_larg,
                pecas=[PecaColocada(desc=peca.desc, x=0.0, y=0.0, comp=comp, larg=larg)],
            )
        )
    return _construir_resultado(placas, fora, placa_comp, placa_larg)
