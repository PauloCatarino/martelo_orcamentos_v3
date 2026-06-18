"""Gerador do Excel interno "Resumo de Custos" a partir do modelo (fase 8W.4.3).

Copia um ficheiro modelo ``.xlsx`` ja formatado e preenche apenas as folhas de
resumo agregadas. A funcao recebe dados simples (sem DB nem Qt) para ser
testavel.
"""

from __future__ import annotations

import shutil
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

_FMT_DIM = "0"
_FMT_INT = "0"
_FMT_QT = "0.##"
_FMT_M2 = "0.000"
_FMT_ML = "0.00"
_FMT_EUR = "#,##0.00 €"
_FMT_PCT = "0.0"


def _to_float(value) -> float | None:
    """Converte Decimal/numero para float (None se vazio/invalido)."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _escrever_numero(cell, value, number_format: str) -> None:
    """Escreve um numero real na celula com o formato dado."""
    numero = _to_float(value)
    if numero is not None:
        cell.value = numero
    cell.number_format = number_format


def _texto(value) -> str:
    return "" if value is None else str(value)


def _limpar_linhas_dados(ws) -> None:
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)


def _folha(wb, nome: str):
    if nome not in wb.sheetnames:
        return None
    ws = wb[nome]
    _limpar_linhas_dados(ws)
    return ws


def _preencher_placas(wb, placas) -> None:
    ws = _folha(wb, "Resumo Placas")
    if ws is None:
        return

    for linha, placa in enumerate(placas or [], start=2):
        ws.cell(row=linha, column=1, value=_texto(getattr(placa, "ref_le", None)))
        ws.cell(
            row=linha,
            column=2,
            value=_texto(getattr(placa, "descricao_no_orcamento", None)),
        )
        _escrever_numero(ws.cell(row=linha, column=3), getattr(placa, "pliq", None), _FMT_EUR)
        ws.cell(row=linha, column=4, value=_texto(getattr(placa, "unidade", None)))
        _escrever_numero(ws.cell(row=linha, column=5), getattr(placa, "desp", None), _FMT_PCT)
        _escrever_numero(ws.cell(row=linha, column=6), getattr(placa, "comp_mp", None), _FMT_DIM)
        _escrever_numero(ws.cell(row=linha, column=7), getattr(placa, "larg_mp", None), _FMT_DIM)
        _escrever_numero(ws.cell(row=linha, column=8), getattr(placa, "esp_mp", None), _FMT_DIM)
        _escrever_numero(ws.cell(row=linha, column=9), getattr(placa, "qt_placas", None), _FMT_INT)
        _escrever_numero(ws.cell(row=linha, column=10), getattr(placa, "area_placa", None), _FMT_M2)
        _escrever_numero(ws.cell(row=linha, column=11), getattr(placa, "m2_consumidos", None), _FMT_M2)
        _escrever_numero(ws.cell(row=linha, column=12), getattr(placa, "custo_mp_total", None), _FMT_EUR)
        _escrever_numero(
            ws.cell(row=linha, column=13),
            getattr(placa, "custo_placa_inteira", None),
            _FMT_EUR,
        )
        _escrever_numero(
            ws.cell(row=linha, column=14),
            1 if getattr(placa, "nao_stock", False) else 0,
            _FMT_INT,
        )


def _preencher_orlas(wb, orlas) -> None:
    ws = _folha(wb, "Resumo Orlas")
    if ws is None:
        return

    for linha, orla in enumerate(orlas or [], start=2):
        ws.cell(row=linha, column=1, value=_texto(getattr(orla, "ref_orla", None)))
        _escrever_numero(ws.cell(row=linha, column=2), getattr(orla, "espessura", None), _FMT_QT)
        _escrever_numero(ws.cell(row=linha, column=3), getattr(orla, "largura", None), _FMT_DIM)
        _escrever_numero(ws.cell(row=linha, column=4), getattr(orla, "ml_total", None), _FMT_ML)
        _escrever_numero(ws.cell(row=linha, column=5), getattr(orla, "custo_total", None), _FMT_EUR)


def _custo_unitario_ferragem(ferragem):
    qt_total = getattr(ferragem, "qt_total", None)
    if not qt_total:
        return 0
    return getattr(ferragem, "custo_total", 0) / qt_total


def _preencher_ferragens(wb, ferragens) -> None:
    ws = _folha(wb, "Resumo Ferragens")
    if ws is None:
        return

    for linha, ferragem in enumerate(ferragens or [], start=2):
        ws.cell(row=linha, column=1, value=_texto(getattr(ferragem, "ref_le", None)))
        ws.cell(
            row=linha,
            column=2,
            value=_texto(getattr(ferragem, "descricao_no_orcamento", None)),
        )
        _escrever_numero(ws.cell(row=linha, column=3), getattr(ferragem, "pliq", None), _FMT_EUR)
        ws.cell(row=linha, column=4, value=_texto(getattr(ferragem, "unidade", None)))
        _escrever_numero(ws.cell(row=linha, column=5), getattr(ferragem, "desp", None), _FMT_PCT)
        ws.cell(row=linha, column=6, value="")
        ws.cell(row=linha, column=7, value="")
        ws.cell(row=linha, column=8, value="")
        _escrever_numero(ws.cell(row=linha, column=9), getattr(ferragem, "qt_total", None), _FMT_QT)
        _escrever_numero(ws.cell(row=linha, column=10), getattr(ferragem, "ml", None), _FMT_ML)
        _escrever_numero(ws.cell(row=linha, column=11), _custo_unitario_ferragem(ferragem), _FMT_EUR)
        _escrever_numero(ws.cell(row=linha, column=12), getattr(ferragem, "custo_total", None), _FMT_EUR)


def _preencher_maquinas(wb, maquinas) -> None:
    ws = _folha(wb, "Resumo Maquinas_MO")
    if ws is None:
        return

    for linha, maquina in enumerate(maquinas or [], start=2):
        ws.cell(row=linha, column=1, value=_texto(getattr(maquina, "centro", None)))
        _escrever_numero(ws.cell(row=linha, column=2), getattr(maquina, "custo_total", None), _FMT_EUR)
        _escrever_numero(ws.cell(row=linha, column=3), getattr(maquina, "ml_corte", None), _FMT_ML)
        _escrever_numero(ws.cell(row=linha, column=4), getattr(maquina, "ml_orlado", None), _FMT_ML)
        _escrever_numero(ws.cell(row=linha, column=5), getattr(maquina, "num_pecas", None), _FMT_QT)


def _preencher_margens(wb, distribuicao) -> None:
    ws = _folha(wb, "Resumo Margens")
    if ws is None:
        return

    linha = 2
    for categoria in getattr(distribuicao, "categorias", None) or []:
        ws.cell(row=linha, column=1, value=_texto(getattr(categoria, "nome", None)))
        _escrever_numero(ws.cell(row=linha, column=2), getattr(categoria, "pct", None), _FMT_PCT)
        _escrever_numero(ws.cell(row=linha, column=3), getattr(categoria, "euros", None), _FMT_EUR)
        linha += 1

    ws.cell(row=linha, column=1, value="Total (Venda)")
    ws.cell(row=linha, column=2, value="")
    _escrever_numero(
        ws.cell(row=linha, column=3),
        getattr(distribuicao, "total_venda", None),
        _FMT_EUR,
    )


def gerar_excel_resumo_custos(output_path, template_path, *, resumo):
    """Copia o MODELO para ``output_path`` e preenche as folhas de resumo.

    Preserva o ficheiro modelo (incluindo cabecalhos e formatacao existentes),
    escreve dados a partir da linha 2 e devolve o ``Path`` de saida.
    """
    output_path = Path(output_path)
    template_path = Path(template_path)

    shutil.copyfile(template_path, output_path)
    workbook = load_workbook(output_path)

    _preencher_placas(workbook, getattr(resumo, "placas", None))
    _preencher_orlas(workbook, getattr(resumo, "orlas", None))
    _preencher_ferragens(workbook, getattr(resumo, "ferragens", None))
    _preencher_maquinas(workbook, getattr(resumo, "maquinas", None))
    _preencher_margens(workbook, getattr(resumo, "distribuicao", None))

    workbook.save(str(output_path))
    return output_path
