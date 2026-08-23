"""Import checks for the production page."""

from __future__ import annotations

import inspect
from pathlib import Path


def test_resposta_nao_no_passo_4_abre_o_excel_para_trabalho(
    monkeypatch, tmp_path
) -> None:
    from app.ui.pages import producao_page
    from app.ui.pages.producao_page import ProducaoPage

    workbook_path = tmp_path / "Lista_Material_teste.xlsm"
    workbook_path.touch()
    answers = iter(
        [
            producao_page.QMessageBox.StandardButton.Yes,
            producao_page.QMessageBox.StandardButton.Yes,
            producao_page.QMessageBox.StandardButton.No,
            producao_page.QMessageBox.StandardButton.No,
        ]
    )
    opened_urls: list[str] = []

    monkeypatch.setattr(
        producao_page.QMessageBox,
        "question",
        staticmethod(lambda *_args, **_kwargs: next(answers)),
    )
    monkeypatch.setattr(
        producao_page,
        "execute_import_csv_imos_macro",
        lambda path: path,
    )
    monkeypatch.setattr(
        producao_page,
        "execute_automation_cutrite_macro",
        lambda path: path,
    )
    monkeypatch.setattr(
        producao_page,
        "execute_import_listas_ferragens_macro",
        lambda path: path,
    )
    monkeypatch.setattr(
        producao_page.QDesktopServices,
        "openUrl",
        staticmethod(lambda url: opened_urls.append(url.toLocalFile()) or True),
    )

    class _StatusLabel:
        text = ""

        def setText(self, text: str) -> None:
            self.text = text

    class _Page:
        status_label = _StatusLabel()

        def _rever_lista_material_assistente(self, *_args, **_kwargs):
            raise AssertionError("O assistente não deve abrir quando a resposta é Não.")

    page = _Page()
    ProducaoPage._oferecer_fluxo_inicial_lista_material(
        page,
        object(),
        workbook_path,
    )

    assert [Path(path) for path in opened_urls] == [workbook_path]
    assert "a abrir o Excel" in page.status_label.text


def test_importacao_ferragens_ocorre_antes_do_assistente(monkeypatch, tmp_path) -> None:
    from app.ui.pages import producao_page
    from app.ui.pages.producao_page import ProducaoPage

    workbook_path = tmp_path / "Lista_Material_teste.xlsm"
    workbook_path.touch()
    answers = iter([producao_page.QMessageBox.StandardButton.Yes] * 4)
    events: list[str] = []

    monkeypatch.setattr(
        producao_page.QMessageBox,
        "question",
        staticmethod(lambda *_args, **_kwargs: next(answers)),
    )
    monkeypatch.setattr(
        producao_page,
        "execute_import_csv_imos_macro",
        lambda path: events.append("csv") or path,
    )
    monkeypatch.setattr(
        producao_page,
        "execute_automation_cutrite_macro",
        lambda path: events.append("automation") or path,
    )
    monkeypatch.setattr(
        producao_page,
        "execute_import_listas_ferragens_macro",
        lambda path: events.append("ferragens") or path,
    )

    class _StatusLabel:
        def setText(self, _text: str) -> None:
            pass

    class _Page:
        status_label = _StatusLabel()

        def _rever_lista_material_assistente(self, *_args, **_kwargs):
            events.append("assistente")

    ProducaoPage._oferecer_fluxo_inicial_lista_material(
        _Page(), object(), workbook_path
    )

    assert events == ["csv", "automation", "ferragens", "assistente"]


def test_producao_page_imports_and_headers() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    assert ProducaoPage.TABLE_HEADERS == [
        "Criada em",
        "Ano",
        "Estado",
        "Responsável",
        "Processo",
        "Nº Enc PHC",
        "V. Obra",
        "V. CutRite",
        "Cliente",
        "Ref Cliente",
        "Obra",
        "Data Início",
        "Data Entrega",
        "Qt Artigos",
        "Preço",
        "Descrição Produção",
        "Enc. iMos",
        "Projeto Cliente",
        "Localização",
        "Tipo Pasta",
    ]


