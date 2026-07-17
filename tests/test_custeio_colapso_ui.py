"""Runtime test of the composite-collapse table methods (real QTableWidget)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage as P


@dataclass
class _Linha:
    id: int
    linha_pai_id: int | None
    tipo_linha: str
    custo_total: Decimal | None = None


class _FakePage:
    """Borrows the real collapse methods; holds only the state they touch."""

    TABLE_HEADERS = P.TABLE_HEADERS
    _aplicar_estado_compostas = P._aplicar_estado_compostas
    _aplicar_visibilidade_compostas = P._aplicar_visibilidade_compostas
    _definir_seta_composta = P._definir_seta_composta
    _anexar_resumo_composta = P._anexar_resumo_composta
    _texto_resumo_composta = P._texto_resumo_composta
    _marcar_ferragem_auto = P._marcar_ferragem_auto
    _toggle_composta = P._toggle_composta


def _montar():
    app = QApplication.instance() or QApplication([])
    linhas = [
        _Linha(1, None, "PECA_COMPOSTA"),
        _Linha(2, 1, "PECA", Decimal("10.00")),
        _Linha(3, 2, "FERRAGEM", Decimal("5.00")),   # neto -> ferragem auto
        _Linha(4, None, "PECA", Decimal("9.00")),    # peça solta
    ]
    headers = P.TABLE_HEADERS
    table = QTableWidget(len(linhas), len(headers))
    col_tipo = headers.index("Tipo linha")
    col_def = headers.index("Def. Peça")
    base_def = {1: "PORTA+DOB", 2: "PORTA_SIMPLES", 3: "DOBRADICA", 4: "LATERAL"}
    base_tipo = {1: "Peça composta", 2: "Peça", 3: "Ferragem", 4: "Peça"}
    for row, linha in enumerate(linhas):
        table.setItem(row, col_tipo, QTableWidgetItem(base_tipo[linha.id]))
        table.setItem(row, col_def, QTableWidgetItem(base_def[linha.id]))

    fake = _FakePage()
    fake.table = table
    fake._custeio_by_row = {row: linha for row, linha in enumerate(linhas)}
    fake._compostas_expandidas = set()
    fake._descendentes_composta = {}
    fake._carregando_tabela = False
    return app, fake, table, linhas, col_tipo, col_def


def test_colapsado_por_defeito_esconde_filhos_e_mostra_resumo():
    app, fake, table, linhas, col_tipo, col_def = _montar()
    fake._aplicar_estado_compostas(linhas)

    # Filhos (peça 2 e ferragem-neto 3) escondidos; composta e peça solta visíveis.
    assert table.isRowHidden(1) is True
    assert table.isRowHidden(2) is True
    assert table.isRowHidden(0) is False
    assert table.isRowHidden(3) is False

    # Seta fechada + resumo (1 peça · 1 ferragem) na composta.
    assert table.item(0, col_tipo).text().startswith("▶")
    resumo = table.item(0, col_def).text()
    assert "1 peça" in resumo and "1 ferragem" in resumo

    # Ferragem auto marcada.
    assert table.item(2, col_def).text().endswith("·auto")
    table.deleteLater()
    app.processEvents()


def test_toggle_expande_e_repoe_a_seta():
    app, fake, table, linhas, col_tipo, col_def = _montar()
    fake._aplicar_estado_compostas(linhas)

    fake._toggle_composta(1)
    assert table.isRowHidden(1) is False
    assert table.isRowHidden(2) is False
    assert table.item(0, col_tipo).text().startswith("▼")

    fake._toggle_composta(1)
    assert table.isRowHidden(1) is True
    assert table.item(0, col_tipo).text().startswith("▶")
    table.deleteLater()
    app.processEvents()
