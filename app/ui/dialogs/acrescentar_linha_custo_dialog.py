"""Acrescentar à mão uma linha ao custo da obra, a partir das Matérias-Primas do V3.

Pedido do Paulo (25-09-2026): a obra gasta muitas vezes mais ferragens do que
as que vêm do IMOS. A linha nova entra no custo desta obra com a quantidade e o
preço escritos aqui; o preço vem do V3 e pode ser mudado.
"""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from app.services import analise_custo_mapeamento_service as maps
from app.services import analise_lista_material_service as svc
from app.ui.dialogs.associar_custo_materia_prima_dialog import filtrar_materias_primas
from app.ui.widgets.combo_sem_scroll import ComboSemScroll, SpinDuploSemScroll

# Categoria no custo → família das matérias-primas que se mostram primeiro.
_FAMILIA = {'Placas': 'Placas', 'Orlas': 'Orlas'}


class AcrescentarLinhaCustoDialog(QDialog):
    def __init__(self, catalog, *, categoria='Ferragens', utilizador='', parent=None):
        super().__init__(parent)
        self.catalog = catalog
        self.utilizador = utilizador
        self.filtered = []
        self.line = None
        self.price = None
        self.setWindowTitle('Acrescentar linha ao custo da obra')
        self.resize(1100, 680)
        layout = QVBoxLayout(self)
        intro = QLabel('Escolha a matéria-prima do V3, a quantidade e o preço. A linha entra só no custo desta '
                       'obra (fica guardada na análise) e pode ser alterada ou eliminada depois.')
        intro.setWordWrap(True)
        layout.addWidget(intro)

        filtros = QHBoxLayout()
        self.categoria = ComboSemScroll()
        self.categoria.addItems(svc.CATEGORIAS_MATERIAIS)
        self.categoria.setCurrentText(categoria if categoria in svc.CATEGORIAS_MATERIAIS else 'Ferragens')
        self.categoria.setToolTip('Em que categoria do custo entra a linha (Placas, Orlas, Ferragens, Comprados, SPP).')
        self.familia = ComboSemScroll()
        self.familia.addItems(['Todas', 'Placas', 'Orlas', 'Ferragens', 'Outros'])
        self.familia.setToolTip('Família das Matérias-Primas mostradas. Pode mudar para Todas.')
        self.search = QLineEdit()
        self.search.setPlaceholderText('Pesquisar Ref_LE, Ref PHC, descrição, fornecedor ou nome IMOS…')
        self.search.setToolTip('Escreva uma ou mais palavras; pesquisa em qualquer posição.')
        self.search.setClearButtonEnabled(True)
        filtros.addWidget(QLabel('Categoria no custo:'))
        filtros.addWidget(self.categoria)
        filtros.addWidget(self.familia)
        filtros.addWidget(self.search, 1)
        layout.addLayout(filtros)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Ref_LE', 'Descrição', 'Família', 'Esp.', 'Un.', 'Preço líquido'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setToolTip('Clique na matéria-prima; o preço líquido do V3 passa para baixo.')
        for col, width in enumerate((110, 520, 100, 60, 60, 110)):
            self.table.setColumnWidth(col, width)
        layout.addWidget(self.table, 1)

        form = QFormLayout()
        self.escolhida = QLabel('—')
        self.escolhida.setWordWrap(True)
        self.quantidade = SpinDuploSemScroll()
        self.quantidade.setRange(0, 10_000_000)
        self.quantidade.setDecimals(3)
        self.quantidade.setToolTip('Quantidade gasta na obra, na unidade da matéria-prima.')
        self.preco = SpinDuploSemScroll()
        self.preco.setRange(0, 10_000_000)
        self.preco.setDecimals(5)
        self.preco.setToolTip('Preço líquido por unidade. Vem do V3; se o mudar, vale só para esta obra.')
        form.addRow('Matéria-prima:', self.escolhida)
        form.addRow('Quantidade:', self.quantidade)
        form.addRow('Preço líquido:', self.preco)
        layout.addLayout(form)

        botoes = QHBoxLayout()
        ok = QPushButton('Acrescentar ao custo')
        ok.setToolTip('Juntar a linha ao custo desta obra. Guarde a análise para a fixar.')
        ok.clicked.connect(self._accept)
        cancelar = QPushButton('Cancelar')
        cancelar.setToolTip('Fechar sem acrescentar nada.')
        cancelar.clicked.connect(self.reject)
        botoes.addStretch()
        botoes.addWidget(ok)
        botoes.addWidget(cancelar)
        layout.addLayout(botoes)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.categoria.currentTextChanged.connect(self._categoria_mudou)
        self.familia.currentIndexChanged.connect(self._filter)
        self.search.textChanged.connect(self._filter)
        self.table.currentCellChanged.connect(lambda *_: self._escolher())
        self.table.cellDoubleClicked.connect(lambda *_: self.quantidade.setFocus())
        self._categoria_mudou(self.categoria.currentText())

    def _categoria_mudou(self, categoria):
        self.familia.setCurrentText(_FAMILIA.get(categoria, 'Ferragens'))
        self._filter()

    def _filter(self, *_):
        self.filtered = filtrar_materias_primas(self.catalog, self.familia.currentText(), self.search.text())
        self.table.setRowCount(len(self.filtered))
        for row, mp in enumerate(self.filtered):
            for col, value in enumerate((mp.ref_le or mp.ref_phc or '', mp.descricao, maps.category(mp),
                                         getattr(mp, 'espessura', None) or '', mp.unidade or '',
                                         mp.preco_liquido if mp.preco_liquido is not None else 'Por apurar')):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.table.setItem(row, col, item)
        self.status.setText(f'{len(self.filtered)} matérias-primas.')

    def _atual(self):
        row = self.table.currentRow()
        return self.filtered[row] if 0 <= row < len(self.filtered) else None

    def _escolher(self):
        mp = self._atual()
        if mp is None:
            return
        unidade = svc.unit(mp.unidade) or 'un'
        self.escolhida.setText(f'{mp.ref_le or mp.ref_phc or ""} — {mp.descricao}')
        self.quantidade.setSuffix(f' {unidade}')
        self.preco.setSuffix(f' € / {unidade}')
        self.preco.setValue(float(svc.number(mp.preco_liquido) or 0))

    def _accept(self):
        mp = self._atual()
        if mp is None:
            self.status.setText('Selecione a matéria-prima na tabela.')
            return
        if self.quantidade.value() <= 0:
            self.status.setText('Escreva a quantidade gasta na obra.')
            self.quantidade.setFocus()
            return
        quantidade = Decimal(str(round(self.quantidade.value(), 3)))
        preco = Decimal(str(round(self.preco.value(), 5)))
        self.line, self.price = svc.linha_manual(self.categoria.currentText(), mp, quantidade, preco,
                                                 utilizador=self.utilizador)
        self.accept()