def test_gravar_supervisiona_a_passagem_a_producao() -> None:
    """Mudar o estado para Produção passa primeiro pelo supervisor."""
    from app.ui.pages.producao_page import ProducaoPage

    save_source = inspect.getsource(ProducaoPage._save)
    supervisao_source = inspect.getsource(
        ProducaoPage._supervisionar_mudanca_para_producao
    )

    assert "self._supervisionar_mudanca_para_producao(data[\"estado\"])" in save_source
    # O supervisor corre antes de gravar seja o que for.
    assert save_source.index("_supervisionar_mudanca_para_producao") < save_source.index(
        "atualizar_processo"
    )
    assert "entra_em_producao(processo.estado, estado_novo)" in supervisao_source
    assert "supervisionar_para_producao" in supervisao_source
    # Tudo OK não interrompe o trabalho; só há diálogo quando falta alguma coisa.
    assert "if supervisao.pronta:" in supervisao_source
    assert "SupervisaoProducaoDialog" in supervisao_source
    # Cancelar devolve o estado anterior ao formulário e não grava nada.
    assert "self._set_combo_text(self.estado_form_combo, processo.estado)" in supervisao_source


def test_producao_page_init_uses_expected_widgets() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    init_source = inspect.getsource(ProducaoPage.__init__)

    assert "BarraCabecalho" in init_source
    assert "CampoPesquisa" in init_source
    assert "self.table" in init_source
    assert "COLUNAS_PRODUCAO" in inspect.getsource(ProducaoPage)
    # O botão "Colunas" foi substituído pelo menu do botão direito no cabeçalho.
    assert '"Colunas"' not in init_source
    assert "customContextMenuRequested.connect(self._abrir_menu_colunas)" in init_source
    assert "Clique com o botão direito para escolher as colunas visíveis" in init_source
    assert "sectionResized" in init_source
    assert '"⟳ Atualizar dados V2"' in init_source
    assert "self.atualizar_v2_button.clicked.connect(self._atualizar_dados_v2)" in init_source
    assert "self.obras_ano_label" in init_source
    assert "ligar_persistencia_larguras" not in inspect.getsource(ProducaoPage)
    assert '"Atualizar"' in init_source
    assert '"Salvar"' in init_source
    # Botão "Pastas" removido: as pastas abrem no duplo-clique da coluna Processo.
    assert '"Pastas"' not in init_source
    assert "Ver as pastas do processo selecionado no servidor" not in init_source
    # Botão "Abrir pasta" removido: a pasta abre pelo campo "Pasta da obra" e
    # pelo duplo-clique na coluna Processo.
    assert '"Abrir pasta"' not in init_source
    assert "self.open_folder_button" not in init_source
    assert hasattr(ProducaoPage, "_abrir_pasta_versao_selecionada")
    # Cliente em cascata com o filtro de Responsável.
    assert (
        "self.responsavel_combo.currentTextChanged.connect(self._on_responsavel_mudou)"
        in init_source
    )
    assert '"Nova Versão"' in init_source
    assert "Criar nova versão de obra/CUT-RITE do processo selecionado" in init_source
    assert '"Lista Material_IMOS"' in init_source
    assert "self.lista_material_button" in init_source
    assert 'self.lista_material_button.setIcon(icone_ficheiro("icon_excel.ico"))' in init_source
    assert "self.lista_material_button.clicked.connect(self._lista_material_imos)" in init_source
    assert "Gerar o Excel 'Lista Material_IMOS' na pasta do processo" in init_source
    workflow_source = inspect.getsource(
        ProducaoPage._oferecer_fluxo_inicial_lista_material
    )
    assert "execute_import_csv_imos_macro" in workflow_source
    assert "execute_automation_cutrite_macro" in workflow_source
    assert "execute_import_listas_ferragens_macro" in workflow_source
    assert "passo 1 de 4" in workflow_source
    assert "passo 2 de 4" in workflow_source
    assert "passo 3 de 4" in workflow_source
    assert "passo 4 de 4" in workflow_source
    assert "self._rever_lista_material_assistente" in workflow_source
    assert (
        "QDesktopServices.openUrl(QUrl.fromLocalFile(str(workbook_path)))"
        in workflow_source
    )
    assert "a abrir o Excel para continuar o trabalho" in workflow_source
    # Um só botão "CUT-RITE" com preparação, envio e PDF no menu.
    assert '"CUT-RITE"' in init_source
    assert "self.cutrite_button.setMenu(self.cutrite_menu)" in init_source
    assert "self.cutrite_menu.setToolTipsVisible(True)" in init_source
    assert "self.enviar_cutrite_button" not in init_source
    assert "self.exportar_resumo_pdf_button" not in init_source
    assert '"Analisar/Completar Lista Material…", self' in init_source
    assert (
        "self.analisar_lista_material_action.triggered.connect("
        in init_source
    )
    assert "self._analisar_lista_material" in init_source
    assert '"Enviar CUT-RITE", self' in init_source
    assert "self.enviar_cutrite_action.triggered.connect(self._enviar_cutrite)" in init_source
    assert "Criar o plano de corte no CUT-RITE a partir da Lista Material" in init_source
    assert '"Exportar PDF CUT-RITE", self' in init_source
    assert (
        "self.exportar_pdf_cutrite_action.triggered.connect(self._exportar_resumo_pdf)"
        in init_source
    )
    assert (
        "Exportar o plano de corte em PDF e gravar diretamente na pasta da obra"
        in init_source
    )
    review_source = inspect.getsource(ProducaoPage._rever_lista_material_assistente)
    send_source = inspect.getsource(ProducaoPage._enviar_cutrite)
    assert "prepare_workbook_for_assistant" in review_source
    assert "resolve_work_config" in review_source
    assert "ListaMaterialRevisaoDialog" in review_source
    assert "except SQLAlchemyError as learning_error" in review_source
    assert "session.rollback()" in review_source
    assert "As alterações foram aplicadas e guardadas no Excel" in review_source
    assert "if explicit:" in review_source
    assert "QDesktopServices.openUrl" in review_source
    assert "QUrl.fromLocalFile(str(workbook_path))" in review_source
    assert "self._rever_lista_material_assistente" in send_source
    assert '"Eliminar"' in init_source
    assert "Eliminar obra: registo e/ou pasta no servidor" in init_source
    assert "doubleClicked.connect(self._handle_table_double_click)" in init_source
    # Tabela com modelo + proxy: ordenação por cabeçalho e filtragem incremental.
    assert "ProducaoTableModel" in init_source
    assert "ProducaoFilterProxy" in init_source
    assert "self.table.setSortingEnabled(True)" in init_source
    assert "COLUNA_ORDEM_ENTRADA" in init_source
    assert "QTableWidget" not in inspect.getsource(ProducaoPage)
    assert "self.atrasadas_check" in init_source
    assert "self.vista_combo" in init_source
    assert "setToolTip" in init_source
    assert "Gravar as alterações da obra selecionada" in init_source
    assert "Recarregar a lista de obras" in init_source
    assert "Converter Orçamento" in init_source
    assert "Converter um orçamento adjudicado numa obra de produção" in init_source
    assert "Novo Processo" in init_source
    assert "self.novo_processo_button" in init_source
    assert "self.novo_processo_button.clicked.connect(self._novo_processo)" in init_source
    assert "Criar uma obra a partir de uma encomenda do PHC" in init_source
    assert "SelecionarClienteDialog" not in inspect.getsource(ProducaoPage)
    assert "QSplitter" in init_source
    assert (
        'ligar_persistencia_splitter(self.splitter, "producao_detalhe_amplo")'
        in init_source
    )


