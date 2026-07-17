"""Technical editor for the four simplified-costing quantity tiers."""

from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.custeio_simplificado import TarifaCusteioSimplificado, TarifaEspessuraGrossa
from app.domain.numeros import parse_decimal_humano
from app.services.custeio_simplificado_tarifas_service import CusteioSimplificadoTarifasService
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho

# Só dígitos e UM separador decimal (ponto ou vírgula; a vírgula é convertida
# em ponto ao guardar). Letras e caracteres especiais ficam bloqueados na
# escrita, para não corromper os cálculos do custeio.
_PADRAO_NUMERICO = QRegularExpression(r"^\d{0,7}([.,]\d{0,4})?$")

# Editor da célula legível durante a edição: fundo branco, texto escuro e
# borda castanha (sem isto o editor herda tons de branco pouco visíveis).
_ESTILO_EDITOR_CELULA = (
    f"QTableWidget QLineEdit {{ background-color: #FFFFFF; color: {tema.TEXTO_NORMAL};"
    f" border: 1px solid {tema.CASTANHO_MEDIO}; padding: 2px 6px;"
    f" selection-background-color: {tema.BEGE_AREIA}; selection-color: {tema.TEXTO_NORMAL}; }}"
)


class DelegateNumericoTarifas(QStyledItemDelegate):
    """Cell editor that only accepts numbers (digits + one '.' or ',')."""

    def createEditor(self, parent, option, index):  # noqa: N802 (Qt override)
        editor = QLineEdit(parent)
        editor.setValidator(QRegularExpressionValidator(_PADRAO_NUMERICO, editor))
        return editor


