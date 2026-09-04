"""Dialog for selecting an adjudicated budget to convert to production."""

from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.producao_service import (
    levantar_orcamentos_para_conversao,
    validar_conversao,
)
from app.ui import tema
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_version
from app.ui.widgets.combo_sem_scroll import ComboSemScroll


#: Quantos motivos se mostram quando a pesquisa não devolve nada.
MAX_MOTIVOS_MOSTRADOS = 5


class ConverterOrcamentoDialog(QDialog):
    """Modal dialog to pick a budget version for production conversion."""

    TABLE_HEADERS = [
        "Ano",
        "Nº Orç",
        "Versão",
        "Cliente",
        "Nº Enc PHC",
        "Preço",
        "Pronto?",
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.selected_orcamento_id: int | None = None
        self.selected_versao_id: int | None = None
        self.selected_num_enc_phc: str | None = None
        # Ano do orçamento escolhido: é por ele que se procura a encomenda no
        # PHC, para trazer as datas e as descrições dos artigos.
        self.selected_ano: str | None = None
        self._todos: list[dict] = []
        self._linhas: list[dict] = []
        # Orçamentos que NÃO entram na lista, com o motivo. Só servem para
        # explicar uma pesquisa sem resultados; nunca aparecem na tabela.
        self._excluidos: list[dict] = []

        self.setWindowTitle("Converter Orçamento")
        self.setModal(True)
        self.setMinimumSize(820, 460)

        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar orçamento, cliente ou encomenda PHC..."
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)

        # Nota fixa com o critério: sem ela, quem procura um orçamento que
        # sabe que existe fica a olhar para uma lista vazia sem perceber
        # porquê. É a mesma regra que a lista aplica, escrita por palavras.
        self.criterios_label = QLabel(
            "Aqui só aparecem os orçamentos Adjudicados, com Nº Enc PHC, e que "
            "ainda não foram passados para produção."
        )
        self.criterios_label.setWordWrap(True)
        self.criterios_label.setStyleSheet(
            f"color: {tema.CASTANHO_MEDIO}; padding: 2px;"
        )

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {tema.TEXTO_AVISO};")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        ligar_persistencia_larguras(self.table, "dialog_converter_orcamento")
        self.table.itemSelectionChanged.connect(self._atualizar_ok)
        self.table.cellDoubleClicked.connect(self._handle_double_click)

        # Phase 5: a version may have several PHC orders; the user picks the
        # one to convert (the principal order is pre-selected).
        self.encomenda_label = QLabel("Encomenda PHC a converter:")
        self.encomenda_combo = ComboSemScroll()
        self.encomenda_combo.setToolTip(
            "Encomenda PHC que dará origem ao processo de produção"
        )
        self.encomenda_combo.setEnabled(False)

        encomenda_layout = QHBoxLayout()
        encomenda_layout.addWidget(self.encomenda_label)
        encomenda_layout.addWidget(self.encomenda_combo, stretch=1)

        self.ok_button = QPushButton("OK")
        self.ok_button.setToolTip("Converter o orçamento selecionado")
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self._confirmar)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setToolTip("Fechar sem converter")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addWidget(self.campo_pesquisa)
        layout.addWidget(self.criterios_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(encomenda_layout)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._carregar()

    def _carregar(self) -> None:
        try:
            with SessionLocal() as session:
                self._todos, self._excluidos = levantar_orcamentos_para_conversao(
                    session
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os orcamentos.")
            return

        self._render()
        if not self._todos:
            self.status_label.setText(
                "Não há orçamentos à espera de passar para produção."
            )

    @staticmethod
    def _termos(texto: str) -> list[str]:
        return [
            termo
            for termo in re.split(r"[\s%]+", (texto or "").strip().lower())
            if termo
        ]

    @staticmethod
    def _corresponde(item: dict, termos: list[str], campos) -> bool:
        haystack = " ".join(str(item.get(campo) or "").lower() for campo in campos)
        return all(termo in haystack for termo in termos)

    def _render(self, *_args) -> None:
        termos = self._termos(self.campo_pesquisa.texto())
        campos = (
            "ano",
            "num_orcamento",
            "numero_versao",
            "cliente_nome",
            "enc_phc",
            "preco_total",
        )
        linhas = [
            item for item in self._todos if self._corresponde(item, termos, campos)
        ]

        self._linhas = linhas
        self._explicar_pesquisa(termos, linhas)
        self.table.setRowCount(len(linhas))
        for row_index, item in enumerate(linhas):
            erros = validar_conversao(
                estado="Adjudicado",
                is_temporary=item["is_temporary"],
                source_system=item["source_system"],
                num_cliente_phc=item["num_cliente_phc"],
                enc_phc=item["enc_phc"],
            )
            encomendas = item.get("encomendas_phc") or []
            enc_display = item["enc_phc"] or ""
            if len(encomendas) > 1:
                enc_display = f"{enc_display} (+{len(encomendas) - 1})"
            values = [
                str(item["ano"]),
                item["num_orcamento"],
                format_version(item["numero_versao"]),
                item["cliente_nome"],
                enc_display,
                format_currency(item["preco_total"]),
                "✓" if not erros else erros[0],
            ]
            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if value:
                    table_item.setToolTip(value)
                self.table.setItem(row_index, column_index, table_item)
            self._marcar_encomendas_ja_criadas(row_index, item)

        self._atualizar_ok()

    def _marcar_encomendas_ja_criadas(self, row_index: int, item: dict) -> None:
        """Dizer na dica quais encomendas desta versão já têm obra.

        A versão continua na lista enquanto tiver encomendas por converter,
        mas quem a vê tem de perceber que as outras já foram — senão parece
        que a lista está a repetir trabalho já feito.
        """
        convertidas = item.get("encomendas_convertidas") or []
        if not convertidas:
            return
        celula = self.table.item(row_index, self.TABLE_HEADERS.index("Nº Enc PHC"))
        if celula is None:
            return
        celula.setToolTip(
            f"{celula.text()}\n\nJá passaram para produção: "
            + ", ".join(str(codigo) for codigo in convertidas)
        )

    def _explicar_pesquisa(self, termos: list[str], linhas: list[dict]) -> None:
        """Dizer porque é que uma pesquisa não devolveu nada.

        Sem isto, procurar um orçamento que não cumpre os critérios dá um ecrã
        vazio e a sensação de que o Martelo se perdeu. Agora vai-se procurar o
        mesmo termo aos orçamentos que ficaram de fora e diz-se o motivo de
        cada um — normalmente "ainda não está Adjudicado" ou "já foi passado
        para produção".
        """
        if linhas:
            self.status_label.setText("")
            return
        if not termos:
            if self._todos:
                self.status_label.setText("")
            return

        campos = ("ano", "num_orcamento", "numero_versao", "cliente_nome")
        encontrados = [
            item
            for item in self._excluidos
            if self._corresponde(item, termos, campos)
        ]
        procurado = self.campo_pesquisa.texto().strip()
        if not encontrados:
            self.status_label.setText(
                f"Nada encontrado para «{procurado}». "
                "Confirme o número do orçamento, ou o Nº Enc PHC."
            )
            return

        detalhes = [
            f"  • {item['num_orcamento']} v{format_version(item['numero_versao'])}"
            f" ({item['cliente_nome']}) — {item['motivo']}"
            for item in encontrados[:MAX_MOTIVOS_MOSTRADOS]
        ]
        if len(encontrados) > MAX_MOTIVOS_MOSTRADOS:
            detalhes.append(f"  • … e mais {len(encontrados) - MAX_MOTIVOS_MOSTRADOS}")
        self.status_label.setText(
            f"«{procurado}» existe nos Orçamentos, mas não pode passar para "
            "produção:\n" + "\n".join(detalhes)
        )

    def _get_selected(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._linhas):
            return None
        return self._linhas[row]

    def _atualizar_ok(self) -> None:
        item = self._get_selected()
        self.ok_button.setEnabled(item is not None)
        self._atualizar_encomendas(item)

    def _atualizar_encomendas(self, item: dict | None) -> None:
        """Fill the PHC-order combo for the selected budget version."""
        self.encomenda_combo.clear()
        encomendas = list((item or {}).get("encomendas_phc") or [])
        if not encomendas and item is not None and item.get("enc_phc"):
            encomendas = [item["enc_phc"]]
        for numero in encomendas:
            self.encomenda_combo.addItem(str(numero))
        self.encomenda_combo.setEnabled(len(encomendas) > 1)

    def _confirmar(self) -> None:
        item = self._get_selected()
        if item is None:
            self.status_label.setText("Selecione um orçamento.")
            return

        self.selected_orcamento_id = item["orcamento_id"]
        self.selected_versao_id = item["versao_id"]
        self.selected_ano = str(item.get("ano") or "").strip() or None
        numero = self.encomenda_combo.currentText().strip()
        self.selected_num_enc_phc = numero or None
        self.accept()

    def _handle_double_click(self, row: int, _column: int) -> None:
        self.table.selectRow(row)
        self._confirmar()