def test_producao_page_detail_editing_hooks() -> None:
    from app.ui.pages.producao_page import ProducaoPage
    import app.ui.pages.producao_page as producao_page
    import app.ui.helpers.colunas_producao as colunas_producao

    source = inspect.getsource(ProducaoPage)
    module_source = inspect.getsource(producao_page)
    helper_source = inspect.getsource(colunas_producao)

    assert hasattr(ProducaoPage, "_fill_form")
    assert hasattr(ProducaoPage, "_collect_form")
    assert hasattr(ProducaoPage, "_on_select_row")
    assert hasattr(ProducaoPage, "_save")
    assert "app_session" in source
    assert "carregar_config" in source
    assert "guardar_config" in source
    # As colunas sao preferencia PESSOAL: vao para as `user_prefs`, que uma
    # conta normal pode escrever — a `system_settings` esta' trancada por causa
    # das credenciais que guarda.
    assert "UserPrefService" in helper_source
    assert "SystemSettingService" not in helper_source
    assert "selectionChanged.connect(self._on_select_row)" in source
    assert "converter_orcamento" in source
    assert "criar_processo_externo" in source
    assert "NovoProcessoDialog" in source
    assert "listar_processos_por_encomenda" in source
    assert "responsavel=responsavel" in source
    assert "partes_nome[0]" in source
    assert '(current_user.nome or "").split()' in source
    assert "pasta_servidor = processo.pasta_servidor" in source
    assert "QMessageBox.information" in source
    assert "Pasta criada no servidor" in source
    assert "falha ao criar a pasta no servidor" in source
    assert "PastasProcessoDialog" in source
    assert "arvore_pastas_processo" in source
    assert "NovaVersaoProcessoDialog" in source
    assert "preparar_nova_versao" in source
    assert "criar_nova_versao" in source
    assert "prepare_lista_material_imos" in source
    assert "execute_lista_material_imos" in source
    assert "prepare_cutrite_import" in module_source
    assert "execute_cutrite_import" in module_source
    assert "prepare_cutrite_resumo_pdf" in module_source
    assert "execute_cutrite_resumo_pdf" in module_source
    assert "_CutRitePdfWorker" in module_source
    assert "pythoncom.CoInitialize()" in module_source
    assert "QThread" in module_source
    assert "CutRiteProgressDialog" in module_source
    assert hasattr(ProducaoPage, "_enviar_cutrite")
    assert hasattr(ProducaoPage, "_cutrite_concluido")
    assert hasattr(ProducaoPage, "_cutrite_falhou")
    assert hasattr(ProducaoPage, "_finalizar_cutrite")
    assert hasattr(ProducaoPage, "_exportar_resumo_pdf")
    assert hasattr(ProducaoPage, "_resumo_pdf_concluido")
    assert hasattr(ProducaoPage, "_resumo_pdf_falhou")
    assert hasattr(ProducaoPage, "_finalizar_resumo_pdf")
    assert "eliminar_processo_completo" in source
    assert "preview_conteudo_pasta" in source
    assert hasattr(ProducaoPage, "_eliminar_processo")
    assert hasattr(ProducaoPage, "_novo_processo")
    assert hasattr(ProducaoPage, "_tratar_encomenda_existente")
    assert hasattr(ProducaoPage, "_executar_nova_versao")
    assert hasattr(ProducaoPage, "_lista_material_imos")
    assert hasattr(ProducaoPage, "_abrir_pasta_versao_selecionada")
    assert "QApplication.setOverrideCursor" in source
    assert "QApplication.restoreOverrideCursor" in source
    assert "Lista Material IMOS" in source
    assert "Lista Material_IMOS" in source
    assert "context.output_path.exists()" in source
    assert "DATA_CONCLUSAO" in source
    assert "NOME_ENC_IMOS_IX" in source
    assert "QDesktopServices.openUrl" in source
    assert "O Excel da Lista Material da obra" in source
    assert "Pretende abrir?" in source
    assert "QUrl.fromLocalFile(str(context.output_path))" in source
    assert "Substituir?" not in inspect.getsource(ProducaoPage._lista_material_imos)
    assert "Pasta ainda não criada" in source
    assert "nome_plano_corte_input" in source
    assert "nome_enc_imos_ix_input" in source
    assert "gerar_nome_plano_cut_rite" in source
    assert "gerar_nome_enc_imos_ix" in source
    assert "codigo_processo_com_cliente" in source
    assert "_atualizar_campos_derivados" in source
    assert "_selecionar_cliente" not in source
    assert "apenas_phc=True" not in source
    assert "cliente_picker" not in source
    assert "self.cliente_input = self._readonly_line()" in source
    assert "self.cliente_simplex_input = self._readonly_line()" in source
    assert "self.num_cliente_phc_input = self._readonly_line()" in source
    assert "Cliente original do processo (fixo)" in source
    # Datas passam a QDateEdit com calendário (sem o diálogo antigo).
    assert "_abrir_calendario_data" not in source
    assert "QDateEdit" in source
    assert "setCalendarPopup(True)" in source
    assert "Data de início no formato dd-mm-aaaa" in source
    assert "codigo_processo" in source
    assert "icone_ficheiro" in source
    assert '"icon_cut_rite.ico"' in source
    assert '"icon_imos_2025.ico"' in source
    assert 'icone("pasta_abrir")' in source  # icone castanho do tema
    # Ícone e dica da coluna Processo vivem agora no modelo da tabela.
    import app.ui.helpers.modelo_producao as modelo_producao

    modelo_source = inspect.getsource(modelo_producao)
    assert "Data em que a obra foi criada nesta lista" in modelo_source
    assert "DecorationRole" in modelo_source
    assert "Ver pastas do processo" in modelo_source
    assert "normalizar_data" in source
    assert "imagem_path" in source
    # Acessos ao servidor passaram para o worker noutra thread.
    assert "resolver_imagem_imos" not in source
    assert "DetalheObraWorker" in source
    assert "self.detalhe_pedido.emit" in source
    assert hasattr(ProducaoPage, "_on_detalhe_resolvido")
    assert hasattr(ProducaoPage, "_parar_thread_detalhe")
    assert "QStackedWidget" in source
    assert "QTreeView" in source
    assert "QFileSystemModel" in source
    assert "_abrir_item_arvore" in source
    assert "self.imagem_stack.setCurrentWidget(self.imagem_preview)" in source
    assert "self.imagem_stack.setCurrentWidget(self.arvore_pasta)" in source
    import app.ui.helpers.detalhe_obra_worker as detalhe_worker

    worker_source = inspect.getsource(detalhe_worker)
    assert "Sem imagem IMOS (sem pasta da obra)" in worker_source
    assert "resolver_imagem_imos" in worker_source
    assert "caminho_versao_de_processo" in worker_source
    assert "resolver_pasta_orcamento" in worker_source
    # O seletor de imagem MANUAL foi removido (a imagem vem do IMOS). Isto é
    # garantido pelas etiquetas abaixo; o QFileDialog voltou a ser usado, mas
    # agora para o relatório PDF do IA Martelo, não para escolher imagens.
    assert "Escolher Imagem/PDF..." not in source
    assert "Limpar Imagem" not in source
    assert "self._imagem_path" in source
    assert "Estado da obra em produção" in source
    assert "Pasta de destino no servidor" in source
    assert "Há alterações por gravar. Descartar?" in source
    assert producao_page.TIPOS_PASTA_PRODUCAO == (
        "Encomenda de Cliente",
        "Encomenda de Cliente Final",
    )


