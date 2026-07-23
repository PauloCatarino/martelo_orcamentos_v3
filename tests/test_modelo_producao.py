"""Tests for the production table model and its filter/sort proxy."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.models.producao import Producao
from app.ui import tema
from app.ui.helpers.colunas_producao import COLUNAS_PRODUCAO
from app.ui.helpers.modelo_producao import ProducaoFilterProxy, ProducaoTableModel


@pytest.fixture(scope="module", autouse=True)
def _app():
    yield QApplication.instance() or QApplication([])


def _coluna(key: str) -> int:
    return next(i for i, c in enumerate(COLUNAS_PRODUCAO) if c.key == key)


def _obra(**kwargs) -> Producao:
    valores = {
        "id": kwargs.pop("id", 1),
        "codigo_processo": "26.1000_01_01_X",
        "ano": "2026",
        "num_enc_phc": "1000",
        "versao_obra": "01",
        "versao_plano": "01",
        "estado": "Desenho",
        "responsavel": "Paulo",
        "nome_cliente": "CLIENTE A",
    }
    valores.update(kwargs)
    processo = Producao()
    for campo, valor in valores.items():
        setattr(processo, campo, valor)
    return processo


@pytest.fixture()
def modelo():
    modelo = ProducaoTableModel()
    modelo.definir_processos(
        [
            _obra(
                id=1,
                codigo_processo="26.1001_01_01_A",
                created_at=datetime(2026, 6, 1, 9, 0),
                data_entrega="30-09-2026",
                preco_total=Decimal("100.00"),
            ),
            _obra(
                id=2,
                codigo_processo="26.1002_01_01_B",
                created_at=datetime(2026, 6, 3, 9, 0),
                data_entrega="01-01-2020",
                estado="Arquivado",
                preco_total=Decimal("2000.00"),
            ),
            _obra(
                id=3,
                codigo_processo="26.1003_01_01_C",
                created_at=datetime(2026, 6, 2, 9, 0),
                data_entrega="",
                responsavel="Ana",
                nome_cliente="CLIENTE B",
                preco_total=None,
            ),
        ]
    )
    return modelo


def test_dimensoes_e_cabecalhos(modelo) -> None:
    assert modelo.rowCount() == 3
    assert modelo.columnCount() == len(COLUNAS_PRODUCAO)
    assert modelo.headerData(
        _coluna("processo"), Qt.Orientation.Horizontal
    ) == "Processo"


def test_ordem_de_entrada_usa_created_at_e_id(modelo) -> None:
    col = _coluna("criada_em")
    chaves = [
        modelo.index(row, col).data(ProducaoTableModel.ROLE_ORDENACAO)
        for row in range(3)
    ]

    assert chaves[0] == (datetime(2026, 6, 1, 9, 0), 1)
    assert chaves[1] > chaves[2] > chaves[0]  # 03-06 > 02-06 > 01-06


def test_datas_e_precos_ordenam_por_valor_nao_por_texto(modelo) -> None:
    col_entrega = _coluna("data_entrega")
    chave_2026 = modelo.index(0, col_entrega).data(ProducaoTableModel.ROLE_ORDENACAO)
    chave_2020 = modelo.index(1, col_entrega).data(ProducaoTableModel.ROLE_ORDENACAO)
    assert chave_2020 < chave_2026

    col_preco = _coluna("preco")
    chave_100 = modelo.index(0, col_preco).data(ProducaoTableModel.ROLE_ORDENACAO)
    chave_2000 = modelo.index(1, col_preco).data(ProducaoTableModel.ROLE_ORDENACAO)
    assert chave_100 < chave_2000  # texto daria "100" > "2 000,00 €"


def test_semaforo_pinta_entrega_em_atraso_mas_nao_obra_arquivada(modelo) -> None:
    col = _coluna("data_entrega")

    # linha 1 = obra arquivada com entrega de 2020: sem alarme.
    assert modelo.index(1, col).data(Qt.ItemDataRole.BackgroundRole) is None

    modelo.definir_processos(
        [_obra(id=9, data_entrega="01-01-2020", estado="Producao")]
    )
    fundo = modelo.index(0, col).data(Qt.ItemDataRole.BackgroundRole)
    assert fundo is not None
    assert fundo.name().upper() == tema.VERMELHO_SUAVE.upper()


def test_proxy_filtra_por_responsavel_e_texto(modelo) -> None:
    proxy = ProducaoFilterProxy()
    proxy.setSourceModel(modelo)
    assert proxy.rowCount() == 3

    proxy.definir_filtros(responsavel="Ana")
    assert proxy.rowCount() == 1

    proxy.definir_filtros(texto="1002")
    assert proxy.rowCount() == 1

    proxy.definir_filtros()
    assert proxy.rowCount() == 3


def test_proxy_so_atrasadas_ignora_obras_fechadas(modelo) -> None:
    proxy = ProducaoFilterProxy()
    proxy.setSourceModel(modelo)

    proxy.definir_filtros(so_atrasadas=True)

    # A única entrega passada é de uma obra Arquivada, logo não conta.
    assert proxy.rowCount() == 0


def test_proxy_ordena_por_coluna(modelo) -> None:
    proxy = ProducaoFilterProxy()
    proxy.setSourceModel(modelo)
    col = _coluna("preco")

    proxy.sort(col, Qt.SortOrder.DescendingOrder)
    topo = proxy.index(0, _coluna("processo")).data()

    assert topo == "26.1002_01_01_B"  # 2000,00 €
