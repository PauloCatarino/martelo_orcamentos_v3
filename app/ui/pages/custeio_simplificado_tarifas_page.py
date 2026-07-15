"""Technical editor for the four simplified-costing quantity tiers."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.custeio_simplificado import TarifaCusteioSimplificado
from app.domain.numeros import parse_decimal_humano
from app.services.custeio_simplificado_tarifas_service import CusteioSimplificadoTarifasService
from app.ui.widgets.barra_cabecalho import BarraCabecalho


class CusteioSimplificadoTarifasPage(QWidget):
    HEADERS = ("Escalão", "Corte €/peça", "PUR 4 lados", "LASER 4 lados", "Urgência €/peça", "Urgência fixa", "Sem Excel €/peça")

    def __init__(self, on_back=None) -> None:
        super().__init__()
        self.on_back = on_back
        layout = QVBoxLayout(self)
        layout.addWidget(BarraCabecalho("Tarifas Custeio Simplificado", ["PUR/LASER são preços para quatro lados; a peça paga a proporção dos lados orlados.", "O escalão ≥25 inclui exatamente 25 peças."]))
        self.table = QTableWidget(4, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        layout.addWidget(self.table)
        actions = QHBoxLayout()
        back = QPushButton("Voltar")
        back.clicked.connect(lambda: self.on_back() if self.on_back else None)
        save = QPushButton("Guardar tarifas")
        save.clicked.connect(self.guardar)
        actions.addWidget(back); actions.addStretch(); actions.addWidget(save)
        layout.addLayout(actions)
        self.status = QLabel(""); layout.addWidget(self.status)
        self.carregar()

    def carregar(self) -> None:
        with SessionLocal() as session:
            tarifas = CusteioSimplificadoTarifasService(session).obter()
        for row, tarifa in enumerate(tarifas):
            escalao = ("1–4", "5–14", "15–24", "≥25")[row]
            valores = (escalao, tarifa.corte_por_peca, tarifa.pur_4_lados, tarifa.laser_4_lados, tarifa.urgencia_por_peca, tarifa.urgencia_fixa, tarifa.sem_excel_por_peca)
            for col, valor in enumerate(valores):
                item = QTableWidgetItem("" if valor is None else str(valor))
                if col == 0:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

    def guardar(self) -> None:
        try:
            tarifas = []
            for row, minimo in enumerate((1, 5, 15, 25)):
                def valor(col, vazio=False):
                    texto = self.table.item(row, col).text().strip()
                    return None if vazio and not texto else parse_decimal_humano(texto)
                tarifas.append(TarifaCusteioSimplificado(minimo, valor(1), valor(2), valor(3), valor(4, True), valor(5, True), valor(6)))
            with SessionLocal() as session:
                CusteioSimplificadoTarifasService(session).guardar(tuple(tarifas))
            self.status.setText("Tarifas guardadas. Atualize os itens Simplificado para aplicar os novos valores.")
        except (SQLAlchemyError, ValueError, AttributeError):
            self.status.setText("Verifique os valores numéricos das tarifas.")
