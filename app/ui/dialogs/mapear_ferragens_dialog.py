"""Mapear as ferragens da obra, uma a uma (V3 → PHC → IMOS provisório).

O mapeamento das ferragens é o mais exigente (Paulo, 21-09-2026) e tem de ser
passo a passo. Para cada ferragem sem preço do V3 mostra o que se sabe dela
(nome IMOS, descrição, Ref PHC, referência e fornecedor, quantidade) e os
três preços possíveis, lado a lado. Associar ao V3 fica memorizado para as
próximas obras; PHC e IMOS valem só para esta obra.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from app.services import analise_lista_material_service as svc
from app.services import custo_ferragens_service as custo
from app.ui.dialogs.associar_custo_materia_prima_dialog import AssociarCustoMateriaPrimaDialog


def _eur(value) -> str:
    number = svc.number(value)
    if number is None:
        return "—"
    return f"{number:.4f}".rstrip("0").rstrip(".").replace(".", ",") + " €"


class MapearFerragensDialog(QDialog):
    def __init__(self, lines, prices, catalog, phc, references=(), *, on_v3, parent=None):
        super().__init__(parent)
        self.lines, self.prices, self.catalog = list(lines), prices, catalog
        self.phc, self.references, self.on_v3 = phc or {}, references, on_v3
        self.index = 0
        self.changed = 0
        self.setWindowTitle("Mapear ferragens passo a passo")
        self.resize(900, 460)
        layout = QVBoxLayout(self)
        self.progress = QLabel()
        self.progress.setStyleSheet("font-size: 15px; font-weight: 650;")
        layout.addWidget(self.progress)
        grid = QGridLayout()
        self.fields = {}
        for row, (key, label) in enumerate((
            ("name", "Nome IMOS"), ("description", "Descrição"), ("ref_phc", "Ref PHC"),
            ("supplier", "Fornecedor / ref."), ("qty", "Quantidade"), ("current", "Preço atual"),
        )):
            grid.addWidget(QLabel(f"<b>{label}:</b>"), row, 0)
            value = QLabel()
            value.setWordWrap(True)
            grid.addWidget(value, row, 1)
            self.fields[key] = value
        layout.addLayout(grid)

        options = QHBoxLayout()
        self.v3_button = QPushButton("1.º Associar à matéria-prima V3…")
        self.v3_button.setToolTip("Escolher a matéria-prima do V3. Fica memorizado para as próximas obras.")
        self.v3_button.clicked.connect(self._use_v3)
        self.phc_button = QPushButton()
        self.phc_button.setToolTip("Usar o preço do PHC só nesta obra (2.ª opção).")
        self.phc_button.clicked.connect(self._use_phc)
        self.imos_button = QPushButton()
        self.imos_button.setToolTip("Usar o preço do IMOS só nesta obra; fica marcado como provisório.")
        self.imos_button.clicked.connect(self._use_imos)
        self.skip_cost_button = QPushButton("Não contabilizar nesta obra")
        self.skip_cost_button.setToolTip(
            "Acessório só para representação no IMOS, ou fornecido pelo cliente: custo 0 nesta obra.")
        self.skip_cost_button.clicked.connect(lambda: self._set(custo.preco_excluido(self.line)))
        for button in (self.v3_button, self.phc_button, self.imos_button, self.skip_cost_button):
            options.addWidget(button)
        layout.addLayout(options)
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)

        nav = QHBoxLayout()
        self.back_button = QPushButton("◀ Anterior")
        self.back_button.setToolTip("Voltar à ferragem anterior.")
        self.back_button.clicked.connect(lambda: self._go(-1))
        skip = QPushButton("Saltar ▶")
        skip.setToolTip("Deixar esta ferragem como está e passar à seguinte.")
        skip.clicked.connect(lambda: self._go(1))
        close = QPushButton("Fechar")
        close.setToolTip("Terminar; o que já foi decidido fica na análise (guarde-a para fixar).")
        close.clicked.connect(self.accept)
        nav.addWidget(self.back_button)
        nav.addWidget(skip)
        nav.addStretch()
        nav.addWidget(close)
        layout.addLayout(nav)
        self._show()

    @property
    def line(self) -> dict:
        return self.lines[self.index]

    def _phc_price(self):
        return custo.preco_phc(self.line, self.phc.get(str(self.line.get("ref_phc") or "").strip().upper()))

    def _show(self):
        line = self.line
        price = self.prices.get(line["key"])
        self.progress.setText(f"{self.index + 1} de {len(self.lines)} — {line['kind']}")
        self.fields["name"].setText(
            (line.get("union_name") or line["name"])
            + (f"   [{line['source_sheet']}" + (f" · {line['articles']}" if line.get("articles") else "") + "]"
               if line.get("source_sheet") else ""))
        self.fields["description"].setText(line.get("description") or "—")
        self.fields["ref_phc"].setText(line.get("ref_phc") or "—")
        self.fields["supplier"].setText(" · ".join(x for x in (line.get("supplier"), line.get("supplier_ref")) if x) or "—")
        self.fields["qty"].setText(f"{line.get('quantity') or '—'} {line.get('unit') or ''}")
        self.fields["current"].setText(
            f"{_eur(price.get('net'))} — {price.get('mapping_source') or 'V3'}" if price else "sem preço")
        phc = self._phc_price()
        self.phc_button.setText(
            (f"2.º Usar PHC: {_eur(phc['net'])}" + (" — CONFIRMAR" if phc["confirmar"] else ""))
            if phc else "2.º PHC: sem preço")
        self.phc_button.setEnabled(bool(phc))
        imos = custo.preco_imos(line)
        self.imos_button.setText(f"3.º Usar IMOS (provisório): {_eur(imos['net'])}" if imos else "3.º IMOS: sem preço")
        self.imos_button.setEnabled(bool(imos))
        self.note.setText(phc.get("confirmar") if phc and phc.get("confirmar") else
                          (phc or {}).get("mapping_source", ""))
        self.back_button.setEnabled(self.index > 0)

    def _go(self, step: int):
        new = self.index + step
        if new >= len(self.lines):
            self.accept()
            return
        self.index = max(0, new)
        self._show()

    def _set(self, price):
        self.prices[self.line["key"]] = {**price, "escolha_manual": True}
        self.changed += 1
        self._go(1)

    def _use_v3(self):
        dialog = AssociarCustoMateriaPrimaDialog(self.line, self.catalog, self.references, self)
        hint = self.line.get("ref_phc") or (self.line.get("supplier_ref") or "").split(" ")[0]
        if hint:
            dialog.family.setCurrentText("Todas")
            dialog.search.setText(hint)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected:
            self.on_v3(self.line, dialog.selected)
            self._set({**svc.price_record(dialog.selected), "mapping_source": "Mapeamento manual guardado no V3"})

    def _use_phc(self):
        price = self._phc_price()
        if price:
            self._set(price)

    def _use_imos(self):
        price = custo.preco_imos(self.line)
        if price:
            self._set(price)