def test_producao_page_layout_detalhe_e_menu_colunas() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    source = inspect.getsource(ProducaoPage)

    # Colunas via menu do botão direito, guardadas por utilizador.
    assert hasattr(ProducaoPage, "_abrir_menu_colunas")
    assert hasattr(ProducaoPage, "_alternar_coluna")
    assert hasattr(ProducaoPage, "_mostrar_todas_colunas")
    assert hasattr(ProducaoPage, "_repor_colunas_default")
    assert "ColunasProducaoDialog" not in source
    assert "Mostrar todas" in source
    assert "Repor colunas por defeito" in source

    # Textos em 2 linhas x 3 colunas.
    detalhe_source = inspect.getsource(ProducaoPage._criar_painel_detalhe)
    assert "row = (index // 3) * 2" in detalhe_source
    assert "col = index % 3" in detalhe_source

    # Imagem maior e campo com a pasta da obra.
    imagem_source = inspect.getsource(ProducaoPage._criar_painel_imagem)
    assert "setMinimumSize(460, 300)" in imagem_source
    assert "QSizePolicy.Policy.Expanding" in imagem_source

    # Divisor arrastável (e guardado) entre os campos e a imagem.
    assert "self.splitter_detalhe = QSplitter(Qt.Orientation.Horizontal)" in detalhe_source
    assert 'ligar_persistencia_splitter(\n            self.splitter_detalhe, "producao_detalhe_topo"\n        )' in detalhe_source
    assert hasattr(ProducaoPage, "_criar_campo_pasta_obra")
    assert hasattr(ProducaoPage, "_aplicar_detalhe")
    assert "caminho_versao_de_processo" in source
    # Botão "Copiar" removido; o "Abrir" leva o ícone de pasta.
    assert not hasattr(ProducaoPage, "_copiar_caminho_pasta")
    pasta_source = inspect.getsource(ProducaoPage._criar_campo_pasta_obra)
    assert "copiar_pasta_button" not in pasta_source
    assert 'icone("pasta_abrir")' in pasta_source

    # Atalho para a pasta do orçamento nos campos Nº Orçamento / V. Orç.
    assert hasattr(ProducaoPage, "_preparar_link_pasta_orcamento")
    assert hasattr(ProducaoPage, "_definir_link_pasta_orcamento")
    assert hasattr(ProducaoPage, "_abrir_pasta_orcamento")
    assert "QLineEdit.ActionPosition.TrailingPosition" in source

    # Botão temporário de sincronização com o V2.
    assert hasattr(ProducaoPage, "_atualizar_dados_v2")
    assert "comparar_v2_com_v3" in source
    assert "ProducaoV2SyncDialog" in source
    assert "aplicar_selecao" in source

    # Contador de obras do ano atual.
    contador_source = inspect.getsource(ProducaoPage._atualizar_contador_obras_ano)
    assert "QDate.currentDate().year()" in contador_source
    assert "self._combo_valor(self.responsavel_combo)" in contador_source


