"""Testes para a modelação (pura) dos gráficos de barras dos relatórios (8W.3a)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.consumos import (
    ConsumoFerragem,
    ConsumoMaquina,
    ConsumoOrla,
    ConsumoPlaca,
    DistribuicaoCategoria,
    DistribuicaoCustos,
)
from app.domain.relatorio_graficos import (
    FatiaPizza,
    GraficoBarras,
    GraficoPizza,
    dados_distribuicao,
    dados_ferragens,
    dados_maquinas,
    dados_orlas,
    dados_placas,
)


def _placa(*, ref_le="LE01", descricao="AGL", custo_mp_total=Decimal("15"),
           custo_no_orcamento=Decimal("15")) -> ConsumoPlaca:
    return ConsumoPlaca(
        ref_le=ref_le, descricao_no_orcamento=descricao, esp_mp=Decimal("19"),
        pliq=Decimal("5"), unidade="m2", desp=Decimal("0"),
        comp_mp=Decimal("2750"), larg_mp=Decimal("1830"), area_placa=Decimal("5"),
        m2_total_pecas=Decimal("3"), m2_consumidos=Decimal("3"), qt_placas=1,
        custo_mp_total=custo_mp_total, custo_placa_inteira=Decimal("25"),
        nao_stock=False, custo_no_orcamento=custo_no_orcamento,
        agravamento=Decimal("0"),
    )


def _orla(*, ref_orla="ORLA_FINA", ml_total=Decimal("4")) -> ConsumoOrla:
    return ConsumoOrla(
        ref_orla=ref_orla, descricao="AGL", espessura=Decimal("0.4"),
        largura=Decimal("22"), ml_total=ml_total, custo_total=Decimal("3"),
    )


def _ferragem(*, ref_le="FER01", descricao="Dobradiça",
              custo_total=Decimal("6")) -> ConsumoFerragem:
    return ConsumoFerragem(
        ref_le=ref_le, descricao_no_orcamento=descricao, pliq=Decimal("1.2"),
        unidade="UND", desp=Decimal("0"), qt_total=Decimal("4"), ml=Decimal("0"),
        custo_total=custo_total,
    )


def _maquina(centro, custo_total) -> ConsumoMaquina:
    return ConsumoMaquina(
        centro=centro, custo_total=custo_total, ml_corte=Decimal("0"),
        ml_orlado=Decimal("0"), num_pecas=Decimal("0"),
    )


# --- Placas (duas séries) ----------------------------------------------------


def test_dados_placas_duas_series() -> None:
    grafico = dados_placas([
        _placa(ref_le="LE01", custo_mp_total=Decimal("15"),
               custo_no_orcamento=Decimal("25")),
        _placa(ref_le="LE02", custo_mp_total=Decimal("8"),
               custo_no_orcamento=Decimal("8")),
    ])

    assert grafico.titulo == "Placas — custo"
    assert grafico.unidade == "€"
    assert grafico.etiquetas == ["LE01", "LE02"]
    assert [s.nome for s in grafico.series] == ["Teórico (% desp.)", "No orçamento"]
    assert grafico.series[0].valores == [Decimal("15"), Decimal("8")]
    assert grafico.series[1].valores == [Decimal("25"), Decimal("8")]


def test_dados_placas_etiqueta_descricao_truncada_quando_sem_ref() -> None:
    grafico = dados_placas([_placa(ref_le="", descricao="Aglomerado Melamina Branca")])

    etiqueta = grafico.etiquetas[0]
    assert etiqueta.endswith("…")
    assert len(etiqueta) == 18


# --- Orlas -------------------------------------------------------------------


def test_dados_orlas_uma_serie_ml() -> None:
    grafico = dados_orlas([
        _orla(ref_orla="ORLA_FINA", ml_total=Decimal("4")),
        _orla(ref_orla="ORLA_GROSSA", ml_total=Decimal("2")),
    ])

    assert grafico.unidade == "ml"
    assert grafico.etiquetas == ["ORLA_FINA", "ORLA_GROSSA"]
    assert len(grafico.series) == 1
    assert grafico.series[0].nome == "ML"
    assert grafico.series[0].valores == [Decimal("4"), Decimal("2")]


# --- Ferragens ---------------------------------------------------------------


def test_dados_ferragens_uma_serie_custo() -> None:
    grafico = dados_ferragens([
        _ferragem(ref_le="FER01", custo_total=Decimal("6")),
        _ferragem(ref_le="", descricao="Pé nivelador", custo_total=Decimal("9")),
    ])

    assert grafico.unidade == "€"
    # Segunda ferragem sem ref -> etiqueta pela descrição.
    assert grafico.etiquetas == ["FER01", "Pé nivelador"]
    assert len(grafico.series) == 1
    assert grafico.series[0].nome == "Custo"
    assert grafico.series[0].valores == [Decimal("6"), Decimal("9")]


# --- Máquinas (filtra custo 0) -----------------------------------------------


def test_dados_maquinas_inclui_so_com_custo() -> None:
    grafico = dados_maquinas([
        _maquina("Seccionadora (Corte)", Decimal("8")),
        _maquina("Orladora (Orlagem)", Decimal("0")),   # filtrada
        _maquina("CNC (Mecanizações)", Decimal("7")),
        _maquina("Montagem / Manual", Decimal("0")),     # filtrada
    ])

    assert grafico.unidade == "€"
    assert grafico.etiquetas == ["Seccionadora (Corte)", "CNC (Mecanizações)"]
    assert grafico.series[0].valores == [Decimal("8"), Decimal("7")]


# --- Listas vazias -> gráfico vazio ------------------------------------------


def test_listas_vazias_devolvem_grafico_vazio() -> None:
    for grafico in (
        dados_placas([]),
        dados_orlas([]),
        dados_ferragens([]),
        dados_maquinas([]),
    ):
        assert isinstance(grafico, GraficoBarras)
        assert grafico.etiquetas == []
        assert grafico.series == []
        assert grafico.titulo  # mantém um título não vazio


def test_dados_maquinas_todas_zero_devolve_vazio() -> None:
    grafico = dados_maquinas([
        _maquina("Seccionadora (Corte)", Decimal("0")),
        _maquina("CNC (Mecanizações)", Decimal("0")),
    ])

    assert grafico.etiquetas == []
    assert grafico.series == []


# --- Distribuição (pizza: filtra <= 0, mantém ordem, leva total_venda) --------


def test_dados_distribuicao_filtra_nao_positivos_e_mantem_ordem() -> None:
    distribuicao = DistribuicaoCustos(
        categorias=[
            DistribuicaoCategoria("Placas", Decimal("40"), Decimal("40")),
            DistribuicaoCategoria("Orlas", Decimal("0"), Decimal("0")),       # filtrada
            DistribuicaoCategoria("Ferragens", Decimal("10"), Decimal("10")),
            DistribuicaoCategoria("Margens", Decimal("-5"), Decimal("-5")),   # filtrada
            DistribuicaoCategoria("Acabamentos", Decimal("25"), Decimal("25")),
        ],
        custo_produzido=Decimal("75"),
        margens_euros=Decimal("-5"),
        total_venda=Decimal("100"),
    )

    grafico = dados_distribuicao(distribuicao)

    assert isinstance(grafico, GraficoPizza)
    assert grafico.titulo == "Distribuição de custos"
    # Mantém a ordem e ignora as categorias com euros <= 0.
    assert [f.nome for f in grafico.fatias] == ["Placas", "Ferragens", "Acabamentos"]
    assert all(isinstance(f, FatiaPizza) for f in grafico.fatias)
    assert [f.euros for f in grafico.fatias] == [
        Decimal("40"), Decimal("10"), Decimal("25"),
    ]
    assert [f.pct for f in grafico.fatias] == [
        Decimal("40"), Decimal("10"), Decimal("25"),
    ]
    # O total de venda é levado tal e qual para o gráfico.
    assert grafico.total_venda == Decimal("100")


def test_dados_distribuicao_sem_categorias_positivas_devolve_pizza_vazia() -> None:
    distribuicao = DistribuicaoCustos(
        categorias=[
            DistribuicaoCategoria("Margens", Decimal("0"), Decimal("0")),
            DistribuicaoCategoria("Placas", Decimal("-3"), Decimal("-3")),
        ],
        total_venda=Decimal("0"),
    )

    grafico = dados_distribuicao(distribuicao)

    assert grafico.fatias == []
    assert grafico.total_venda == Decimal("0")
