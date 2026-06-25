"""Diálogo para criar um processo de produção a partir do PHC ou do Streamlit."""

from __future__ import annotations

import re
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.db.session import SessionLocal
from app.services.encomendas_phc_service import query_phc_encomenda_itens
from app.services.streamlit_sql_service import query_streamlit_encomenda_itens
from app.ui import tema
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


_COLUNAS_PHC = (
    ("Ano", "Ano"),
    ("Nome Cliente", "Cliente"),
    ("Nome Cliente Simplex", "Cliente_Abreviado"),
    ("Nº Enc PHC", "Enc_No"),
    ("Num PHC", "Num_PHC"),
    ("Ref Cliente", "Ref_Cliente"),
    ("Descrição Artigo", "Descricao_Artigo"),
    ("Data Encomenda", "Data_Encomenda"),
    ("Data Entrega", "Data_Entrega"),
)

_COLUNAS_STREAMLIT = (
    ("Ano", "Ano"),
    ("Cliente", "Cliente"),
    ("Cliente Abreviado", "Cliente_Abreviado"),
    ("Número", "Numero"),
    ("Ref Cliente", "RefCliente"),
    ("Designação", "Designacao"),
    ("Data Receção", "DataRecepcao"),
    ("Data Entrega", "DataEntrega"),
)


class _OrigemTab(QWidget):
    """Separador reutilizável: pesquisa de encomenda (PHC ou Streamlit) + tabela."""

    dados_carregados = Signal()

    def __init__(self, *, origem, colunas, larguras_key, num_enc_placeholder, parent=None):
        super().__init__(parent)
        self.origem = origem
        self._colunas = colunas
        self._linhas: list[dict] = []
        self._linhas_visiveis: list[dict] = []

        self.ano_spin = QSpinBox()
        self.ano_spin.setRange(2000, 2100)
        self.ano_spin.setValue(datetime.now().year)
        self.ano_spin.setToolTip("Ano da encomenda a pesquisar")

        self.num_enc_input = QLineEdit()
        self.num_enc_input.setPlaceholderText(num_enc_placeholder)
        if origem == "phc":
            self.num_enc_input.setValidator(QIntValidator(0, 999999999, self))
            self.num_enc_input.setToolTip("Número da encomenda no PHC (só dígitos)")
        else:
            self.num_enc_input.setToolTip("Número da encomenda Cliente Final (ex.: _001 ou 001)")
        self.num_enc_input.returnPressed.connect(self._carregar)

        self.pesquisar_button = QPushButton("Pesquisar")
        self.pesquisar_button.setToolTip("Pesquisar a encomenda (só leitura) e mostrar os itens")
        self.pesquisar_button.clicked.connect(self._carregar)

        self.campo_pesquisa = CampoPesquisa()
        self.campo_pesquisa.setToolTip("Filtrar a lista já carregada (vários termos: espaço ou %)")
        self.campo_pesquisa.pesquisa_mudou.connect(self._render)
        self.campo_pesquisa.limpar_clicado.connect(self._render)

        filtros = QHBoxLayout()
        filtros.addWidget(QLabel("Ano"))
        filtros.addWidget(self.ano_spin)
        filtros.addWidget(QLabel("Nº Enc"))
        filtros.addWidget(self.num_enc_input)
        filtros.addWidget(self.pesquisar_button)
        filtros.addSpacing(12)
        filtros.addWidget(self.campo_pesquisa, stretch=1)

        self.status_label = QLabel("")

        self.table = QTableWidget(0, len(colunas))
        self.table.setHorizontalHeaderLabels([titulo for titulo, _chave in colunas])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        ligar_persistencia_larguras(self.table, larguras_key)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addLayout(filtros)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

    # API usada pelo diálogo
    def tem_linhas(self) -> bool:
        return bool(self._linhas)

    def linhas(self) -> list[dict]:
        return list(self._linhas)

    def linha_selecionada(self) -> dict | None:
        row = self.table.currentRow()
        if 0 <= row < len(self._linhas_visiveis):
            return self._linhas_visiveis[row]
        if self._linhas_visiveis:
            return self._linhas_visiveis[0]
        return None

    def _carregar(self) -> None:
        num_enc = self.num_enc_input.text().strip()
        if not num_enc:
            QMessageBox.warning(self, "Pesquisar", "Indique o número da encomenda.")
            return

        self.status_label.setText("A carregar...")
        self.pesquisar_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            with SessionLocal() as session:
                if self.origem == "phc":
                    linhas = query_phc_encomenda_itens(
                        session, num_enc_phc=num_enc, ano=self.ano_spin.value()
                    )
                else:
                    linhas = query_streamlit_encomenda_itens(
                        session, num_enc_final=num_enc, ano=self.ano_spin.value()
                    )
        except ValueError as exc:
            self._linhas = []
            self._render()
            self.status_label.setText(str(exc))
            self.dados_carregados.emit()
            return
        except Exception as exc:  # ligação/SQL/config externos
            self._linhas = []
            self._render()
            self.status_label.setText(self._mensagem_erro(exc))
            self.dados_carregados.emit()
            return
        finally:
            QApplication.restoreOverrideCursor()
            self.pesquisar_button.setEnabled(True)

        self._linhas = list(linhas)
        self._render()
        if self._linhas:
            self.table.selectRow(0)
            self.status_label.setText(f"{len(self._linhas)} linha(s) carregada(s).")
        else:
            self.status_label.setText("Encomenda não encontrada.")
        self.dados_carregados.emit()

    def _render(self, *_args) -> None:
        self._linhas_visiveis = self._filtrar(self._linhas, self.campo_pesquisa.texto())
        self.table.setRowCount(len(self._linhas_visiveis))
        for row, linha in enumerate(self._linhas_visiveis):
            for col, (_titulo, chave) in enumerate(self._colunas):
                valor = self._valor(linha, chave)
                item = QTableWidgetItem(valor)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if valor:
                    item.setToolTip(valor)
                self.table.setItem(row, col, item)

    def _filtrar(self, linhas, texto):
        termos = [t for t in re.split(r"[\s%]+", (texto or "").strip().lower()) if t]
        if not termos:
            return list(linhas or [])
        resultado = []
        for linha in linhas or []:
            haystack = " ".join(self._valor(linha, chave) for _t, chave in self._colunas).lower()
            if all(t in haystack for t in termos):
                resultado.append(linha)
        return resultado

    @staticmethod
    def _valor(linha, chave):
        valor = linha.get(chave)
        return "" if valor is None else str(valor).strip()

    @staticmethod
    def _mensagem_erro(exc):
        texto = str(exc)
        if "Configuracao PHC" in texto or "Configuração PHC" in texto:
            return "PHC não configurado. Configure a ligação em Configurações."
        if "Configuracao Streamlit" in texto or "Configuração Streamlit" in texto:
            return "Streamlit não configurado. Configure a ligação em Configurações."
        return f"Não foi possível carregar: {texto}"

    def construir_resultado(self) -> dict | None:
        base = self.linha_selecionada()
        if base is None:
            return None
        return self._resultado_phc(base) if self.origem == "phc" else self._resultado_streamlit(base)

    def _descricoes(self, chave):
        seen, out = set(), []
        for linha in self._linhas:
            d = self._valor(linha, chave)
            if not d or d in seen:
                continue
            seen.add(d)
            out.append(d)
        return "\n".join(out).strip()

    def _ano_resultado(self, base):
        ano_row = self._valor(base, "Ano")
        return ano_row if ano_row.isdigit() else str(self.ano_spin.value())

    def _resultado_phc(self, base):
        num_enc = re.sub(r"\D", "", self._valor(base, "Enc_No")) or self.num_enc_input.text().strip()
        return {
            "source": "phc",
            "ano": self._ano_resultado(base),
            "num_enc_phc": num_enc,
            "nome_cliente": self._valor(base, "Cliente"),
            "nome_cliente_simplex": self._valor(base, "Cliente_Abreviado"),
            "num_cliente_phc": self._valor(base, "Num_PHC"),
            "ref_cliente": self._valor(base, "Ref_Cliente"),
            "descricao_artigos": self._descricoes("Descricao_Artigo"),
            "data_inicio": self._valor(base, "Data_Encomenda"),
            "data_entrega": self._valor(base, "Data_Entrega"),
        }

    def _resultado_streamlit(self, base):
        digits = re.sub(r"\D", "", self._valor(base, "Numero"))
        num_enc = "_" + digits.zfill(3) if digits else self._valor(base, "Numero")
        nome_cliente = self._valor(base, "Cliente")
        return {
            "source": "streamlit",
            "ano": self._ano_resultado(base),
            "num_enc_phc": num_enc,
            "nome_cliente": nome_cliente,
            "nome_cliente_simplex": self._valor(base, "Cliente_Abreviado") or nome_cliente,
            "num_cliente_phc": "",
            "ref_cliente": self._valor(base, "RefCliente"),
            "descricao_artigos": self._descricoes("Designacao"),
            "data_inicio": self._valor(base, "DataRecepcao"),
            "data_entrega": self._valor(base, "DataEntrega"),
        }


