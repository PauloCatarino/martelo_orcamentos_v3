"""Revisão de materiais e custo parcial de produção, por versão da obra."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
from app.services.user_pref_service import UserPrefService
from datetime import datetime
import re
from PySide6.QtCore import QThread, QTimer, Signal, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QKeySequence, QShortcut

from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QHeaderView,
    QFileDialog, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget, QInputDialog, QSplitter,
)
from sqlalchemy.exc import SQLAlchemyError

from app.domain import referencias_placa as refs
from app.services import analise_lista_material_service as svc
from app.services import lista_material_decisoes_service as decisoes
from app.services import pedido_material_woodstore_pdf as pedido_pdf
from app.services import analise_custo_mapeamento_service as maps
from app.services import tempos_lista_material_service as times
from app.services import streamlit_sql_service as streamlit
from app.services.placas_referencias_service import listar_referencias
from app.ui.dialogs.associar_custo_materia_prima_dialog import AssociarCustoMateriaPrimaDialog
from app.ui.dialogs.acrescentar_linha_custo_dialog import AcrescentarLinhaCustoDialog
from app.services.permission_service import (
    permissions_for_user, PERMISSAO_ANALISE_LISTA_MATERIAL,
    PERMISSAO_CUSTOS_LISTA_MATERIAL, PERMISSAO_CORRIGIR_LISTA_MATERIAL,
)
from app.services.woodstore_service import query_woodstore
from app.ui.widgets.combo_sem_scroll import ComboSemScroll
from app.ui.dialogs.procedimentos_lista_material_widget import ProcedimentosListaMaterialWidget
from app.ui.dialogs.mapear_ferragens_dialog import MapearFerragensDialog
from app.services import custo_ferragens_service as custo_ferragens
from app.services.def_maquina_service import DefMaquinaService


class _TimesWorker(QThread):
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, connection, plan, parent):
        super().__init__(parent)
        self.connection, self.plan = connection, plan

    def run(self):
        try:
            p = self.plan
            self.result.emit(times.fetch(self.connection, 2000 + int(p.year), p.order, p.version))
        except Exception:
            # Exceptions from the driver may contain connection details.
            self.failed.emit('Não foi possível consultar os tempos. Verifique a ligação Streamlit e o acesso às tabelas de histórico.')
        finally:
            self.connection = None


class AnaliseListaMaterialDialog(QDialog):
    def __init__(self, session, *, workbook_path, plan_name, cutrite_folder, user,
                 materiais_usados='', obra_info=None, parent=None):
        super().__init__(parent)
        # Texto livre do campo «Matérias usados» da obra: comparação superficial.
        self.materiais_usados = str(materiais_usados or '')
        self.obra_info = dict(obra_info or {})
        self.temp_names = {}
        self.session, self.user = session, user
        self.permissions = permissions_for_user(session, user)
        if not self.permissions.get(PERMISSAO_ANALISE_LISTA_MATERIAL):
            raise ValueError('O administrador tem de atribuir acesso à Análise da Lista Material.')
        self.path = Path(workbook_path)
        self.plan_name, self.cutrite_folder = plan_name, Path(cutrite_folder)
        self.version = svc.PlanName.parse(plan_name).version_key
        if self.path.stem != 'Lista_Material_' + self.version:
            raise ValueError('A Lista Material não corresponde à versão do plano selecionado.')
        self.analysis_ready = False
        self.applied = 0
        self.catalog = []
        self.prices = {}
        # Linhas que o utilizador tirou do custo DESTA obra (ex.: calceiro que o
        # cliente compra). O preço e o mapeamento ficam como estão para as outras.
        self.excluded = set()
        # Linhas eliminadas nesta obra (as que vêm do Excel/Cut-Rite; as acrescentadas
        # à mão, ao eliminar, desaparecem de vez).
        self.removed = set()
        self.removed_lines = []
        self.production = {}
        self.times_worker = None
        self.lines, self.plans, self.warnings = [], [], []
        self.setWindowTitle(f'Análise da Lista Material — {self.version}')
        screen = self.screen().availableGeometry()
        self.resize(int(screen.width() * .96), int(screen.height() * .92))
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        layout = QVBoxLayout(self)
        self.summary = QLabel('Validar materiais e apurar custos de produção desta versão.')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        materials = QWidget()
        ml = QVBoxLayout(materials)
        note = QLabel('Sem stock é válido. As diferenças são avisos e nunca bloqueiam o envio para Cut-Rite.\n'
                      'Material sem código no Woodstore não é cortado: escolha um código existente, ou decida '
                      '«Pedir criação no Woodstore», «Nome temporário» ou «Fora do Cut-Rite». '
                      'A referência (B3768, M6305…) é comparada com as «Matérias usados» da obra.')
        note.setWordWrap(True)
        ml.addWidget(note)
        self.material_summary = QLabel('')
        self.material_summary.setWordWrap(True)
        ml.addWidget(self.material_summary)
        self.material_table = self._table(['Material no Excel', 'Peças / linhas', 'Estado Woodstore', 'Decisão / referência proposta', 'Motivo / características', 'Materialcode encontrado', 'Esp. nominal', 'Verificação da referência'])
        ml.addWidget(self.material_table)
        material_actions = QHBoxLayout()
        self.pedido_button = self._button(
            material_actions, 'Pedido de criação no Woodstore (PDF)…', self._pedido_pdf,
            'Gerar o PDF para as compras com os materiais marcados «Pedir criação no Woodstore»: '
            'nome, espessura, peças, orlas e os materiais parecidos que já existem.')
        material_actions.addStretch()
        ml.addLayout(material_actions)
        self.tabs.addTab(materials, 'Materiais Woodstore')
        # Procedimentos manuais da LISTAGEM_CUT_RITE (analisador religado na F3).
        self.procedures = ProcedimentosListaMaterialWidget(
            session, user=user, permissions=self.permissions, workbook_path=self.path,
            obra_info=self.obra_info, catalog_provider=lambda: self.catalog,
            on_applied=self._reload, parent=self)
        self.tabs.addTab(self.procedures, 'Procedimentos da listagem')
        self.cost_table = self._table(['Categoria', 'Artigo / material', 'Comp', 'Larg', 'Esp', 'Quantidade', 'Un.', 'Referência V3 — descrição', 'Preço líquido', 'Custo €', 'Estado / data do preço'])
        # Linha da tabela → linha de custo; None é a separadora entre categorias.
        self._cost_rows = []
        self.cost_table.verticalHeader().setMinimumSectionSize(6)   # a separadora é baixa
        self.cost_table.cellClicked.connect(
            lambda row, col: self._associate() if col == 7 and self._line_at(row) else None)
        self.cost_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        # Só a quantidade e o preço das linhas acrescentadas à mão se editam aqui
        # (as outras vêm do Excel e do Cut-Rite); cada célula decide pelas flags.
        self.cost_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked
                                        | QTableWidget.EditTrigger.EditKeyPressed)
        self.cost_table.itemChanged.connect(self._cost_item_changed)
        atalho = QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), self.cost_table)
        atalho.setContext(Qt.ShortcutContext.WidgetShortcut)
        atalho.activated.connect(self._remove_lines)
        if self.permissions.get(PERMISSAO_CUSTOS_LISTA_MATERIAL):
            cost = QWidget()
            cl = QVBoxLayout(cost)
            # Rigor do custo: provisório até a obra fechar e tudo estar apurado.
            self.rigor_label = QLabel()
            self.rigor_label.setWordWrap(True)
            self.rigor_label.setTextFormat(Qt.TextFormat.RichText)
            cl.addWidget(self.rigor_label)
            self.cost_summary = QLabel()
            self.cost_summary.setWordWrap(True)
            cl.addWidget(self.cost_summary)
            cl.addWidget(self.cost_table)
            row = QHBoxLayout()
            if self.permissions.get(PERMISSAO_CORRIGIR_LISTA_MATERIAL):
                self._button(row, 'Importar custo de ferragens…', self._import_hardware,
                             'Trazer o 5_Custo_Obra_Ferragens do IMOS: dá só o preço IMOS de referência e as cavilhas '
                             '«fora da lista». As ferragens contadas são as dos separadores 1_FERRAGENS, 2_PURCH e 3_SPP.')
            self._button(row, 'Mapear ferragens passo a passo…', self._map_hardware,
                         'Percorrer uma a uma as ferragens sem preço do V3: associar à matéria-prima V3 '
                         '(fica para as próximas obras), usar o preço PHC ou o preço IMOS provisório.')
            self._button(row, 'Não considerar nesta obra / voltar a considerar', self._toggle_excluded,
                         'Tirar do custo desta obra as linhas selecionadas (p. ex. um acessório que o cliente '
                         'compra), ou voltar a pô-las. O preço e o mapeamento V3/PHC ficam para as outras obras.')
            self._button(row, 'Associar matéria-prima V3…', self._associate,
                         'Associar a linha selecionada e memorizar a correspondência de custo no V3 para próximas obras.')
            self._button(row, 'Atualizar preços do V3', self._update_prices,
                         'Recolher os preços líquidos atuais; só ficam registados ao guardar a análise.')
            self._button(row, 'Guardar análise de custos', self._save,
                         'Guardar uma nova análise com os preços, fontes e pendências, preservando as anteriores.')
            cl.addLayout(row)
            report = QHBoxLayout()
            self._button(report, 'Acrescentar linha…', self._add_line,
                         'Juntar ao custo desta obra uma linha a partir das Matérias-Primas do V3 (p. ex. ferragens '
                         'gastas a mais do que as que vêm do IMOS). Quantidade e preço editam-se com duplo clique.')
            self._button(report, 'Eliminar linhas', self._remove_lines,
                         'Tirar da tabela e do custo desta obra as linhas selecionadas (também com a tecla Delete). '
                         'As acrescentadas à mão desaparecem; as do Excel/Cut-Rite podem voltar com «Repor eliminadas».')
            self.restore_button = self._button(
                report, 'Repor eliminadas', self._restore_removed,
                'Voltar a pôr no custo as linhas do Excel/Cut-Rite que foram eliminadas nesta obra.')
            export = self._button(report, 'Inserir relatório no Excel', lambda: self._save(write_report=True),
                         'Acrescentar um relatório de custos por categoria à Lista Material, com fórmulas e pendências de produção.')
            export.setEnabled(self.permissions.get(PERMISSAO_CORRIGIR_LISTA_MATERIAL, False))
            self.category_filter = ComboSemScroll()
            self.category_filter.addItems(['Todas', *svc.CATEGORIAS_MATERIAIS])
            self.category_filter.setToolTip('Filtrar as linhas de custo por categoria; os totais mantêm toda a obra.')
            self.category_filter.currentTextChanged.connect(self._filter_costs)
            report.addWidget(self.category_filter)
            cl.addLayout(report)
            self.tabs.addTab(cost, 'Custo de produção (parcial)')
            production_tab = QWidget()
            pl = QVBoxLayout(production_tab)
            self.times_summary = QLabel('Consultar o desenho, o plano de corte e os oito setores: encomenda + modelo Streamlit = encomenda + versão Martelo. Soma todas as versões do modelo no Streamlit.')
            self.times_summary.setWordWrap(True)
            pl.addWidget(self.times_summary)
            # O custo da produção vive aqui (e não no separador do custo): horas de
            # cada setor/máquina × €/h da máquina definida no Martelo.
            self.times_table = self._table(['Setor', 'Máquina (Streamlit)', 'Horas registadas', 'Horas estimadas',
                                            'Desvio h', '€/h', 'Custo €', 'Máquina V3 — tarifa', 'Estado'])
            self.times_table.setToolTip('Horas de cada setor e máquina do Streamlit × €/h da máquina definida em '
                                        f'{times.MENU_MAQUINAS}. Clique na coluna «Máquina V3» para escolher outra.')
            self._times_rows = []
            self.times_table.cellClicked.connect(
                lambda row, col: self._associate_machine() if col == self._COLUNA_TARIFA else None)
            self.times_splitter = QSplitter(Qt.Orientation.Vertical)
            self.times_splitter.setChildrenCollapsible(False)
            self.times_splitter.setToolTip('Arraste a divisória para ajustar a altura das tabelas.')
            self.times_splitter.addWidget(self.times_table)
            pl.addWidget(self.times_splitter)
            self.events_table = self._table(['Data', 'Setor', 'Máquina', 'Pessoa / login', 'Horas', 'Chave Streamlit', 'Plano de corte'])
            self.times_splitter.addWidget(self.events_table)
            actions_times = QHBoxLayout()
            self.times_button = self._button(actions_times, 'Consultar / atualizar tempos Streamlit', self._query_times,
                'Consultar apenas este ano, encomenda e modelo. Substitui os tempos desta análise; mantém as tarifas guardadas.')
            self._button(actions_times, 'Associar máquina V3…', self._associate_machine,
                         'Escolher a máquina do Martelo (e o seu €/h) para a linha selecionada. O nome do Streamlit '
                         f'fica memorizado nessa máquina ({times.MENU_MAQUINAS}) para as próximas obras.')
            pl.addLayout(actions_times)
            self.times_status = QLabel('Tempos ainda não consultados. Horas por pessoa são lançamentos, não duração automática da máquina.')
            self.times_status.setWordWrap(True)
            pl.addWidget(self.times_status)
            self.tabs.addTab(production_tab, 'Tempos por setor')
        actions = QHBoxLayout()
        self._button(actions, 'Reanalisar ficheiros', self._reload,
                     'Reler o Excel guardado, o Woodstore e os planos desta versão. Seleções ainda não aplicadas são reiniciadas.')
        self.apply_button = self._button(actions, 'Aplicar materiais selecionados', self._apply,
                                        'Guardar uma cópia anterior e corrigir apenas a coluna Material, com registo das alterações.')
        self.apply_button.setEnabled(self.permissions.get(PERMISSAO_CORRIGIR_LISTA_MATERIAL, False))
        self._button(actions, 'Fechar', self.accept, 'Fechar a análise; o envio para Cut-Rite continua disponível.')
        layout.addLayout(actions)
        self.status = QLabel('A preparar a análise…')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self._reload()
        self._restore_layout()

    @staticmethod
    def _decimal(value):
        number = svc.number(value)
        return f'{number:.2f}' if number is not None else str(value or '')

    def _layout_tables(self):
        return {name: getattr(self, name) for name in ('material_table', 'cost_table', 'times_table', 'events_table') if hasattr(self, name)}

    def _restore_layout(self):
        try:
            raw = UserPrefService(self.session).obter_valor(getattr(self.user, 'id', 0), 'analise_lista_material_layout', '{}')
            data = json.loads(raw or '{}')
            for name, widths in data.get('columns', {}).items():
                table = self._layout_tables().get(name)
                if table is not None and len(widths) == table.columnCount():
                    for col, width in enumerate(widths):
                        table.setColumnWidth(col, max(35, min(1500, int(width))))
                    table.setProperty('layout_ready', True)
            if hasattr(self, 'times_splitter') and data.get('splitter'):
                self.times_splitter.setSizes(data['splitter'])
        except Exception:
            self.status.setText('Não foi possível recuperar a disposição pessoal das tabelas.')

    def _save_layout(self):
        try:
            data = {'columns': {name: [table.columnWidth(c) for c in range(table.columnCount())] for name, table in self._layout_tables().items()},
                    'splitter': self.times_splitter.sizes() if hasattr(self, 'times_splitter') else []}
            UserPrefService(self.session).guardar_valor(getattr(self.user, 'id', 0), 'analise_lista_material_layout', json.dumps(data))
        except Exception:
            self.session.rollback()
            self.status.setText('Não foi possível guardar a disposição pessoal das tabelas.')

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    @staticmethod
    def _button(layout, label, callback, tooltip):
        button = QPushButton(label)
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def _allowed(self, permission):
        if not permissions_for_user(self.session, self.user).get(permission):
            raise ValueError('O administrador não atribuiu a permissão necessária.')
        self._allowed_module()

    def _allowed_module(self):
        if not permissions_for_user(self.session, self.user).get(PERMISSAO_ANALISE_LISTA_MATERIAL):
            raise ValueError('Sem acesso ao módulo Análise da Lista Material.')

    def _error(self, error):
        self.status.setText(str(error))
        QMessageBox.warning(self, 'Análise da Lista Material', str(error))

    def _reload(self):
        if self.times_worker and self.times_worker.isRunning():
            self.status.setText('Aguarde a consulta de tempos antes de reanalisar os ficheiros.')
            return
        self.analysis_ready = False
        self.status.setText('A ler Excel, Woodstore e resultados Cut-Rite…')
        QApplication.processEvents()
        try:
            self._allowed_module()
            before = svc.fingerprint(self.path)
            rows = svc.read_material_inputs(self.path)
            self.workbook_hash = svc.fingerprint(self.path)
            if before != self.workbook_hash:
                raise ValueError('O Excel mudou durante a leitura. Repita a análise.')
            self.woodstore_error = ''
            try:
                self.catalog = query_woodstore(self.session)
                if not any(str(r.get('Codigo') or '').strip() for r in self.catalog):
                    self.woodstore_error = 'Catálogo sem Materialcode; não foi possível validar.'
            except RuntimeError as exc:
                self.catalog = []
                self.woodstore_error = str(exc)
            self._materials(rows)
            if self.permissions.get(PERMISSAO_CUSTOS_LISTA_MATERIAL):
                self._load_costs()
            if svc.fingerprint(self.path) != self.workbook_hash:
                raise ValueError('O Excel mudou durante a análise. Volte a analisar.')
            self.analysis_ready = True
            self.status.setText(self.woodstore_error or 'Análise concluída. Reveja as propostas antes de aplicar. O envio para Cut-Rite não é bloqueado.')
        except Exception as exc:
            self.apply_button.setEnabled(False)
            self._error(exc)

    # Cores das linhas: iguais em claro e escuro porque o texto é escuro.
    _COR_POR_DECIDIR = QColor('#F6D3CE')
    _COR_ALERTA = QColor('#F9DDA8')
    _COR_AVISO = QColor('#FFF3CF')

    def _materials(self, rows):
        self.rows = rows
        counts = Counter(r.material for r in rows)
        pieces = Counter()
        thicknesses = {}
        for row in rows:
            pieces[row.material] += row.quantity or 0
            # Esp inclui tolerâncias da máquina (ex.: 19.2). Esp.Mat é nominal.
            esp = svc.nominal_thickness(row.values.get('Esp.Mat'))
            if esp is None:
                esp = svc.nominal_thickness(svc.material_traits(row.material)[1])
            if esp is None:
                esp = svc.nominal_thickness(row.values.get('Esp'))
            if esp is not None:
                thicknesses.setdefault(row.material, set()).add(esp)
        codes = {str(r.get('Codigo') or '').strip() for r in self.catalog} - {''}
        code_list = sorted(codes)
        self.decisions = decisoes.ler(self.path)
        self.choices = {}
        self.temp_names = {}
        validated = missing = decided = alerts = 0
        can_fix = self.permissions.get(PERMISSAO_CORRIGIR_LISTA_MATERIAL, False)
        self.material_table.setRowCount(len(counts))
        for i, (material, count) in enumerate(sorted(counts.items())):
            found = material in codes and not self.woodstore_error
            decision = self.decisions.get(material) if not found else None
            if self.woodstore_error:
                state = 'Não foi possível validar'
            elif found:
                state = 'Código igual — validado'
                validated += 1
            elif decision:
                state = 'Sem código no Woodstore — decidido: ' + decisoes.descricao(decision)
                missing += 1
                decided += 1
            else:
                state = 'Não encontrado — decidir: criar no Woodstore, nome temporário ou fora do Cut-Rite'
                missing += 1
            for col, text in enumerate((material, f'{pieces[material]} / {count}', state)):
                item = QTableWidgetItem(str(text))
                item.setToolTip(str(text))
                self.material_table.setItem(i, col, item)
            values = thicknesses.get(material, set())
            self.material_table.setItem(i, 5, QTableWidgetItem(material if found else '—'))
            self.material_table.setItem(i, 6, QTableWidgetItem(' / '.join(str(v) for v in sorted(values))))

            # Verificação da referência: contra «Matérias usados» (alerta) e
            # contra o Woodstore (só informação: há refs parecidas a mais).
            check = refs.comparar_com_materiais_usados(material, self.materiais_usados)
            nearby = refs.vizinhas_no_woodstore(material, code_list) if code_list else []
            check_text = check.mensagem
            if nearby:
                check_text += ' · Parecidas no Woodstore: ' + ', '.join(
                    ' '.join(sorted(refs.referencias(c))) for c in nearby[:3])
            check_item = QTableWidgetItem(check_text)
            check_item.setToolTip(check.mensagem + (
                '\n\nMesma espessura, ref parecida no Woodstore (confirmar que escolheu a certa):\n  '
                + '\n  '.join(nearby) if nearby else ''))
            if check.nivel == refs.ALERTA:
                alerts += 1
                check_item.setBackground(self._COR_ALERTA)
            elif check.nivel == refs.AVISO:
                check_item.setBackground(self._COR_AVISO)
            self.material_table.setItem(i, 7, check_item)

            combo = ComboSemScroll()
            combo.setToolTip('Manter o nome atual, trocar por um código do Woodstore ou decidir o que '
                             'fazer a um material sem código. Nunca se aplica automaticamente.')
            combo.addItem('Manter material atual', None)
            single = next(iter(values)) if len(values) == 1 else None
            offered = set()
            if not found and not self.woodstore_error and len(values) <= 1:
                for code in refs.mesma_referencia_no_woodstore(material, code_list):
                    combo.addItem(code, {'code': code, 'reason': 'Mesma referência e espessura no Woodstore — '
                                         'pode ser só o nome escrito de outra forma.'})
                    offered.add(code)
                for candidate in svc.material_candidates(material, self.catalog, single):
                    if candidate['code'] not in offered:
                        combo.addItem(candidate['code'], candidate)
                        offered.add(candidate['code'])
            if check.sugeridas and not self.woodstore_error:
                # A ref das «Matérias usados» é parecida: oferecer esses códigos.
                for code in code_list:
                    if code in offered or code == material:
                        continue
                    same_thickness = refs.espessura(code) in (None, refs.espessura(material))
                    if same_thickness and refs.referencias(code) & set(check.sugeridas):
                        combo.addItem(code, {'code': code, 'reason': 'Ref indicada nas «Matérias usados» da obra.'})
                        offered.add(code)
            if not found and not self.woodstore_error:
                combo.insertSeparator(combo.count())
                for action in (decisoes.CRIAR_WOODSTORE, decisoes.TEMPORARIO, decisoes.FORA_CUTRITE):
                    label = decisoes.ROTULOS[action] + ('…' if action == decisoes.TEMPORARIO else '')
                    combo.addItem(label, {'acao': action, 'reason': decisoes.EXPLICACOES[action]})
                # O nome temporário já está no Excel: não se volta a escolher.
                if decision and decision['acao'] != decisoes.TEMPORARIO:
                    for index in range(combo.count()):
                        if (combo.itemData(index) or {}).get('acao') == decision['acao']:
                            combo.setCurrentIndex(index)
                            break
            combo.setEnabled(can_fix and not self.woodstore_error)
            if len(values) > 1:
                reason_text = 'Espessuras diferentes no mesmo código — confirmar no Excel'
            elif found:
                reason_text = 'Excel = Materialcode Woodstore. Não necessita correção; stock não condiciona.'
            elif decision:
                reason_text = decisoes.EXPLICACOES[decision['acao']]
            else:
                reason_text = 'Sem alteração selecionada'
            reason = QTableWidgetItem(reason_text)
            reason.setToolTip(reason_text)
            self.material_table.setItem(i, 4, reason)
            combo.currentIndexChanged.connect(
                lambda _, c=combo, item=reason, m=material: self._choice_changed(m, c, item))
            self.material_table.setCellWidget(i, 3, combo)
            self.choices[material] = combo
            if not found and not decision and not self.woodstore_error:
                for col in (0, 1, 2, 5, 6):
                    self.material_table.item(i, col).setBackground(self._COR_POR_DECIDIR)
        # Colocar a prova da correspondência junto ao material de origem.
        header = self.material_table.horizontalHeader()
        header.moveSection(header.visualIndex(5), 1)
        header.moveSection(header.visualIndex(6), 2)
        header.moveSection(header.visualIndex(7), 5)
        for col, width in enumerate((280, 95, 260, 300, 340, 280, 85, 420)):
            if not self.material_table.property('layout_ready'):
                self.material_table.setColumnWidth(col, width)
        self.material_table.setProperty('layout_ready', True)
        self.apply_button.setEnabled(can_fix and not self.woodstore_error)
        self._summarise_materials(len(counts), validated, missing, decided, alerts, list(counts))

    def _summarise_materials(self, total, validated, missing, decided, alerts, materials):
        if self.woodstore_error:
            text = f'{total} materiais — Woodstore indisponível: {self.woodstore_error}'
        else:
            text = f'{total} materiais: {validated} validados no Woodstore'
            if missing:
                text += f', {missing} sem código ({decided} já decididos, {missing - decided} por decidir)'
            if alerts:
                text += f', {alerts} com referência a confirmar'
            text += '.'
        forgotten = refs.referencias_esquecidas(materials, self.materiais_usados)
        if forgotten:
            text += (f"\n«Matérias usados» refere {', '.join(forgotten)}, mas nenhuma peça da lista "
                     'usa essa referência — confirmar.')
        if not self.materiais_usados.strip():
            text += '\nO campo «Matérias usados» da obra está vazio: as referências não foram comparadas.'
        self.material_summary.setText(text)

    def _choice_changed(self, material, combo, item):
        data = combo.currentData() or {}
        text = data.get('reason', 'Sem alteração selecionada')
        if data.get('acao') == decisoes.TEMPORARIO:
            suggestion = self.temp_names.get(material) or (
                'TEMP_' + re.sub(r'[^A-Z0-9]+', '_', material.upper()).strip('_'))
            name, ok = QInputDialog.getText(
                self, 'Nome temporário',
                f'Nome temporário para «{material}» (só esta obra).\n'
                'Crie-o também no Cut-Rite para as peças serem cortadas:', text=suggestion)
            name = name.strip()
            if not ok or not name:
                self.temp_names.pop(material, None)
                combo.blockSignals(True)
                combo.setCurrentIndex(0)
                combo.blockSignals(False)
                text = 'Sem alteração selecionada'
            else:
                self.temp_names[material] = name
                text = f'Nome temporário: {name}. ' + decisoes.EXPLICACOES[decisoes.TEMPORARIO]
        item.setText(text)
        item.setToolTip(text)

    def _apply(self):
        try:
            self._allowed(PERMISSAO_CORRIGIR_LISTA_MATERIAL)
            changes, new_decisions = {}, {}
            for material, combo in self.choices.items():
                data = combo.currentData()
                if not data:
                    continue
                if data.get('code'):
                    changes[material] = data['code']
                elif data.get('acao') == decisoes.TEMPORARIO:
                    name = self.temp_names.get(material)
                    if name and name != material:
                        changes[material] = name
                        new_decisions[name] = {'acao': decisoes.TEMPORARIO, 'original': material}
                elif data.get('acao'):
                    if (self.decisions.get(material) or {}).get('acao') != data['acao']:
                        new_decisions[material] = {'acao': data['acao']}
            count = svc.apply_material_codes(self.path, self.workbook_hash, changes, self.user.username) if changes else 0
            if new_decisions:
                decisoes.gravar(self.path, new_decisions, utilizador=self.user.username)
            self.applied += count
            self._reload()
            self.status.setText(
                f'{count} células Material corrigidas, {len(new_decisions)} decisões registadas. '
                'Cópia anterior e log preservados. Custos por revalidar se a otimização mudou.')
        except Exception as exc:
            self._error(exc)

    def _pedido_pdf(self):
        try:
            self._allowed_module()
            wanted = [m for m, combo in self.choices.items()
                      if (combo.currentData() or {}).get('acao') == decisoes.CRIAR_WOODSTORE
                      or (self.decisions.get(m) or {}).get('acao') == decisoes.CRIAR_WOODSTORE]
            if not wanted:
                self.status.setText('Escolha «Pedir criação no Woodstore» num material sem código antes de gerar o pedido.')
                return
            codes = sorted({str(r.get('Codigo') or '').strip() for r in self.catalog} - {''})
            materials = []
            for material in sorted(wanted):
                rows = [r.values for r in self.rows if r.material == material]
                similar = refs.mesma_referencia_no_woodstore(material, codes)
                similar += [c['code'] for c in svc.material_candidates(material, self.catalog, refs.espessura(material))
                            if c['code'] not in similar]
                materials.append(pedido_pdf.resumir_material(material, rows, similar[:5]))
            destination = self.path.parent / f'Pedido_Material_Woodstore_{self.version}.pdf'
            info = {'plano': self.plan_name, **self.obra_info}
            pedido_pdf.gerar_pedido_pdf(destination, obra=info, materiais=materials,
                                        gerado_em=datetime.now().strftime('%d-%m-%Y %H:%M'),
                                        pedido_por=getattr(self.user, 'username', '') or 'Martelo')
            # Gerar o pedido é decidir: não voltar a avisar no envio para o Cut-Rite.
            if self.permissions.get(PERMISSAO_CORRIGIR_LISTA_MATERIAL):
                pending = {m: {'acao': decisoes.CRIAR_WOODSTORE} for m in wanted
                           if (self.decisions.get(m) or {}).get('acao') != decisoes.CRIAR_WOODSTORE}
                if pending:
                    self.decisions = decisoes.gravar(self.path, pending, utilizador=self.user.username)
            self.status.setText(f'Pedido gerado: {destination}')
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(destination)))
        except Exception as exc:
            self._error(exc)

    def _load_costs(self):
        self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
        self.mp_catalog = maps.load_catalog(self.session)
        self.mappings = maps.load_mappings(self.session)
        component_warning = ''
        try:
            self.components = maps.load_components(self.session)
        except RuntimeError as exc:
            self.components = []
            component_warning = str(exc)
        self.references = []
        reference_warning = ''
        try:
            self.references = listar_referencias(self.session)
        # SQLAlchemyError entrou aqui quando as referências passaram a vir da
        # base martelo_catalogos: se a base não existir ou não estiver
        # acessível, isto tem de degradar como sempre degradou quando faltava o
        # Excel. Sem isto o erro subia até ao QMessageBox e o diálogo abria com
        # um aviso modal por cima, em vez de abrir com uma linha de estado.
        except (RuntimeError, OSError, ValueError, SQLAlchemyError):
            reference_warning = ('Catálogo dos fornecedores indisponível; '
                                 'associação manual disponível.')
        try:
            self.plans, self.warnings = svc.discover_plans(self.cutrite_folder, self.plan_name)
        except (OSError, ValueError) as exc:
            self.plans, self.warnings = [], [str(exc)]
        extra, warnings = svc.workbook_cost_lines(self.path)
        self.warnings += warnings
        if component_warning:
            self.warnings.append(component_warning)
        if reference_warning:
            self.warnings.append(reference_warning)
        self.lines = svc.board_cost_lines(self.plans) + extra
        snapshot = svc.latest_snapshot(self.path, self.version)
        # As linhas acrescentadas à mão só existem na análise guardada.
        self.lines += [dict(line) for line in snapshot.get('manual_lines', [])]
        self.production = snapshot.get('production', {})
        # Uma linha por setor mesmo sem consulta: o €/h do Martelo vê-se sempre.
        self.lines += times.completar_setores(self.production.get('lines', []), self.production.get('sectors'))
        self.warnings.append('Produção: horas e €/h no separador Tempos por setor.')
        previous = snapshot.get('prices', {})
        self.excluded = set(snapshot.get('excluded', []))
        self.machine_catalog = self._machine_catalog()
        # A reanálise mantém os preços guardados; a atualização é uma ação distinta.
        self.prices = {line['key']: previous.get(line['key']) or previous.get(line.get('legacy_key', '')) or
                       (times.match_machine(line, self.machine_catalog) if line['kind'] == 'Produção'
                        else maps.resolve_price(line, self.mp_catalog, self.mappings, self.references, self.components))
                       for line in self.lines}
        # Eliminadas nesta obra: saem do custo e da tabela, mas podem voltar.
        self.removed = set(snapshot.get('removed', []))
        self.removed_lines = [line for line in self.lines if line['key'] in self.removed]
        self.lines = [line for line in self.lines if line['key'] not in self.removed]
        self._fill_hardware_prices()
        if snapshot and (snapshot.get('workbook_hash') != self.workbook_hash or snapshot.get('plans') != self.plans):
            self.warnings.append('Fontes alteradas desde a análise guardada; quantidades relidas e preços guardados mantidos.')
        self._render_costs()

    def _machine_catalog(self):
        """Máquinas ativas do Martelo com o €/h; vazio se a base não responder."""
        try:
            return times.machines(self.session)
        except Exception:
            self.session.rollback()
            self.warnings.append('Não foi possível ler as máquinas do Martelo; €/h da produção por apurar.')
            return []

    def _fill_hardware_prices(self, *, refresh=False):
        """Ferragens sem preço V3: 2.º PHC (só leitura), 3.º IMOS provisório."""
        pending = [line for line in self.lines if line['kind'] in custo_ferragens.CATEGORIAS_FERRAGENS
                   and (refresh or not self.prices.get(line['key']))
                   and custo_ferragens.fonte(self.prices.get(line['key'])) != custo_ferragens.FONTE_V3]
        if not pending:
            return
        if refresh or not getattr(self, 'phc', None):
            self.phc = {}
            try:
                self.phc = custo_ferragens.ler_precos_phc(self.session, [l.get('ref_phc') for l in pending])
                # Objetos comprados sem Ref PHC: procura-se pela ref do fornecedor.
                sem_ref = [l.get('supplier_ref') for l in pending if l['kind'] == 'Comprados'
                           and not custo_ferragens.refs_validas([l.get('ref_phc')])]
                self.phc.update(custo_ferragens.ler_precos_phc_por_ref_fornecedor(self.session, sem_ref))
            except Exception:
                self.warnings.append('PHC sem ligação: preços PHC não consultados (fica o preço IMOS provisório).')
        for line in pending:
            chosen = self.prices.get(line['key'])
            if chosen and chosen.get('escolha_manual'):
                continue
            self.prices[line['key']] = custo_ferragens.resolver_ferragem(line, None, self.phc)

    def _map_hardware(self):
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            pending = [line for line in self.lines if line['kind'] in custo_ferragens.CATEGORIAS_FERRAGENS
                       and line['key'] not in self.excluded
                       and custo_ferragens.fonte(self.prices.get(line['key'])) != custo_ferragens.FONTE_V3]
            if not pending:
                self.status.setText('Todas as ferragens consideradas já têm preço do V3.')
                return
            dialog = MapearFerragensDialog(
                pending, self.prices, self.mp_catalog, getattr(self, 'phc', {}), self.references,
                excluded=self.excluded,
                on_v3=lambda line, mp: maps.save_mapping(self.session, line, mp, self.user.username),
                parent=self)
            dialog.exec()
            self.mappings = maps.load_mappings(self.session)
            self._render_costs()
            self.status.setText(f'{dialog.changed} ferragens decididas. Guarde a análise para fixar os preços desta obra.')
        except Exception as exc:
            self.session.rollback()
            self._error(exc)

    def _query_times(self):
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            if self.times_worker and self.times_worker.isRunning():
                return
            connection = streamlit.build_connection_string(streamlit.load_streamlit_config(self.session))
            self.times_worker = _TimesWorker(connection, svc.PlanName.parse(self.plan_name), self)
            self.times_worker.result.connect(self._receive_times)
            self.times_worker.failed.connect(self._times_failed)
            self.times_worker.finished.connect(lambda: self.times_button.setEnabled(True))
            self.times_button.setEnabled(False)
            self.times_status.setText('A consultar o Streamlit só de leitura…')
            self.times_worker.start()
        except Exception:
            self._times_failed('Não foi possível iniciar a consulta. Verifique a configuração Streamlit.')

    def _times_failed(self, message):
        if self.production:
            self.production['last_query_error'] = message
        self.times_status.setText(message + ' Os últimos tempos, se existirem, mantêm a data da consulta anterior.')

    def _receive_times(self, data):
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            try:
                catalog = times.machines(self.session)
            except Exception:
                self.session.rollback()
                catalog = []
                data['warnings'].append('Não foi possível ler as tarifas de máquinas V3; horas disponíveis, custo por apurar.')
            self.machine_catalog = catalog
            self.production = data
            data['lines'] = times.completar_setores(data['lines'], data.get('sectors'))
            self.lines = [line for line in self.lines if line['kind'] != 'Produção'] + data['lines']
            for line in data['lines']:
                self.prices[line['key']] = self.prices.get(line['key']) or times.match_machine(line, catalog)
            self._render_costs()
            self.times_status.setText('Consulta concluída. Guarde a análise para registar tempos e tarifas. ' + ' | '.join(data['warnings']))
        except Exception as exc:
            self._error(exc)

    _COLUNA_TARIFA = 7   # «Máquina V3 — tarifa» no separador Tempos por setor

    def _render_times(self):
        if not hasattr(self, 'times_table'):
            return
        data = self.production or {}
        effective = self._effective_prices()
        self._times_rows = [line for line in self.lines if line['kind'] == 'Produção']
        sectors = {s['sector']: s for s in data.get('sectors', [])}
        total_hours, total_cost, missing = svc.Decimal(0), svc.Decimal(0), 0
        seen = set()
        self.times_table.setRowCount(len(self._times_rows))
        for r, line in enumerate(self._times_rows):
            stage = line.get('sector')
            entry = sectors.get(stage, {})
            price = effective.get(line['key'])
            hours = svc.number(line.get('quantity'))
            cost = svc.calculate_cost(line, price)[0]
            tariff, has_tariff = times.descrever_tarifa(line, price, getattr(self, 'machine_catalog', None))
            first_of_sector = stage not in seen
            seen.add(stage)
            estimated = svc.number(entry.get('estimated')) if first_of_sector else None
            sector_hours = svc.number(entry.get('hours'))
            if estimated is not None:
                estimate_text = f'{estimated:.2f}'
                deviation = f'{sector_hours - estimated:.2f}' if sector_hours is not None else '—'
            else:
                estimate_text = ('Não disponível' if first_of_sector and data else '')
                deviation = '—' if first_of_sector else ''
            total_hours += hours or 0
            total_cost += cost or 0
            if hours != 0 and not has_tariff:
                missing += 1
            label = times.ROTULOS.get(stage, line['name'])
            values = (label if first_of_sector else '', line.get('machine') or '—',
                      f'{hours:.2f}' if hours is not None else 'Por apurar', estimate_text, deviation,
                      self._decimal((price or {}).get('net')) if (price or {}).get('net') is not None else '—',
                      f'{cost:.2f}' if cost is not None else '—', tariff,
                      entry.get('state') or ('Tempos não consultados' if not data else 'Estado por confirmar'))
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                if c == self._COLUNA_TARIFA and not has_tariff and hours != 0:
                    item.setBackground(self._COR_POR_DECIDIR)
                    item.setToolTip(str(value) + '\n\nClique para escolher a máquina do Martelo.')
                self.times_table.setItem(r, c, item)
        consulta = (f"Encomenda {data['order']} · modelo {data['model']} · ano {data['year']} · versões Streamlit: "
                    f"{', '.join(data['versions']) or 'nenhuma'} · consulta {data['queried_at']}" if data
                    else 'Tempos Streamlit ainda não consultados — as horas podem ser escritas à mão no Excel.')
        self.times_summary.setText(
            f'{consulta}\nProdução: {total_hours:.2f} h registadas · {total_cost:.2f} € ao €/h das máquinas do Martelo'
            + (f' · {missing} linha(s) sem €/h — associe a máquina ou crie-a em {times.MENU_MAQUINAS}'
               if missing else ''))
        events = data.get('events', [])
        self.events_table.setRowCount(len(events))
        for r, e in enumerate(events):
            for c, value in enumerate((e.get('data_registo'), e['setor'], e.get('maquina'), e.get('responsavel'),
                                       self._decimal(e['horas']) if e['horas'] is not None else 'Inválido', e['bd_key'], e.get('bd_plano_corte'))):
                item = QTableWidgetItem(str(value or ''))
                item.setToolTip(item.text())
                self.events_table.setItem(r, c, item)
        for table in (self.times_table, self.events_table):
            if not table.property('layout_ready') and table.rowCount():
                table.resizeColumnsToContents()
                table.setProperty('layout_ready', True)
                if table is self.times_table:
                    # A mensagem «sem €/h» é comprida: lê-se inteira na dica.
                    table.setColumnWidth(self._COLUNA_TARIFA, min(table.columnWidth(self._COLUNA_TARIFA), 460))
        if data.get('last_query_error'):
            self.times_status.setText(data['last_query_error'] + ' A mostrar a consulta guardada de ' + data['queried_at'])

    def done(self, result):
        if self.times_worker and self.times_worker.isRunning():
            self.times_status.setText('Aguarde a conclusão da consulta antes de fechar.')
            return
        self._save_layout()
        super().done(result)

    def closeEvent(self, event):
        if self.times_worker and self.times_worker.isRunning():
            event.ignore()
            return
        super().closeEvent(event)

    def _effective_prices(self):
        """Os preços que contam: as linhas não consideradas nesta obra valem 0."""
        return {line['key']: custo_ferragens.preco_excluido(line) if line['key'] in self.excluded
                else self.prices.get(line['key']) for line in self.lines}

    def _line_at(self, row):
        """A linha de custo desta linha da tabela (None na separadora)."""
        return self._cost_rows[row] if 0 <= row < len(self._cost_rows) else None

    def _cost_row_of(self, line):
        return next((i for i, other in enumerate(self._cost_rows) if other is line), -1)

    def _toggle_excluded(self):
        rows = sorted({i.row() for i in self.cost_table.selectionModel().selectedRows()}
                      or ({self.cost_table.currentRow()} - {-1}))
        lines = [line for line in (self._line_at(row) for row in rows) if line is not None]
        if not lines:
            self.status.setText('Selecione as linhas a tirar ou a voltar a pôr no custo desta obra.')
            return
        for line in lines:
            self.excluded.symmetric_difference_update({line['key']})
        self._render_costs()
        self.status.setText(f'{len(lines)} linha(s) alterada(s). Guarde a análise para fixar nesta obra; '
                            'os mapeamentos não mudam.')

    # Linha vazia entre categorias (pedido do Paulo, 24-09-2026), num tom acastanhado.
    _COR_SEPARADOR = QColor('#DDD3C9')

    # Colunas da tabela do custo que se editam nas linhas acrescentadas à mão.
    _COL_QUANTIDADE, _COL_PRECO = 5, 8
    _COR_EDITAVEL = QColor('#FFF2CC')   # o amarelo das células alteráveis no Excel

    def _render_costs(self):
        # Escrever as células não é uma edição do utilizador: sem itemChanged.
        self.cost_table.blockSignals(True)
        try:
            self._render_costs_sem_sinais()
        finally:
            self.cost_table.blockSignals(False)

    def _render_costs_sem_sinais(self):
        # A produção não entra aqui: as horas × €/h estão no separador Tempos por setor.
        self._cost_rows = svc.linhas_por_categoria(self.lines)
        self.cost_table.clearSelection()
        self.cost_table.setRowCount(len(self._cost_rows))
        total, pending = svc.Decimal(0), 0
        effective = self._effective_prices()
        altura = self.cost_table.verticalHeader().defaultSectionSize()
        numeros = []
        for i, line in enumerate(self._cost_rows):
            if line is None:
                numeros.append('')
                for col in range(self.cost_table.columnCount()):
                    item = QTableWidgetItem('')
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    item.setBackground(self._COR_SEPARADOR)
                    self.cost_table.setItem(i, col, item)
                self.cost_table.setRowHeight(i, 8)
                continue
            numeros.append(str(len(numeros) - numeros.count('') + 1))
            self.cost_table.setRowHeight(i, altura)
            price = effective.get(line['key'])
            cost, state = svc.calculate_cost(line, price)
            if line['key'] in self.excluded:
                state = 'NÃO CONSIDERADA NESTA OBRA'
            if cost is None:
                pending += 1
            else:
                total += cost
            detail = line['name'] + (f" ({line.get('size')})" if line.get('size') else '')
            ref = ' — '.join(str((price or {}).get(k) or '') for k in ('ref','description')) if price else 'Clique para associar…'
            manual = bool(line.get('manual'))
            if manual:
                state += f" · acrescentada à mão{' por ' + line['added_by'] if line.get('added_by') else ''}"
            values = (line['kind'], detail, self._decimal(line.get('length','')), self._decimal(line.get('width','')), self._decimal(line.get('thickness','')),
                      self._decimal(line['quantity']) if line['quantity'] is not None else 'Por apurar', line['unit'], ref,
                      self._decimal((price or {}).get('net', 'Por apurar')), f'{cost:.2f}' if cost is not None else 'Por apurar',
                      state + (' · ' + price['date'] if price else '') + (' · ' + price.get('mapping_source','') if price else ''))
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value) + (f"\nPlaca: {line['board']}" if col == 1 and line.get('board') else ''))
                if manual and col in (self._COL_QUANTIDADE, self._COL_PRECO):
                    item.setBackground(self._COR_EDITAVEL)
                    item.setToolTip(f'{value}\nDuplo clique para alterar (só nesta obra).')
                    # O texto mostrado: se voltar igual, não foi alterado.
                    item.setData(Qt.ItemDataRole.UserRole, str(value))
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if line['key'] in self.excluded:
                    item.setForeground(QColor('#8a8f98'))
                self.cost_table.setItem(i, col, item)
        self.cost_table.setVerticalHeaderLabels(numeros)
        # Totais da obra: materiais + produção (esta vem do separador dos tempos).
        production_cost = svc.Decimal(0)
        for line in self.lines:
            if line['kind'] == 'Produção':
                cost = svc.calculate_cost(line, effective.get(line['key']))[0]
                if cost is not None:
                    total += cost
                    production_cost += cost
        board_area = sum((svc.Decimal(p['total']) for p in self.plans), svc.Decimal(0))
        categories = []
        for kind in svc.CATEGORIAS_MATERIAIS:
            rows = [line for line in self.lines if line['kind'] == kind]
            costs = [svc.calculate_cost(line, effective.get(line['key']))[0] for line in rows]
            categories.append(f"{kind}: {len(rows)} linhas, {sum((v for v in costs if v is not None), svc.Decimal(0)):.2f} €")
        categories.append(f'Produção (Tempos por setor): {production_cost:.2f} €')
        state = custo_ferragens.estado_do_custo(self.obra_info.get('estado', ''), self.lines, effective,
                                                self.plans, self.production)
        self.cost_state = state
        self.rigor_label.setText(
            f"<b>{state.titulo}</b><br>" + '<br>'.join(('✓ ' if ok else '✗ ') + text for ok, text in state.pontos))
        self.rigor_label.setStyleSheet('background:#e7f6ea;padding:6px;color:#1f2328;' if state.final
                                       else 'background:#fff4d6;padding:6px;color:#1f2328;')
        manuais = sum(1 for line in self.lines if line.get('manual'))
        mao = ' · '.join(texto for n, texto in (
            (manuais, f'{manuais} linha(s) acrescentada(s) à mão'),
            (len(self.removed_lines), f'{len(self.removed_lines)} eliminada(s) nesta obra')) if n)
        if hasattr(self, 'restore_button'):
            self.restore_button.setEnabled(bool(self.removed_lines))
            self.restore_button.setText(f'Repor eliminadas ({len(self.removed_lines)})' if self.removed_lines
                                        else 'Repor eliminadas')
        self.cost_summary.setText(f'Custo {"final" if state.final else "provisório"}: {total:.2f} € · {pending} linhas de material pendentes · placas usadas: {board_area:.2f} m² · versão {self.version}\n'
                                 + ' · '.join(categories) + (f'\n{mao}' if mao else '') + '\n' +
                                 f"Planos incluídos: {', '.join(p['name'] for p in self.plans) or 'nenhum'}\n" + '\n'.join(self.warnings))
        for col, width in enumerate((85, 300, 85, 65, 60, 85, 45, 400, 100, 100, 330)):
            if not self.cost_table.property('layout_ready'):
                self.cost_table.setColumnWidth(col, width)
        self.cost_table.setProperty('layout_ready', True)
        self._filter_costs()
        self._render_times()

    def _filter_costs(self, *_):
        category = self.category_filter.currentText()
        for i, line in enumerate(self._cost_rows):
            # Com uma categoria só, as separadoras não fazem falta.
            self.cost_table.setRowHidden(i, category != 'Todas' and (line is None or line['kind'] != category))

    # ---- Linhas acrescentadas à mão e eliminadas (pedido do Paulo, 25-09-2026) ----

    def _cost_item_changed(self, item):
        line = self._line_at(item.row())
        column = item.column()
        if not line or not line.get('manual') or column not in (self._COL_QUANTIDADE, self._COL_PRECO):
            return
        texto = item.text().strip()
        if texto == item.data(Qt.ItemDataRole.UserRole):
            return
        # Nunca redesenhar a tabela dentro do commit do editor: foi isso que fechou
        # o Martelo sozinho no custeio (18-09-2026). Aplica-se a seguir.
        QTimer.singleShot(0, lambda: self._aplicar_edicao(line, column, texto))

    def _aplicar_edicao(self, line, column, texto):
        valor = svc.number(texto)
        if valor is None or valor < 0:
            self.status.setText(f'«{texto}» não é um número válido (0 ou mais, p. ex. 12 ou 0,45). Nada mudou.')
        elif column == self._COL_QUANTIDADE:
            line['quantity'] = str(valor)
            self.status.setText(f'Quantidade de «{line["name"]}» = {valor}. Guarde a análise para fixar nesta obra.')
        else:
            self.prices[line['key']] = svc.preco_escrito_a_mao(self.prices.get(line['key']), valor)
            self.status.setText(f'Preço de «{line["name"]}» = {valor} € — só nesta obra; «Atualizar preços do V3» '
                                'não lhe mexe. Guarde a análise para o fixar.')
        self._render_costs()

    def _selected_lines(self):
        rows = sorted({i.row() for i in self.cost_table.selectionModel().selectedRows()}
                      or ({self.cost_table.currentRow()} - {-1}))
        return [line for line in (self._line_at(row) for row in rows) if line is not None]

    def _add_line(self, *_):
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            filtro = self.category_filter.currentText()
            atual = self._line_at(self.cost_table.currentRow())
            categoria = filtro if filtro != 'Todas' else (atual['kind'] if atual else 'Ferragens')
            dialog = AcrescentarLinhaCustoDialog(self.mp_catalog, categoria=categoria,
                                                 utilizador=getattr(self.user, 'username', ''), parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.line:
                return
            self.lines.append(dialog.line)
            self.prices[dialog.line['key']] = dialog.price
            self._render_costs()
            row = self._cost_row_of(dialog.line)
            if row >= 0:
                self.cost_table.selectRow(row)
                self.cost_table.scrollToItem(self.cost_table.item(row, 0))
            self.status.setText(f'Linha «{dialog.line["name"]}» acrescentada em {dialog.line["kind"]}. Quantidade e '
                                'preço alteram-se com duplo clique; guarde a análise para a fixar nesta obra.')
        except Exception as exc:
            self._error(exc)

    def _remove_lines(self, *_):
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            lines = self._selected_lines()
            if not lines:
                self.status.setText('Selecione as linhas a eliminar do custo desta obra.')
                return
            manuais = [line for line in lines if line.get('manual')]
            avisos = []
            if manuais:
                avisos.append(f'{len(manuais)} acrescentada(s) à mão desaparece(m) de vez.')
            if len(lines) > len(manuais):
                avisos.append(f'{len(lines) - len(manuais)} do Excel/Cut-Rite fica(m) guardada(s) como eliminada(s) '
                              'e pode(m) voltar com «Repor eliminadas».')
            resposta = QMessageBox.question(
                self, 'Eliminar linhas do custo',
                f'Eliminar {len(lines)} linha(s) do custo desta obra?\n\n' + '\n'.join(avisos),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if resposta != QMessageBox.StandardButton.Yes:
                return
            keys = {line['key'] for line in lines}
            self.lines = [line for line in self.lines if line['key'] not in keys]
            for line in lines:
                if not line.get('manual'):
                    self.removed.add(line['key'])
                    self.removed_lines.append(line)
            self._render_costs()
            self.status.setText(f'{len(lines)} linha(s) eliminada(s) do custo. Guarde a análise para fixar nesta obra.')
        except Exception as exc:
            self._error(exc)

    def _restore_removed(self, *_):
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            if not self.removed_lines:
                self.status.setText('Não há linhas eliminadas nesta obra.')
                return
            quantas = len(self.removed_lines)
            self.lines += self.removed_lines
            self.removed_lines, self.removed = [], set()
            self._render_costs()
            self.status.setText(f'{quantas} linha(s) de volta ao custo. Guarde a análise para fixar nesta obra.')
        except Exception as exc:
            self._error(exc)

    def _avisos_feitos_a_mao(self):
        """O que o relatório do Excel tem de dizer sobre as mudanças à mão."""
        avisos = []
        manuais = [line['name'] for line in self.lines if line.get('manual')]
        if manuais:
            avisos.append(f'Acrescentadas à mão nesta obra ({len(manuais)}): ' + '; '.join(manuais))
        if self.removed_lines:
            avisos.append(f'Eliminadas nesta obra ({len(self.removed_lines)}): '
                          + '; '.join(line['name'] for line in self.removed_lines))
        return avisos

    def _associate(self):
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            line = self._line_at(self.cost_table.currentRow())
            if line is None:
                self.status.setText('Selecione uma linha de custo.')
                return
            if line.get('manual'):
                self.status.setText('Linha acrescentada à mão: para outra matéria-prima, elimine-a e acrescente outra. '
                                    'A quantidade e o preço mudam-se com duplo clique.')
                return
            dialog = AssociarCustoMateriaPrimaDialog(line, self.mp_catalog, self.references, self)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected:
                maps.save_mapping(self.session, line, dialog.selected, self.user.username)
                self.mappings = maps.load_mappings(self.session)
                self.prices[line['key']] = {**svc.price_record(dialog.selected), 'mapping_source': 'Mapeamento manual guardado no V3'}
                self._render_costs()
                self.status.setText('Correspondência memorizada no V3 para próximas obras. Guarde a análise para fixar o preço desta obra.')
        except Exception as exc:
            self.session.rollback()
            self._error(exc)

    def _associate_machine(self, *_):
        """Escolher a máquina do Martelo de uma linha de horas e memorizar o nome."""
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            row = self.times_table.currentRow()
            if not 0 <= row < len(self._times_rows):
                self.times_status.setText('Selecione uma linha de horas no separador Tempos por setor.')
                return
            line = self._times_rows[row]
            catalog = times.machines(self.session)
            if not catalog:
                raise ValueError(f'Não há máquinas ativas no Martelo: crie-as em {times.MENU_MAQUINAS}.')
            labels = [f"{m['codigo']} — {m['nome']} · "
                      f"{m['custo_hora'] if m['custo_hora'] is not None else 'sem custo/hora'} €/h" for m in catalog]
            nome = line.get('machine') or times.ROTULOS.get(line.get('sector'), line['name'])
            atual = (self.prices.get(line['key']) or {}).get('machine_id')
            inicial = next((i for i, m in enumerate(catalog) if m['id'] == atual), 0)
            choice, ok = QInputDialog.getItem(
                self, 'Associar máquina V3',
                f'Máquina do Martelo para «{nome}» ({line["name"]}).\n'
                f'O nome fica memorizado nessa máquina para as próximas obras.', labels, inicial, False)
            if not ok or choice not in labels:
                return
            machine = catalog[labels.index(choice)]
            retirado = DefMaquinaService(self.session).memorizar_nome_streamlit(machine['id'], nome)
            self.machine_catalog = times.machines(self.session)
            self.prices[line['key']] = times.machine_price(machine, f'Custo/hora máquina V3 (STD), escolhida para «{nome}»')
            self._render_costs()
            self.times_status.setText(
                f'«{nome}» ligado a {machine["codigo"]} e memorizado em {times.MENU_MAQUINAS} (Nomes no Streamlit)'
                + (f'; saiu de {", ".join(retirado)}' if retirado else '')
                + '. Guarde a análise para fixar o €/h nesta obra.')
        except Exception as exc:
            self.session.rollback()
            self._error(exc)

    def _import_hardware(self):
        try:
            self._allowed(PERMISSAO_CORRIGIR_LISTA_MATERIAL)
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            sheets = svc.hardware_sheet_names(self.path)
            if sheets:
                self._reload()
                self.status.setText('Análise feita a partir do separador existente no Excel: ' + ', '.join(sheets)
                    if len(sheets) == 1 else 'Existem vários separadores de custos de ferragens. Confirme no Excel qual deve ser usado; não foram somados.')
                return
            sources = svc.hardware_sources(self.path, self.version)
            source = str(sources[0]) if len(sources) == 1 else ''
            if not source:
                source, _ = QFileDialog.getOpenFileName(self, 'Selecionar custos de ferragens desta versão',
                            str(sources[0].parent if sources else self.path.parent),
                            'Custos de ferragens (*Custo_Obra_Ferragens*.xlsx)')
            if source:
                svc.import_hardware_cost(self.path, Path(source))
                self._reload()
                self.status.setText('Ficheiro transferido para 5_Custo_Obra_Ferragens.xlsx na obra. Separador disponível no Excel.')
        except Exception as exc:
            self._error(exc)

    def _update_prices(self):
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            self.session.expire_all()
            self.mp_catalog = maps.load_catalog(self.session)
            try:
                self.components = maps.load_components(self.session)
            except RuntimeError:
                self.components = []
            by_id = {mp.id: mp for mp in self.mp_catalog}
            machine_catalog = times.machines(self.session) if any(l['kind'] == 'Produção' for l in self.lines) else []
            self.machine_catalog = machine_catalog
            for line in self.lines:
                price = self.prices.get(line['key'])
                if price and price.get('preco_manual'):
                    continue   # preço escrito à mão nesta obra: o V3 não lhe mexe
                if line.get('manual'):
                    mp = by_id.get((price or {}).get('id'))
                    if mp is not None:
                        self.prices[line['key']] = {**svc.price_record(mp), 'mapping_source': svc.ORIGEM_MANUAL}
                    continue
                if line['kind'] == 'Produção':
                    machine = next((m for m in machine_catalog if m['id'] == (price or {}).get('machine_id')), None)
                    self.prices[line['key']] = times.machine_price(machine) if machine else times.match_machine(line, machine_catalog)
                elif price and price.get('component_id'):
                    self.prices[line['key']] = maps.component_price(line, self.mp_catalog, self.components)
                elif price and price.get('id') is not None:
                    self.prices[line['key']] = svc.price_record(by_id[price['id']]) if price['id'] in by_id else None
                else:
                    # Sem id = preço PHC/IMOS ou nenhum: o V3 volta a ter prioridade.
                    self.prices[line['key']] = maps.resolve_price(line, self.mp_catalog, self.mappings, self.references, self.components)
            self._fill_hardware_prices(refresh=True)
            self._render_costs()
            self.status.setText('Preços atuais recolhidos. Guarde uma nova análise para os registar; o histórico mantém-se.')
        except Exception as exc:
            self._error(exc)

    def _save(self, _checked=False, *, write_report=False):
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            if self.times_worker and self.times_worker.isRunning():
                raise ValueError('Aguarde a consulta de tempos antes de guardar a análise.')
            if not self.analysis_ready:
                raise ValueError('Reanalise os ficheiros antes de guardar os custos.')
            if svc.fingerprint(self.path) != self.workbook_hash:
                raise ValueError('O Excel mudou. Reanalise antes de guardar os custos.')
            try:
                plans, warnings = svc.discover_plans(self.cutrite_folder, self.plan_name)
            except (OSError, ValueError):
                if self.plans:
                    raise ValueError('Não foi possível confirmar os planos. Reanalise antes de guardar.')
                plans = []
            if plans != self.plans:
                raise ValueError('Os planos Cut-Rite mudaram. Reanalise antes de guardar.')
            report_name = ''
            if write_report:
                self._allowed(PERMISSAO_CORRIGIR_LISTA_MATERIAL)
                report_name = svc.export_cost_report(self.path, self.workbook_hash, self.version, self.lines,
                                                     self._effective_prices(),
                                                     self.warnings + self._avisos_feitos_a_mao(),
                                                     production=self.production)
                self.workbook_hash = svc.fingerprint(self.path)
            destination = svc.save_snapshot(self.path, {'version': self.version, 'user': self.user.username,
                'workbook_hash': self.workbook_hash, 'plans': self.plans, 'lines': self.lines,
                'prices': self.prices, 'excluded': sorted(self.excluded),
                'manual_lines': [line for line in self.lines if line.get('manual')],
                'removed': sorted(line['key'] for line in self.removed_lines),
                'warnings': self.warnings, 'production': self.production,
                'complete': bool(getattr(self, 'cost_state', None) and self.cost_state.final)})
            self.status.setText(f'Análise guardada com preços e pendências: {destination.name}' + (f' · Relatório no Excel: {report_name}' if report_name else ''))
        except Exception as exc:
            self._error(exc)
