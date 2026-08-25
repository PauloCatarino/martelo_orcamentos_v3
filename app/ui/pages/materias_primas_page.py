"""Raw materials catalog page."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.materia_prima_types import (
    MESES_PRECO_DESATUALIZADO,
    TIPO_PRECO_LIVRE,
    preco_desatualizado,
    preco_em_falta,
)
from app.domain.materias_primas_validacao import resumir
from app.domain.numeros import formatar_percentagem, normalize_percentagem_humana
from app.repositories.def_materia_prima_repository import DefMateriaPrimaResumo
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.colunas_visiveis import ligar_menu_colunas
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_quantity


class MateriasPrimasPage(QWidget):
    """Page for listing imported raw materials."""

    TABLE_HEADERS = [
        "Ref LE",
        "Descri\u00e7\u00e3o",
        "Tipo Excel",
        "Fam\u00edlia Excel",
        "Unidade",
        "Desp %",
        "Pre\u00e7o L\u00edquido",
        "\u00daltimo pre\u00e7o",
        "Stock",
        "Fornecedor",
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Ativo",
    ]

    #: Colunas que levam as cores dos avisos (pre\u00e7o em falta / pre\u00e7o antigo).
    COLUNA_PRECO_LIQUIDO = 6
    COLUNA_ULTIMO_PRECO = 7

    def __init__(self) -> None:
        super().__init__()

        self._materias_primas: list[DefMateriaPrimaResumo] = []

        self.cabecalho = BarraCabecalho(
            "Mat\u00e9rias-Primas",
            [
                "Cat\u00e1logo de mat\u00e9rias-primas do Martelo: \u00e9 aqui que se inserem, "
                "alteram e descontinuam os materiais que alimentam o custeio dos "
                "or\u00e7amentos. Descontinuar n\u00e3o mexe nos or\u00e7amentos j\u00e1 feitos."
            ],
        )

        self.refresh_button = QPushButton("Atualizar Página")
        self.refresh_button.clicked.connect(self.carregar_materias_primas)
        self.refresh_button.setToolTip("Recarregar as matérias-primas importadas")

        self.novo_button = QPushButton("+ Nova matéria-prima")
        self.novo_button.clicked.connect(self.nova_materia_prima)
        self.novo_button.setToolTip("Criar uma matéria-prima nova no Martelo")

        self.editar_button = QPushButton("Editar")
        self.editar_button.clicked.connect(self.editar_materia_prima)
        self.editar_button.setToolTip(
            "Editar a matéria-prima selecionada (duplo-clique faz o mesmo)"
        )

        self.duplicar_button = QPushButton("Duplicar")
        self.duplicar_button.clicked.connect(self.duplicar_materia_prima)
        self.duplicar_button.setToolTip(
            "Criar uma matéria-prima nova a partir da selecionada"
        )

        self.ativar_button = QPushButton("Desativar")
        self.ativar_button.clicked.connect(self.alternar_ativo)
        self.ativar_button.setToolTip(
            "Descontinuar a matéria-prima: deixa de aparecer nas escolhas de "
            "linhas novas, mas os orçamentos que já a usam ficam intactos"
        )

        self.mostrar_inativos_input = QCheckBox("Mostrar não ativos")
        self.mostrar_inativos_input.setToolTip(
            "Mostrar também as matérias-primas descontinuadas, riscadas"
        )
        self.mostrar_inativos_input.stateChanged.connect(self.aplicar_pesquisa)

        self.verificar_button = QPushButton("Verificar Excel")
        self.verificar_button.clicked.connect(self.verificar_excel)
        self.verificar_button.setToolTip(
            "Ler o Excel e mostrar o que precisa de correção — sem gravar nada"
        )

        self.import_button = QPushButton("Importar/Atualizar Excel")
        self.import_button.clicked.connect(self.importar_do_excel)
        self.import_button.setToolTip(
            "Importar ou atualizar o catálogo a partir do Excel configurado"
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName("materiasPrimasStatus")

        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar mat\u00e9ria-prima\u2026 (espa\u00e7o para v\u00e1rios termos)"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self.aplicar_pesquisa)
        self.campo_pesquisa.limpar_clicado.connect(self.aplicar_pesquisa)

        self.open_excel_button = QPushButton("Abrir Excel")
        self.open_excel_button.setToolTip(
            "Abrir o ficheiro Excel de origem das matérias-primas"
        )
        self.open_excel_button.clicked.connect(self.abrir_excel)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.campo_pesquisa)
        toolbar.addWidget(self.novo_button)
        toolbar.addWidget(self.editar_button)
        toolbar.addWidget(self.duplicar_button)
        toolbar.addWidget(self.ativar_button)
        toolbar.addWidget(self.mostrar_inativos_input)
        toolbar.addStretch()
        toolbar.addWidget(self.verificar_button)
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.open_excel_button)
        toolbar.addWidget(self.refresh_button)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        self._larguras_restauradas = ligar_persistencia_larguras(
            self.table, "materias_primas"
        )
        ligar_menu_colunas(self.table, "materias_primas")
        self._larguras_seed_feito = False
        # Mapa linha->matéria-prima e "modo resolução" (assistente): duplo-clique
        # aplica a matéria-prima à linha do custeio e volta.
        self._materias_por_row: dict[int, DefMateriaPrimaResumo] = {}
        self._resolucao_callback = None
        self.table.cellDoubleClicked.connect(self._on_duplo_clique)
        self.table.itemSelectionChanged.connect(self._atualizar_botoes)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(toolbar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_materias_primas()

    def abrir_excel(self) -> None:
        """Open the configured source workbook without modifying it."""
        from scripts.import_materias_primas_excel import (
            get_default_excel_path_resolution,
            resolve_excel_path,
        )

        try:
            with SessionLocal() as session:
                resolucao = resolve_excel_path(session=session)
                esperada = get_default_excel_path_resolution(session).path
        except (SQLAlchemyError, OSError):
            self.status_label.setText("Não foi possível localizar o Excel configurado.")
            return

        if resolucao is None:
            self.status_label.setText(f"Ficheiro Excel não encontrado: {esperada}")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(resolucao.path)))

    def carregar_materias_primas(self) -> None:
        """Load raw materials into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()
        self._materias_primas = []

        try:
            with SessionLocal() as session:
                materias_primas = DefMateriaPrimaService(session).listar_materias_primas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as materias-primas.")
            return

        self._materias_primas = materias_primas
        self.aplicar_pesquisa()

        if not materias_primas:
            self.status_label.setText("Sem materias-primas para mostrar.")

    def _analisar_excel(self):
        """Read and validate the configured Excel. Returns (caminho, relatorio).

        Returns None (and fills the status line) when the file cannot be read,
        so both the verification and the import can bail out the same way.
        """
        try:
            from scripts.import_materias_primas_excel import analisar_materias_primas

            with SessionLocal() as session:
                return analisar_materias_primas(session)
        except FileNotFoundError as error:
            print(f"[Materias-Primas] Excel nao encontrado: {error}")
            self.status_label.setText(
                "Ficheiro Excel de matérias-primas não encontrado. "
                "Verifique a configuração."
            )
        except (ImportError, SQLAlchemyError, RuntimeError, OSError) as error:
            print(f"[Materias-Primas] Erro ao verificar o Excel: {error}")
            self.status_label.setText("Não foi possível verificar o Excel.")

        return None

    def verificar_excel(self) -> None:
        """Show what is wrong in the Excel without writing anything."""
        self.status_label.setText("A verificar o Excel…")
        analise = self._analisar_excel()
        if analise is None:
            return

        caminho, relatorio = analise
        self.status_label.setText(resumir(relatorio))
        self._mostrar_relatorio(relatorio, caminho)

    def _mostrar_relatorio(self, relatorio, caminho) -> None:
        """Open the verification report dialog."""
        from app.ui.dialogs.verificar_excel_materias_primas_dialog import (
            VerificarExcelMateriasPrimasDialog,
        )

        VerificarExcelMateriasPrimasDialog(relatorio, str(caminho), self).exec()

    def importar_do_excel(self) -> None:
        """Run the real raw-material import from the configured Excel (upsert by ref_le)."""
        analise = self._analisar_excel()
        if analise is None:
            return

        caminho, relatorio = analise
        if relatorio.criticos:
            escolha = QMessageBox.warning(
                self,
                "Problemas no Excel",
                f"O Excel tem {len(relatorio.criticos)} problemas críticos "
                "(por exemplo referências repetidas ou preços a zero).\n\n"
                "Quer ver a lista antes de importar?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if escolha == QMessageBox.StandardButton.Cancel:
                self.status_label.setText("Importação cancelada.")
                return
            if escolha == QMessageBox.StandardButton.Yes:
                self.status_label.setText(resumir(relatorio))
                self._mostrar_relatorio(relatorio, caminho)
                return

        confirm = QMessageBox.question(
            self,
            "Importar/Atualizar Excel",
            "Esta operação vai atualizar as matérias-primas a partir do Excel "
            "configurado. As referências existentes serão atualizadas e não "
            "duplicadas. Deseja continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            from scripts.import_materias_primas_excel import importar_materias_primas

            with SessionLocal() as session:
                summary = importar_materias_primas(session)
        except FileNotFoundError as error:
            print(f"[Materias-Primas] Excel nao encontrado: {error}")
            self.status_label.setText(
                "Ficheiro Excel de matérias-primas não encontrado. "
                "Verifique a configuração."
            )
            return
        except (ImportError, SQLAlchemyError, RuntimeError, OSError) as error:
            print(f"[Materias-Primas] Erro ao importar do Excel: {error}")
            self.status_label.setText(
                "Não foi possível importar as matérias-primas do Excel."
            )
            return

        self.carregar_materias_primas()
        self.status_label.setText(
            f"Importação concluída: {summary.criadas} criadas, "
            f"{summary.atualizadas} atualizadas, {summary.erros} erros."
        )

    def aplicar_pesquisa(self, _text: str | None = None) -> None:
        """Filter the loaded raw materials according to the search text."""
        self.status_label.clear()
        search_text = self.campo_pesquisa.texto()
        mostrar_inativos = self.mostrar_inativos_input.isChecked()

        filtered = [
            materia
            for materia in self._materias_primas
            if (mostrar_inativos or materia.ativo)
            and (
                not search_text.strip()
                or materia_matches_search(materia, search_text)
            )
        ]

        self._preencher_tabela(filtered)

        if not self._materias_primas:
            self.status_label.setText("Sem materias-primas para mostrar.")
        elif search_text.strip() and not filtered:
            self.status_label.setText("Sem resultados para a pesquisa.")
        else:
            self.status_label.setText(self._texto_rodape(filtered))

    def _texto_rodape(self, visiveis: list[DefMateriaPrimaResumo]) -> str:
        """Linha do supervisor: o que está à vista e o que precisa de atenção."""
        sem_preco = sum(1 for m in self._materias_primas if m.ativo and preco_em_falta(m))
        a_rever = sum(
            1 for m in self._materias_primas if m.ativo and preco_desatualizado(m)
        )
        inativos = sum(1 for m in self._materias_primas if not m.ativo)

        partes = [f"{len(visiveis)} matérias-primas à vista"]
        if inativos and not self.mostrar_inativos_input.isChecked():
            partes.append(f"{inativos} descontinuadas escondidas")
        if a_rever:
            partes.append(f"{a_rever} preços a rever")
        if sem_preco:
            partes.append(f"{sem_preco} sem preço")

        return " · ".join(partes) + "."

    def _materia_selecionada(self) -> DefMateriaPrimaResumo | None:
        """A matéria-prima da linha selecionada, ou None."""
        linhas = self.table.selectionModel().selectedRows()
        if not linhas:
            return None

        return self._materias_por_row.get(linhas[0].row())

    def _exigir_selecao(self) -> DefMateriaPrimaResumo | None:
        """Como acima, mas a avisar quando não há nada escolhido."""
        materia = self._materia_selecionada()
        if materia is None:
            self.status_label.setText("Escolha primeiro uma matéria-prima na lista.")

        return materia

    def nova_materia_prima(self) -> None:
        """Criar uma matéria-prima de raiz."""
        self._abrir_dialogo(None)

    def editar_materia_prima(self) -> None:
        """Editar a matéria-prima selecionada."""
        materia = self._exigir_selecao()
        if materia is not None:
            self._abrir_dialogo(materia)

    def duplicar_materia_prima(self) -> None:
        """Criar uma matéria-prima nova a partir da selecionada."""
        materia = self._exigir_selecao()
        if materia is not None:
            self._abrir_dialogo(materia, duplicar=True)

    def alternar_ativo(self) -> None:
        """Descontinuar (ou repor) a matéria-prima selecionada."""
        materia = self._exigir_selecao()
        if materia is None:
            return

        novo_estado = not materia.ativo
        if not novo_estado:
            usos = self._contar_utilizacoes(materia.id)
            aviso = (
                f"\n\nEsta matéria-prima está em {usos} linhas de orçamento. "
                "Esses orçamentos não mudam: cada linha guarda a cópia do preço "
                "com que foi calculada."
                if usos
                else ""
            )
            confirmacao = QMessageBox.question(
                self,
                "Desativar matéria-prima",
                f"Desativar «{materia.descricao}»?\n\n"
                "Deixa de aparecer nas escolhas de linhas novas, mas continua a "
                "existir e pode ser reposta a qualquer momento." + aviso,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirmacao != QMessageBox.StandardButton.Yes:
                return

        try:
            with SessionLocal() as session:
                DefMateriaPrimaService(session).definir_ativo(
                    materia.id, ativo=novo_estado
                )
        except SQLAlchemyError as error:
            print(f"[Materias-Primas] Erro ao mudar o estado: {error}")
            self.status_label.setText("Não foi possível mudar o estado da matéria-prima.")
            return

        self.carregar_materias_primas()
        self.status_label.setText(
            f"«{materia.descricao}» "
            + ("reposta como ativa." if novo_estado else "desativada.")
        )

    def _contar_utilizacoes(self, materia_prima_id: int) -> int:
        """Em quantas linhas de orçamento o material já foi usado."""
        try:
            with SessionLocal() as session:
                return DefMateriaPrimaService(session).contar_utilizacoes(
                    materia_prima_id
                )
        except SQLAlchemyError:
            return 0

    def _abrir_dialogo(
        self, materia: DefMateriaPrimaResumo | None, duplicar: bool = False
    ) -> None:
        """Abrir a ficha da matéria-prima (nova, a editar ou a duplicar)."""
        from app.ui.dialogs.materia_prima_dialog import MateriaPrimaDialog

        historico: list = []
        utilizacoes = 0
        if materia is not None and not duplicar:
            try:
                with SessionLocal() as session:
                    service = DefMateriaPrimaService(session)
                    historico = service.historico_precos(materia.id)
                    utilizacoes = service.contar_utilizacoes(materia.id)
            except SQLAlchemyError as error:
                print(f"[Materias-Primas] Erro ao ler o histórico: {error}")

        base = materia
        if duplicar and materia is not None:
            # A cópia entra sem referência: o V3 atribui a próxima da família.
            base = replace(materia, id=0, ref_le=None, descricao=f"{materia.descricao} (cópia)")

        dialogo = MateriaPrimaDialog(
            base if not duplicar else None,
            parent=self,
            on_save=lambda dados: self._guardar(
                dados, None if duplicar else materia
            ),
            historico=historico,
            utilizacoes=utilizacoes,
            ref_le_sugerida=self._proxima_ref_le,
        )
        if duplicar and base is not None:
            dialogo._carregar(base)
            dialogo.ref_le_input.clear()

        dialogo.exec()

    def _proxima_ref_le(self, familia: str) -> str | None:
        """Referência que uma matéria-prima nova dessa família vai receber."""
        try:
            with SessionLocal() as session:
                return DefMateriaPrimaService(session).proxima_ref_le(familia)
        except SQLAlchemyError:
            return None

    def _guardar(self, dados, materia: DefMateriaPrimaResumo | None) -> bool:
        """Gravar a ficha. Devolve False para o diálogo ficar aberto no erro."""
        from app.services.def_materia_prima_service import (
            CriarDefMateriaPrimaData,
            EditarDefMateriaPrimaData,
            ORIGEM_DADOS_V3,
        )

        campos = {
            "descricao": dados.descricao,
            "ref_le": dados.ref_le,
            "referencia_fornecedor": dados.referencia_fornecedor,
            "tipo_original_excel": dados.tipo,
            "familia_original_excel": dados.familia,
            "coresp_orla_0_4": dados.coresp_orla_0_4,
            "coresp_orla_1_0": dados.coresp_orla_1_0,
            "unidade": dados.unidade,
            "preco_tabela": dados.preco_tabela,
            "desconto": dados.desconto,
            "margem": dados.margem,
            "desperdicio_percentagem": dados.desperdicio_percentagem,
            "preco_liquido": dados.preco_liquido,
            "comprimento": dados.comprimento,
            "largura": dados.largura,
            "espessura": dados.espessura,
            "fornecedor": dados.fornecedor,
            "tipo_preco": dados.tipo_preco,
            "data_ultimo_preco": dados.data_ultimo_preco,
            "stock": dados.stock,
            "cor": dados.cor,
            "nome_fabricante": dados.nome_fabricante,
            "ref_phc": dados.ref_phc,
            "ativo": dados.ativo,
            "observacoes": dados.observacoes,
            "origem_dados": ORIGEM_DADOS_V3,
        }

        try:
            with SessionLocal() as session:
                service = DefMateriaPrimaService(session)
                if materia is None:
                    resultado = service.criar_materia_prima(
                        CriarDefMateriaPrimaData(**campos)
                    )
                    mensagem = f"«{resultado.descricao}» criada com a referência {resultado.ref_le}."
                else:
                    # A família normalizada do Martelo acompanha o registo.
                    resultado = service.editar_materia_prima(
                        materia.id,
                        EditarDefMateriaPrimaData(
                            tipo_martelo=materia.tipo_martelo,
                            familia_martelo=materia.familia_martelo,
                            **campos,
                        ),
                    )
                    mensagem = f"«{resultado.descricao}» gravada."
        except ValueError as error:
            self.status_label.setText(str(error))
            return False
        except SQLAlchemyError as error:
            print(f"[Materias-Primas] Erro ao gravar: {error}")
            self.status_label.setText("Não foi possível gravar a matéria-prima.")
            return False

        self.carregar_materias_primas()
        self.status_label.setText(mensagem)
        return True

    def focar_materia_prima(self, ref_le: str | None) -> None:
        """Filtra pela Ref LE, seleciona e pisca a matéria-prima (assistente 3B)."""
        if not ref_le:
            return
        alvo = ref_le.strip().upper()
        # Filtrar pela Ref LE isola a matéria-prima na tabela (re-preenche já).
        self.campo_pesquisa.definir_texto(ref_le)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and (item.text() or "").strip().upper() == alvo:
                self.table.selectRow(row)
                self.table.scrollToItem(
                    item, QAbstractItemView.ScrollHint.PositionAtCenter
                )
                self._piscar_linha(row)
                return

    def _piscar_linha(self, row: int) -> None:
        """Pisca a linha (fundo ocre) durante ~1,5 s e repõe o fundo original."""
        itens = [
            self.table.item(row, col) for col in range(self.table.columnCount())
        ]
        itens = [item for item in itens if item is not None]
        fundos = [item.background() for item in itens]
        realce = QColor(tema.OCRE_SUAVE)
        for item in itens:
            item.setBackground(realce)

        def repor() -> None:
            for item, fundo in zip(itens, fundos):
                item.setBackground(fundo)

        QTimer.singleShot(1500, repor)

    def entrar_modo_resolucao(self, ao_escolher) -> None:
        """Ativa o modo resolução: duplo-clique aplica a matéria-prima (assistente 3B)."""
        self._resolucao_callback = ao_escolher
        self.status_label.setText(
            "A resolver: duplo-clique numa matéria-prima para a aplicar à linha e voltar."
        )

    def sair_modo_resolucao(self) -> None:
        self._resolucao_callback = None

    def _on_duplo_clique(self, row: int, _column: int) -> None:
        callback = self._resolucao_callback
        materia = self._materias_por_row.get(row)
        if materia is None:
            return

        if callback is not None:
            self.sair_modo_resolucao()
            callback(materia)
            return

        # Fora do modo resolução, o duplo-clique abre a ficha para editar.
        self._abrir_dialogo(materia)

    def _atualizar_botoes(self) -> None:
        """O botão de estado diz o que vai fazer à linha escolhida."""
        materia = self._materia_selecionada()
        ativa = materia is None or materia.ativo
        self.ativar_button.setText("Desativar" if ativa else "Repor ativo")
        self.ativar_button.setToolTip(
            "Descontinuar a matéria-prima: deixa de aparecer nas escolhas de "
            "linhas novas, mas os orçamentos que já a usam ficam intactos"
            if ativa
            else "Voltar a pôr a matéria-prima disponível para orçamentos novos"
        )

    def _preencher_tabela(self, materias_primas: list[DefMateriaPrimaResumo]) -> None:
        """Fill the table with raw material read models."""
        self.table.setRowCount(len(materias_primas))
        self._materias_por_row = {}

        for row_index, materia in enumerate(materias_primas):
            self._materias_por_row[row_index] = materia
            values = [
                materia.ref_le or "",
                materia.descricao,
                materia.tipo_original_excel or "",
                materia.familia_original_excel or "",
                materia.unidade or "",
                formatar_percentagem(
                    normalize_percentagem_humana(materia.desperdicio_percentagem)
                ),
                self._texto_preco(materia),
                self._texto_data_preco(materia),
                self._texto_stock(materia),
                materia.fornecedor or "",
                materia.coresp_orla_0_4 or "",
                materia.coresp_orla_1_0 or "",
                format_quantity(materia.comprimento),
                format_quantity(materia.largura),
                format_quantity(materia.espessura),
                "Sim" if materia.ativo else "N\u00e3o",
            ]

            riscado = not materia.ativo
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                if riscado:
                    # Descontinuado: risco por cima e cinzento, como o Ctrl+5 do
                    # Excel. A coluna "Ativo" fica leg\u00edvel, sem risco.
                    if column_index != len(values) - 1:
                        fonte = item.font()
                        fonte.setStrikeOut(True)
                        item.setFont(fonte)
                    item.setForeground(QColor(tema.CINZA_ESCURO))
                self.table.setItem(row_index, column_index, item)

            self._pintar_avisos(row_index, materia)

        if (
            not self._larguras_restauradas
            and not self._larguras_seed_feito
            and materias_primas
        ):
            self.table.resizeColumnsToContents()
            self._larguras_seed_feito = True

    def _texto_preco(self, materia: DefMateriaPrimaResumo) -> str:
        """Preço líquido, ou a menção de que é escrito no orçamento."""
        if materia.tipo_preco == TIPO_PRECO_LIVRE:
            return "preço livre"

        return format_currency(materia.preco_liquido)

    def _texto_data_preco(self, materia: DefMateriaPrimaResumo) -> str:
        if materia.data_ultimo_preco is None:
            return ""

        return f"{materia.data_ultimo_preco:%d-%m-%Y}"

    def _texto_stock(self, materia: DefMateriaPrimaResumo) -> str:
        if materia.stock is None:
            return ""

        return "Sim" if materia.stock else "Não"

    def _pintar_avisos(self, row_index: int, materia: DefMateriaPrimaResumo) -> None:
        """As mesmas cores do Excel: preço em falta a vermelho, preço velho a âmbar."""
        if preco_em_falta(materia):
            item = self.table.item(row_index, self.COLUNA_PRECO_LIQUIDO)
            if item is not None:
                item.setBackground(QColor(tema.VERMELHO_SUAVE))
                item.setToolTip(
                    "Sem preço: este material entra no custeio a 0,00 €. "
                    "Preencha o preço de tabela, ou marque-o como preço livre."
                )

        if preco_desatualizado(materia):
            item = self.table.item(row_index, self.COLUNA_ULTIMO_PRECO)
            if item is not None:
                item.setBackground(QColor(tema.OCRE_SUAVE))
                item.setToolTip(
                    f"Preço com mais de {MESES_PRECO_DESATUALIZADO} meses — deve ser revisto."
                )


def normalize_search_text(value: object) -> str:
    """Normalize text for accent-insensitive, case-insensitive search."""
    if value is None:
        return ""

    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def materia_matches_search(materia: DefMateriaPrimaResumo, search_text: str) -> bool:
    """Return whether a raw material matches all search tokens."""
    tokens = normalize_search_text(search_text).split()
    if not tokens:
        return True

    searchable_text = normalize_search_text(
        " ".join(
            [
                materia.ref_le or "",
                materia.descricao,
                materia.tipo_original_excel or "",
                materia.familia_original_excel or "",
                materia.unidade or "",
                materia.fornecedor or "",
            ]
        )
    )

    return all(token in searchable_text for token in tokens)
