"""Extração (pura) dos dados do plano de corte a partir de uma versão (C3.2).

Recebe os dicts do "Resumo Geral" (``construir_linhas_geral``) e as placas do
resumo (``resumo.placas``) e devolve grupos de peças de PLACA por
material/espessura/placa, já com a contagem de placas do ORÇAMENTO (para depois
comparar com o otimizador). Sem DB nem Qt.
"""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from app.domain.plano_corte import PecaCorte, ResultadoEmpacotamento, empacotar


def _rodar(def_peca: str | None) -> bool:
    """True se a peça é gaveta/rodapé (sem veio -> pode rodar)."""
    s = unicodedata.normalize("NFKD", str(def_peca or "").upper())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return ("GAVET" in s) or ("RODAPE" in s)


@dataclass(frozen=True)
class GrupoCorte:
    """Peças de um material/espessura/placa, com as placas do orçamento."""

    ref: str            # descricao_no_orcamento (material)
    esp: float          # esp_mp
    placa_comp: float   # comp_mp
    placa_larg: float   # larg_mp
    pecas: list[PecaCorte]
    placas_orcamento: int   # qt_placas (do orçamento) deste material/esp/placa


def _to_float(value) -> float | None:
    """Converte para float; None se vazio/inválido."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mm(value) -> int | None:
    """Dimensão normalizada para mm inteiros (None se inválida)."""
    numero = _to_float(value)
    if numero is None:
        return None
    return int(round(numero))


def _esp_chave(value) -> float | None:
    """Espessura normalizada (1 casa) para a chave (None se inválida)."""
    numero = _to_float(value)
    if numero is None:
        return None
    return round(numero, 1)


def _chave(ref, esp, comp, larg) -> tuple[str, float, int, int] | None:
    """Chave normalizada (ref, esp, comp, larg) ou None se dims inválidas."""
    comp_n = _mm(comp)
    larg_n = _mm(larg)
    esp_n = _esp_chave(esp)
    if comp_n is None or larg_n is None or esp_n is None:
        return None
    if comp_n <= 0 or larg_n <= 0:
        return None
    return (str(ref or "").strip(), esp_n, comp_n, larg_n)


def construir_grupos_corte(linhas_geral: list[dict], placas) -> list[GrupoCorte]:
    """Constrói os grupos de peças de placa a partir das linhas e das placas."""
    # Índice das placas por chave normalizada -> soma de qt_placas + valores reais.
    indice: dict[tuple[str, float, int, int], dict] = {}
    for placa in placas or []:
        ref = getattr(placa, "descricao_no_orcamento", None)
        esp = getattr(placa, "esp_mp", None)
        comp = getattr(placa, "comp_mp", None)
        larg = getattr(placa, "larg_mp", None)
        chave = _chave(ref, esp, comp, larg)
        if chave is None:
            continue
        qt = _to_float(getattr(placa, "qt_placas", None)) or 0.0
        entrada = indice.get(chave)
        if entrada is None:
            indice[chave] = {
                "ref": str(ref or "").strip(),
                "esp": _to_float(esp) or 0.0,
                "comp": _to_float(comp) or 0.0,
                "larg": _to_float(larg) or 0.0,
                "placas_orcamento": int(round(qt)),
            }
        else:
            entrada["placas_orcamento"] += int(round(qt))

    # Peças de placa por chave (só linhas cuja chave existe no índice de placas).
    pecas_por_chave: dict[tuple[str, float, int, int], list[PecaCorte]] = {}
    contador = 0
    for linha in linhas_geral or []:
        chave = _chave(
            linha.get("descricao_no_orcamento"),
            linha.get("esp_mp"),
            linha.get("comp_mp"),
            linha.get("larg_mp"),
        )
        if chave is None or chave not in indice:
            continue

        comp_real = _to_float(linha.get("comp_real"))
        larg_real = _to_float(linha.get("larg_real"))
        qt_total = _to_float(linha.get("qt_total"))
        if not comp_real or comp_real <= 0:
            continue
        if not larg_real or larg_real <= 0:
            continue
        if not qt_total or qt_total <= 0:
            continue

        def_peca = linha.get("def_peca")
        roda = _rodar(def_peca)
        for _ in range(int(round(qt_total))):
            contador += 1
            pecas_por_chave.setdefault(chave, []).append(
                PecaCorte(
                    id=contador,
                    desc=str(def_peca or ""),
                    comp=comp_real,
                    larg=larg_real,
                    rodar=roda,
                )
            )

    grupos = [
        GrupoCorte(
            ref=indice[chave]["ref"],
            esp=indice[chave]["esp"],
            placa_comp=indice[chave]["comp"],
            placa_larg=indice[chave]["larg"],
            pecas=pecas,
            placas_orcamento=indice[chave]["placas_orcamento"],
        )
        for chave, pecas in pecas_por_chave.items()
    ]
    grupos.sort(key=lambda g: (g.ref, g.esp))
    return grupos


@dataclass(frozen=True)
class GrupoCorteResultado:
    """Um grupo de corte com o resultado do otimizador."""

    grupo: GrupoCorte
    resultado: ResultadoEmpacotamento


@dataclass(frozen=True)
class LinhaResumoCorte:
    """Uma linha do resumo: placas do orçamento vs placas do otimizador."""

    ref: str
    esp: float
    dim_placa: str
    placas_orcamento: int
    placas_otimizador: int
    diferenca: int
    aproveitamento_pct: float
    nao_alocadas: int


def empacotar_grupos(
    grupos, *, kerf: float = 3.0, rotacao: bool = True
) -> list[GrupoCorteResultado]:
    """Corre o otimizador em cada grupo e devolve grupo + resultado."""
    return [
        GrupoCorteResultado(
            grupo=grupo,
            resultado=empacotar(
                grupo.pecas, grupo.placa_comp, grupo.placa_larg,
                kerf=kerf, rotacao=rotacao,
            ),
        )
        for grupo in grupos
    ]


def construir_resumo_corte(
    resultados: list[GrupoCorteResultado],
) -> list[LinhaResumoCorte]:
    """Constrói as linhas do resumo (orçamento vs otimizador) por grupo."""
    linhas: list[LinhaResumoCorte] = []
    for item in resultados:
        grupo = item.grupo
        resultado = item.resultado
        placas_otimizador = len(resultado.placas)
        linhas.append(
            LinhaResumoCorte(
                ref=grupo.ref,
                esp=grupo.esp,
                dim_placa=f"{int(grupo.placa_comp)}x{int(grupo.placa_larg)}",
                placas_orcamento=grupo.placas_orcamento,
                placas_otimizador=placas_otimizador,
                # Negativo = o otimizador poupa placas face ao orçamento.
                diferenca=placas_otimizador - grupo.placas_orcamento,
                aproveitamento_pct=resultado.aproveitamento_pct,
                nao_alocadas=len(resultado.nao_alocadas),
            )
        )
    return linhas