def test_detalhe_obra_segue_a_ordem_do_mockup() -> None:
    """Os campos do detalhe ficam agrupados por assunto, linha a linha."""
    from app.ui.pages.producao_page import ProducaoPage

    detalhe_source = inspect.getsource(ProducaoPage._criar_painel_detalhe)
    linhas_esperadas = [
        ["Processo", "Nome Plano CUT-RITE", "Nome Enc IMOS IX"],
        ["Cliente", "Cliente simplex", "Nº Cliente PHC"],
        ["Nº Enc PHC", "V. Obra", "V. CutRite", "Ano"],
        ["Nº Orçamento", "V. Orç", "Qt artigos", "Preço total"],
        ["Estado", "Responsável"],
        ["Ref Cliente", "Obra", "Localização"],
        ["Data Início", "Data Entrega", "Tipo Pasta"],
    ]
    etiquetas = [etiqueta for linha in linhas_esperadas for etiqueta in linha]
    posicoes = [detalhe_source.index(f'"{etiqueta}"') for etiqueta in etiquetas]
    assert posicoes == sorted(posicoes), "ordem dos campos do detalhe mudou"

    # Larguras dadas por pesos por linha (e não pela largura natural do campo).
    compactar_source = inspect.getsource(ProducaoPage._compactar_campos_detalhe)
    assert "QSizePolicy.Policy.Ignored" in compactar_source
    # Primeira etiqueta de cada linha alinhada, campos espalhados na altura.
    assert "primeiras_etiquetas" in detalhe_source
    assert "dados_layout.addLayout(linha_layout, 1)" in detalhe_source


