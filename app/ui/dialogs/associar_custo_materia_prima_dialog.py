"""Seleção pesquisável de matéria-prima para o custo da obra."""
import unicodedata
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView)
from app.services import analise_custo_mapeamento_service as maps
from app.ui.widgets.combo_sem_scroll import ComboSemScroll


class AssociarCustoMateriaPrimaDialog(QDialog):
    def __init__(self, line, catalog, references=(), parent=None):
        super().__init__(parent)
        self.catalog = catalog
        self.selected = None
        self.setWindowTitle('Associar matéria-prima V3')
        self.resize(1150, 650)
        layout = QVBoxLayout(self)
        title = QLabel(f"{line['kind']} — {line['name']}\nJogo de uniões: {line.get('union_set') or '—'}\n"
                       f"Comp: {line.get('length') or '—'} | Larg: {line.get('width') or '—'} | Esp: {line.get('thickness') or '—'} mm")
        title.setWordWrap(True)
        layout.addWidget(title)
        recommended, reason = maps.egger_candidates(line, catalog, references)
        self.recommended_ids = {mp.id for mp in recommended}
        hint = QLabel(reason or 'A associação fica disponível para próximas obras. Os preços antigos mantêm-se nas análises guardadas.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        filters = QHBoxLayout()
        self.family = ComboSemScroll()
        self.family.addItems(['Todas', 'Placas', 'Orlas', 'Ferragens', 'Outros'])
        self.family.setCurrentText(line['kind'] if line['kind'] in ('Placas','Orlas') else 'Ferragens')
        self.family.setToolTip('Pré-filtro pela categoria. Pode mudar para Todas.')
        self.search = QLineEdit()
        self.search.setPlaceholderText('Pesquisar Ref_LE, descrição, fornecedor, nome IMOS ou grupo EGGER…')
        self.search.setToolTip('Escreva uma ou mais palavras; pesquisa em qualquer posição.')
        self.search.setClearButtonEnabled(True)
        filters.addWidget(self.family)
        filters.addWidget(self.search, 1)
        layout.addLayout(filters)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(['Ref_LE', 'Descrição', 'Categoria', 'Esp.', 'Un.', 'Preço líquido', 'Correspondência'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        for col, width in enumerate((100,470,100,65,60,110,190)):
            self.table.setColumnWidth(col,width)
        layout.addWidget(self.table,1)
        buttons = QHBoxLayout()
        apply = QPushButton('Associar e memorizar no V3')
        apply.setToolTip('Guardar esta correspondência de custo para obras futuras; não altera códigos Woodstore.')
        apply.clicked.connect(self._choose)
        cancel = QPushButton('Cancelar')
        cancel.setToolTip('Fechar sem alterar a associação.')
        cancel.clicked.connect(self.reject)
        buttons.addWidget(apply)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.search.textChanged.connect(self._filter)
        self.family.currentIndexChanged.connect(self._filter)
        self.table.cellDoubleClicked.connect(lambda *_: self._choose())
        self._filter()

    def _filter(self, *_):
        def norm(text):
            return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))
        terms = norm(self.search.text()).split()
        family = self.family.currentText()
        self.filtered = [mp for mp in self.catalog if (family == 'Todas' or maps.category(mp) == family)
            and all(term in norm(' '.join(str(getattr(mp, f, '') or '') for f in
                ('ref_le','ref_phc','descricao','fornecedor','referencia_fornecedor','nome_imos'))) for term in terms)]
        self.filtered.sort(key=lambda mp: (mp.id not in self.recommended_ids, mp.ref_le or '', mp.descricao))
        self.table.setRowCount(len(self.filtered))
        self.table.clearSelection()
        self.table.setCurrentCell(-1,-1)
        for row, mp in enumerate(self.filtered):
            for col, value in enumerate((mp.ref_le or mp.ref_phc or '', mp.descricao, maps.category(mp),
                    getattr(mp,'espessura',None) or '', mp.unidade or '', mp.preco_liquido if mp.preco_liquido is not None else 'Por apurar',
                    'Grupo EGGER compatível' if mp.id in self.recommended_ids else '')):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.table.setItem(row,col,item)
        self.status.setText(f'{len(self.filtered)} matérias-primas. Selecione a referência correta e confirme a unidade e a espessura.')

    def _choose(self):
        row = self.table.currentRow()
        if row < 0:
            self.status.setText('Selecione uma matéria-prima na tabela.')
            return
        self.selected = self.filtered[row]
        self.accept()