class NovoProcessoDialog(QDialog):
    """Cria um processo de produção a partir de uma encomenda PHC ou Streamlit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Novo Processo")
        self.resize(1000, 580)
        self._result: dict | None = None

        self.tabs = QTabWidget()
        self.tab_phc = _OrigemTab(
            origem="phc",
            colunas=_COLUNAS_PHC,
            larguras_key="novo_processo_phc",
            num_enc_placeholder="Ex.: 1956",
        )
        self.tab_streamlit = _OrigemTab(
            origem="streamlit",
            colunas=_COLUNAS_STREAMLIT,
            larguras_key="novo_processo_streamlit",
            num_enc_placeholder="Ex.: _001 ou 001",
        )
        self.tabs.addTab(self.tab_phc, "Encomenda de Cliente (PHC)")
        self.tabs.addTab(self.tab_streamlit, "Encomenda Cliente Final (Streamlit)")

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Criar Processo")
        self.ok_button.setEnabled(False)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        for botao in (self.ok_button, cancel_button):
            if botao is not None:
                botao.setAutoDefault(False)
                botao.setDefault(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs, stretch=1)
        layout.addWidget(self.buttons)

        self.tabs.currentChanged.connect(self._refresh_ok)
        self.tab_phc.dados_carregados.connect(self._refresh_ok)
        self.tab_streamlit.dados_carregados.connect(self._refresh_ok)
        self._refresh_ok()

    def result_data(self) -> dict | None:
        return self._result

    def _tab_ativa(self):
        return self.tabs.currentWidget()

    def _refresh_ok(self, *_args):
        tab = self._tab_ativa()
        self.ok_button.setEnabled(bool(tab and tab.tem_linhas()))

    def _on_accept(self):
        tab = self._tab_ativa()
        if tab is None or not tab.tem_linhas():
            QMessageBox.warning(self, "Novo Processo", "Pesquise uma encomenda antes de continuar.")
            return
        resultado = tab.construir_resultado()
        if not resultado:
            QMessageBox.warning(self, "Novo Processo", "Selecione uma linha da encomenda.")
            return
        if not resultado.get("nome_cliente"):
            QMessageBox.warning(self, "Novo Processo", "A encomenda não tem nome de cliente.")
            return
        self._result = resultado
        self.accept()
