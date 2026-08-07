"""Detail page for one ValueSet model and its lines."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.domain.numeros import formatar_percentagem
from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaResumo
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo
from app.services.def_operacao_service import DefOperacaoService
from app.services.def_valueset_modelo_service import (
    CriarDefValuesetModeloData,
    DefValuesetModeloService,
)
from app.services.def_valueset_modelo_linha_operacao_service import (
    DefValuesetModeloLinhaOperacaoService,
)
from app.services.def_valueset_modelo_linha_service import (
    CriarDefValuesetModeloLinhaData,
    DefValuesetModeloLinhaService,
    EditarDefValuesetModeloLinhaData,
)
from app.services.def_valueset_operacao_propagacao_service import (
    DefValuesetOperacaoPropagacaoService,
)
from app.ui.dialogs.atualizar_precos_valueset_dialog import AtualizarPrecosValuesetDialog
from app.ui.dialogs.def_valueset_modelo_dialog import DefValuesetModeloDialog
from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog
from app.ui.dialogs.propagar_operacoes_valueset_modelo_dialog import (
    PropagarOperacoesValuesetModeloDialog,
)
from app.ui.helpers.erros import mensagem_erro_bd
from app.ui.helpers.valueset_prioridades import (
    avisar_prioridade_repetida_apos_colagem,
)
from app.ui.helpers.valueset_precos import (
    atualizacoes_de_divergencias,
    detetar_divergencias_valueset,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.estilo_tabela_valueset import (
    aplicar_estilo_item_valueset,
    configurar_tabela_valueset,
    preparar_linhas_valueset,
    texto_ativo_valueset,
    texto_chave_valueset,
    texto_editado_valueset,
    texto_opcao_valueset,
    texto_prioridade_valueset,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency


class DefValuesetModeloDetailPage(QWidget):
    """Detail page showing one ValueSet model and managing its lines."""

    # Partilhado entre instâncias para permitir copiar de um modelo e colar
    # noutro depois de regressar à lista.
    _copied_snapshot: dict | None = None
    _copied_operacoes: list | None = None

    LINHA_HEADERS = [
        "Chave",
        "Opção",
        "Ref LE",
        "Descrição orçamento",
        "Unidade",
        "Preço tabela",
        "Margem %",
        "Desconto %",
        "Preço líquido",
        "Desp %",
        "Tipo",
        "Família",
        "Prioridade",
        "Ordem",
        "Editado localmente",
        "Ativo",
        "Operações",
    ]

    def __init__(
        self,
        modelo: DefValuesetModeloResumo,
        on_back: Callable[[], None] | None = None,
        on_modelo_duplicado: Callable[[DefValuesetModeloResumo, str], None] | None = None,
    ) -> None:
        super().__init__()

        self.modelo = modelo
        self.on_back = on_back
        self.on_modelo_duplicado = on_modelo_duplicado
        self._linhas_by_row: dict[int, DefValuesetModeloLinhaResumo] = {}
        self._operacoes_por_linha: dict[int, str] = {}

        self.cabecalho = BarraCabecalho(
            f"Modelo ValueSet: {modelo.nome}",
            [f"Configurações > Modelos ValueSet > {modelo.nome}"],
        )

        form = QFormLayout()
        for label, value in [
            ("Código", modelo.codigo),
            ("Nome", modelo.nome),
            ("Tipo", modelo.tipo or ""),
            ("Âmbito", modelo.ambito),
            ("Ativo", self._format_bool(modelo.ativo)),
        ]:
            form.addRow(f"{label}:", QLabel(value))

        self.new_button = QPushButton("Nova Linha")
        self.new_button.clicked.connect(self.abrir_nova_linha)
        self.edit_button = QPushButton("Editar Linha")
        self.edit_button.clicked.connect(self.abrir_editar_linha)
        self.copy_button = QPushButton("Copiar Dados")
        self.copy_button.setToolTip(
            "Copiar prioridade, dados de material e operações da linha selecionada (Ctrl+C)."
        )
        self.copy_button.clicked.connect(self.copiar_dados)
        self.paste_button = QPushButton("Colar Dados")
        self.paste_button.setToolTip(
            "Colar numa linha existente, mantendo chave, opção e estrutura do destino (Ctrl+V)."
        )
        self.paste_button.clicked.connect(self.colar_dados)
        self.propagate_operations_button = QPushButton("Propagar Operações…")
        self.propagate_operations_button.setToolTip(
            "Selecionar outras linhas com a mesma chave e Ref LE e substituir as operações."
        )
        self.propagate_operations_button.clicked.connect(self.propagar_operacoes)
        self.toggle_button = QPushButton("Ativar/Desativar")
        self.toggle_button.clicked.connect(self.alternar_linha_ativa)
        self.subir_button = QPushButton("↑")
        self.subir_button.setToolTip(
            "Mover as linhas selecionadas uma posição para cima "
            "(Ctrl/Shift para escolher várias)"
        )
        self.subir_button.clicked.connect(lambda: self.mover_linha(para_cima=True))
        self.descer_button = QPushButton("↓")
        self.descer_button.setToolTip(
            "Mover as linhas selecionadas uma posição para baixo "
            "(Ctrl/Shift para escolher várias)"
        )
        self.descer_button.clicked.connect(lambda: self.mover_linha(para_cima=False))
        self.agrupar_button = QPushButton("Agrupar por chave")
        self.agrupar_button.setToolTip(
            "Voltar a arrumar todas as linhas por chave (e por prioridade dentro "
            "de cada chave), desfazendo a ordenação feita com as setas."
        )
        self.agrupar_button.clicked.connect(self.agrupar_por_chave)
        self.mostrar_inativas_check = QCheckBox("Mostrar inativas")
        self.mostrar_inativas_check.stateChanged.connect(
            lambda _=0: self.carregar_linhas()
        )
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_linhas)
        self.check_prices_button = QPushButton("Verificar preços…")
        self.check_prices_button.clicked.connect(self.verificar_precos)
        self.back_button = QPushButton("Voltar à lista")
        self.back_button.clicked.connect(self._handle_back)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.copy_button)
        actions_layout.addWidget(self.paste_button)
        actions_layout.addWidget(self.propagate_operations_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.subir_button)
        actions_layout.addWidget(self.descer_button)
        actions_layout.addWidget(self.agrupar_button)
        actions_layout.addWidget(self.mostrar_inativas_check)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addWidget(self.check_prices_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.back_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("defValuesetModeloDetailStatus")

        self.table = QTableWidget(0, len(self.LINHA_HEADERS))
        self.table.setHorizontalHeaderLabels(self.LINHA_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Várias linhas de cada vez (Ctrl/Shift), para as mover em bloco.
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self._larguras_iniciais_aplicadas = False
        self.table.cellDoubleClicked.connect(self._handle_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._abrir_menu_contexto)
        self._instalar_atalhos_clipboard()
        # Restaura larguras guardadas; se restaurou, salta o seed por conteúdo.
        if ligar_persistencia_larguras(self.table, "valueset_modelo"):
            self._larguras_iniciais_aplicadas = True
        configurar_tabela_valueset(self.table, "valueset_modelo")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(form)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_linhas()

    def carregar_linhas(self) -> None:
        """Load the model lines into the table."""
        timer = getattr(self, "_prioridade_flash_timer", None)
        if timer is not None:
            timer.stop()
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                linhas = DefValuesetModeloLinhaService(session).listar_linhas_do_modelo(
                    self.modelo.id
                )
                operacao_service = DefValuesetModeloLinhaOperacaoService(session)
                operacoes = {
                    operacao.id: operacao.codigo
                    for operacao in DefOperacaoService(session).listar_operacoes()
                }
                self._operacoes_por_linha = {}
                for linha in linhas:
                    ligacoes = operacao_service.listar_operacoes_ativas_da_linha(
                        linha.id
                    )
                    self._operacoes_por_linha[linha.id] = "; ".join(
                        operacoes.get(ligacao.def_operacao_id, f"#{ligacao.def_operacao_id}")
                        for ligacao in ligacoes
                    )
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Nao foi possivel carregar as linhas do modelo.", error)
            )
            return

        if not self.mostrar_inativas_check.isChecked():
            linhas = [linha for linha in linhas if linha.ativo]

        self._preencher(linhas)

        if not linhas:
            self.status_label.setText("Sem linhas neste modelo.")
        else:
            self._avisar_prioridades_repetidas(linhas)

    def mover_linha(self, *, para_cima: bool) -> None:
        """Move the selected line(s) one position up or down."""
        ids_selecionados = self._ids_selecionados()
        if not ids_selecionados:
            self.status_label.setText("Selecione uma linha para mover.")
            return

        try:
            with SessionLocal() as session:
                movida = DefValuesetModeloLinhaService(session).mover_linhas(
                    self.modelo.id,
                    ids_selecionados,
                    para_cima=para_cima,
                    # Só se movem entre as linhas à vista: com as inativas
                    # escondidas, trocar com uma delas não se veria.
                    ids_visiveis=self._ids_visiveis(),
                )
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível mover a linha.", error)
            )
            return

        if not movida:
            extremo = "primeira" if para_cima else "última"
            self.status_label.setText(f"A seleção já está na {extremo} posição.")
            return

        self.carregar_linhas()
        self._selecionar_linhas(ids_selecionados)
        total = len(ids_selecionados)
        self.status_label.setText(
            "Linha movida." if total == 1 else f"{total} linhas movidas."
        )

    def _ids_visiveis(self) -> list[int]:
        """Ids of the lines currently in the table, in display order."""
        return [
            linha.id
            for _row, linha in sorted(self._linhas_by_row.items())
        ]

    def _ids_selecionados(self) -> list[int]:
        """Ids of the selected lines, in display order."""
        modelo_selecao = self.table.selectionModel()
        if modelo_selecao is None:
            return []

        linhas = sorted(indice.row() for indice in modelo_selecao.selectedRows())
        if not linhas and self.table.currentRow() >= 0:
            linhas = [self.table.currentRow()]

        return [
            self._linhas_by_row[row].id for row in linhas if row in self._linhas_by_row
        ]

    def _selecionar_linhas(self, linha_ids: list[int]) -> None:
        """Keep the moved lines selected after the table is rebuilt."""
        alvos = set(linha_ids)
        modelo_selecao = self.table.selectionModel()
        if modelo_selecao is None:
            return

        modelo_selecao.clearSelection()
        flags = (
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows
        )
        for row, linha in self._linhas_by_row.items():
            if linha.id in alvos:
                modelo_selecao.select(self.table.model().index(row, 0), flags)

    def agrupar_por_chave(self) -> None:
        """Rearrange every line by key, undoing the manual ordering."""
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            "Voltar a arrumar todas as linhas por chave? A ordenação que fez "
            "com as setas é substituída.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                total = DefValuesetModeloLinhaService(session).agrupar_linhas_por_chave(
                    self.modelo.id
                )
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível arrumar as linhas.", error)
            )
            return

        self.carregar_linhas()
        self.status_label.setText(f"{total} linhas arrumadas por chave.")

    def verificar_precos(self) -> None:
        """Explicitly check model line prices against the material catalog."""
        try:
            with SessionLocal() as session:
                linhas = DefValuesetModeloLinhaService(session).listar_linhas_do_modelo(
                    self.modelo.id
                )
                divergencias = detetar_divergencias_valueset(session, linhas)
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível verificar os preços.", error)
            )
            return

        if not divergencias:
            self.status_label.setText("Sem divergências de preço.")
            return

        dialog = AtualizarPrecosValuesetDialog(divergencias, parent=self)
        if not dialog.exec():
            self.status_label.setText(self._status_precos(0, len(divergencias)))
            return

        selecionadas = dialog.selected_divergencias
        if not selecionadas:
            self.status_label.setText(self._status_precos(0, len(divergencias)))
            return

        try:
            with SessionLocal() as session:
                atualizadas = DefValuesetModeloLinhaService(
                    session
                ).atualizar_precos_linhas(atualizacoes_de_divergencias(selecionadas))
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível atualizar os preços.", error)
            )
            return

        self.carregar_linhas()
        self.status_label.setText(
            self._status_precos(atualizadas, len(divergencias) - atualizadas)
        )

    def gravar_modelo_como(self) -> None:
        """Save this ValueSet model as a new model."""
        saved_as = False
        saved_as_codigo: str | None = None
        saved_as_linhas = 0
        modelo_novo: DefValuesetModeloResumo | None = None

        def handle_save_as(form_data) -> bool:
            nonlocal saved_as, saved_as_codigo, saved_as_linhas, modelo_novo

            try:
                with SessionLocal() as session:
                    result = DefValuesetModeloService(session).duplicar_modelo(
                        self.modelo.id,
                        self._criar_modelo_data_from_form_data(form_data),
                    )
            except IntegrityError:
                dialog.set_error("Já existe um modelo com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._modelo_error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar o modelo.", error)
                )
                return False

            saved_as = True
            modelo_novo = result.modelo
            saved_as_codigo = result.modelo.codigo
            saved_as_linhas = result.linhas_copiadas
            return True

        dialog = DefValuesetModeloDialog(
            modelo=self.modelo,
            parent=self,
            on_save_as=handle_save_as,
        )
        save_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setVisible(False)

        if not dialog.exec() or not saved_as or modelo_novo is None:
            return

        mensagem = f"Modelo gravado como {saved_as_codigo}."
        if self.on_modelo_duplicado is not None:
            self.on_modelo_duplicado(modelo_novo, mensagem)
            return

        self.status_label.setText(f"{mensagem} {saved_as_linhas} linhas copiadas.")

    def _preencher(self, linhas: list[DefValuesetModeloLinhaResumo]) -> None:
        """Fill the table with model lines."""
        self._linhas_by_row = {}
        # As linhas já vêm na ordem que o utilizador arrumou (coluna Ordem);
        # re-ordenar aqui por chave desfazia o trabalho das setas.
        estados = preparar_linhas_valueset(linhas, ordenar=False)
        self.table.setRowCount(len(estados))

        for row_index, estado in enumerate(estados):
            linha = estado.linha
            self._linhas_by_row[row_index] = linha
            values = [
                texto_chave_valueset(estado),
                texto_opcao_valueset(
                    estado, linha.nome_opcao or linha.codigo_opcao or ""
                ),
                linha.ref_le or "",
                linha.descricao_no_orcamento or "",
                linha.unidade or "",
                format_currency(linha.preco_tabela),
                formatar_percentagem(linha.margem_percentagem),
                formatar_percentagem(linha.desconto_percentagem),
                format_currency(linha.preco_liquido),
                formatar_percentagem(linha.desperdicio_percentagem),
                linha.tipo_materia_prima or "",
                linha.familia_materia_prima or "",
                texto_prioridade_valueset(estado),
                str(linha.ordem),
                texto_editado_valueset(estado),
                texto_ativo_valueset(estado),
                self._operacoes_por_linha.get(linha.id, ""),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                aplicar_estilo_item_valueset(
                    item, self.LINHA_HEADERS[column_index], estado
                )
                self.table.setItem(row_index, column_index, item)

        # Seed sensible initial widths once (content-based); after that the
        # columns stay Interactive and keep the user's manual sizes on reload.
        if not self._larguras_iniciais_aplicadas and linhas:
            self.table.resizeColumnsToContents()
            self._larguras_iniciais_aplicadas = True

    def abrir_nova_linha(self) -> None:
        """Open the dialog to create a new model line."""
        self._abrir_dialog_criar_linha(success_message="Linha criada.")

    def _instalar_atalhos_clipboard(self) -> None:
        """Bind copy/paste only while the model table has focus."""
        for sequencia, handler in (
            (QKeySequence.StandardKey.Copy, self.copiar_dados),
            (QKeySequence.StandardKey.Paste, self.colar_dados),
        ):
            atalho = QShortcut(sequencia, self.table)
            atalho.setContext(Qt.ShortcutContext.WidgetShortcut)
            atalho.activated.connect(handler)

    def copiar_dados(self) -> None:
        """Copy reusable material content and detached operation snapshots."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para copiar.")
            return

        try:
            with SessionLocal() as session:
                type(self)._copied_snapshot = DefValuesetModeloLinhaService(
                    session
                ).copiar_snapshot_linha(linha.id)
                type(self)._copied_operacoes = DefValuesetModeloLinhaOperacaoService(
                    session
                ).listar_operacoes_da_linha(linha.id)
        except (SQLAlchemyError, ValueError) as error:
            type(self)._copied_snapshot = None
            type(self)._copied_operacoes = None
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível copiar os dados da linha.", error)
            )
            return

        self.status_label.setText(
            "Dados e operações da linha copiados. Selecione uma linha de destino."
        )

    def colar_dados(self) -> None:
        """Replace the selected line content, preserving its identity."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha de destino.")
            return

        snapshot = type(self)._copied_snapshot
        operacoes = type(self)._copied_operacoes
        if snapshot is None:
            self.status_label.setText("Não existem dados copiados.")
            return

        colar_operacoes = False
        total_operacoes = len(operacoes) if operacoes else 0
        if total_operacoes:
            confirm = QMessageBox.question(
                self,
                "Colar operações",
                f"A linha copiada tem {total_operacoes} operação(ões). Colar também "
                "as operações? As operações da linha de destino serão substituídas.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            colar_operacoes = confirm == QMessageBox.StandardButton.Yes

        try:
            with SessionLocal() as session:
                try:
                    DefValuesetModeloLinhaService(session).aplicar_snapshot_linha(
                        linha.id, snapshot, commit=False
                    )
                    if colar_operacoes:
                        DefValuesetModeloLinhaOperacaoService(
                            session
                        ).substituir_operacoes_de(
                            operacoes or [], linha.id, commit=False
                        )
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
        except (SQLAlchemyError, ValueError) as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível colar os dados da linha.", error)
            )
            return

        self.carregar_linhas()
        aviso_prioridade = avisar_prioridade_repetida_apos_colagem(
            self,
            table=self.table,
            headers=self.LINHA_HEADERS,
            linhas_by_row=self._linhas_by_row,
            linha_id=linha.id,
        )
        if aviso_prioridade:
            self.status_label.setText(aviso_prioridade)
            return
        if colar_operacoes:
            self.status_label.setText(
                "Dados e operações colados; a identidade da linha de destino foi mantida."
            )
        else:
            self.status_label.setText(
                "Dados colados; a identidade e as operações da linha de destino foram mantidas."
            )

    def _abrir_menu_contexto(self, pos) -> None:
        """Show the model-line actions on right click."""
        item = self.table.itemAt(pos)
        if item is not None:
            selected_rows = {
                index.row() for index in self.table.selectionModel().selectedRows()
            }
            if item.row() not in selected_rows:
                self.table.selectRow(item.row())

        menu = QMenu(self)
        menu.addAction("Editar Linha", self.abrir_editar_linha)
        menu.addAction("Copiar Dados (Ctrl+C)", self.copiar_dados)
        menu.addAction("Colar Dados (Ctrl+V)", self.colar_dados)
        menu.addAction("Propagar Operações…", self.propagar_operacoes)
        menu.addAction("Ativar/Desativar", self.alternar_linha_ativa)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def propagar_operacoes(self) -> None:
        """Preview and propagate source operations to explicit model-line targets."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione a linha de origem das operações.")
            return

        try:
            with SessionLocal() as session:
                contexto = DefValuesetOperacaoPropagacaoService(
                    session
                ).preparar_contexto(linha.id, app_session.current_user)
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível localizar os destinos.", error)
            )
            return

        if not contexto.destinos:
            self.status_label.setText(
                "Não existem outras linhas com a mesma chave ValueSet e a mesma Ref LE."
            )
            return

        dialog = PropagarOperacoesValuesetModeloDialog(contexto, parent=self)
        if not dialog.exec():
            self.status_label.setText("Propagação cancelada; nenhuma linha foi alterada.")
            return

        try:
            with SessionLocal() as session:
                resultado = DefValuesetOperacaoPropagacaoService(session).executar(
                    contexto, dialog.selected_ids, app_session.current_user
                )
        except (ValueError, PermissionError) as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível propagar as operações.", error)
            )
            return

        self.carregar_linhas()
        self.status_label.setText(
            f"Operações propagadas para {resultado.destinos_atualizados} linha(s): "
            f"{resultado.substituidas} substituída(s), "
            f"{resultado.adicionadas} adicionada(s) e "
            f"{resultado.desativadas} desativada(s)."
        )

    def _abrir_dialog_criar_linha(
        self,
        *,
        success_message: str,
    ) -> None:
        """Open a create dialog for a model line."""
        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                self._criar_linha_from_form_data(form_data)
            except (IntegrityError, ValueError) as error:
                dialog.set_error(self._linha_error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar a linha.", error)
                )
                return False

            saved = True
            return True

        dialog = DefValuesetModeloLinhaDialog(parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar_linhas()
            self.status_label.setText(success_message)

    def _criar_linha_from_form_data(self, form_data, *, copiar_operacoes_de=None):
        """Create one model line from dialog data.

        ``copiar_operacoes_de`` is the line the new one is being copied from
        ("Gravar como…"): the operations of the variant travel with it, senão a
        opção nova custeava diferente da original sem se dar por isso.
        """
        with SessionLocal() as session:
            service = DefValuesetModeloLinhaService(session)
            result = service.criar_linha(
                CriarDefValuesetModeloLinhaData(
                    def_valueset_modelo_id=self.modelo.id,
                    chave=form_data.chave,
                    codigo_opcao=form_data.codigo_opcao,
                    nome_opcao=form_data.nome_opcao,
                    ref_materia_prima=form_data.ref_materia_prima,
                    descricao_materia_prima=form_data.descricao_materia_prima,
                    valor_texto=form_data.valor_texto,
                    prioridade=form_data.prioridade,
                    ordem=form_data.ordem,
                    observacoes=form_data.observacoes,
                    ativo=form_data.ativo,
                    ref_le=form_data.ref_le,
                    descricao_no_orcamento=form_data.descricao_no_orcamento,
                    preco_tabela=form_data.preco_tabela,
                    margem_percentagem=form_data.margem_percentagem,
                    desconto_percentagem=form_data.desconto_percentagem,
                    preco_liquido=form_data.preco_liquido,
                    unidade=form_data.unidade,
                    desperdicio_percentagem=form_data.desperdicio_percentagem,
                    tipo_materia_prima=form_data.tipo_materia_prima,
                    familia_materia_prima=form_data.familia_materia_prima,
                    coresp_orla_0_4=form_data.coresp_orla_0_4,
                    coresp_orla_1_0=form_data.coresp_orla_1_0,
                    preco_orla_0_4_m2=form_data.preco_orla_0_4_m2,
                    preco_orla_1_0_m2=form_data.preco_orla_1_0_m2,
                    comp_mp=form_data.comp_mp,
                    larg_mp=form_data.larg_mp,
                    esp_mp=form_data.esp_mp,
                    origem_dados=form_data.origem_dados,
                    editado_localmente=form_data.editado_localmente,
                )
            )

            if copiar_operacoes_de is not None:
                DefValuesetModeloLinhaOperacaoService(
                    session
                ).copiar_operacoes_entre_linhas(copiar_operacoes_de, result.id)

            return result

    def _criar_modelo_data_from_form_data(self, form_data) -> CriarDefValuesetModeloData:
        """Build create-service data from model dialog data."""
        return CriarDefValuesetModeloData(
            codigo=form_data.codigo,
            nome=form_data.nome,
            descricao=form_data.descricao,
            tipo=form_data.tipo,
            ambito=form_data.ambito,
            visivel_para_todos=form_data.visivel_para_todos,
            observacoes=form_data.observacoes,
            ativo=form_data.ativo,
        )

    def abrir_editar_linha(self) -> None:
        """Open the dialog to edit the selected model line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para editar.")
            return

        saved = False
        saved_as = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    service = DefValuesetModeloLinhaService(session)
                    service.editar_linha(
                        linha.id,
                        EditarDefValuesetModeloLinhaData(
                            def_valueset_modelo_id=self.modelo.id,
                            chave=form_data.chave,
                            codigo_opcao=form_data.codigo_opcao,
                            nome_opcao=form_data.nome_opcao,
                            ref_materia_prima=form_data.ref_materia_prima,
                            descricao_materia_prima=form_data.descricao_materia_prima,
                            valor_texto=form_data.valor_texto,
                            padrao=linha.padrao,
                            prioridade=form_data.prioridade,
                            ordem=form_data.ordem,
                            observacoes=form_data.observacoes,
                            ativo=form_data.ativo,
                            ref_le=form_data.ref_le,
                            descricao_no_orcamento=form_data.descricao_no_orcamento,
                            preco_tabela=form_data.preco_tabela,
                            margem_percentagem=form_data.margem_percentagem,
                            desconto_percentagem=form_data.desconto_percentagem,
                            preco_liquido=form_data.preco_liquido,
                            unidade=form_data.unidade,
                            desperdicio_percentagem=form_data.desperdicio_percentagem,
                            tipo_materia_prima=form_data.tipo_materia_prima,
                            familia_materia_prima=form_data.familia_materia_prima,
                            coresp_orla_0_4=form_data.coresp_orla_0_4,
                            coresp_orla_1_0=form_data.coresp_orla_1_0,
                            preco_orla_0_4_m2=form_data.preco_orla_0_4_m2,
                            preco_orla_1_0_m2=form_data.preco_orla_1_0_m2,
                            comp_mp=form_data.comp_mp,
                            larg_mp=form_data.larg_mp,
                            esp_mp=form_data.esp_mp,
                            origem_dados=form_data.origem_dados,
                            editado_localmente=form_data.editado_localmente,
                        ),
                    )
            except (IntegrityError, ValueError) as error:
                dialog.set_error(self._linha_error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar a linha.", error)
                )
                return False

            saved = True
            return True

        def handle_save_as(form_data) -> bool:
            nonlocal saved_as

            try:
                self._criar_linha_from_form_data(
                    form_data, copiar_operacoes_de=linha.id
                )
            except (IntegrityError, ValueError) as error:
                dialog.set_error(self._linha_error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar a linha.", error)
                )
                return False

            saved_as = True
            return True

        dialog = DefValuesetModeloLinhaDialog(
            linha=linha,
            parent=self,
            on_save=handle_save,
            on_save_as=handle_save_as,
        )
        if dialog.exec() and saved:
            self.carregar_linhas()
            self.status_label.setText("Linha atualizada.")
        elif saved_as:
            self.carregar_linhas()
            self.status_label.setText(
                "Linha gravada como nova opção, com as operações da original."
            )
        elif dialog.operacoes_alteradas:
            self.carregar_linhas()
            self.status_label.setText("Operações da linha atualizadas.")

    def alternar_linha_ativa(self) -> None:
        """Toggle the active state of the selected model line after confirmation."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para ativar/desativar.")
            return

        acao = "desativar" if linha.ativo else "reativar"
        aviso = ""
        if linha.ativo and linha.prioridade is not None:
            aviso = " A escolha automatica desta chave passa para a proxima prioridade."
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} esta linha?{aviso}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = DefValuesetModeloLinhaService(session)
                if linha.ativo:
                    service.desativar_linha(linha.id)
                else:
                    service.ativar_linha(linha.id)
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível atualizar o estado da linha.", error)
            )
            return

        estado = "desativada" if linha.ativo else "reativada"
        self.carregar_linhas()
        self.status_label.setText(f"Linha {estado}.")

    def _get_selected_linha(self) -> DefValuesetModeloLinhaResumo | None:
        """Return the selected model line."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._linhas_by_row.get(row)

    def _handle_double_click(self, row: int, _column: int) -> None:
        """Edit a line when the user double-clicks its row."""
        self.table.selectRow(row)
        self.abrir_editar_linha()

    def _handle_back(self) -> None:
        """Return to the model list."""
        if self.on_back is not None:
            self.on_back()

    def _linha_error_message(self, error: Exception) -> str:
        """Map a service error to a friendly message."""
        if "opcao ja existe" in str(error):
            return "Já existe uma opção com esse código nesta chave."
        if isinstance(error, ValueError):
            return str(error)

        return mensagem_erro_bd(
            "Não foi possível guardar a linha. Verifique a chave e o código da opção.",
            error,
        )

    def _modelo_error_message(self, error: ValueError) -> str:
        """Map a model service error to a friendly message."""
        if "codigo ja existe" in str(error):
            return "Já existe um modelo com esse código."
        return "Não foi possível guardar o modelo."

    def _format_materia_prima(self, linha: DefValuesetModeloLinhaResumo) -> str:
        """Format the materia-prima / value cell."""
        return (
            linha.ref_materia_prima
            or linha.descricao_materia_prima
            or linha.valor_texto
            or ""
        )

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"

    def _status_precos(self, atualizados: int, mantidos: int) -> str:
        """Format the final price-update status."""
        mantido_label = "mantido" if mantidos == 1 else "mantidos"
        return f"{atualizados} preços atualizados; {mantidos} {mantido_label}."

    def _format_prioridade(self, prioridade: int | None) -> str:
        """Format the priority for display ("—" when empty)."""
        return "—" if prioridade is None else str(prioridade)

    def _avisar_prioridades_repetidas(self, linhas) -> None:
        """Soft warning when two active lines of one key share a priority."""
        contagem: dict[tuple[str, int], int] = {}
        for linha in linhas:
            if not linha.ativo or linha.prioridade is None:
                continue
            par = (linha.chave, linha.prioridade)
            contagem[par] = contagem.get(par, 0) + 1

        chaves = sorted({chave for (chave, _), total in contagem.items() if total > 1})
        if chaves:
            self.status_label.setText(
                "Aviso: prioridade repetida nas chaves: "
                + ", ".join(chaves)
                + ". O desempate é pelo id da linha."
            )
