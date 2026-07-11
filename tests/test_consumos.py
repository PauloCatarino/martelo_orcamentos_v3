"""Tests for the consumption/cost aggregation domain (phase 8W.0)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.consumos import (
    LinhaConsumo,
    agregar_ferragens,
    agregar_maquinas,
    agregar_operacoes,
    agregar_orlas,
    agregar_placas,
    distribuicao_custos,
)
from app.domain.precos import MargensOrcamento


def _linha(**kw) -> LinhaConsumo:
    base = dict(tipo_linha="PECA", item_qt=Decimal("1"))
    base.update(kw)
    return LinhaConsumo(**base)


# --- Placas ------------------------------------------------------------------


def test_placas_area_consumo_qt_e_custo() -> None:
    linha = _linha(
        unidade="m2", item_qt=Decimal("2"), quantidade=Decimal("3"),
        area_m2=Decimal("0.5"), comp_mp=Decimal("2750"), larg_mp=Decimal("1830"),
        esp_mp=Decimal("19"), preco_liquido=Decimal("5.79"),
        desperdicio_percentagem=Decimal("5"), custo_mp=Decimal("10"),
        ref_le="LE01", descricao_no_orcamento="AGL",
    )
    (placa,) = agregar_placas([linha])

    assert placa.area_placa == Decimal("5.0325")          # 2.75 x 1.83
    assert placa.m2_total_pecas == Decimal("3.0")         # 0.5 x 3 x 2
    assert placa.m2_consumidos == Decimal("3.15")         # x (1 + 5%)
    assert placa.qt_placas == 1                            # ceil(3.15 / 5.0325)
    # Theoretical (%-waste) cost = m2 consumidos x pliq.
    assert placa.custo_mp_total == Decimal("18.2385")     # 3.15 x 5.79
    assert placa.custo_placa_inteira == Decimal("29.138175")  # 1 x 5.0325 x 5.79
    assert placa.nao_stock is False
    # Not Não-Stock -> the budget uses the theoretical cost.
    assert placa.custo_no_orcamento == Decimal("18.2385")
    assert placa.agravamento == Decimal("0")


def test_placas_agrupa_por_ref_e_esp() -> None:
    comum = dict(
        unidade="m2", quantidade=Decimal("1"), area_m2=Decimal("1"),
        comp_mp=Decimal("2000"), larg_mp=Decimal("1000"),
        preco_liquido=Decimal("5"), ref_le="LE01", descricao_no_orcamento="AGL",
    )
    linhas = [
        _linha(**comum, esp_mp=Decimal("19")),
        _linha(**comum, esp_mp=Decimal("19")),   # same group -> accumulates
        _linha(**comum, esp_mp=Decimal("25")),   # different esp -> new group
    ]
    placas = agregar_placas(linhas)

    assert len(placas) == 2
    por_esp = {p.esp_mp: p for p in placas}
    assert por_esp[Decimal("19")].m2_total_pecas == Decimal("2")  # two lines
    assert por_esp[Decimal("25")].m2_total_pecas == Decimal("1")


# --- Orlas -------------------------------------------------------------------


def test_orlas_separa_fina_e_grossa_por_referencia() -> None:
    linha = _linha(
        item_qt=Decimal("2"), esp_real=Decimal("19"),
        descricao_no_orcamento="AGL",
        coresp_orla_0_4="ORLA_FINA", ml_orla_fina=Decimal("2"),
        custo_orla_fina=Decimal("1.5"),
        coresp_orla_1_0="ORLA_GROSSA", ml_orla_grossa=Decimal("1"),
        custo_orla_grossa=Decimal("0.8"),
    )
    orlas = agregar_orlas([linha])
    por_esp = {o.espessura: o for o in orlas}

    fina = por_esp[Decimal("0.4")]
    assert fina.ref_orla == "ORLA_FINA"
    assert fina.ml_total == Decimal("4")        # 2 x item_qt(2)
    assert fina.custo_total == Decimal("3.0")   # 1.5 x 2
    assert fina.largura == Decimal("22")        # roll width for esp 19 mm

    grossa = por_esp[Decimal("1.0")]
    assert grossa.ref_orla == "ORLA_GROSSA"
    assert grossa.ml_total == Decimal("2")      # 1 x 2
    assert grossa.custo_total == Decimal("1.6")  # 0.8 x 2


def test_orlas_ignora_lados_sem_ml_nem_custo() -> None:
    linha = _linha(coresp_orla_0_4="ORLA_FINA", ml_orla_fina=Decimal("0"),
                   custo_orla_fina=Decimal("0"), esp_real=Decimal("19"))
    assert agregar_orlas([linha]) == []


# --- Ferragens ---------------------------------------------------------------


def test_ferragens_und_e_ml() -> None:
    und = _linha(
        tipo_linha="FERRAGEM", unidade="UND", item_qt=Decimal("3"),
        quantidade=Decimal("4"), custo_ferragem=Decimal("2"),
        preco_liquido=Decimal("1.2"), ref_le="FER01",
        descricao_no_orcamento="Dobradiça",
    )
    ml = _linha(
        tipo_linha="FERRAGEM", unidade="ML", item_qt=Decimal("2"),
        quantidade=Decimal("1"), consumo_ml_total=Decimal("5"),
        custo_ferragem=Decimal("3"), ref_le="FER02",
        descricao_no_orcamento="Calha",
    )
    ferragens = agregar_ferragens([und, ml])
    por_ref = {f.ref_le: f for f in ferragens}

    assert por_ref["FER01"].qt_total == Decimal("12")   # 4 x 3
    assert por_ref["FER01"].ml == Decimal("0")
    assert por_ref["FER01"].custo_total == Decimal("6")  # 2 x 3

    assert por_ref["FER02"].qt_total == Decimal("2")    # 1 x 2
    assert por_ref["FER02"].ml == Decimal("10")         # 5 x 2 (ML)
    assert por_ref["FER02"].custo_total == Decimal("6")  # 3 x 2


def test_ferragens_ignora_pecas_m2() -> None:
    placa = _linha(tipo_linha="PECA", unidade="m2", custo_ferragem=Decimal("9"))
    assert agregar_ferragens([placa]) == []


def test_ferragem_da_biblioteca_conta_mesmo_sendo_tipo_peca() -> None:
    # A dobradiça added from the piece LIBRARY is stored as tipo_linha=PECA, UND
    # (not FERRAGEM). It must still be counted as a ferragem, by unit + material.
    dobradica = _linha(
        tipo_linha="PECA", unidade="UND", item_qt=Decimal("1"),
        quantidade=Decimal("4"), custo_ferragem=Decimal("5"),
        preco_liquido=Decimal("1.25"), ref_le="FER0015",
        descricao_no_orcamento="Dobradiça Blum",
    )
    (ferragem,) = agregar_ferragens([dobradica])

    assert ferragem.ref_le == "FER0015"
    assert ferragem.qt_total == Decimal("4")
    assert ferragem.custo_total == Decimal("5")


def test_ferragens_sem_dupla_contagem_placa_und_e_servico() -> None:
    placa = _linha(
        tipo_linha="PECA", unidade="m2", quantidade=Decimal("1"),
        area_m2=Decimal("1"), comp_mp=Decimal("2000"), larg_mp=Decimal("1000"),
        preco_liquido=Decimal("5"), ref_le="LE01", descricao_no_orcamento="AGL",
    )
    ferragem = _linha(
        tipo_linha="PECA", unidade="UND", quantidade=Decimal("2"),
        custo_ferragem=Decimal("3"), ref_le="FER01",
        descricao_no_orcamento="Pé nivelador",
    )
    # Service piece: UND but NO material (no ref_le, no cost) -> not a ferragem.
    servico = _linha(
        tipo_linha="PECA", unidade="UND", quantidade=Decimal("1"),
        descricao_no_orcamento="Montagem",
    )

    linhas = [placa, ferragem, servico]

    # The board only counts in placas; the UND material only in ferragens.
    (placa_resumo,) = agregar_placas(linhas)
    assert placa_resumo.ref_le == "LE01"
    (ferragem_resumo,) = agregar_ferragens(linhas)
    assert ferragem_resumo.ref_le == "FER01"
    assert ferragem_resumo.qt_total == Decimal("2")


# --- Máquinas / MO -----------------------------------------------------------


def test_maquinas_soma_por_centro() -> None:
    corte = _linha(
        custo_corte=Decimal("4"), custo_producao=Decimal("4"),
        perimetro_ml=Decimal("3"), quantidade=Decimal("2"), item_qt=Decimal("2"),
    )
    orlagem = _linha(
        custo_orlagem=Decimal("5"), custo_producao=Decimal("5"),
        ml_orla_fina=Decimal("1"), ml_orla_grossa=Decimal("0.5"),
        quantidade=Decimal("1"), item_qt=Decimal("2"),
    )
    cnc = _linha(custo_cnc=Decimal("7"), quantidade=Decimal("1"), item_qt=Decimal("1"))
    montagem = _linha(
        custo_montagem_manual=Decimal("9"), quantidade=Decimal("1"),
        item_qt=Decimal("1"),
    )
    por_centro = {m.centro: m for m in agregar_maquinas([corte, orlagem, cnc, montagem])}

    sec = por_centro["Seccionadora (Corte)"]
    assert sec.custo_total == Decimal("8")    # 4 x 2
    assert sec.ml_corte == Decimal("12")      # 3 x 2 x 2
    assert sec.num_pecas == Decimal("4")      # 2 x 2

    orl = por_centro["Orladora (Orlagem)"]
    assert orl.custo_total == Decimal("10")   # 5 x 2
    assert orl.ml_orlado == Decimal("3.0")    # (1 + 0.5) x 2

    assert por_centro["CNC (Mecanizações)"].custo_total == Decimal("7")
    assert por_centro["Montagem / Manual"].custo_total == Decimal("9")


def test_operacoes_detalhadas_separam_cnc_e_aplicam_quantidade_item() -> None:
    cavilha = _linha(
        operacoes="CNC_ABD", maquina="CNC_ABD", quantidade=Decimal("10"),
        item_qt=Decimal("2"), tempo_setup=Decimal("0.01"),
        tempo_cnc=Decimal("0.10"), custo_producao=Decimal("0.055"),
    )
    parafuso = _linha(
        operacoes="CNC_VERTICAL", maquina="CNC_VERTICAL", quantidade=Decimal("10"),
        tempo_setup=Decimal("0.01"), tempo_cnc=Decimal("0.10"),
        custo_producao=Decimal("0.11"),
    )

    por_operacao = {o.operacoes: o for o in agregar_operacoes([cavilha, parafuso])}

    assert por_operacao["CNC_ABD"].maquina == "CNC_ABD"
    assert por_operacao["CNC_ABD"].qt_total == Decimal("20")
    assert por_operacao["CNC_ABD"].tempo_setup == Decimal("0.02")
    assert por_operacao["CNC_ABD"].tempo_cnc == Decimal("0.20")
    assert por_operacao["CNC_ABD"].custo_total == Decimal("0.110")
    assert por_operacao["CNC_VERTICAL"].qt_total == Decimal("10")


# --- Consumo conta com Excluir; distribuição respeita Excluir ----------------


def test_consumo_conta_mesmo_com_excluir() -> None:
    linha = _linha(
        unidade="m2", quantidade=Decimal("1"), area_m2=Decimal("1"),
        comp_mp=Decimal("2000"), larg_mp=Decimal("1000"),
        preco_liquido=Decimal("5"), custo_mp=Decimal("10"),
        ref_le="LE01", descricao_no_orcamento="AGL", excluir_mp=True,
    )
    # The physical consumption (m2, theoretical cost) still counts.
    (placa,) = agregar_placas([linha])
    assert placa.m2_total_pecas == Decimal("1")
    assert placa.custo_mp_total == Decimal("5")  # m2 consumidos(1) x pliq(5)


def test_distribuicao_respeita_excluir() -> None:
    incluida = _linha(custo_mp=Decimal("10"), custo_orlas=Decimal("4"),
                      custo_ferragem=Decimal("6"), custo_producao=Decimal("8"),
                      custo_acabamento=Decimal("2"))
    excluida = _linha(custo_mp=Decimal("5"), excluir_mp=True)

    dist = distribuicao_custos([incluida, excluida], MargensOrcamento())
    por_nome = {c.nome: c.euros for c in dist.categorias}

    assert por_nome["Placas"] == Decimal("10")   # the excluded 5 does NOT count
    assert por_nome["Orlas"] == Decimal("4")
    assert por_nome["Ferragens"] == Decimal("6")
    assert por_nome["Máquinas / MO"] == Decimal("8")
    assert por_nome["Acabamentos"] == Decimal("2")
    assert dist.custo_produzido == Decimal("30")
    # No margins -> sell == produced cost, margins slice == 0.
    assert dist.total_venda == Decimal("30")
    assert dist.margens_euros == Decimal("0")


def test_distribuicao_aplica_margens_e_percentagens() -> None:
    linha = _linha(custo_mp=Decimal("100"))
    margens = MargensOrcamento(margem_lucro_pct=Decimal("10"))

    dist = distribuicao_custos([linha], margens)

    assert dist.custo_produzido == Decimal("100")
    assert dist.total_venda == Decimal("110")     # 100 x (1 + 10%)
    assert dist.margens_euros == Decimal("10")
    por_nome = {c.nome: c.pct for c in dist.categorias}
    # Percentages are relative to the sell total.
    assert por_nome["Placas"].quantize(Decimal("0.01")) == Decimal("90.91")
    assert por_nome["Margens"].quantize(Decimal("0.01")) == Decimal("9.09")


# --- Tipos ignorados ---------------------------------------------------------


def test_separador_divisao_composta_sao_ignorados() -> None:
    comum = dict(unidade="m2", quantidade=Decimal("1"), area_m2=Decimal("1"),
                 comp_mp=Decimal("2000"), larg_mp=Decimal("1000"),
                 custo_mp=Decimal("9"), custo_producao=Decimal("9"),
                 custo_corte=Decimal("9"))
    linhas = [
        _linha(tipo_linha="SEPARADOR", **comum),
        _linha(tipo_linha="DIVISAO_INDEPENDENTE", **comum),
        _linha(tipo_linha="PECA_COMPOSTA", **comum),
    ]
    assert agregar_placas(linhas) == []
    assert agregar_maquinas(linhas) == [
        m for m in agregar_maquinas(linhas) if m.custo_total == Decimal("0")
    ]
    dist = distribuicao_custos(linhas, MargensOrcamento())
    assert dist.custo_produzido == Decimal("0")