class CusteioSimplificadoTarifasPage(QWidget):
    HEADERS = ("Escalão", "Corte €/peça", "PUR 4 lados", "LASER 4 lados", "Urgência €/item", "Sem Excel €/peça")
    HEADERS_GROSSA = ("Espessura", "Corte €/peça", "Orlagem €/lado orlado")
    TOOLTIPS = {
        "Escalão": "Escalão pela quantidade total de peças do item (o ≥25 inclui exatamente 25).",
        "Corte €/peça": "Preço de corte por peça neste escalão (espessura ≤ 19 mm).",
        "PUR 4 lados": "Preço PUR para QUATRO lados; a peça paga a proporção dos lados orlados.",
        "LASER 4 lados": "Preço LASER para QUATRO lados; a peça paga a proporção dos lados orlados.",
        "Urgência €/item": "Valor de urgência cobrado UMA vez por item (não multiplica pela quantidade de peças).",
        "Sem Excel €/peça": "Custo adicional por peça quando a lista não vem em Excel.",
    }
    TOOLTIPS_GROSSA = {
        "Corte €/peça": "Corte por peça quando a espessura é superior a 19 mm (igual em todos os escalões).",
        "Orlagem €/lado orlado": "Orlagem por lado orlado (código de orlas 2222=4 lados, 2100=2, ...) acima de 19 mm; ignora PUR/LASER.",
    }

    def __init__(self, on_back=None) -> None:
        super().__init__()
        self.on_back = on_back
        layout = QVBoxLayout(self)
        layout.addWidget(BarraCabecalho("Tarifas Custeio Simplificado", [
            "Espessura ≤ 19 mm: PUR/LASER são preços para quatro lados; a peça paga a proporção dos lados orlados.",
            "Espessura > 19 mm: corte por peça e orlagem por lado orlado da tabela própria (igual para PUR e LASER).",
            "Urgência: valor único por item, escolhido pelo escalão. O escalão ≥25 inclui exatamente 25 peças.",
        ]))
        self.table = self._criar_tabela(4, self.HEADERS, self.TOOLTIPS)
        self.table_grossa = self._criar_tabela(1, self.HEADERS_GROSSA, self.TOOLTIPS_GROSSA)
        actions = QHBoxLayout()
        back = QPushButton("Voltar")
        back.setToolTip("Regressar às Configurações sem guardar alterações pendentes.")
        back.clicked.connect(lambda: self.on_back() if self.on_back else None)
        save = QPushButton("Guardar tarifas")
        save.setToolTip("Guardar as duas tabelas de tarifas. Os itens Simplificado só usam os novos valores após Atualizar.")
        save.clicked.connect(self.guardar)
        actions.addWidget(back); actions.addStretch(); actions.addWidget(save)
        layout.addLayout(actions)
        # Linha de acompanhamento logo abaixo dos botões, como nos outros menus.
        self.status = QLabel(""); layout.addWidget(self.status)
        layout.addWidget(QLabel("Escalões por quantidade de peças (espessura ≤ 19 mm):"))
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Espessura de material > 19 mm (sem escalões):"))
        layout.addWidget(self.table_grossa)
        layout.addStretch()
        self.carregar()

    def _criar_tabela(self, linhas: int, headers, tooltips) -> QTableWidget:
        tabela = QTableWidget(linhas, len(headers))
        tabela.setHorizontalHeaderLabels(headers)
        # Mesma linguagem visual das outras tabelas de configuração + editor
        # de célula legível (a lógica de cores vive em app/ui/tema.py).
        tabela.setStyleSheet(tema.ESTILO_TABELA_CONFIG_CABECALHO + "\n" + _ESTILO_EDITOR_CELULA)
        tabela.setAlternatingRowColors(True)
        tabela.setItemDelegate(DelegateNumericoTarifas(tabela))
        for indice, nome in enumerate(headers):
            item = tabela.horizontalHeaderItem(indice)
            if item is not None and nome in tooltips:
                item.setToolTip(tooltips[nome])
        altura = tabela.horizontalHeader().sizeHint().height() + linhas * tabela.verticalHeader().defaultSectionSize() + 2 * tabela.frameWidth() + 6
        tabela.setMaximumHeight(altura)
        return tabela

    def carregar(self) -> None:
        with SessionLocal() as session:
            tarifas, grossa = CusteioSimplificadoTarifasService(session).obter_completo()
        for row, tarifa in enumerate(tarifas):
            escalao = ("1–4", "5–14", "15–24", "≥25")[row]
            valores = (escalao, tarifa.corte_por_peca, tarifa.pur_4_lados, tarifa.laser_4_lados, tarifa.urgencia_item, tarifa.sem_excel_por_peca)
            for col, valor in enumerate(valores):
                self.table.setItem(row, col, self._criar_item(valor, editavel=col != 0))
        for col, valor in enumerate(("> 19 mm", grossa.corte_por_peca, grossa.orlagem_por_lado)):
            self.table_grossa.setItem(0, col, self._criar_item(valor, editavel=col != 0))

    @staticmethod
    def _criar_item(valor, *, editavel: bool) -> QTableWidgetItem:
        item = QTableWidgetItem("" if valor is None else str(valor))
        if not editavel:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def guardar(self) -> None:
        try:
            tarifas = []
            for row, minimo in enumerate((1, 5, 15, 25)):
                def valor(col):
                    return parse_decimal_humano(self.table.item(row, col).text().strip())
                tarifas.append(TarifaCusteioSimplificado(minimo, valor(1), valor(2), valor(3), valor(4), valor(5)))
            grossa = TarifaEspessuraGrossa(
                corte_por_peca=parse_decimal_humano(self.table_grossa.item(0, 1).text().strip()),
                orlagem_por_lado=parse_decimal_humano(self.table_grossa.item(0, 2).text().strip()),
            )
            if any(campo is None for tarifa in tarifas for campo in (tarifa.corte_por_peca, tarifa.pur_4_lados, tarifa.laser_4_lados, tarifa.urgencia_item, tarifa.sem_excel_por_peca)):
                raise ValueError("tarifa em falta")
            if grossa.corte_por_peca is None or grossa.orlagem_por_lado is None:
                raise ValueError("tarifa em falta")
            with SessionLocal() as session:
                CusteioSimplificadoTarifasService(session).guardar(tuple(tarifas), grossa)
        except (SQLAlchemyError, ValueError, AttributeError):
            self.status.setText("Verifique os valores numéricos das tarifas (todos os campos são obrigatórios).")
            return
        self.status.setText("Tarifas guardadas. Atualize os itens Simplificado para aplicar os novos valores.")
        self.carregar()
