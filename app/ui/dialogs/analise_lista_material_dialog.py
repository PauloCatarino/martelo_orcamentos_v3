"""Revisão de materiais e custo parcial de produção, por versão da obra."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
from app.services.user_pref_service import UserPrefService
from PySide6.QtCore import QThread, Signal, Qt

from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QHeaderView,
    QFileDialog, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget, QInputDialog, QSplitter,
)
from app.services import analise_lista_material_service as svc
from app.services import analise_custo_mapeamento_service as maps
from app.services import tempos_lista_material_service as times
from app.services import streamlit_sql_service as streamlit
from app.services.placas_referencias_service import listar_referencias
from app.ui.dialogs.associar_custo_materia_prima_dialog import AssociarCustoMateriaPrimaDialog
from app.services.permission_service import (
    permissions_for_user, PERMISSAO_ANALISE_LISTA_MATERIAL,
    PERMISSAO_CUSTOS_LISTA_MATERIAL, PERMISSAO_CORRIGIR_LISTA_MATERIAL,
)
from app.services.woodstore_service import query_woodstore
from app.ui.widgets.combo_sem_scroll import ComboSemScroll


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
    def __init__(self, session, *, workbook_path, plan_name, cutrite_folder, user, parent=None):
        super().__init__(parent)
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
                      'Escolha uma referência para corrigir todas as peças com esse código, apenas nesta obra.')
        note.setWordWrap(True)
        ml.addWidget(note)
        self.material_table = self._table(['Material no Excel', 'Peças / linhas', 'Estado Woodstore', 'Referência proposta — selecionar', 'Motivo / características', 'Materialcode encontrado', 'Esp. nominal'])
        ml.addWidget(self.material_table)
        self.tabs.addTab(materials, 'Materiais Woodstore')
        self.cost_table = self._table(['Categoria', 'Artigo / material', 'Comp', 'Larg', 'Esp', 'Quantidade', 'Un.', 'Referência V3 — descrição', 'Preço líquido', 'Custo €', 'Estado / data do preço'])
        self.cost_table.cellClicked.connect(lambda row, col: self._associate() if col == 7 else None)
        if self.permissions.get(PERMISSAO_CUSTOS_LISTA_MATERIAL):
            cost = QWidget()
            cl = QVBoxLayout(cost)
            self.cost_summary = QLabel()
            self.cost_summary.setWordWrap(True)
            cl.addWidget(self.cost_summary)
            cl.addWidget(self.cost_table)
            row = QHBoxLayout()
            if self.permissions.get(PERMISSAO_CORRIGIR_LISTA_MATERIAL):
                self._button(row, 'Importar custo de ferragens…', self._import_hardware,
                             'Usar primeiro o separador do Excel. Se faltar, procurar o ficheiro na obra e depois na pasta IMOS; pedir seleção se necessário.')
            self._button(row, 'Associar matéria-prima V3…', self._associate,
                         'Associar a linha selecionada e memorizar a correspondência de custo no V3 para próximas obras.')
            self._button(row, 'Atualizar preços do V3', self._update_prices,
                         'Recolher os preços líquidos atuais; só ficam registados ao guardar a análise.')
            self._button(row, 'Guardar análise de custos', self._save,
                         'Guardar uma nova análise com os preços, fontes e pendências, preservando as anteriores.')
            cl.addLayout(row)
            report = QHBoxLayout()
            export = self._button(report, 'Inserir relatório no Excel', lambda: self._save(write_report=True),
                         'Acrescentar um relatório de custos por categoria à Lista Material, com fórmulas e pendências de produção.')
            export.setEnabled(self.permissions.get(PERMISSAO_CORRIGIR_LISTA_MATERIAL, False))
            self.category_filter = ComboSemScroll()
            self.category_filter.addItems(['Todas', 'Placas', 'Orlas', 'Ferragens', 'SPP', 'Comprados', 'Produção'])
            self.category_filter.setToolTip('Filtrar as linhas de custo por categoria; os totais mantêm toda a obra.')
            self.category_filter.currentTextChanged.connect(self._filter_costs)
            report.addWidget(self.category_filter)
            cl.addLayout(report)
            self.tabs.addTab(cost, 'Custo de produção (parcial)')
            production_tab = QWidget()
            pl = QVBoxLayout(production_tab)
            self.times_summary = QLabel('Consultar os oito setores: encomenda + modelo Streamlit = encomenda + versão Martelo. Soma todas as versões do modelo no Streamlit.')
            self.times_summary.setWordWrap(True)
            pl.addWidget(self.times_summary)
            self.times_table = self._table(['Setor', 'Horas registadas', 'Horas estimadas', 'Desvio h', 'Estado'])
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

    def _materials(self, rows):
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
        codes = {str(r.get('Codigo') or '').strip() for r in self.catalog}
        self.choices = {}
        self.material_table.setRowCount(len(counts))
        for i, (material, count) in enumerate(sorted(counts.items())):
            state = 'Código igual — validado' if material in codes else 'Não encontrado — confirmar/criar com administrador Woodstore'
            if self.woodstore_error:
                state = 'Não foi possível validar'
            for col, text in enumerate((material, f'{pieces[material]} / {count}', state)):
                item = QTableWidgetItem(str(text))
                item.setToolTip(str(text))
                self.material_table.setItem(i, col, item)
            combo = ComboSemScroll()
            combo.setToolTip('Manter o nome atual ou selecionar uma alternativa. Nunca se aplica automaticamente.')
            combo.addItem('Manter material atual', None)
            values = thicknesses.get(material, set())
            self.material_table.setItem(i, 5, QTableWidgetItem(material if material in codes and not self.woodstore_error else '—'))
            self.material_table.setItem(i, 6, QTableWidgetItem(' / '.join(str(v) for v in sorted(values))))
            candidates = svc.material_candidates(material, self.catalog, next(iter(values)) if len(values) == 1 else None)
            if material not in codes and not self.woodstore_error and len(values) <= 1:
                for candidate in candidates:
                    combo.addItem(candidate['code'], candidate)
            combo.setEnabled(self.permissions.get(PERMISSAO_CORRIGIR_LISTA_MATERIAL, False) and not self.woodstore_error)
            reason = QTableWidgetItem('Espessuras diferentes no mesmo código — confirmar no Excel' if len(values) > 1 else
                ('Excel = Materialcode Woodstore. Não necessita correção; stock não condiciona.' if material in codes and not self.woodstore_error else 'Sem alteração selecionada'))
            reason.setToolTip(reason.text())
            self.material_table.setItem(i, 4, reason)
            def describe(_, c=combo, item=reason):
                text = (c.currentData() or {}).get('reason', 'Sem alteração selecionada')
                item.setText(text)
                item.setToolTip(text)
            combo.currentIndexChanged.connect(describe)
            self.material_table.setCellWidget(i, 3, combo)
            self.choices[material] = combo
        # Colocar a prova da correspondência junto ao material de origem.
        header = self.material_table.horizontalHeader()
        header.moveSection(header.visualIndex(5), 1)
        header.moveSection(header.visualIndex(6), 2)
        for col, width in enumerate((280, 95, 200, 280, 340, 280, 85)):
            if not self.material_table.property('layout_ready'):
                self.material_table.setColumnWidth(col, width)
        self.material_table.setProperty('layout_ready', True)
        self.apply_button.setEnabled(self.permissions.get(PERMISSAO_CORRIGIR_LISTA_MATERIAL, False) and not self.woodstore_error)

    def _apply(self):
        try:
            self._allowed(PERMISSAO_CORRIGIR_LISTA_MATERIAL)
            changes = {key: combo.currentData()['code'] for key, combo in self.choices.items() if combo.currentData()}
            count = svc.apply_material_codes(self.path, self.workbook_hash, changes, self.user.username)
            self.applied += count
            self._reload()
            self.status.setText(f'{count} células Material corrigidas. Cópia anterior e log preservados. Custos por revalidar se a otimização mudou.')
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
        except (RuntimeError, OSError, ValueError) as exc:
            reference_warning = 'Catálogo de grupos EGGER indisponível; associação manual disponível.'
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
        self.production = snapshot.get('production', {})
        self.lines += self.production.get('lines', [])
        self.warnings.append('Produção parcial: consulte o separador Tempos por setor para verificar horas, estados e tarifas.')
        previous = snapshot.get('prices', {})
        # A reanálise mantém os preços guardados; a atualização é uma ação distinta.
        self.prices = {line['key']: previous.get(line['key']) or previous.get(line.get('legacy_key', '')) or
                       (None if line['kind'] == 'Produção' else maps.resolve_price(line, self.mp_catalog, self.mappings, self.references, self.components)) for line in self.lines}
        if snapshot and (snapshot.get('workbook_hash') != self.workbook_hash or snapshot.get('plans') != self.plans):
            self.warnings.append('Fontes alteradas desde a análise guardada; quantidades relidas e preços guardados mantidos.')
        self._render_costs()
        self._render_times()

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
                catalog = []
                data['warnings'].append('Não foi possível ler as tarifas de máquinas V3; horas disponíveis, custo por apurar.')
            self.production = data
            self.lines = [line for line in self.lines if line['kind'] != 'Produção'] + data['lines']
            for line in data['lines']:
                self.prices[line['key']] = self.prices.get(line['key']) or times.match_machine(line, catalog)
            self._render_times()
            self._render_costs()
            self.times_status.setText('Consulta concluída. Guarde a análise para registar tempos e tarifas. ' + ' | '.join(data['warnings']))
        except Exception as exc:
            self._error(exc)

    def _render_times(self):
        data = self.production
        if not data:
            return
        self.times_summary.setText(f"Encomenda {data['order']} · modelo {data['model']} · ano {data['year']} · versões Streamlit: {', '.join(data['versions']) or 'nenhuma'}\nConsulta: {data['queried_at']}. Horas somadas por lançamento; custo parcial até confirmar as pendências.")
        self.times_table.setRowCount(len(data['sectors']))
        for r, s in enumerate(data['sectors']):
            real, estimated = svc.number(s['hours']), svc.number(s['estimated'])
            values = (s['name'], f'{real:.2f}', f'{estimated:.2f}' if estimated is not None else 'Não disponível',
                      f'{real-estimated:.2f}' if estimated is not None else '—', s['state'])
            for c, value in enumerate(values):
                self.times_table.setItem(r, c, QTableWidgetItem(value))
        self.events_table.setRowCount(len(data['events']))
        for r, e in enumerate(data['events']):
            for c, value in enumerate((e.get('data_registo'), e['setor'], e.get('maquina'), e.get('responsavel'),
                                       self._decimal(e['horas']) if e['horas'] is not None else 'Inválido', e['bd_key'], e.get('bd_plano_corte'))):
                item = QTableWidgetItem(str(value or ''))
                item.setToolTip(item.text())
                self.events_table.setItem(r, c, item)
        for table in (self.times_table, self.events_table):
            if not table.property('layout_ready'):
                table.resizeColumnsToContents()
                table.setProperty('layout_ready', True)
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

    def _render_costs(self):
        self.cost_table.setRowCount(len(self.lines))
        total, pending = svc.Decimal(0), 0
        for i, line in enumerate(self.lines):
            price = self.prices.get(line['key'])
            cost, state = svc.calculate_cost(line, price)
            if cost is None:
                pending += 1
            else:
                total += cost
            detail = line['name'] + (f" ({line.get('size')})" if line.get('size') else '')
            ref = ' — '.join(str((price or {}).get(k) or '') for k in ('ref','description')) if price else 'Clique para associar…'
            values = (line['kind'], detail, self._decimal(line.get('length','')), self._decimal(line.get('width','')), self._decimal(line.get('thickness','')),
                      self._decimal(line['quantity']) if line['quantity'] is not None else 'Por apurar', line['unit'], ref,
                      self._decimal((price or {}).get('net', 'Por apurar')), f'{cost:.2f}' if cost is not None else 'Por apurar',
                      state + (' · ' + price['date'] if price else '') + (' · ' + price.get('mapping_source','') if price else ''))
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value) + (f"\nPlaca: {line['board']}" if col == 1 and line.get('board') else ''))
                self.cost_table.setItem(i, col, item)
        board_area = sum((svc.Decimal(p['total']) for p in self.plans), svc.Decimal(0))
        categories = []
        for kind in ('Placas','Orlas','Ferragens','SPP','Comprados','Produção'):
            rows = [line for line in self.lines if line['kind'] == kind]
            costs = [svc.calculate_cost(line, self.prices.get(line['key']))[0] for line in rows]
            categories.append(f"{kind}: {len(rows)} linhas, {sum((v for v in costs if v is not None), svc.Decimal(0)):.2f} €")
        self.cost_summary.setText(f'Custo conhecido: {total:.2f} € · {pending} linhas pendentes · placas usadas: {board_area:.2f} m² · versão {self.version}\n'
                                 + ' · '.join(categories) + '\n' +
                                 f"Planos incluídos: {', '.join(p['name'] for p in self.plans) or 'nenhum'}\n" + '\n'.join(self.warnings))
        for col, width in enumerate((85, 300, 85, 65, 60, 85, 45, 400, 100, 100, 330)):
            if not self.cost_table.property('layout_ready'):
                self.cost_table.setColumnWidth(col, width)
        self.cost_table.setProperty('layout_ready', True)
        self._filter_costs()

    def _filter_costs(self, *_):
        category = self.category_filter.currentText()
        for i, line in enumerate(self.lines):
            self.cost_table.setRowHidden(i, category != 'Todas' and line['kind'] != category)

    def _associate(self):
        try:
            self._allowed(PERMISSAO_CUSTOS_LISTA_MATERIAL)
            row = self.cost_table.currentRow()
            if row < 0:
                self.status.setText('Selecione uma linha de custo.')
                return
            if self.lines[row]['kind'] == 'Produção':
                catalog = times.machines(self.session)
                labels = ['Selecionar máquina / centro de trabalho…'] + [f"{m['codigo']} — {m['nome']} · {m['custo_hora'] if m['custo_hora'] is not None else 'Por apurar'} €/h" for m in catalog]
                choice, ok = QInputDialog.getItem(self, 'Associar tarifa de produção V3', 'Máquina / centro de trabalho (custo/hora STD):', labels, 0, False)
                if ok and choice in labels[1:]:
                    self.prices[self.lines[row]['key']] = times.machine_price(catalog[labels.index(choice)-1])
                    self._render_costs()
                    self.status.setText('Tarifa associada nesta obra. Guarde a análise para fixar o custo/hora.')
                return
            dialog = AssociarCustoMateriaPrimaDialog(self.lines[row], self.mp_catalog, self.references, self)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected:
                maps.save_mapping(self.session, self.lines[row], dialog.selected, self.user.username)
                self.mappings = maps.load_mappings(self.session)
                self.prices[self.lines[row]['key']] = {**svc.price_record(dialog.selected), 'mapping_source': 'Mapeamento manual guardado no V3'}
                self._render_costs()
                self.status.setText('Correspondência memorizada no V3 para próximas obras. Guarde a análise para fixar o preço desta obra.')
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
            for line in self.lines:
                price = self.prices.get(line['key'])
                if line['kind'] == 'Produção':
                    machine = next((m for m in machine_catalog if m['id'] == (price or {}).get('machine_id')), None)
                    self.prices[line['key']] = times.machine_price(machine) if machine else times.match_machine(line, machine_catalog)
                elif price and price.get('component_id'):
                    self.prices[line['key']] = maps.component_price(line, self.mp_catalog, self.components)
                elif price:
                    self.prices[line['key']] = svc.price_record(by_id[price['id']]) if price['id'] in by_id else None
                else:
                    self.prices[line['key']] = maps.resolve_price(line, self.mp_catalog, self.mappings, self.references, self.components)
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
                report_name = svc.export_cost_report(self.path, self.workbook_hash, self.version, self.lines, self.prices, self.warnings, production=self.production)
                self.workbook_hash = svc.fingerprint(self.path)
            destination = svc.save_snapshot(self.path, {'version': self.version, 'user': self.user.username,
                'workbook_hash': self.workbook_hash, 'plans': self.plans, 'lines': self.lines,
                'prices': self.prices, 'warnings': self.warnings, 'production': self.production, 'complete': False})
            self.status.setText(f'Análise guardada com preços e pendências: {destination.name}' + (f' · Relatório no Excel: {report_name}' if report_name else ''))
        except Exception as exc:
            self._error(exc)