def test_filtro_clientes_segue_o_responsavel_escolhido() -> None:
    """O combo de Cliente só lista clientes do responsável filtrado."""
    from types import SimpleNamespace

    from PySide6.QtWidgets import QApplication, QComboBox

    from app.ui.pages.producao_page import ProducaoPage

    QApplication.instance() or QApplication([])

    page = SimpleNamespace()
    page._todos = [
        SimpleNamespace(nome_cliente="ALFA", responsavel="Paulo"),
        SimpleNamespace(nome_cliente="BETA", responsavel="Ana"),
        SimpleNamespace(nome_cliente="GAMA", responsavel="paulo"),
        SimpleNamespace(nome_cliente="", responsavel="Paulo"),
    ]
    page.responsavel_combo = QComboBox()
    page.responsavel_combo.addItems(["Todos", "Paulo", "Ana"])
    page.cliente_combo = QComboBox()
    page._combo_valor = ProducaoPage._combo_valor
    page._valores_distintos = lambda atributo: ProducaoPage._valores_distintos(
        page, atributo
    )
    page._popular_combo = lambda combo, valores: ProducaoPage._popular_combo(
        page, combo, valores
    )

    ProducaoPage._atualizar_filtro_clientes(page)
    todos = [page.cliente_combo.itemText(i) for i in range(page.cliente_combo.count())]
    assert todos == ["Todos", "ALFA", "BETA", "GAMA"]

    page.responsavel_combo.setCurrentText("Paulo")
    ProducaoPage._atualizar_filtro_clientes(page)
    so_paulo = [page.cliente_combo.itemText(i) for i in range(page.cliente_combo.count())]
    assert so_paulo == ["Todos", "ALFA", "GAMA"]
    # BETA já não existe na lista: volta a "Todos" em vez de dar 0 resultados.
    assert page.cliente_combo.currentText() == "Todos"


