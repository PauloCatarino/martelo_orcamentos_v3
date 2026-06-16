"""Aggregate the consumption/cost of a budget version (phase 8W.0).

Pure and testable: it takes a flat list of :class:`LinhaConsumo` (each costing
line already projected, carrying the QUANTITY OF ITS ITEM) and produces the
consumption tables (boards, edge banding, hardware, machines/labour) plus the
cost distribution for the pie chart.

Rules (mirroring Martelo V2, but reading the V3 cost-line fields):
- every consumption (m2 / ml / qt) AND its theoretical cost are multiplied by
  the item quantity (``item_qt``);
- consumptions ALWAYS count, even when the item has an "Excluir X" flag set
  (the physical consumption is for purchasing); the Excluir flags only affect
  what enters the COST DISTRIBUTION / sell total;
- SEPARADOR, DIVISAO_INDEPENDENTE and the PECA_COMPOSTA header are ignored (the
  real consumption/cost lives in the actual piece/hardware lines).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, Decimal

from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    FERRAGEM,
    PECA_COMPOSTA,
    SEPARADOR,
)
from app.domain.custos import fator_desperdicio
from app.domain.medidas import normalizar_numero
from app.domain.orlas import selecionar_largura_orla_mm
from app.domain.precos import (
    BlocosCusto,
    MargensOrcamento,
    calcular_preco_unitario,
)

_ZERO = Decimal("0")
_UM = Decimal("1")
_MIL = Decimal("1000")

# Edge-banding thicknesses (the V3 line splits orla into fina/grossa).
_ESP_ORLA_FINA = Decimal("0.4")
_ESP_ORLA_GROSSA = Decimal("1.0")

_UNIDADES_M2 = {"M2", "M²", "M2.", "MTQ", "METRO2", "M^2"}
_UNIDADES_UND = {"UND", "UN", "UNID", "UNIDADE"}
_UNIDADES_ML = {"ML", "M", "MTL", "METRO"}


@dataclass(frozen=True)
class LinhaConsumo:
    """One costing line projected for the consumption aggregation."""

    tipo_linha: str
    item_qt: Decimal = _UM
    unidade: str | None = None
    quantidade: Decimal | None = None          # qt_total of the line
    area_m2: Decimal | None = None              # per unit
    perimetro_ml: Decimal | None = None         # per unit
    comp_mp: Decimal | None = None
    larg_mp: Decimal | None = None
    esp_mp: Decimal | None = None
    esp_real: Decimal | None = None
    preco_liquido: Decimal | None = None
    desperdicio_percentagem: Decimal | None = None
    ref_le: str | None = None
    descricao_no_orcamento: str | None = None
    familia_materia_prima: str | None = None
    # Edge banding (fine = 0.4 mm / coresp_orla_0_4, thick = 1.0 mm / coresp_orla_1_0)
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    ml_orla_fina: Decimal | None = None
    ml_orla_grossa: Decimal | None = None
    custo_orla_fina: Decimal | None = None
    custo_orla_grossa: Decimal | None = None
    consumo_ml_total: Decimal | None = None
    # Costs (line totals; multiplied by item_qt here)
    custo_mp: Decimal | None = None
    custo_orlas: Decimal | None = None
    custo_ferragem: Decimal | None = None
    custo_acabamento: Decimal | None = None
    custo_producao: Decimal | None = None
    custo_corte: Decimal | None = None
    custo_orlagem: Decimal | None = None
    custo_cnc: Decimal | None = None
    custo_montagem_manual: Decimal | None = None
    # Exclusions (only the distribution honours them)
    excluir_mp: bool = False
    excluir_orla: bool = False
    excluir_ferragem: bool = False
    excluir_producao: bool = False
    excluir_acabamento: bool = False
    excluir_mo: bool = False


# --- Output models -----------------------------------------------------------


@dataclass(frozen=True)
class ConsumoPlaca:
    ref_le: str | None
    descricao_no_orcamento: str | None
    esp_mp: Decimal
    pliq: Decimal
    unidade: str | None
    desp: Decimal
    comp_mp: Decimal
    larg_mp: Decimal
    area_placa: Decimal
    m2_total_pecas: Decimal
    m2_consumidos: Decimal
    qt_placas: int
    custo_mp_total: Decimal
    custo_placa_inteira: Decimal
    nao_stock: bool = False


@dataclass(frozen=True)
class ConsumoOrla:
    ref_orla: str | None
    descricao: str | None
    espessura: Decimal
    largura: Decimal | None
    ml_total: Decimal
    custo_total: Decimal


@dataclass(frozen=True)
class ConsumoFerragem:
    ref_le: str | None
    descricao_no_orcamento: str | None
    pliq: Decimal
    unidade: str | None
    desp: Decimal
    qt_total: Decimal
    ml: Decimal
    custo_total: Decimal


@dataclass(frozen=True)
class ConsumoMaquina:
    centro: str
    custo_total: Decimal
    ml_corte: Decimal
    ml_orlado: Decimal
    num_pecas: Decimal


@dataclass(frozen=True)
class DistribuicaoCategoria:
    nome: str
    euros: Decimal
    pct: Decimal


@dataclass(frozen=True)
class DistribuicaoCustos:
    categorias: list = field(default_factory=list)
    custo_produzido: Decimal = _ZERO
    margens_euros: Decimal = _ZERO
    total_venda: Decimal = _ZERO


@dataclass(frozen=True)
class ResumoConsumos:
    placas: list
    orlas: list
    ferragens: list
    maquinas: list
    distribuicao: DistribuicaoCustos


# --- Helpers -----------------------------------------------------------------


def _num(valor) -> Decimal:
    """Normalise to Decimal, defaulting missing/invalid to 0."""
    numero = normalizar_numero(valor)
    return numero if numero is not None else _ZERO


def _eh_linha_real(tipo_linha: str | None) -> bool:
    """A real piece/hardware line (not a division/composite header/separator)."""
    return tipo_linha not in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR)


def _unidade_norm(unidade: str | None) -> str:
    return (unidade or "").strip().upper()


def _eh_m2(unidade: str | None) -> bool:
    return _unidade_norm(unidade) in _UNIDADES_M2


def _linhas_reais(linhas):
    return [linha for linha in linhas if _eh_linha_real(linha.tipo_linha)]


# --- 1. Boards (placas) ------------------------------------------------------


def agregar_placas(linhas) -> list:
    """Group M2 material lines by (ref_le, descricao, esp_mp) and size the boards.

    area_placa = (comp_mp/1000) * (larg_mp/1000);
    m2_total_pecas = Σ area_m2 * qt_total * item_qt;
    m2_consumidos = m2_total_pecas * (1 + desp);
    qt_placas = ceil(m2_consumidos / area_placa);
    custo_mp_total = Σ custo_mp * item_qt   (theoretical, with waste %);
    custo_placa_inteira = qt_placas * area_placa * pliq.
    """
    grupos: dict[tuple, dict] = {}
    for linha in _linhas_reais(linhas):
        if not _eh_m2(linha.unidade):
            continue

        item_qt = _num(linha.item_qt)
        qt_total = _num(linha.quantidade)
        comp_mp = _num(linha.comp_mp)
        larg_mp = _num(linha.larg_mp)
        esp_mp = _num(linha.esp_mp)
        area_placa = (comp_mp / _MIL) * (larg_mp / _MIL)
        m2_pecas = _num(linha.area_m2) * qt_total * item_qt
        m2_consumidos = m2_pecas * fator_desperdicio(linha.desperdicio_percentagem)

        chave = (linha.ref_le, linha.descricao_no_orcamento, esp_mp)
        grupo = grupos.get(chave)
        if grupo is None:
            grupo = grupos[chave] = {
                "ref_le": linha.ref_le,
                "descricao_no_orcamento": linha.descricao_no_orcamento,
                "esp_mp": esp_mp,
                "pliq": _num(linha.preco_liquido),
                "unidade": linha.unidade,
                "desp": _num(linha.desperdicio_percentagem),
                "comp_mp": comp_mp,
                "larg_mp": larg_mp,
                "area_placa": area_placa,
                "m2_total_pecas": _ZERO,
                "m2_consumidos": _ZERO,
                "custo_mp_total": _ZERO,
            }
        if area_placa > 0:
            grupo["area_placa"] = area_placa
            grupo["comp_mp"] = comp_mp
            grupo["larg_mp"] = larg_mp
        if _num(linha.preco_liquido) > 0:
            grupo["pliq"] = _num(linha.preco_liquido)
        grupo["m2_total_pecas"] += m2_pecas
        grupo["m2_consumidos"] += m2_consumidos
        grupo["custo_mp_total"] += _num(linha.custo_mp) * item_qt

    placas: list[ConsumoPlaca] = []
    for grupo in grupos.values():
        area = grupo["area_placa"]
        qt_placas = (
            int((grupo["m2_consumidos"] / area).to_integral_value(ROUND_CEILING))
            if area > 0 and grupo["m2_consumidos"] > 0
            else 0
        )
        placas.append(
            ConsumoPlaca(
                ref_le=grupo["ref_le"],
                descricao_no_orcamento=grupo["descricao_no_orcamento"],
                esp_mp=grupo["esp_mp"],
                pliq=grupo["pliq"],
                unidade=grupo["unidade"],
                desp=grupo["desp"],
                comp_mp=grupo["comp_mp"],
                larg_mp=grupo["larg_mp"],
                area_placa=area,
                m2_total_pecas=grupo["m2_total_pecas"],
                m2_consumidos=grupo["m2_consumidos"],
                qt_placas=qt_placas,
                custo_mp_total=grupo["custo_mp_total"],
                custo_placa_inteira=Decimal(qt_placas) * area * grupo["pliq"],
                nao_stock=False,
            )
        )
    return placas


# --- 2. Edge banding (orlas) -------------------------------------------------


def agregar_orlas(linhas) -> list:
    """Split each line's edge banding into fine (0.4 mm) / thick (1.0 mm) groups.

    The fine banding goes to the coresp_orla_0_4 reference and the thick to
    coresp_orla_1_0; ml and cost are multiplied by item_qt. The roll width comes
    from the piece thickness (esp_real).
    """
    grupos: dict[tuple, dict] = {}

    def acumular(ref, descricao, espessura, largura, ml, custo):
        if not ref or (ml == 0 and custo == 0):
            return
        chave = (ref, descricao, espessura)
        grupo = grupos.get(chave)
        if grupo is None:
            grupo = grupos[chave] = {
                "ref_orla": ref,
                "descricao": descricao,
                "espessura": espessura,
                "largura": largura,
                "ml_total": _ZERO,
                "custo_total": _ZERO,
            }
        grupo["ml_total"] += ml
        grupo["custo_total"] += custo

    for linha in _linhas_reais(linhas):
        item_qt = _num(linha.item_qt)
        largura = selecionar_largura_orla_mm(linha.esp_real)
        acumular(
            linha.coresp_orla_0_4,
            linha.descricao_no_orcamento,
            _ESP_ORLA_FINA,
            largura,
            _num(linha.ml_orla_fina) * item_qt,
            _num(linha.custo_orla_fina) * item_qt,
        )
        acumular(
            linha.coresp_orla_1_0,
            linha.descricao_no_orcamento,
            _ESP_ORLA_GROSSA,
            largura,
            _num(linha.ml_orla_grossa) * item_qt,
            _num(linha.custo_orla_grossa) * item_qt,
        )

    return [
        ConsumoOrla(
            ref_orla=g["ref_orla"],
            descricao=g["descricao"],
            espessura=g["espessura"],
            largura=g["largura"],
            ml_total=g["ml_total"],
            custo_total=g["custo_total"],
        )
        for g in grupos.values()
    ]


# --- 3. Hardware (ferragens) -------------------------------------------------


def agregar_ferragens(linhas) -> list:
    """Group FERRAGEM lines (unit UND or ML) by (ref_le, descricao).

    qt_total = Σ quantidade * item_qt; ml = Σ consumo_ml_total * item_qt (ML);
    custo_total = Σ custo_ferragem * item_qt.
    """
    grupos: dict[tuple, dict] = {}
    for linha in _linhas_reais(linhas):
        if linha.tipo_linha != FERRAGEM:
            continue
        unidade = _unidade_norm(linha.unidade)
        if unidade and unidade not in _UNIDADES_UND and unidade not in _UNIDADES_ML:
            continue

        item_qt = _num(linha.item_qt)
        chave = (linha.ref_le, linha.descricao_no_orcamento)
        grupo = grupos.get(chave)
        if grupo is None:
            grupo = grupos[chave] = {
                "ref_le": linha.ref_le,
                "descricao_no_orcamento": linha.descricao_no_orcamento,
                "pliq": _num(linha.preco_liquido),
                "unidade": linha.unidade,
                "desp": _num(linha.desperdicio_percentagem),
                "qt_total": _ZERO,
                "ml": _ZERO,
                "custo_total": _ZERO,
            }
        grupo["qt_total"] += _num(linha.quantidade) * item_qt
        if unidade in _UNIDADES_ML:
            grupo["ml"] += _num(linha.consumo_ml_total) * item_qt
        grupo["custo_total"] += _num(linha.custo_ferragem) * item_qt

    return [
        ConsumoFerragem(
            ref_le=g["ref_le"],
            descricao_no_orcamento=g["descricao_no_orcamento"],
            pliq=g["pliq"],
            unidade=g["unidade"],
            desp=g["desp"],
            qt_total=g["qt_total"],
            ml=g["ml"],
            custo_total=g["custo_total"],
        )
        for g in grupos.values()
    ]


# --- 4. Machines / labour ----------------------------------------------------


_CENTROS = (
    ("Seccionadora (Corte)", "custo_corte"),
    ("Orladora (Orlagem)", "custo_orlagem"),
    ("CNC (Mecanizações)", "custo_cnc"),
    ("Montagem / Manual", "custo_montagem_manual"),
)


def agregar_maquinas(linhas) -> list:
    """Aggregate production costs per machine/labour centre.

    custo_total = Σ custo_<centro> * item_qt; num_pecas = Σ qt_total * item_qt on
    the lines that used that centre; ml_corte (Seccionadora) = Σ perimetro_ml *
    qt_total * item_qt; ml_orlado (Orladora) = Σ (ml_orla_fina+ml_orla_grossa) *
    item_qt.
    """
    centros: list[ConsumoMaquina] = []
    reais = _linhas_reais(linhas)
    for nome, campo in _CENTROS:
        custo_total = _ZERO
        num_pecas = _ZERO
        ml_corte = _ZERO
        ml_orlado = _ZERO
        for linha in reais:
            item_qt = _num(linha.item_qt)
            custo = _num(getattr(linha, campo))
            if custo <= 0:
                continue
            custo_total += custo * item_qt
            num_pecas += _num(linha.quantidade) * item_qt
            if campo == "custo_corte":
                ml_corte += _num(linha.perimetro_ml) * _num(linha.quantidade) * item_qt
            elif campo == "custo_orlagem":
                ml_orlado += (
                    _num(linha.ml_orla_fina) + _num(linha.ml_orla_grossa)
                ) * item_qt
        centros.append(
            ConsumoMaquina(
                centro=nome,
                custo_total=custo_total,
                ml_corte=ml_corte,
                ml_orlado=ml_orlado,
                num_pecas=num_pecas,
            )
        )
    return centros


# --- 5. Cost distribution (pie chart) ---------------------------------------


def distribuicao_custos(
    linhas, margens: MargensOrcamento, ajuste_eur_total=_ZERO
) -> DistribuicaoCustos:
    """Per-category cost totals (respecting the Excluir flags) + margins + sell.

    Unlike the consumption tables, here the Excluir flags DO count: an excluded
    cost does not enter the distribution nor the produced cost. The sell total
    reuses the existing pricing (precos.calcular_preco_unitario) with the version
    margins applied to the aggregated cost blocks.
    """
    placas = orlas = ferragens = maquinas = acabamentos = _ZERO
    for linha in _linhas_reais(linhas):
        item_qt = _num(linha.item_qt)
        if not linha.excluir_mp:
            placas += _num(linha.custo_mp) * item_qt
        if not linha.excluir_orla:
            orlas += _num(linha.custo_orlas) * item_qt
        if not linha.excluir_ferragem:
            ferragens += _num(linha.custo_ferragem) * item_qt
        if not linha.excluir_producao:
            maquinas += _num(linha.custo_producao) * item_qt
        if not linha.excluir_acabamento:
            acabamentos += _num(linha.custo_acabamento) * item_qt

    custo_produzido = placas + orlas + ferragens + maquinas + acabamentos
    blocos = BlocosCusto(
        bloco_mp=placas + orlas + ferragens,
        bloco_producao=maquinas,
        bloco_acabamento=acabamentos,
    )
    total_venda = calcular_preco_unitario(blocos, margens, ajuste_eur_total)
    margens_euros = total_venda - custo_produzido

    def categoria(nome, euros) -> DistribuicaoCategoria:
        pct = (euros / total_venda * Decimal("100")) if total_venda > 0 else _ZERO
        return DistribuicaoCategoria(nome=nome, euros=euros, pct=pct)

    categorias = [
        categoria("Placas", placas),
        categoria("Orlas", orlas),
        categoria("Ferragens", ferragens),
        categoria("Máquinas / MO", maquinas),
        categoria("Acabamentos", acabamentos),
        categoria("Margens", margens_euros),
    ]
    return DistribuicaoCustos(
        categorias=categorias,
        custo_produzido=custo_produzido,
        margens_euros=margens_euros,
        total_venda=total_venda,
    )


def agregar_consumos(
    linhas, margens: MargensOrcamento, ajuste_eur_total=_ZERO
) -> ResumoConsumos:
    """Build the full consumption/cost summary of a budget version."""
    return ResumoConsumos(
        placas=agregar_placas(linhas),
        orlas=agregar_orlas(linhas),
        ferragens=agregar_ferragens(linhas),
        maquinas=agregar_maquinas(linhas),
        distribuicao=distribuicao_custos(linhas, margens, ajuste_eur_total),
    )