def test_producao_page_abre_pastas_no_duplo_clique_do_processo() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    double_click_source = inspect.getsource(ProducaoPage._handle_table_double_click)
    open_source = inspect.getsource(ProducaoPage._abrir_pastas_processo)

    assert 'COLUNAS_PRODUCAO[column].key != "processo"' in double_click_source
    assert "self._abrir_pastas_processo(processo)" in double_click_source
    assert "ano=processo.ano" in open_source
    assert "num_enc_phc=processo.num_enc_phc" in open_source
    assert "tipo_pasta=processo.tipo_pasta" in open_source
    assert "dialog.exec()" in open_source


def test_tratar_encomenda_existente_chama_nova_versao_da_mais_recente(monkeypatch) -> None:
    import app.ui.pages.producao_page as page_module
    from app.ui.pages.producao_page import ProducaoPage

    class FakeButton:
        pass

    nova_versao_button = FakeButton()
    chamadas: dict[str, object] = {}

    class FakeMessageBox:
        Icon = page_module.QMessageBox.Icon
        ButtonRole = page_module.QMessageBox.ButtonRole

        def __init__(self, parent=None):
            chamadas["parent"] = parent

        def setIcon(self, icon):
            chamadas["icon"] = icon

        def setWindowTitle(self, title):
            chamadas["title"] = title

        def setText(self, text):
            chamadas["text"] = text

        def setInformativeText(self, text):
            chamadas["informative"] = text

        def addButton(self, text, role):
            chamadas.setdefault("buttons", []).append((text, role))
            if text == "Nova Versão":
                return nova_versao_button
            return FakeButton()

        def exec(self):
            chamadas["exec"] = True

        def clickedButton(self):
            return nova_versao_button

    monkeypatch.setattr(page_module, "QMessageBox", FakeMessageBox)

    page = type("PageStub", (), {})()
    executadas: list[int] = []
    page._executar_nova_versao = lambda *, processo_id: executadas.append(processo_id)

    ProducaoPage._tratar_encomenda_existente(
        page,
        {"ano": "2026", "num_enc_phc": "1134"},
        [
            {
                "id": 1,
                "codigo": "26.1134_01_01_CLIENTE",
                "estado": "Desenho",
                "versao_obra": "01",
                "versao_plano": "01",
                "data_inicio": "25-06-2026",
                "data_entrega": "10-08-2026",
            },
            {
                "id": 2,
                "codigo": "26.1134_02_01_CLIENTE",
                "estado": "Desenho",
                "versao_obra": "02",
                "versao_plano": "01",
                "data_inicio": "25-06-2026",
                "data_entrega": "10-08-2026",
            },
        ],
    )

    assert chamadas["title"] == "Encomenda já existe"
    assert "26.1134_01_01_CLIENTE" in chamadas["informative"]
    assert "Nova Versão" in [text for text, _role in chamadas["buttons"]]
    assert executadas == [2]
